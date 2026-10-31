from .utils import display_name, home_url_for, is_founder


def account(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {"is_founder": False}
    context = {
        "is_founder": is_founder(user),
        "dashboard_url": home_url_for(user),
        "user_name": display_name(user),
    }
    if context["is_founder"]:
        from studio.models import Booking
        context["nav_new"] = Booking.objects.filter(status=Booking.Status.NEW).count()
    return context
