import re

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from studio.models import Booking, OrderMessage, Project

User = get_user_model()

FOUNDER_PAGES = ["founder:overview", "founder:orders", "founder:projects", "founder:project_add", "founder:clients",
                 "founder:team", "founder:account"]
ADMIN_PAGES = ["adminpanel:overview", "adminpanel:orders", "adminpanel:account"]


def make_admin(email="sakib@example.com", password="Admin-pass-123", **kw):
    return User.objects.create_user(email.split("@")[0], email, password, is_staff=True, first_name=kw.pop("first_name", "Sakib"), **kw)


def make_booking(**kw):
    defaults = dict(name="Rafiq Ahmed", email="rafiq@example.com", services="website", budget_bdt=120000,
                    description="Turf booking website with online payment.")
    defaults.update(kw)
    return Booking.objects.create(**defaults)


class AccessTests(TestCase):
    """Founder dashboard: founder only. Admin dashboard: admins + founder. Everyone else: page not found."""

    def setUp(self):
        cache.clear()
        self.founder = User.objects.create_superuser("f", "projectaethrix@gmail.com", "Founder-pass-123")
        self.client_user = User.objects.create_user("c", "client@example.com", "Client-pass-123")
        self.admin = make_admin()
        self.booking = make_booking()

    def test_visitors_are_sent_to_the_right_login(self):
        for name in ADMIN_PAGES:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 302, name)
            self.assertTrue(response.url.startswith(reverse("adminpanel:login")), name)

    def test_admin_sees_admin_dashboard_but_not_founder_dashboard(self):
        self.client.force_login(self.admin)
        for name in ADMIN_PAGES:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
        self.assertEqual(self.client.get(reverse("adminpanel:order", args=[self.booking.reference])).status_code, 200)
        for name in FOUNDER_PAGES:
            self.assertEqual(self.client.get(reverse(name)).status_code, 404, name)
        self.assertEqual(self.client.get(reverse("founder:orders_csv")).status_code, 404)
        self.assertEqual(self.client.get(reverse("founder:client", args=[self.client_user.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("founder:login")).status_code, 404)
        overview = self.client.get(reverse("adminpanel:overview"))
        self.assertContains(overview, "Admin dashboard")
        self.assertNotContains(overview, "Open pipeline")
        self.assertNotContains(overview, "Demo projects")
        self.assertNotContains(overview, "Download CSV")

    def test_admin_cannot_use_backup_django_admin(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 302)

    def test_clients_get_page_not_found_on_admin_dashboard(self):
        self.client.force_login(self.client_user)
        for name in ADMIN_PAGES:
            self.assertEqual(self.client.get(reverse(name)).status_code, 404, name)
        self.assertEqual(self.client.get(reverse("adminpanel:login")).status_code, 404)

    def test_founder_can_open_admin_dashboard_too(self):
        self.client.force_login(self.founder)
        for name in ADMIN_PAGES:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
        self.assertContains(self.client.get(reverse("founder:overview")), reverse("adminpanel:overview"))

    def test_visitors_are_sent_to_founder_login(self):
        for name in FOUNDER_PAGES:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 302, name)
            self.assertTrue(response.url.startswith(reverse("founder:login")), name)

    def test_clients_get_page_not_found_everywhere(self):
        self.client.force_login(self.client_user)
        for name in FOUNDER_PAGES:
            self.assertEqual(self.client.get(reverse(name)).status_code, 404, name)
        self.assertEqual(self.client.get(reverse("founder:order", args=[self.booking.reference])).status_code, 404)
        self.assertEqual(self.client.get(reverse("founder:orders_csv")).status_code, 404)
        self.assertEqual(self.client.get(reverse("founder:login")).status_code, 404)
        self.assertEqual(self.client.post(reverse("founder:order_invite", args=[self.booking.reference])).status_code, 404)

    def test_clients_cannot_use_django_admin(self):
        self.client.force_login(self.client_user)
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_founder_login_rejects_client_accounts(self):
        response = self.client.post(reverse("founder:login"), {"email": "client@example.com", "password": "Client-pass-123"})
        self.assertContains(response, "Email or password is wrong.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_founder_login_works(self):
        response = self.client.post(reverse("founder:login"), {"email": "ProjectAethrix@gmail.com", "password": "Founder-pass-123"})
        self.assertRedirects(response, reverse("founder:overview"))
        self.assertEqual(self.client.get(reverse("portal:dashboard")).status_code, 302)  # founder is sent to their own dashboard

    def test_founder_sees_every_page(self):
        self.client.force_login(self.founder)
        for name in FOUNDER_PAGES:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
        overview = self.client.get(reverse("founder:overview"))
        self.assertContains(overview, 'id="seriesData"')
        self.assertContains(overview, 'data-3d="bars"')


class OrderWorkTests(TestCase):
    def setUp(self):
        cache.clear()
        self.founder = User.objects.create_superuser("f", "projectaethrix@gmail.com", "Founder-pass-123")
        self.client.force_login(self.founder)
        self.booking = make_booking()
        self.url = reverse("founder:order", args=[self.booking.reference])

    def update(self, **fields):
        data = {"o-status": "in_progress", "o-title": "Kickoff Arena", "o-quoted_price_bdt": "150000",
                "o-progress": "40", "o-due_date": "", "o-delivery_url": "", "o-admin_notes": "", "o-note": ""}
        data.update(fields)
        return self.client.post(self.url, data)

    def test_update_saves_logs_and_emails_client(self):
        response = self.update(**{"o-notify_client": "on", "o-note": "Homepage is ready."})
        self.assertRedirects(response, self.url)
        b = Booking.objects.get(pk=self.booking.pk)
        self.assertEqual((b.status, b.progress, b.quoted_price_bdt, b.title), ("in_progress", 40, 150000, "Kickoff Arena"))
        self.assertTrue(OrderMessage.objects.filter(booking=b, is_event=True).exists())
        self.assertTrue(OrderMessage.objects.filter(booking=b, body="Homepage is ready.").exists())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["rafiq@example.com"])
        self.assertIn("In progress", mail.outbox[0].body)

    def test_update_without_email(self):
        self.update()
        self.assertEqual(len(mail.outbox), 0)

    def test_completing_sets_full_progress(self):
        self.update(**{"o-status": "completed", "o-progress": "70", "o-delivery_url": "https://kickoff.example.com"})
        b = Booking.objects.get(pk=self.booking.pk)
        self.assertEqual(b.progress, 100)
        self.assertIsNotNone(b.completed_at)

    def test_message_is_posted_and_emailed(self):
        self.client.post(reverse("founder:order_message", args=[self.booking.reference]), {"m-body": "Can we call at 4?", "m-notify": "on"})
        self.assertTrue(OrderMessage.objects.filter(from_founder=True, body="Can we call at 4?").exists())
        self.assertEqual(len(mail.outbox), 1)

    def test_invite_creates_account_that_can_set_password_and_see_order(self):
        self.client.post(reverse("founder:order_invite", args=[self.booking.reference]))
        user = User.objects.get(email="rafiq@example.com")
        self.assertFalse(user.has_usable_password())
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.client, user)
        self.assertEqual(len(mail.outbox), 1)
        path = re.search(r"https?://testserver(\S+)", mail.outbox[0].body).group(1)
        self.client.logout()
        page = self.client.get(path, follow=True)
        response = self.client.post(page.redirect_chain[-1][0], {"new_password1": "Rafiq-turf-2026", "new_password2": "Rafiq-turf-2026"})
        self.assertRedirects(response, reverse("portal:dashboard"))
        dashboard = self.client.get(reverse("portal:dashboard"))
        self.assertContains(dashboard, self.booking.reference)

    def test_csv_export(self):
        response = self.client.get(reverse("founder:orders_csv"))
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn(self.booking.reference, response.content.decode("utf-8-sig"))

    def test_orders_filter_and_search(self):
        make_booking(name="Other Person", email="o@example.com", status="completed")
        page = self.client.get(reverse("founder:orders") + "?status=completed")
        self.assertContains(page, "Other Person")
        self.assertNotContains(page, "Rafiq Ahmed</a>")
        found = self.client.get(reverse("founder:orders") + "?q=rafiq")
        self.assertContains(found, "Rafiq Ahmed")


class TeamTests(TestCase):
    """The founder adds admins; admins handle orders and message clients."""

    def setUp(self):
        cache.clear()
        self.founder = User.objects.create_superuser("f", "projectaethrix@gmail.com", "Founder-pass-123")

    def test_founder_creates_admin_who_can_sign_in(self):
        self.client.force_login(self.founder)
        page = self.client.get(reverse("founder:team"))
        self.assertContains(page, reverse("adminpanel:login"))
        self.client.post(reverse("founder:team"), {"name": "Sakib Khan", "email": "Sakib@Example.com",
                                                   "phone": "01712345678", "password": "Team-member-2026"})
        admin = User.objects.get(email="sakib@example.com")
        self.assertTrue(admin.is_staff)
        self.assertFalse(admin.is_superuser)
        self.assertEqual(admin.profile.phone, "01712345678")
        self.client.logout()
        response = self.client.post(reverse("adminpanel:login"), {"email": "sakib@example.com", "password": "Team-member-2026"})
        self.assertRedirects(response, reverse("adminpanel:overview"))

    def test_duplicate_email_is_rejected(self):
        User.objects.create_user("c", "client@example.com", "Client-pass-123")
        self.client.force_login(self.founder)
        page = self.client.post(reverse("founder:team"), {"name": "X", "email": "client@example.com", "phone": "", "password": "Team-member-2026"})
        self.assertContains(page, "already")
        self.assertFalse(User.objects.filter(is_staff=True, is_superuser=False).exists())

    def test_blocked_admin_cannot_sign_in(self):
        admin = make_admin()
        self.client.force_login(self.founder)
        self.client.post(reverse("founder:team_toggle", args=[admin.pk]))
        admin.refresh_from_db()
        self.assertFalse(admin.is_active)
        self.client.logout()
        response = self.client.post(reverse("adminpanel:login"), {"email": "sakib@example.com", "password": "Admin-pass-123"})
        self.assertContains(response, "Email or password is wrong.")

    def test_admin_updates_order_and_client_is_emailed(self):
        booking = make_booking()
        self.client.force_login(make_admin())
        url = reverse("adminpanel:order", args=[booking.reference])
        response = self.client.post(url, {"o-status": "in_progress", "o-title": "Kickoff Arena", "o-quoted_price_bdt": "",
                                          "o-progress": "30", "o-due_date": "", "o-delivery_url": "", "o-admin_notes": "",
                                          "o-note": "Design started.", "o-notify_client": "on"})
        self.assertRedirects(response, url)
        booking.refresh_from_db()
        self.assertEqual((booking.status, booking.progress), ("in_progress", 30))
        self.assertEqual(mail.outbox[-1].to, ["rafiq@example.com"])
        self.client.post(reverse("adminpanel:order_message", args=[booking.reference]), {"m-body": "Call at 4?", "m-notify": "on"})
        self.assertIn("Sakib", mail.outbox[-1].body)
        msg = OrderMessage.objects.get(body="Call at 4?")
        self.assertEqual(msg.author.email, "sakib@example.com")
        self.assertTrue(msg.from_founder)


class ClientViewTests(TestCase):
    """The founder can open any client's dashboard."""

    def test_founder_sees_client_dashboard(self):
        founder = User.objects.create_superuser("f", "projectaethrix@gmail.com", "Founder-pass-123")
        nadia = User.objects.create_user("n", "nadia@example.com", "Clinic-app-2026", first_name="Nadia")
        order = make_booking(client=nadia, email="nadia@example.com", title="Clinic app", status="in_progress", progress=55)
        self.client.force_login(founder)
        clients = self.client.get(reverse("founder:clients"))
        self.assertContains(clients, reverse("founder:client", args=[nadia.pk]))
        page = self.client.get(reverse("founder:client", args=[nadia.pk]))
        self.assertContains(page, "Nadia's <em>dashboard.</em>")
        self.assertContains(page, "Clinic app")
        self.assertContains(page, 'data-progress="55"')
        self.assertContains(page, reverse("founder:order", args=[order.reference]))
        self.assertNotContains(page, reverse("portal:order", args=[order.reference]))
        self.assertEqual(self.client.get(reverse("founder:client", args=[founder.pk])).status_code, 404)


class ProjectManagementTests(TestCase):
    def setUp(self):
        self.founder = User.objects.create_superuser("f", "projectaethrix@gmail.com", "Founder-pass-123")
        self.client.force_login(self.founder)

    def test_add_toggle_edit_delete(self):
        Project.objects.all().delete()  # start without the two seeded demo projects
        self.client.post(reverse("founder:project_add"), {
            "title": "Kickoff Arena", "slug": "", "category": "website", "summary": "Turf booking",
            "description": "A turf booking site.\n\nBuilt for Mirpur.", "features_title": "What it does",
            "features": "Live slots — See free slots\nbKash payments", "roadmap_title": "", "roadmap": "", "roadmap_note": "",
            "closing_title": "", "closing": "",
            "live_url": "https://kickoff.example.com", "tech_stack": "Django, Tailwind", "is_published": "on", "sort_order": "0"})
        p = Project.objects.get()
        self.assertEqual(p.slug, "kickoff-arena")
        self.assertContains(self.client.get(reverse("studio:home")), "Kickoff Arena")
        detail = self.client.get(reverse("studio:project", args=["kickoff-arena"]))
        self.assertContains(detail, "<h3>Live slots</h3>")
        self.assertContains(detail, "Built for Mirpur.")
        self.client.post(reverse("founder:project_toggle", args=[p.pk]))
        self.assertNotContains(self.client.get(reverse("studio:home")), "Kickoff Arena")
        self.client.post(reverse("founder:project_edit", args=[p.pk]), {
            "title": "Kickoff Arena 2", "slug": "kickoff-arena", "category": "website", "summary": "", "description": "",
            "features_title": "What it does", "features": "", "roadmap_title": "", "roadmap": "", "roadmap_note": "",
            "closing_title": "", "closing": "", "live_url": "", "tech_stack": "", "sort_order": "1"})
        p.refresh_from_db()
        self.assertEqual(p.title, "Kickoff Arena 2")
        self.assertContains(self.client.get(reverse("founder:project_delete", args=[p.pk])), "Yes, delete it")
        self.client.post(reverse("founder:project_delete", args=[p.pk]))
        self.assertFalse(Project.objects.exists())
