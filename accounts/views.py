from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from studio.emails import send_verification_email

from .forms import AethrixPasswordResetForm, LoginForm, SignupForm
from .models import Profile
from .utils import (claim_bookings, clear, client_ip, hit, home_url_for, is_founder, is_limited, is_team,
                    read_verify_token)

LOGIN_LIMIT, LOGIN_WINDOW = 8, 15 * 60
BACKEND = "accounts.backends.EmailBackend"


def _next_url(request, default):
    target = request.POST.get("next") or request.GET.get("next")
    if target and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return target
    return default


def _login(request, template, allow=None, landing=None, extra=None):
    """Shared sign-in. `allow` limits who may sign in here; `landing` is where they go after."""
    form = LoginForm(request, data=request.POST or None)
    key = f"login:{client_ip(request)}"
    error = None
    if request.method == "POST":
        if is_limited(key, LOGIN_LIMIT):
            error = "Too many tries. Please wait 15 minutes and try again."
        elif form.is_valid() and (allow is None or allow(form.user)):
            clear(key)
            auth_login(request, form.user, backend=BACKEND)
            if landing:
                return redirect(landing)
            return redirect(_next_url(request, home_url_for(form.user)))
        else:
            hit(key, LOGIN_WINDOW)
            if not form.errors:
                error = LoginForm.error_messages["invalid"]
    context = {"form": form, "error": error, "next": request.GET.get("next", "")}
    context.update(extra or {})
    return render(request, template, context)


def login_view(request):
    if request.user.is_authenticated:
        return redirect(home_url_for(request.user))
    return _login(request, "accounts/login.html")


def founder_login_view(request):
    if request.user.is_authenticated:
        if is_founder(request.user):
            return redirect("founder:overview")
        raise Http404
    return _login(request, "accounts/founder_login.html", allow=is_founder, landing=reverse("founder:overview"),
                  extra={"console": "Founder"})


def admin_login_view(request):
    if request.user.is_authenticated:
        if is_team(request.user):
            return redirect("adminpanel:overview")
        raise Http404
    return _login(request, "accounts/founder_login.html", allow=is_team, landing=reverse("adminpanel:overview"),
                  extra={"console": "Admin"})


@require_POST
def logout_view(request):
    auth_logout(request)
    return redirect("studio:home")


def signup_view(request):
    if request.user.is_authenticated:
        return redirect(home_url_for(request.user))
    initial = {"email": request.GET.get("email", ""), "name": request.GET.get("name", "")}
    form = SignupForm(request.POST or None, initial=initial)
    error = None
    if request.method == "POST":
        key = f"signup:{client_ip(request)}"
        if is_limited(key, 6):
            error = "Too many new accounts from this connection. Please try again in an hour."
        elif form.is_valid():
            hit(key, 60 * 60)
            user = form.save()
            auth_login(request, user, backend=BACKEND)
            send_verification_email(request, user)
            messages.success(request, f"Welcome, {user.first_name.split()[0] if user.first_name else 'there'}! Your client dashboard is ready. Order your first project below.")
            return redirect("portal:dashboard")
    return render(request, "accounts/signup.html", {"form": form, "error": error})


def verify_email(request, token):
    user = read_verify_token(token)
    if user is None:
        return render(request, "accounts/verify.html", {"ok": False}, status=400)
    profile = Profile.for_user(user)
    if not profile.email_verified:
        profile.email_verified = True
        profile.save(update_fields=["email_verified"])
    claimed = claim_bookings(user)
    return render(request, "accounts/verify.html", {"ok": True, "claimed": claimed, "verified": user})


@login_required
@require_POST
def resend_verification(request):
    key = f"verify:{request.user.pk}"
    if is_limited(key, 3):
        messages.error(request, "We already sent a few links. Check your spam folder, or try again in an hour.")
    else:
        hit(key, 60 * 60)
        if send_verification_email(request, request.user):
            messages.success(request, f"Verification link sent to {request.user.email}.")
        else:
            messages.error(request, "We couldn't send the email right now. Please try again later.")
    return redirect(_next_url(request, home_url_for(request.user)))


class ForgotPasswordView(auth_views.PasswordResetView):
    form_class = AethrixPasswordResetForm
    template_name = "accounts/password_forgot.html"
    email_template_name = "emails/password_reset.txt"
    html_email_template_name = "emails/password_reset.html"
    subject_template_name = "emails/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:password_forgot_sent")

    extra_email_context = {"site_name": settings.SITE_NAME, "contact_email": settings.CONTACT_EMAIL,
                           "site_url": settings.SITE_URL, "founder_name": settings.FOUNDER_NAME}

    def form_valid(self, form):
        key = f"reset:{client_ip(self.request)}"
        if is_limited(key, 5):
            return redirect(self.success_url)
        hit(key, 60 * 60)
        return super().form_valid(form)


class ForgotPasswordSentView(auth_views.PasswordResetDoneView):
    template_name = "accounts/password_forgot_sent.html"


class SetPasswordView(auth_views.PasswordResetConfirmView):
    """Used by 'forgot password' links and by client invites. Logs the person in afterwards."""

    template_name = "accounts/password_set.html"
    post_reset_login = True
    post_reset_login_backend = BACKEND
    success_url = reverse_lazy("portal:dashboard")

    def form_valid(self, form):
        response = super().form_valid(form)
        user = form.user
        profile = Profile.for_user(user)
        if not profile.email_verified:
            profile.email_verified = True
            profile.save(update_fields=["email_verified"])
        claim_bookings(user)
        messages.success(self.request, "Your password is set. You're signed in.")
        if is_founder(user):
            return redirect(reverse("founder:overview"))
        return response
