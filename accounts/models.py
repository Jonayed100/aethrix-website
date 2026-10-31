from django.conf import settings
from django.db import models


class Profile(models.Model):
    """Extra details for a login: contact info and whether the email is verified."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    phone = models.CharField("Phone or WhatsApp", max_length=40, blank=True)
    company = models.CharField("Company or brand", max_length=120, blank=True)
    email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Profile of {self.user.email or self.user.username}"

    @classmethod
    def for_user(cls, user):
        profile, _ = cls.objects.get_or_create(user=user)
        return profile
