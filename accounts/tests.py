import re

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from studio.models import Booking

from .models import Profile
from .utils import make_verify_token, set_password_path

User = get_user_model()


def make_booking(email="nadia@example.com", **kw):
    return Booking.objects.create(name=kw.pop("name", "Nadia Islam"), email=email, services="app", budget_bdt=90000,
                                  description="An appointment app for our clinic in Dhanmondi.", **kw)


def link_in(message):
    return re.search(r"https?://testserver(\S+)", message.body).group(1)


class SignupAndVerifyTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_signup_logs_in_and_sends_verification(self):
        response = self.client.post(reverse("accounts:signup"), {
            "name": "Nadia Islam", "email": "Nadia@Example.com", "password1": "Clinic-app-2026", "password2": "Clinic-app-2026"})
        self.assertRedirects(response, reverse("portal:dashboard"))
        user = User.objects.get(email="nadia@example.com")
        self.assertFalse(user.profile.email_verified)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Verify", mail.outbox[0].subject)

    def test_duplicate_email_and_weak_password_are_rejected(self):
        User.objects.create_user("x", "taken@example.com", "Some-pass-123")
        response = self.client.post(reverse("accounts:signup"), {
            "name": "A", "email": "TAKEN@example.com", "password1": "123", "password2": "123"})
        self.assertContains(response, "already exists")
        self.assertContains(response, "too short")

    def test_verify_link_marks_email_and_claims_old_bookings(self):
        old = make_booking()
        self.client.post(reverse("accounts:signup"), {
            "name": "Nadia", "email": "nadia@example.com", "password1": "Clinic-app-2026", "password2": "Clinic-app-2026"})
        old.refresh_from_db()
        self.assertIsNone(old.client)  # not before verifying
        response = self.client.get(link_in(mail.outbox[-1]))
        self.assertContains(response, "1 earlier booking")
        old.refresh_from_db()
        self.assertEqual(old.client.email, "nadia@example.com")
        self.assertTrue(Profile.objects.get(user=old.client).email_verified)

    def test_bad_verify_link(self):
        self.assertEqual(self.client.get(reverse("accounts:verify", args=["nonsense"])).status_code, 400)
        user = User.objects.create_user("y", "y@example.com", "Some-pass-123")
        token = make_verify_token(user)
        user.email = "changed@example.com"
        user.save()
        self.assertEqual(self.client.get(reverse("accounts:verify", args=[token])).status_code, 400)


class LoginTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client_user = User.objects.create_user("c", "client@example.com", "Client-pass-123")
        self.founder = User.objects.create_superuser("f", "projectaethrix@gmail.com", "Founder-pass-123")

    def test_client_logs_in_with_email_any_case(self):
        response = self.client.post(reverse("accounts:login"), {"email": "CLIENT@example.com", "password": "Client-pass-123"})
        self.assertRedirects(response, reverse("portal:dashboard"))

    def test_wrong_password(self):
        response = self.client.post(reverse("accounts:login"), {"email": "client@example.com", "password": "nope"})
        self.assertContains(response, "Email or password is wrong.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_rate_limit(self):
        for _ in range(8):
            self.client.post(reverse("accounts:login"), {"email": "client@example.com", "password": "nope"})
        response = self.client.post(reverse("accounts:login"), {"email": "client@example.com", "password": "Client-pass-123"})
        self.assertContains(response, "Too many tries")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_next_parameter_is_safe(self):
        response = self.client.post(reverse("accounts:login") + "?next=https://evil.example/",
                                    {"email": "client@example.com", "password": "Client-pass-123", "next": "https://evil.example/"})
        self.assertRedirects(response, reverse("portal:dashboard"))

    def test_founder_using_client_login_lands_in_founder_dashboard(self):
        response = self.client.post(reverse("accounts:login"), {"email": "projectaethrix@gmail.com", "password": "Founder-pass-123"})
        self.assertRedirects(response, reverse("founder:overview"))

    def test_logout_needs_post(self):
        self.client.force_login(self.client_user)
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)
        self.assertRedirects(self.client.post(reverse("accounts:logout")), reverse("studio:home"))


class PasswordResetTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_invited_client_without_password_can_reset_and_gets_logged_in(self):
        user = User(username="inv", email="inv@example.com")
        user.set_unusable_password()
        user.save()
        make_booking(email="inv@example.com", client=None)
        self.client.post(reverse("accounts:password_forgot"), {"email": "INV@example.com"})
        self.assertEqual(len(mail.outbox), 1)
        path = link_in(mail.outbox[0])
        form_page = self.client.get(path, follow=True)
        response = self.client.post(form_page.redirect_chain[-1][0],
                                    {"new_password1": "Brand-new-pass-77", "new_password2": "Brand-new-pass-77"})
        self.assertRedirects(response, reverse("portal:dashboard"))
        user.refresh_from_db()
        self.assertTrue(user.check_password("Brand-new-pass-77"))
        self.assertTrue(user.profile.email_verified)
        self.assertEqual(user.orders.count(), 1)

    def test_unknown_email_gives_same_answer(self):
        response = self.client.post(reverse("accounts:password_forgot"), {"email": "nobody@example.com"})
        self.assertRedirects(response, reverse("accounts:password_forgot_sent"))
        self.assertEqual(len(mail.outbox), 0)

    def test_set_password_link_is_single_use(self):
        user = User.objects.create_user("z", "z@example.com", "Old-pass-1234")
        path = set_password_path(user)
        page = self.client.get(path, follow=True)
        self.client.post(page.redirect_chain[-1][0], {"new_password1": "New-pass-5678x", "new_password2": "New-pass-5678x"})
        self.client.logout()
        again = self.client.get(path, follow=True)
        self.assertContains(again, "has expired")
