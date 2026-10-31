"""Every email the website sends. All go through Django's mail system,
so the Brevo backend (live) or the terminal (local) handles delivery."""
import logging
from urllib.parse import urlencode

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse

from accounts.utils import absolute, display_name

log = logging.getLogger(__name__)


def _send(to, subject, context, html=True, reply_to=None):
    ctx = {
        "site_name": settings.SITE_NAME,
        "site_url": settings.SITE_URL,
        "contact_email": settings.CONTACT_EMAIL,
        "founder_name": settings.FOUNDER_NAME,
        **context,
    }
    text = render_to_string("emails/layout.txt", ctx)
    message = EmailMultiAlternatives(subject, text, settings.DEFAULT_FROM_EMAIL, [to],
                                     reply_to=[reply_to] if reply_to else None)
    if html:
        message.attach_alternative(render_to_string("emails/layout.html", ctx), "text/html")
    try:
        return message.send() == 1
    except Exception as exc:  # never break a page because an email failed
        log.warning("Email to %s failed: %s", to, exc)
        return False


def _order_rows(b):
    rows = [("Reference", b.reference), ("Needs", b.services_display), ("Budget", b.budget_display),
            ("Timeline", b.get_timeline_display()), ("Preferred call", b.call_display)]
    return rows


def track_path(booking):
    """Where a client follows their order: the dashboard, or sign-up with their email filled in."""
    if booking.client_id:
        return reverse("portal:order", args=[booking.reference])
    return reverse("accounts:signup") + "?" + urlencode({"email": booking.email, "name": booking.name})


def track_link(request, booking):
    return absolute(request, track_path(booking))


def send_booking_emails(booking, request=None):
    """Alert to Project Aethrix + confirmation to the client. Returns (founder_sent, client_sent)."""
    b = booking
    founder_rows = [("Reference", b.reference), ("Name", b.name), ("Email", b.email),
                    ("Phone/WhatsApp", b.phone or "-"), ("Company", b.company or "-"),
                    ("Needs", b.services_display), ("Budget", b.budget_display),
                    ("Timeline", b.get_timeline_display()), ("Preferred call", b.call_display),
                    ("Client account", "Linked" if b.client_id else "Not yet")]
    founder_sent = _send(
        settings.BOOKING_NOTIFY_EMAIL,
        f"New booking {b.reference}: {b.services_display} ({b.name})",
        {"heading": "New project booking", "intro": "Reply to this email to answer the client directly.",
         "rows": founder_rows, "quote_title": "About the work", "quote": b.description,
         "button_label": "Open in founder dashboard",
         "button_url": absolute(request, reverse("founder:order", args=[b.reference]))},
        html=False, reply_to=b.email,
    )
    first = b.name.split()[0] if b.name.split() else b.name
    client_sent = _send(
        b.email,
        f"We received your booking · {b.reference}",
        {"heading": f"Booking received, {first}.",
         "intro": "Thanks for booking with Project Aethrix. We will contact you within one working day to confirm your call.",
         "rows": _order_rows(b), "quote_title": "What you told us", "quote": b.description,
         "button_label": "Track your order", "button_url": track_link(request, b),
         "outro": "Need to add something? Just reply to this email."},
        reply_to=settings.CONTACT_EMAIL,
    )
    return founder_sent, client_sent


def send_verification_email(request, user):
    from accounts.utils import make_verify_token
    url = absolute(request, reverse("accounts:verify", args=[make_verify_token(user)]))
    return _send(user.email, "Verify your email · Project Aethrix", {
        "heading": f"Hi {display_name(user)}, verify your email.",
        "intro": "Confirm this is your email to finish setting up your client dashboard. "
                 "Any projects you booked with this email will appear there.",
        "button_label": "Verify my email", "button_url": url,
        "outro": "The link works for 7 days. If you didn't create an account, you can ignore this email.",
    })


def send_invite_email(request, user, booking, set_password_url=None):
    if set_password_url:
        intro = (f"{settings.FOUNDER_NAME} has set up a client dashboard for your project {booking.reference}. "
                 "Set a password to see your order, its progress and messages.")
        label, url = "Set my password", set_password_url
        outro = "The link works for 3 days. After that, use 'Forgot password' on the login page."
    else:
        intro = f"Your project {booking.reference} is now in your client dashboard. Log in with your email and password."
        label, url = "Open my dashboard", absolute(request, reverse("portal:order", args=[booking.reference]))
        outro = "Forgot your password? Use the 'Forgot password' link on the login page."
    return _send(user.email, f"Your client dashboard is ready · {booking.reference}", {
        "heading": f"Hi {display_name(user)}, your dashboard is ready.",
        "intro": intro, "rows": [("Project", booking.display_title), ("Reference", booking.reference)],
        "button_label": label, "button_url": url, "outro": outro,
    }, reply_to=settings.CONTACT_EMAIL)


def send_order_update_email(request, booking, changes, note=""):
    rows = [(label, value) for label, value in changes]
    return _send(booking.email, f"Update on your project · {booking.reference}", {
        "heading": f"Update on {booking.display_title}",
        "intro": f"Here's what changed on your project {booking.reference}.",
        "rows": rows, "quote_title": "Note" if note else "", "quote": note,
        "button_label": "Open my dashboard", "button_url": track_link(request, booking),
        "outro": "Reply to this email if you have any questions.",
    }, reply_to=settings.CONTACT_EMAIL)


def send_founder_message_email(request, booking, message):
    return _send(booking.email, f"New message about your project · {booking.reference}", {
        "heading": f"New message from {settings.FOUNDER_NAME}",
        "intro": f"About your project {booking.display_title} ({booking.reference}):",
        "quote": message.body,
        "button_label": "Reply in my dashboard", "button_url": track_link(request, booking),
    }, reply_to=settings.CONTACT_EMAIL)


def send_client_message_email(request, booking, message):
    return _send(settings.BOOKING_NOTIFY_EMAIL, f"Client message on {booking.reference} ({booking.name})", {
        "heading": f"{booking.name} sent a message",
        "intro": f"On {booking.display_title} ({booking.reference}).",
        "quote": message.body,
        "button_label": "Open the order", "button_url": absolute(request, reverse("founder:order", args=[booking.reference])),
    }, html=False, reply_to=booking.email)
