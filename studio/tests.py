import datetime

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Profile

from .models import Booking, Project, format_bdt


def next_weekday(weekday):
    day = timezone.localdate() + datetime.timedelta(days=1)
    while day.weekday() != weekday:
        day += datetime.timedelta(days=1)
    return day


def booking_data(**overrides):
    data = {
        "name": "Rafiq Ahmed",
        "email": "rafiq@example.com",
        "phone": "+8801700000000",
        "company": "Mirpur Turf",
        "services": ["website", "chatbot"],
        "budget_bdt": "120000",
        "timeline": "1_month",
        "preferred_date": next_weekday(0).isoformat(),
        "preferred_time": "15:00",
        "description": "We need a turf booking website with online payment and an admin page.",
        "website_url": "",
    }
    data.update(overrides)
    return data


AJAX = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}


class PublicSiteTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_home_shows_founder_three_services_and_booking_form(self):
        response = self.client.get(reverse("studio:home"))
        self.assertEqual(response.status_code, 200)
        for text in ["Founder of Project Aethrix", "JONAYED", 'id="bookForm"', "projectaethrix@gmail.com",
                     "Web development", "Application development", "AI chatbot", "Client login"]:
            self.assertContains(response, text)
        for removed in ["Computer vision", "UI/UX", "Figma", "OpenCV", "Something else"]:
            self.assertNotContains(response, removed)

    def test_published_projects_appear_and_hidden_ones_do_not(self):
        Project.objects.create(title="Kickoff Arena", slug="kickoff-arena", category="website",
                               summary="Turf booking", live_url="https://kickoff.example.com")
        Project.objects.create(title="Secret Draft", slug="secret-draft", category="app", is_published=False)
        response = self.client.get(reverse("studio:home"))
        self.assertContains(response, "Kickoff Arena")
        self.assertContains(response, "kickoff.example.com")
        self.assertNotContains(response, "Secret Draft")

    def test_booking_is_saved_and_emailed(self):
        response = self.client.post(reverse("studio:book"), booking_data(), **AJAX)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        booking = Booking.objects.get(reference=data["reference"])
        self.assertEqual(booking.services, "website,chatbot")
        self.assertIsNone(booking.client)
        self.assertIn(reverse("accounts:signup"), data["track_url"])
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[0].to, ["projectaethrix@gmail.com"])
        self.assertIn(booking.reference, mail.outbox[0].subject)
        self.assertEqual(mail.outbox[1].to, ["rafiq@example.com"])

    def test_booking_by_signed_in_client_goes_to_their_dashboard(self):
        user = get_user_model().objects.create_user("c@example.com", "c@example.com", "Strong-pass-123", first_name="Nadia")
        Profile.objects.create(user=user, phone="01800", company="Clinic")
        self.client.force_login(user)
        page = self.client.get(reverse("studio:home"))
        self.assertContains(page, 'value="c@example.com"')
        self.assertContains(page, "Dashboard")
        data = self.client.post(reverse("studio:book"), booking_data(email="c@example.com"), **AJAX).json()
        booking = Booking.objects.get(reference=data["reference"])
        self.assertEqual(booking.client, user)
        self.assertEqual(data["track_url"], reverse("portal:order", args=[booking.reference]))

    def test_booking_without_javascript_redirects_to_thank_you_page(self):
        response = self.client.post(reverse("studio:book"), booking_data())
        booking = Booking.objects.get()
        self.assertRedirects(response, reverse("studio:booking_thanks", args=[booking.reference]))
        self.assertContains(self.client.get(response.url), booking.reference)

    def test_thank_you_page_is_private(self):
        booking = Booking.objects.create(name="A", email="a@example.com", services="app", budget_bdt=50000,
                                         description="A long enough description here.")
        self.assertEqual(self.client.get(reverse("studio:booking_thanks", args=[booking.reference])).status_code, 404)

    def test_invalid_booking_returns_errors(self):
        data = booking_data(services=["other"], description="too short", preferred_date=next_weekday(4).isoformat())
        response = self.client.post(reverse("studio:book"), data, **AJAX)
        self.assertEqual(response.status_code, 400)
        errors = response.json()["errors"]
        for field in ["services", "description", "preferred_date"]:
            self.assertIn(field, errors)
        self.assertEqual(Booking.objects.count(), 0)

    def test_invalid_booking_without_javascript_shows_form_again(self):
        response = self.client.post(reverse("studio:book"), booking_data(name=""))
        self.assertContains(response, "Please enter your name.", status_code=400)

    def test_honeypot_blocks_bots(self):
        response = self.client.post(reverse("studio:book"), booking_data(website_url="http://spam.example"), **AJAX)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(Booking.objects.count(), 0)

    def test_rate_limit(self):
        with self.settings(BOOKING_RATE_LIMIT=2):
            for _ in range(2):
                self.assertEqual(self.client.post(reverse("studio:book"), booking_data(), **AJAX).status_code, 200)
            self.assertEqual(self.client.post(reverse("studio:book"), booking_data(), **AJAX).status_code, 429)

    def test_seo_files_do_not_reveal_private_addresses(self):
        robots = self.client.get("/robots.txt").content.decode()
        self.assertIn("Sitemap:", robots)
        self.assertNotIn("founder", robots)
        self.assertNotIn("admin", robots)
        self.assertEqual(self.client.get("/sitemap.xml").status_code, 200)
        self.assertEqual(self.client.get("/healthz").status_code, 200)

    def test_completed_order_sets_progress_and_date(self):
        b = Booking.objects.create(name="A", email="a@example.com", services="app", budget_bdt=50000,
                                   description="A long enough description here.", progress=40)
        b.status = Booking.Status.COMPLETED
        b.save()
        self.assertEqual(b.progress, 100)
        self.assertIsNotNone(b.completed_at)
        self.assertEqual(b.stage, 3)

    def test_taka_format(self):
        self.assertEqual(format_bdt(80000), "৳ 80,000")
        self.assertEqual(format_bdt(500000), "৳ 5,00,000")
        self.assertEqual(format_bdt(12345678), "৳ 1,23,45,678")
