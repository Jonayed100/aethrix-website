import csv
from collections import Counter
from datetime import date, datetime
from functools import wraps

from django.conf import settings
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
from accounts.utils import absolute, claim_bookings, display_name, is_founder, set_password_path, unique_username
from studio.emails import send_founder_message_email, send_invite_email, send_order_update_email
from studio.models import Booking, OrderMessage, Project, format_bdt

from .forms import FounderMessageForm, OrderForm, ProjectForm

S = Booking.Status


def founder_required(view):
    """Only the founder gets in. Anyone else signed in sees a 404, as if the page didn't exist."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{reverse('founder:login')}?next={request.get_full_path()}")
        if not is_founder(request.user):
            raise Http404
        return view(request, *args, **kwargs)
    return wrapper


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


@founder_required
def overview(request):
    qs = Booking.objects.all()
    counts = dict(qs.values_list("status").annotate(n=Count("id")).values_list("status", "n"))
    open_orders = list(qs.filter(status__in=Booking.ACTIVE_STATUSES).only("quoted_price_bdt", "budget_bdt"))
    pipeline = sum(b.value_bdt for b in open_orders)
    earned = sum(qs.filter(status=S.COMPLETED).exclude(quoted_price_bdt=None).values_list("quoted_price_bdt", flat=True))
    series = _month_series()
    total = sum(counts.values())
    strip = []
    for key, label in S.choices:
        n = counts.get(key, 0)
        strip.append({"key": key, "label": label, "count": n, "pct": round(n / total * 100, 1) if total else 0})
    context = {
        "section": "overview",
        "greeting": _greeting(),
        "founder_first": display_name(request.user).split()[0],
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
        "inbox": OrderMessage.objects.filter(from_founder=False, is_event=False).select_related("booking").order_by("-created_at")[:5],
        "client_count": get_user_model().objects.filter(is_superuser=False).count(),
    }
    return render(request, "founder/overview.html", context)


ORDER_FILTERS = {
    "all": ("All", None),
    "new": ("New", [S.NEW]),
    "active": ("Active", Booking.WORKING_STATUSES),
    "completed": ("Completed", [S.COMPLETED]),
    "declined": ("Declined", [S.DECLINED]),
}


def _filtered_orders(request):
    key = request.GET.get("status", "all")
    if key not in ORDER_FILTERS:
        key = "all"
    qs = Booking.objects.select_related("client")
    statuses = ORDER_FILTERS[key][1]
    if statuses:
        qs = qs.filter(status__in=statuses)
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(reference__icontains=q) | Q(name__icontains=q) | Q(email__icontains=q)
                       | Q(company__icontains=q) | Q(title__icontains=q))
    return key, q, qs


@founder_required
def orders(request):
    key, q, qs = _filtered_orders(request)
    counts = dict(Booking.objects.values_list("status").annotate(n=Count("id")).values_list("status", "n"))
    tabs = []
    for k, (label, statuses) in ORDER_FILTERS.items():
        n = sum(counts.values()) if statuses is None else sum(counts.get(s, 0) for s in statuses)
        tabs.append({"key": k, "label": label, "count": n})
    page = Paginator(qs, 20).get_page(request.GET.get("page"))
    return render(request, "founder/orders.html", {"section": "orders", "tabs": tabs, "active_tab": key, "q": q, "page": page})


@founder_required
def orders_csv(request):
    _, _, qs = _filtered_orders(request)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="aethrix-orders.csv"'
    response.write("﻿")
    writer = csv.writer(response)
    writer.writerow(["Reference", "Received", "Status", "Project", "Name", "Email", "Phone", "Company", "Services",
                     "Budget (BDT)", "Quote (BDT)", "Progress %", "Due date", "Delivery link", "Description"])
    for b in qs:
        writer.writerow([b.reference, timezone.localtime(b.created_at).strftime("%Y-%m-%d %H:%M"), b.get_status_display(),
                         b.title, b.name, b.email, b.phone, b.company, b.services_display, b.budget_bdt,
                         b.quoted_price_bdt or "", b.progress, b.due_date or "", b.delivery_url, b.description])
    return response


@founder_required
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
                messages.warning(request, "Saved, but the email to the client didn't go out. Check your email settings.")
        else:
            messages.success(request, "Order saved." if old_status == booking.status else f"Order saved. Status is now {booking.get_status_display()}.")
        return redirect("founder:order", reference=booking.reference)
    thread = booking.messages.select_related("author").all()
    account = booking.client or get_user_model().objects.filter(email__iexact=booking.email).first()
    return render(request, "founder/order_detail.html", {
        "section": "orders", "b": booking, "form": form, "message_form": FounderMessageForm(prefix="m"),
        "thread": thread, "account": account,
        "account_ready": bool(account and account.has_usable_password()),
    })


@founder_required
@require_POST
def order_message(request, reference):
    booking = get_object_or_404(Booking, reference=reference)
    form = FounderMessageForm(request.POST, prefix="m")
    if form.is_valid():
        msg = OrderMessage.objects.create(booking=booking, author=request.user, from_founder=True, body=form.cleaned_data["body"].strip())
        if form.cleaned_data["notify"]:
            sent = send_founder_message_email(request, booking, msg)
            messages.success(request, "Message posted and emailed to the client." if sent else "Message posted. The email didn't go out.")
        else:
            messages.success(request, "Message posted to the client's dashboard.")
    else:
        messages.error(request, "Write a message first.")
    return redirect(reverse("founder:order", args=[reference]) + "#thread")


@founder_required
@require_POST
def order_invite(request, reference):
    """Give the client a dashboard login for this order (creates the account if needed)."""
    booking = get_object_or_404(Booking, reference=reference)
    User = get_user_model()
    user = booking.client or User.objects.filter(email__iexact=booking.email).first()
    if user and is_founder(user):
        messages.error(request, "That email belongs to the founder account.")
        return redirect("founder:order", reference=reference)
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
        messages.warning(request, "The account is linked, but the email didn't go out. Check your email settings.")
    return redirect("founder:order", reference=reference)


# --- Demo projects ---------------------------------------------------------------

@founder_required
def projects(request):
    items = Project.objects.all()
    return render(request, "founder/projects.html", {"section": "projects", "items": items})


@founder_required
def project_edit(request, pk=None):
    project = get_object_or_404(Project, pk=pk) if pk else None
    form = ProjectForm(request.POST or None, instance=project)
    if request.method == "POST" and form.is_valid():
        saved = form.save()
        messages.success(request, f"'{saved.title}' saved." + (" It's live on the website." if saved.is_published else " It's hidden from the website."))
        return redirect("founder:projects")
    return render(request, "founder/project_form.html", {"section": "projects", "form": form, "project": project})


@founder_required
def project_delete(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.method == "POST":
        title = project.title
        project.delete()
        messages.success(request, f"'{title}' deleted.")
        return redirect("founder:projects")
    return render(request, "founder/project_delete.html", {"section": "projects", "project": project})


@founder_required
@require_POST
def project_toggle(request, pk):
    project = get_object_or_404(Project, pk=pk)
    project.is_published = not project.is_published
    project.save(update_fields=["is_published", "updated_at"])
    messages.success(request, f"'{project.title}' is now {'live' if project.is_published else 'hidden'}.")
    return redirect("founder:projects")


# --- Clients and account -----------------------------------------------------------

@founder_required
def clients(request):
    q = request.GET.get("q", "").strip()
    qs = get_user_model().objects.filter(is_superuser=False).select_related("profile").annotate(
        total=Count("orders", distinct=True),
        open=Count("orders", filter=Q(orders__status__in=Booking.ACTIVE_STATUSES), distinct=True),
        done=Count("orders", filter=Q(orders__status=S.COMPLETED), distinct=True),
    ).order_by("-date_joined")
    if q:
        qs = qs.filter(Q(email__icontains=q) | Q(first_name__icontains=q) | Q(profile__company__icontains=q))
    page = Paginator(qs, 25).get_page(request.GET.get("page"))
    return render(request, "founder/clients.html", {"section": "clients", "page": page, "q": q})


@founder_required
def account(request):
    form = PasswordChangeForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, "Password changed.")
        return redirect("founder:account")
    return render(request, "founder/account.html", {
        "section": "account", "form": form,
        "founder_path": "/" + settings.FOUNDER_URL, "admin_path": "/" + settings.ADMIN_URL,
    })
