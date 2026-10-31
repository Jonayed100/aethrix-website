"""Django's built-in admin, kept as a backup tool. Day-to-day work happens in the founder dashboard."""
from django.contrib import admin
from django.utils.html import format_html

from .models import Booking, OrderMessage, Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "link", "is_published", "sort_order", "updated_at")
    list_editable = ("is_published", "sort_order")
    list_filter = ("category", "is_published")
    search_fields = ("title", "summary", "tech_stack")
    prepopulated_fields = {"slug": ("title",)}

    @admin.display(description="Live demo")
    def link(self, obj):
        if not obj.live_url:
            return "Coming soon"
        return format_html('<a href="{}" target="_blank" rel="noopener">{} ↗</a>', obj.live_url, obj.domain)


class OrderMessageInline(admin.TabularInline):
    model = OrderMessage
    extra = 0
    fields = ("created_at", "from_founder", "is_event", "body")
    readonly_fields = ("created_at",)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("reference", "name", "email", "services_display", "budget_display", "status", "progress", "client", "created_at")
    list_filter = ("status", "timeline", "created_at")
    search_fields = ("reference", "name", "email", "phone", "company", "description", "title")
    date_hierarchy = "created_at"
    raw_id_fields = ("client",)
    readonly_fields = ("reference", "created_at", "updated_at", "completed_at", "ip_address")
    inlines = [OrderMessageInline]
    fieldsets = (
        ("Order", {"fields": ("reference", "status", "title", "quoted_price_bdt", "progress", "due_date", "delivery_url", "completed_at", "admin_notes")}),
        ("Client", {"fields": ("client", "name", "email", "phone", "company")}),
        ("Request", {"fields": ("services", "budget_bdt", "timeline", "preferred_date", "preferred_time", "description")}),
        ("Record", {"fields": ("created_at", "updated_at", "ip_address"), "classes": ("collapse",)}),
    )

    @admin.display(description="Services")
    def services_display(self, obj):
        return obj.services_display

    @admin.display(description="Budget", ordering="budget_bdt")
    def budget_display(self, obj):
        return obj.budget_display
