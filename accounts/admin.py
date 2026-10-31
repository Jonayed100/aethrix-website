from django.contrib import admin

from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "company", "email_verified", "created_at")
    list_filter = ("email_verified",)
    search_fields = ("user__email", "user__first_name", "phone", "company")
