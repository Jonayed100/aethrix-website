from .utils import display_name, home_url_for, is_team, role_of

CONSOLES = {"founder": "Founder", "adminpanel": "Admin"}


def account(request):
    user = getattr(request, "user", None)
    match = getattr(request, "resolver_match", None)
    ns = match.namespace if match and match.namespace in CONSOLES else ""
    # client_user: a signed-in client. The public website only ever shows "My dashboard"
    # to clients; the founder and admins see it like a visitor (Log in / Sign up),
    # so no private dashboard is ever linked from the website.
    context = {"is_founder": False, "is_team": False, "client_user": False, "ns": ns, "console_label": CONSOLES.get(ns, "")}
    if not user or not user.is_authenticated:
        return context
    role = role_of(user)
    context.update({
        "role": role,
        "is_founder": role == "founder",
        "is_team": is_team(user),
        "client_user": not is_team(user),
        "dashboard_url": home_url_for(user),
        "user_name": display_name(user),
    })
    if context["is_team"]:
        from studio.models import Booking
        context["nav_new"] = Booking.objects.filter(status=Booking.Status.NEW).count()
    return context
