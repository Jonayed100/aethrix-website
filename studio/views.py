import json

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils.safestring import mark_safe
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET

from .models import Project


def _org_json_ld():
    data = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": settings.SITE_NAME,
        "url": settings.SITE_URL,
        "email": settings.CONTACT_EMAIL,
        "slogan": "Ideas into Intelligence",
        "founder": {"@type": "Person", "name": settings.FOUNDER_NAME},
        "address": {"@type": "PostalAddress", "addressLocality": "Dhaka", "addressCountry": "BD"},
        "knowsAbout": ["Web development", "Application development", "AI chatbots"],
    }
    return mark_safe(json.dumps(data).replace("<", "\\u003c"))


def home(request):
    """The public website. Demo projects come from the database (founder dashboard → Demo projects)."""
    projects = list(Project.objects.filter(is_published=True))
    for p in projects:
        features = p.feature_items
        p.top_features = features[:3]
        p.more_features = max(0, len(features) - 3)
    return render(request, "home.html", {"projects": projects, "org_json_ld": _org_json_ld()})


def project_detail(request, slug):
    """Full details page for one demo project."""
    project = get_object_or_404(Project, slug=slug, is_published=True)
    others = Project.objects.filter(is_published=True).exclude(pk=project.pk)[:3]
    return render(request, "project_detail.html", {"p": project, "others": others, "section": "projects"})


@require_GET
@cache_control(max_age=86400)
def robots_txt(request):
    lines = [
        "User-agent: *",
        "Disallow: /dashboard/",
        "Disallow: /login/",
        "Disallow: /signup/",
        f"Sitemap: {settings.SITE_URL}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain")


def health(request):
    return HttpResponse("ok", content_type="text/plain")


def not_found(request, exception):
    return render(request, "404.html", status=404)