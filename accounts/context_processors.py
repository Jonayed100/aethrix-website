from .utils import display_name, home_url_for, is_team, role_of

CONSOLES = {"founder": "Founder", "adminpanel": "Admin"}


def account(request):
    user = getattr(request, "user", None)
    match = getattr(request, "resolver_match", None)
    ns = match.namespace if match and match.namespace in CONSOLES else ""
    context = {"is_founder": False, "is_team": False, "ns": ns, "console_label": CONSOLES.get(ns, "")}
    if not user or not user.is_authenticated:
        return context
    role = role_of(user)
    context.update({
        "role": role,
        "is_founder": role == "founder",
        "is_team": is_team(user),
        "dashboard_url": home_url_for(user),
        "user_name": display_name(user),
    })
    if context["is_team"]:
        from studio.models import Booking
        context["nav_new"] = Booking.objects.filter(status=Booking.Status.NEW).count()
    return context