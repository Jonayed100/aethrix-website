"""The two private dashboards.

Founder dashboard (FOUNDER_URL)      founder only: everything.
Admin dashboard (ADMIN_PANEL_URL)    admins + founder: orders, updates, messages.

Shared pages (overview, orders, order detail, account) are the same views; the
URL namespace ("founder" or "adminpanel") decides which dashboard they belong to.
Anyone else who opens these addresses gets "page not found".
"""
import csv
from collections import Counter
from datetime import date, datetime
from functools import wraps
from urllib.parse import quote

from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import Profile
from accounts.utils import (absolute, claim_bookings, display_name, is_founder, is_team, set_password_path,
                            unique_username)
from studio.emails import send_founder_message_email, send_invite_email, send_order_update_email
from studio.models import Booking, OrderMessage, Project, format_bdt

from .forms import AdminCreateForm, FounderMessageForm, OrderForm, ProjectForm

S = Booking.Status
User = get_user_model()
CONSOLES = ("founder", "adminpanel")


# --- Access -------------------------------------------------------------------------

def _console(founder_only=False):
    def decorate(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            ns = request.resolver_match.namespace if request.resolver_match else "founder"
            if founder_only or ns not in CONSOLES:
                ns = "founder"
            if not request.user.is_authenticated:
                return redirect(f"{reverse(ns + ':login')}?next={quote(request.get_full_path())}")
            allowed = is_founder(request.user) if ns == "founder" else is_team(request.user)
            if not allowed:
                raise Http404
            request.ns = ns
            return view(request, *args, **kwargs)
        return wrapper
    return decorate


team_view = _console()                     # founder dashboard: founder; admin dashboard: admins + founder
founder_view = _console(founder_only=True)  # founder dashboard only


def _url(request, name, *args):
    return reverse(f"{request.ns}:{name}", args=args)


# --- Overview -----------------------------------------------------------------------

def _month_series(months=6):
    today = timezone.localdate()
    keys = []
    for back in range(months - 1, -1, -1):
        y, m = today.year, today.month - back
        while m <= 0:
            m += 12
            y -= 1
        keys.append((y, m))
    start = timezone.make_aware(datetime(keys[0][0], keys[0][1], 1))
    counts = Counter()
    for created in Booking.objects.filter(created_at__gte=start).values_list("created_at", flat=True):
        local = timezone.localtime(created)
        counts[(local.year, local.month)] += 1
    top = max([counts[k] for k in keys] + [1])
    return [{
        "label": date(y, m, 1).strftime("%b"),
        "full": date(y, m, 1).strftime("%B %Y"),
        "value": counts[(y, m)],
        "pct": round(counts[(y, m)] / top * 100),
        "current": (y, m) == (today.year, today.month),
    } for y, m in keys]


def _greeting():
    hour = timezone.localtime().hour
    return "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"


@team_view
def overview(request):
    qs = Booking.objects.all()
    counts = dict(qs.values_list("status").annotate(n=Count("id")).values_list("status", "n"))
    open_orders = list(qs.filter(status__in=Booking.ACTIVE_STATUSES).only("quoted_price_bdt", "budget_bdt"))
    pipeline = sum(b.value_bdt for b in open_orders)
    earned = sum(qs.filter(status=S.COMPLETED).exclude(quoted_price_bdt=None).values_list("quoted_price_bdt", flat=True))
    series = _month_series()
    total = sum(counts.values())
    strip = [{"key": k, "label": label, "count": counts.get(k, 0)} for k, label in S.choices]
    context = {
        "section": "overview",
        "show_money": request.ns == "founder",
        "greeting": _greeting(),
        "first_name": display_name(request.user).split()[0],
        "today": timezone.localdate(),
        "stats": {
            "new": counts.get(S.NEW, 0),
            "active": sum(counts.get(k, 0) for k in Booking.WORKING_STATUSES),
            "completed": counts.get(S.COMPLETED, 0),
            "total": total,
        },
        "pipeline": pipeline,
        "pipeline_display": format_bdt(pipeline),
        "earned_display": format_bdt(earned),
        "series": series,
        "series_total": sum(m["value"] for m in series),
        "this_month": series[-1]["value"],
        "last_month": series[-2]["value"],
        "strip": strip,
        "recent": qs.select_related("client")[:6],
        "inbox": OrderMessage.objects.filter(from_founder=False, is_event=False)
                 .select_related("booking").order_by("-created_at")[:5],
        "client_count": User.objects.filter(is_staff=False, is_superuser=False).count(),
        "team_count": User.objects.filter(is_staff=True, is_superuser=False, is_active=True).count(),
    }
    return render(request, "founder/overview.html", context)


# --- Orders -------------------------------------------------------------------------

ORDER_TABS = {
    "all": ("All", None),
    "incoming": ("Incoming", [S.NEW]),
    "pending": ("Pending", Booking.WORKING_STATUSES),
    "completed": ("Completed", [S.COMPLETED]),
    "declined": ("Declined", [S.DECLINED]),
}


def _filtered_orders(request):
    key = request.GET.get("status", "all")
    if key not in ORDER_TABS:
        key = "all"
    qs = Booking.objects.select_related("client")
    statuses = ORDER_TABS[key][1]
    if statuses:
        qs = qs.filter(status__in=statuses)
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(reference__icontains=q) | Q(name__icontains=q) | Q(email__icontains=q)
                       | Q(company__icontains=q) | Q(title__icontains=q))
    return key, q, qs


@team_view
def orders(request):
    key, q, qs = _filtered_orders(request)
    counts = dict(Booking.objects.values_list("status").annotate(n=Count("id")).values_list("status", "n"))
    tabs = []
    for k, (label, statuses) in ORDER_TABS.items():
        n = sum(counts.values()) if statuses is None else sum(counts.get(s, 0) for s in statuses)
        tabs.append({"key": k, "label": label, "count": n})
    page = Paginator(qs, 20).get_page(request.GET.get("page"))
    return render(request, "founder/orders.html", {"section": "orders", "tabs": tabs, "active_tab": key, "q": q, "page": page})


@founder_view
def orders_csv(request):
    _, _, qs = _filtered_orders(request)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="aethrix-orders.csv"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(["Reference", "Received", "Status", "Project", "Name", "Email", "Phone", "Company", "Services",
                     "Budget (BDT)", "Quote (BDT)", "Progress %", "Due date", "Delivery link", "Description"])
    for b in qs:
        writer.writerow([b.reference, timezone.localtime(b.created_at).strftime("%Y-%m-%d %H:%M"), b.get_status_display(),
                         b.title, b.name, b.email, b.phone, b.company, b.services_display, b.budget_bdt,
                         b.quoted_price_bdt or "", b.progress, b.due_date or "", b.delivery_url, b.description])
    return response


@team_view
def order_detail(request, reference):
    booking = get_object_or_404(Booking.objects.select_related("client"), reference=reference)
    form = OrderForm(request.POST or None, instance=booking, prefix="o")
    if request.method == "POST" and form.is_valid():
        old_status = Booking.objects.values_list("status", flat=True).get(pk=booking.pk)
        booking = form.save()
        changes = form.client_changes()
        note = form.cleaned_data.get("note", "").strip()
        if changes:
            summary = " · ".join(f"{label}: {value}" for label, value in changes)
            OrderMessage.objects.create(booking=booking, author=request.user, from_founder=True, is_event=True, body=summary)
        if note:
            OrderMessage.objects.create(booking=booking, author=request.user, from_founder=True, body=note)
        if form.cleaned_data.get("notify_client") and (changes or note):
            if send_order_update_email(request, booking, changes, note):
                messages.success(request, f"Saved and emailed {booking.email}.")
            else:
                messages.warning(request, "Saved. The client sees the update in their dashboard, but the email didn't go out.")
        else:
            messages.success(request, "Order saved." if old_status == booking.status else f"Order saved. Status is now {booking.get_status_display()}.")
        return redirect(_url(request, "order", booking.reference))
    account = booking.client or User.objects.filter(email__iexact=booking.email).first()
    return render(request, "founder/order_detail.html", {
        "section": "orders", "b": booking, "form": form, "message_form": FounderMessageForm(prefix="m"),
        "thread": booking.messages.select_related("author").all(), "account": account,
        "account_ready": bool(account and account.has_usable_password()),
    })


@team_view
@require_POST
def order_message(request, reference):
    booking = get_object_or_404(Booking, reference=reference)
    form = FounderMessageForm(request.POST, prefix="m")
    if form.is_valid():
        msg = OrderMessage.objects.create(booking=booking, author=request.user, from_founder=True, body=form.cleaned_data["body"].strip())
        if form.cleaned_data["notify"]:
            sent = send_founder_message_email(request, booking, msg)
            messages.success(request, "Message posted and emailed to the client." if sent else "Message posted to the client's dashboard. The email didn't go out.")
        else:
            messages.success(request, "Message posted to the client's dashboard.")
    else:
        messages.error(request, "Write a message first.")
    return redirect(_url(request, "order", reference) + "#thread")


@team_view
@require_POST
def order_invite(request, reference):
    """Give the client a dashboard login for this order (creates the account if needed)."""
    booking = get_object_or_404(Booking, reference=reference)
    user = booking.client or User.objects.filter(email__iexact=booking.email).first()
    if user and is_team(user):
        messages.error(request, "That email belongs to a team account.")
        return redirect(_url(request, "order", reference))
    if user is None:
        user = User(username=unique_username(booking.email), email=booking.email.lower(), first_name=booking.name[:150])
        user.set_unusable_password()
        user.save()
        Profile.objects.create(user=user, phone=booking.phone, company=booking.company)
    booking.client = user
    booking.save(update_fields=["client", "updated_at"])
    claim_bookings(user)
    link = None if user.has_usable_password() else absolute(request, set_password_path(user))
    if send_invite_email(request, user, booking, link):
        messages.success(request, f"Dashboard access sent to {user.email}.")
    else:
        messages.warning(request, "The order is linked to the client's account, but the email didn't go out.")
    return redirect(_url(request, "order", reference))


@team_view
def account(request):
    form = PasswordChangeForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        update_session_auth_hash(request, form.save())
        messages.success(request, "Password changed.")
        return redirect(_url(request, "account"))
    from django.conf import settings
    return render(request, "founder/account.html", {
        "section": "account", "form": form,
        "founder_path": "/" + settings.FOUNDER_URL, "panel_path": "/" + settings.ADMIN_PANEL_URL,
        "admin_path": "/" + settings.ADMIN_URL,
    })


# --- Founder only: demo projects -----------------------------------------------------

@founder_view
def projects(request):
    return render(request, "founder/projects.html", {"section": "projects", "items": Project.objects.all()})


@founder_view
def project_edit(request, pk=None):
    project = get_object_or_404(Project, pk=pk) if pk else None
    form = ProjectForm(request.POST or None, instance=project)
    if request.method == "POST" and form.is_valid():
        saved = form.save()
        messages.success(request, f"'{saved.title}' saved." + (" It's live on the website." if saved.is_published else " It's hidden from the website."))
        return redirect("founder:projects")
    return render(request, "founder/project_form.html", {"section": "projects", "form": form, "project": project})


@founder_view
def project_delete(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.method == "POST":
        title = project.title
        project.delete()
        messages.success(request, f"'{title}' deleted.")
        return redirect("founder:projects")
    return render(request, "founder/project_delete.html", {"section": "projects", "project": project})


@founder_view
@require_POST
def project_toggle(request, pk):
    project = get_object_or_404(Project, pk=pk)
    project.is_published = not project.is_published
    project.save(update_fields=["is_published", "updated_at"])
    messages.success(request, f"'{project.title}' is now {'live' if project.is_published else 'hidden'}.")
    return redirect("founder:projects")


# --- Founder only: clients ------------------------------------------------------------

@founder_view
def clients(request):
    q = request.GET.get("q", "").strip()
    qs = User.objects.filter(is_superuser=False, is_staff=False).select_related("profile").annotate(
        total=Count("orders", distinct=True),
        open=Count("orders", filter=Q(orders__status__in=Booking.ACTIVE_STATUSES), distinct=True),
        done=Count("orders", filter=Q(orders__status=S.COMPLETED), distinct=True),
    ).order_by("-date_joined")
    if q:
        qs = qs.filter(Q(email__icontains=q) | Q(first_name__icontains=q) | Q(profile__company__icontains=q)
                       | Q(profile__phone__icontains=q))
    page = Paginator(qs, 25).get_page(request.GET.get("page"))
    return render(request, "founder/clients.html", {"section": "clients", "page": page, "q": q})


@founder_view
def client_detail(request, pk):
    """See a client's dashboard exactly as they see it."""
    client = get_object_or_404(User, pk=pk, is_superuser=False, is_staff=False)
    profile = Profile.for_user(client)
    orders_list = list(client.orders.order_by("-updated_at"))
    active = [o for o in orders_list if o.is_open]
    completed = [o for o in orders_list if o.status == S.COMPLETED]
    closed = [o for o in orders_list if o.status == S.DECLINED]
    invested = sum(o.quoted_price_bdt or 0 for o in completed)
    return render(request, "founder/client_detail.html", {
        "section": "clients", "client": client, "profile": profile,
        "first_name": display_name(client).split()[0],
        "active": active, "completed": completed, "closed": closed,
        "focus": active[0] if active else (completed[0] if completed else None),
        "stats": {"total": len(orders_list), "active": len(active), "completed": len(completed)},
        "invested": invested, "invested_display": format_bdt(invested) if invested else "৳ 0",
        "tab": request.GET.get("tab", "active"), "as_founder": True,
    })


# --- Founder only: team (admins) -----------------------------------------------------

@founder_view
def team(request):
    form = AdminCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        admin = form.save()
        messages.success(request, f"{admin.first_name} can now sign in to the admin dashboard with {admin.email}.")
        return redirect("founder:team")
    from django.conf import settings
    members = User.objects.filter(is_staff=True, is_superuser=False).select_related("profile").annotate(
        updates=Count("ordermessage", filter=Q(ordermessage__from_founder=True), distinct=True),
    ).order_by("-is_active", "first_name")
    return render(request, "founder/team.html", {
        "section": "team", "form": form, "members": members,
        "panel_login": absolute(request, reverse("adminpanel:login")),
        "panel_path": "/" + settings.ADMIN_PANEL_URL,
    })


@founder_view
@require_POST
def team_toggle(request, pk):
    member = get_object_or_404(User, pk=pk, is_staff=True, is_superuser=False)
    member.is_active = not member.is_active
    member.save(update_fields=["is_active"])
    messages.success(request, f"{display_name(member)} is now {'active' if member.is_active else 'blocked from signing in'}.")
    return redirect("founder:team")
