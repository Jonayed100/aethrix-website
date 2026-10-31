from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.forms import ProfileForm
from accounts.models import Profile
from accounts.utils import claim_bookings, client_ip, display_name, hit, home_url_for, is_limited, is_team
from studio.emails import send_booking_emails, send_client_message_email
from studio.models import Booking, OrderMessage, format_bdt

from .forms import ClientMessageForm, NewOrderForm


def client_required(view):
    """Client pages. The founder and admins are sent to their own dashboard instead."""
    @login_required
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if is_team(request.user):
            return redirect(home_url_for(request.user))
        return view(request, *args, **kwargs)
    return wrapper


@client_required
def dashboard(request):
    user = request.user
    profile = Profile.for_user(user)
    if profile.email_verified:
        claim_bookings(user)
    orders = list(user.orders.prefetch_related("messages").order_by("-updated_at"))
    active = [o for o in orders if o.is_open]
    completed = [o for o in orders if o.status == Booking.Status.COMPLETED]
    closed = [o for o in orders if o.status == Booking.Status.DECLINED]
    focus = active[0] if active else (completed[0] if completed else None)
    invested = sum(o.quoted_price_bdt or 0 for o in completed)
    return render(request, "portal/overview.html", {
        "section": "overview",
        "profile": profile,
        "first_name": display_name(user).split()[0],
        "active": active, "completed": completed, "closed": closed, "focus": focus,
        "stats": {"total": len(orders), "active": len(active), "completed": len(completed)},
        "invested": invested, "invested_display": format_bdt(invested) if invested else "৳ 0",
        "tab": request.GET.get("tab", "active"),
    })


@client_required
def new_order(request):
    """Order a new project. Saved to the database as a Booking linked to this client."""
    user, profile = request.user, Profile.for_user(request.user)
    form = NewOrderForm(request.POST or None)
    if request.method == "POST":
        key = f"order-rate:{user.pk}"
        if is_limited(key, settings.BOOKING_RATE_LIMIT):
            messages.error(request, "You've placed several orders in the last hour. Please wait a little, or message us on an existing order.")
        elif form.is_valid():
            hit(key, 60 * 60)
            booking = form.save(commit=False)
            booking.client = user
            booking.name = display_name(user)[:120]
            booking.email = user.email
            booking.phone = profile.phone
            booking.company = profile.company
            booking.ip_address = client_ip(request)
            booking.save()
            send_booking_emails(booking, request)
            messages.success(request, f"Order {booking.reference} placed. Our team has been notified and will contact you within one working day.")
            return redirect("portal:order", reference=booking.reference)
    return render(request, "portal/new_order.html", {"section": "new", "form": form, "profile": profile})


@client_required
def order_detail(request, reference):
    booking = get_object_or_404(Booking, reference=reference, client=request.user)
    form = ClientMessageForm(request.POST or None)
    if request.method == "POST":
        key = f"client-msg:{request.user.pk}"
        if is_limited(key, 20):
            messages.error(request, "You've sent a lot of messages in the last hour. Please wait a little, or email us.")
        elif form.is_valid():
            hit(key, 60 * 60)
            msg = OrderMessage.objects.create(booking=booking, author=request.user, body=form.cleaned_data["body"].strip())
            send_client_message_email(request, booking, msg)
            messages.success(request, "Message sent. We usually reply within one working day.")
            return redirect(reverse("portal:order", args=[reference]) + "#thread")
    return render(request, "portal/order_detail.html", {
        "section": "orders", "b": booking, "thread": booking.messages.select_related("author"), "form": form,
    })


@client_required
def account(request):
    user, profile = request.user, Profile.for_user(request.user)
    action = request.POST.get("action")
    profile_form = ProfileForm(request.POST if action == "profile" else None,
                               initial={"name": user.first_name, "phone": profile.phone, "company": profile.company})
    password_form = PasswordChangeForm(user, request.POST if action == "password" else None)
    if action == "profile" and profile_form.is_valid():
        profile_form.save(user)
        messages.success(request, "Details saved.")
        return redirect("portal:account")
    if action == "password" and password_form.is_valid():
        update_session_auth_hash(request, password_form.save())
        messages.success(request, "Password changed.")
        return redirect("portal:account")
    return render(request, "portal/account.html", {
        "section": "account", "profile": profile, "profile_form": profile_form, "password_form": password_form,
    })
