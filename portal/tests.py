from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from accounts.models import Profile
from studio.models import Booking, OrderMessage

User = get_user_model()


def make_booking(client=None, **kw):
    defaults = dict(name="Nadia Islam", email="nadia@example.com", services="app", budget_bdt=90000,
                    description="An appointment app for our clinic in Dhanmondi.", client=client)
    defaults.update(kw)
    return Booking.objects.create(**defaults)


class ClientDashboardTests(TestCase):
    def setUp(self):
        cache.clear()
        self.nadia = User.objects.create_user("nadia", "nadia@example.com", "Clinic-app-2026", first_name="Nadia")
        Profile.objects.create(user=self.nadia, email_verified=True)
        self.other = User.objects.create_user("other", "other@example.com", "Other-pass-2026")
        self.mine = make_booking(self.nadia, title="Clinic app", status="in_progress", progress=60)
        self.done = make_booking(self.nadia, title="Clinic website", status="completed", delivery_url="https://clinic.example.com")
        self.theirs = make_booking(self.other, name="Other", email="other@example.com", title="Secret shop")

    def test_visitors_must_log_in(self):
        response = self.client.get(reverse("portal:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse("accounts:login")))

    def test_client_sees_only_their_orders(self):
        self.client.force_login(self.nadia)
        page = self.client.get(reverse("portal:dashboard"))
        self.assertContains(page, "Clinic app")
        self.assertContains(page, "Clinic website")
        self.assertContains(page, 'data-3d="blocks"')
        self.assertContains(page, 'data-progress="60"')
        self.assertNotContains(page, "Secret shop")
        self.assertEqual(self.client.get(reverse("portal:order", args=[self.theirs.reference])).status_code, 404)

    def test_completed_order_shows_live_link(self):
        self.client.force_login(self.nadia)
        page = self.client.get(reverse("portal:order", args=[self.done.reference]))
        self.assertContains(page, "https://clinic.example.com")
        self.assertContains(page, "Open your live project")

    def test_private_notes_never_reach_the_client(self):
        self.mine.admin_notes = "Charge extra for rush"
        self.mine.save()
        self.client.force_login(self.nadia)
        self.assertNotContains(self.client.get(reverse("portal:order", args=[self.mine.reference])), "Charge extra")

    def test_client_message_reaches_founder(self):
        self.client.force_login(self.nadia)
        response = self.client.post(reverse("portal:order", args=[self.mine.reference]), {"body": "Can we add Bangla?"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(OrderMessage.objects.filter(booking=self.mine, from_founder=False, body="Can we add Bangla?").exists())
        self.assertEqual(mail.outbox[-1].to, ["projectaethrix@gmail.com"])

    def test_founder_is_sent_to_founder_dashboard(self):
        founder = User.objects.create_superuser("f", "projectaethrix@gmail.com", "Founder-pass-123")
        self.client.force_login(founder)
        self.assertRedirects(self.client.get(reverse("portal:dashboard")), reverse("founder:overview"))

    def test_verified_client_picks_up_new_bookings_with_their_email(self):
        loose = make_booking(None, title="Booked while logged out")
        self.client.force_login(self.nadia)
        self.assertContains(self.client.get(reverse("portal:dashboard")), "Booked while logged out")
        loose.refresh_from_db()
        self.assertEqual(loose.client, self.nadia)

    def test_unverified_client_sees_banner_and_no_unlinked_bookings(self):
        self.client.force_login(self.other)
        make_booking(None, name="X", email="other@example.com", title="Unclaimed")
        page = self.client.get(reverse("portal:dashboard"))
        self.assertContains(page, "Verify your email")
        self.assertNotContains(page, "Unclaimed")

    def test_account_details_and_password(self):
        self.client.force_login(self.nadia)
        self.client.post(reverse("portal:account"), {"action": "profile", "name": "Nadia I.", "phone": "01711", "company": "CareLink"})
        self.nadia.refresh_from_db()
        self.assertEqual(self.nadia.first_name, "Nadia I.")
        self.assertEqual(self.nadia.profile.company, "CareLink")
        self.client.post(reverse("portal:account"), {"action": "password", "old_password": "Clinic-app-2026",
                                                    "new_password1": "Newer-pass-2027", "new_password2": "Newer-pass-2027"})
        self.nadia.refresh_from_db()
        self.assertTrue(self.nadia.check_password("Newer-pass-2027"))
        self.assertEqual(self.client.get(reverse("portal:dashboard")).status_code, 200)  # still signed in
