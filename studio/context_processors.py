from django.conf import settings


def site(request):
    return {
        "SITE_NAME": settings.SITE_NAME,
        "SITE_URL": settings.SITE_URL,
        "CONTACT_EMAIL": settings.CONTACT_EMAIL,
        "FOUNDER_NAME": settings.FOUNDER_NAME,
        "FOUNDER_PORTFOLIO_URL": settings.FOUNDER_PORTFOLIO_URL,
    }
