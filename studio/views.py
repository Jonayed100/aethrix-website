import json
import logging

from django.conf import settings
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET, require_POST

from accounts.models import Profile
from accounts.utils import client_ip, hit, is_founder, is_limited

from .emails import send_booking_emails, track_link, track_path
from .forms import BookingForm
from .models import Booking, Project

log = logging.getLogger(__name__)

CATEGORY_INFO = [
    {
        "key": Project.Category.WEBSITE,
        "title": "Websites",
        "blurb": "Business sites, landing pages and online stores.",
        "empty": "Website demos are on the way.",
        "icon": '<svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="14" rx="1"/><path d="M3 8h18M8 21h8"/></svg>',
    },
    {
        "key": Project.Category.APP,
        "title": "Apps",
        "blurb": "Web and mobile apps with logins, bookings and dashboards.",
        "empty": "App demos are on the way.",
        "icon": '<svg viewBox="0 0 24 24"><rect x="7" y="2.5" width="10" height="19" rx="1"/><path d="M11 18.5h2"/></svg>',
    },
    {
        "key": Project.Category.CHATBOT,
        "title": "AI chatbots",
        "blurb": "Assistants that answer from your own documents.",
        "empty": "Chatbot demos are on the way.",
        "icon": '<svg viewBox="0 0 24 24"><path d="M4 5h16v11H9l-5 4z"/><path d="M8 10h8M8 13h5"/></svg>',
    },
]


def _wants_json(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest" or "application/json" in request.headers.get("accept", "")


def _org_json_ld():
    data = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": settings.SITE_NAME,
        "url": settings.SITE_URL,
        "email": settings.CONTACT_EMAIL,
        "founder": {"@type": "Person", "name": settings.FOUNDER_NAME},
        "address": {"@type": "PostalAddress", "addressLocality": "Dhaka", "addressCountry": "BD"},
        "knowsAbout": ["Web development", "Application development", "AI chatbots"],
    }
    return mark_safe(json.dumps(data).replace("<", "\\u003c"))


def _client_account(request):
    user = request.user
    return user if user.is_authenticated and not is_founder(user) else None


def home(request, form=None):
    projects = list(Project.objects.filter(is_published=True))
    categories = []
    for info in CATEGORY_INFO:
        items = [p for p in projects if p.category == info["key"]]
        categories.append({
            **info,
            "icon": mark_safe(info["icon"]),
            "projects": items,
            "live_count": sum(1 for p in items if p.live_url),
        })
    status = 400 if form is not None else 200
    if form is None:
        initial = {}
        client = _client_account(request)
        if client:
            profile = Profile.for_user(client)
            initial = {"name": client.first_name, "email": client.email, "phone": profile.phone, "company": profile.company}
        form = BookingForm(initial=initial)
    context = {"categories": categories, "form": form, "org_json_ld": _org_json_ld()}
    return render(request, "home.html", context, status=status)


@require_POST
def book(request):
    ip = client_ip(request)
    rate_key = f"booking-rate:{ip}"
    if is_limited(rate_key, settings.BOOKING_RATE_LIMIT):
        message = "Too many bookings from this connection. Please try again in an hour, or email us."
        if _wants_json(request):
            return JsonResponse({"ok": False, "errors": {"__all__": [message]}}, status=429)
        return HttpResponse(message, status=429)

    form = BookingForm(request.POST)
    if not form.is_valid():
        if _wants_json(request):
            return JsonResponse({"ok": False, "errors": form.errors.get_json_data()}, status=400)
        return home(request, form=form)

    if form.is_spam():
        # Pretend it worked so bots learn nothing.
        if _wants_json(request):
            return JsonResponse({"ok": True, "reference": "AX-0000-0000", "emailed": False})
        return redirect("studio:home")

    booking = form.save(commit=False)
    booking.ip_address = ip
    booking.client = _client_account(request)
    booking.save()
    hit(rate_key, 60 * 60)

    founder_sent, client_sent = send_booking_emails(booking, request)
    if not founder_sent:
        log.warning("Founder alert for booking %s was not sent; it is saved in the dashboard.", booking.reference)

    request.session["last_booking"] = booking.reference
    thanks_url = reverse("studio:booking_thanks", args=[booking.reference])
    if _wants_json(request):
        return JsonResponse({
            "ok": True,
            "reference": booking.reference,
            "first_name": booking.name.split()[0],
            "emailed": client_sent and settings.EMAIL_PROVIDER != "console",
            "track_url": track_path(booking),
            "track_label": "Track it in your dashboard" if booking.client_id else "Create an account to track it",
            "redirect": thanks_url,
        })
    return redirect(thanks_url)


def booking_thanks(request, reference):
    if request.session.get("last_booking") != reference:
        raise Http404
    booking = get_object_or_404(Booking, reference=reference)
    return render(request, "booking_thanks.html", {
        "booking": booking,
        "track_url": track_link(request, booking),
        "track_label": "Track it in your dashboard" if booking.client_id else "Create an account to track it",
    })


@require_GET
@cache_control(max_age=86400)
def robots_txt(request):
    lines = [
        "User-agent: *",
        "Disallow: /book/",
        "Disallow: /dashboard/",
        f"Sitemap: {settings.SITE_URL}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain")


def health(request):
    return HttpResponse("ok", content_type="text/plain")


def not_found(request, exception):
    return render(request, "404.html", status=404)
