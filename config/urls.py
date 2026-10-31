from django.conf import settings
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from studio.sitemaps import ProjectSitemap, StaticViewSitemap
from studio.views import health, robots_txt

admin.site.site_header = "Project Aethrix admin"
admin.site.site_title = "Project Aethrix admin"
admin.site.index_title = "Backup admin (use the founder dashboard day to day)"
# The backup admin opens for the founder only, never for team admins or clients.
admin.site.has_permission = lambda request: bool(request.user.is_active and request.user.is_superuser)

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("robots.txt", robots_txt, name="robots"),
    path("sitemap.xml", sitemap, {"sitemaps": {"pages": StaticViewSitemap, "projects": ProjectSitemap}}, name="sitemap"),
    path("healthz", health, name="health"),
    path(settings.FOUNDER_URL, include("founder.urls")),
    path(settings.ADMIN_PANEL_URL, include("founder.admin_urls")),
    path("dashboard/", include("portal.urls")),
    path("", include("accounts.urls")),
    path("", include("studio.urls")),
]

handler404 = "studio.views.not_found"
