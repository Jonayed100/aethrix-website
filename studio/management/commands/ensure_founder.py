"""
Create the founder login from environment variables if it doesn't exist yet.

Render's free plan has no shell for `createsuperuser`, so build.sh runs this
on every deploy. It never changes an existing account's password.

    FOUNDER_EMAIL=projectaethrix@gmail.com
    FOUNDER_PASSWORD=a-long-strong-password
"""
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from accounts.models import Profile


class Command(BaseCommand):
    help = "Create the founder account from FOUNDER_EMAIL / FOUNDER_PASSWORD if it is missing."

    def handle(self, *args, **options):
        email = (os.environ.get("FOUNDER_EMAIL") or os.environ.get("DJANGO_SUPERUSER_EMAIL") or "").strip().lower()
        password = os.environ.get("FOUNDER_PASSWORD") or os.environ.get("DJANGO_SUPERUSER_PASSWORD")
        name = os.environ.get("FOUNDER_NAME_FIRST", "Jonayed")
        if not email or not password:
            self.stdout.write("ensure_founder: FOUNDER_EMAIL / FOUNDER_PASSWORD not set, skipping.")
            return
        User = get_user_model()
        existing = User.objects.filter(email__iexact=email).first()
        if existing:
            if not existing.is_superuser:
                existing.is_staff = existing.is_superuser = True
                existing.save(update_fields=["is_staff", "is_superuser"])
                self.stdout.write(self.style.SUCCESS(f"ensure_founder: gave founder access to {email}."))
            else:
                self.stdout.write(f"ensure_founder: founder {email} already exists.")
            Profile.objects.update_or_create(user=existing, defaults={"email_verified": True})
            return
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME") or email
        user = User.objects.create_superuser(username=username, email=email, password=password, first_name=name)
        Profile.objects.create(user=user, email_verified=True)
        self.stdout.write(self.style.SUCCESS(f"ensure_founder: created founder {email}."))
