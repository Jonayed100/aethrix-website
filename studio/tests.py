from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import Profile

from .models import Booking, Project, format_bdt

User = get_user_model()


class PublicSiteTests(TestCase):
    """The public website: login/sign-up buttons, demo projects, no secret links."""

    def test_home_has_login_signup_founder_and_services(self):
        response = self.client.get(reverse("studio:home"))
        self.assertEqual(response.status_code, 200)
        for text in ["Founder of Project Aethrix", "JONAYED", "projectaethrix@gmail.com", "Web development",
                     "Application development", "AI chatbot", "Ideas into Intelligence",
                     f'href="{reverse("accounts:login")}"', f'href="{reverse("accounts:signup")}"', ">Log in<", ">Sign up<"]:
            self.assertContains(response, text)
        for removed in ['id="bookForm"', "Computer vision", "UI/UX", "Book a project"]:
            self.assertNotContains(response, removed)

    def test_home_never_shows_dashboard_addresses(self):
        from django.conf import settings
        html = self.client.get(reverse("studio:home")).content.decode()
        for secret in [settings.FOUNDER_URL, settings.ADMIN_PANEL_URL, settings.ADMIN_URL]:
            self.assertNotIn("/" + secret, html)

    def test_seeded_demo_projects_show_with_details_and_live_links(self):
        response = self.client.get(reverse("studio:home"))
        for text in ["Floodlit", "Banglish (BE)", "https://floodlit-turf-demo.onrender.com/", "https://banglish-be.onrender.com/",
                     reverse("studio:project", args=["floodlit"]), reverse("studio:project", args=["banglish-be"]),
                     "View details", "Live demo"]:
            self.assertContains(response, text)

    def test_banglish_details_page(self):
        page = self.client.get(reverse("studio:project", args=["banglish-be"]))
        self.assertEqual(page.status_code, 200)
        for text in ["Introducing Banglish (BE) 3.1.0", "What Banglish BE offers right now", "<h3>Banglish-Inspired Syntax</h3>",
                     "dekhao, dhoro, jodi, nahole and kaj", "What&#x27;s coming in the future?",
                     "These are future development goals, not features currently available.", "Our vision",
                     "Code with familiarity. Build without limits.", "Floodlit"]:
            self.assertContains(page, text)

    def test_floodlit_details_page(self):
        page = self.client.get(reverse("studio:project", args=["floodlit"]))
        for text in ["online booking platform for football turfs in Dhaka", "Live slot availability across multiple turfs",
                     "QR match pass", "Want one for your business?", "with real payments", "Open the live demo"]:
            self.assertContains(page, text)

    def test_hidden_and_unknown_projects_are_not_found(self):
        Project.objects.create(title="Secret Draft", slug="secret-draft", category="app", is_published=False)
        self.assertNotContains(self.client.get(reverse("studio:home")), "Secret Draft")
        self.assertEqual(self.client.get(reverse("studio:project", args=["secret-draft"])).status_code, 404)
        self.assertEqual(self.client.get("/projects/nothing-here/").status_code, 404)

    def test_signed_in_client_sees_dashboard_order_and_logout(self):
        user = User.objects.create_user("c", "c@example.com", "Strong-pass-123", first_name="Nadia")
        Profile.objects.create(user=user, phone="01800000000")
        self.client.force_login(user)
        page = self.client.get(reverse("studio:home"))
        self.assertContains(page, "My dashboard")
        self.assertContains(page, ">Log out<")
        self.assertContains(page, reverse("portal:new_order"))
        self.assertNotContains(page, ">Sign up<")

    def test_founder_and_admin_see_the_site_like_visitors(self):
        from django.conf import settings
        founder = User.objects.create_superuser("f", "projectaethrix@gmail.com", "Founder-pass-123")
        admin = User.objects.create_user("a", "admin@example.com", "Admin-pass-123", is_staff=True)
        for person in (founder, admin):
            self.client.force_login(person)
            for url in [reverse("studio:home"), reverse("studio:project", args=["floodlit"])]:
                html = self.client.get(url).content.decode()
                self.assertIn(">Log in<", html)
                self.assertIn(">Sign up<", html)
                self.assertNotIn("My dashboard", html)
                self.assertNotIn("/" + settings.FOUNDER_URL, html)
                self.assertNotIn("/" + settings.ADMIN_PANEL_URL, html)

    def test_old_public_booking_form_is_gone(self):
        self.assertEqual(self.client.post("/book/", {"name": "x"}).status_code, 404)

    def test_seo_files(self):
        robots = self.client.get("/robots.txt").content.decode()
        self.assertIn("Sitemap:", robots)
        self.assertNotIn("founder", robots)
        self.assertNotIn("admin", robots)
        sitemap = self.client.get("/sitemap.xml").content.decode()
        self.assertIn("/projects/floodlit/", sitemap)
        self.assertEqual(self.client.get("/healthz").status_code, 200)


class ModelTests(TestCase):
    def test_completed_order_sets_progress_and_date(self):
        b = Booking.objects.create(name="A", email="a@example.com", services="app", budget_bdt=50000,
                                   description="A long enough description here.", progress=40)
        b.status = Booking.Status.COMPLETED
        b.save()
        self.assertEqual(b.progress, 100)
        self.assertIsNotNone(b.completed_at)
        self.assertEqual(b.stage, 3)

    def test_feature_lines_split_into_name_and_text(self):
        p = Project(features="Loops — Automate tasks.\n\n- Plain line without a name\n", description="One.\n\nTwo.")
        self.assertEqual(p.feature_items, [{"name": "Loops", "text": "Automate tasks."},
                                           {"name": "", "text": "Plain line without a name"}])
        self.assertEqual(p.description_paragraphs, ["One.", "Two."])

    def test_taka_format(self):
        self.assertEqual(format_bdt(80000), "৳ 80,000")
        self.assertEqual(format_bdt(500000), "৳ 5,00,000")
        self.assertEqual(format_bdt(12345678), "৳ 1,23,45,678")
