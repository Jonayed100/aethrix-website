from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import signing
from django.core.cache import cache
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

VERIFY_SALT = "aethrix.verify-email"
VERIFY_MAX_AGE = 60 * 60 * 24 * 7


# --- Requests ------------------------------------------------------------------

def client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return (forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR")) or None


def absolute(request, path):
    from django.conf import settings
    if request is not None:
        return request.build_absolute_uri(path)
    return settings.SITE_URL + path


# --- Simple rate limits (per connection) ------------------------------------------

def is_limited(key, limit):
    return cache.get(key, 0) >= limit


def hit(key, window):
    if cache.add(key, 1, window):
        return
    try:
        cache.incr(key)
    except ValueError:
        cache.set(key, 1, window)


def clear(key):
    cache.delete(key)


# --- Users ---------------------------------------------------------------------

def is_founder(user):
    """The founder: sees everything."""
    return bool(user and user.is_authenticated and user.is_active and user.is_superuser)


def is_team(user):
    """Admins and the founder: can work on orders in the admin dashboard."""
    return bool(user and user.is_authenticated and user.is_active and (user.is_staff or user.is_superuser))


def role_of(user):
    if is_founder(user):
        return "founder"
    if is_team(user):
        return "admin"
    return "client"


def home_url_for(user):
    role = role_of(user)
    if role == "founder":
        return reverse("founder:overview")
    if role == "admin":
        return reverse("adminpanel:overview")
    return reverse("portal:dashboard")


def display_name(user):
    name = (user.first_name or user.get_full_name() or "").strip()
    return name or (user.email.split("@")[0] if user.email else user.username)


def unique_username(email):
    User = get_user_model()
    base = (email or "client").lower()[:140]
    name, n = base, 1
    while User.objects.filter(username__iexact=name).exists():
        n += 1
        name = f"{base}-{n}"
    return name


def claim_bookings(user):
    """Link bookings made with this email (before the account existed) to the account."""
    from studio.models import Booking
    if not user.email:
        return 0
    return Booking.objects.filter(client__isnull=True, email__iexact=user.email).update(client=user)


# --- Links sent by email ----------------------------------------------------------

def make_verify_token(user):
    return signing.dumps({"u": user.pk, "e": user.email.lower()}, salt=VERIFY_SALT)


def read_verify_token(token):
    try:
        data = signing.loads(token, salt=VERIFY_SALT, max_age=VERIFY_MAX_AGE)
    except signing.BadSignature:
        return None
    user = get_user_model().objects.filter(pk=data.get("u")).first()
    if user is None or (user.email or "").lower() != data.get("e"):
        return None
    return user


def set_password_path(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    return reverse("accounts:password_set", args=[uid, default_token_generator.make_token(user)])
