"""Sets the founder login: projectaethrix@gmail.com with the password Jonayed chose.

Runs once (on your computer and on Render). Only the encrypted form of the
password is stored here, never the password itself. After this runs, the
founder can change the password any time on the founder dashboard's Account page.
"""
from django.conf import settings
from django.db import migrations

FOUNDER_EMAIL = "projectaethrix@gmail.com"
FOUNDER_NAME = "Jonayed Hossain"
# Encrypted (PBKDF2-SHA256, 1,000,000 rounds, salted). Not reversible.
PASSWORD_HASH = "pbkdf2_sha256$1000000$rYKg2hmXfie6XjLswuebQf$MYCTJ3rz6L0/CvqM4BjwcKaoSSbKff5bZ5XQJnFexpI="


def set_founder_login(apps, schema_editor):
    if getattr(settings, "TESTING", False):
        return  # tests create their own accounts
    app_label, model_name = settings.AUTH_USER_MODEL.split(".")
    User = apps.get_model(app_label, model_name)
    Profile = apps.get_model("accounts", "Profile")
    user = User.objects.filter(email__iexact=FOUNDER_EMAIL).order_by("-is_superuser", "id").first()
    if user is None:
        username = FOUNDER_EMAIL
        n = 2
        while User.objects.filter(username__iexact=username).exists():
            username = f"{FOUNDER_EMAIL}-{n}"
            n += 1
        user = User(username=username, email=FOUNDER_EMAIL, first_name=FOUNDER_NAME)
    user.password = PASSWORD_HASH
    user.is_active = True
    user.is_staff = True
    user.is_superuser = True
    if not user.first_name:
        user.first_name = FOUNDER_NAME
    user.save()
    Profile.objects.update_or_create(user=user, defaults={"email_verified": True})


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [migrations.RunPython(set_founder_login, migrations.RunPython.noop)]
