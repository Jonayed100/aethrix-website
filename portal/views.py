from functools import wraps

from django import forms
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.forms import ProfileForm
from accounts.models import Profile
from accounts.utils import claim_bookings, display_name, hit, is_founder, is_limited
from studio.emails import send_client_message_email
from studio.models import Booking, OrderMessage, format_bdt


class ClientMessageForm(forms.Form):
    body = forms.CharField(label="Message", max_length=4000,
                           widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Ask a question, or share links, feedback or changes."}))


def client_required(view):
    @login_required
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if is_founder(request.user):
            return redirect("founder:overview")
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
        "section": "orders", "b": booking, "thread": booking.messages.all(), "form": form,
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
