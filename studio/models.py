import secrets
from urllib.parse import urlparse

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

# The three services Project Aethrix offers.
SERVICE_CHOICES = [
    ("website", "Web development"),
    ("app", "Application development"),
    ("chatbot", "AI chatbot"),
]
# "other" stays readable for bookings made before it was removed.
SERVICE_LABELS = {**dict(SERVICE_CHOICES), "other": "Something else"}

CALL_TIME_CHOICES = [
    ("10:00", "10:00 AM"),
    ("11:00", "11:00 AM"),
    ("12:00", "12:00 PM"),
    ("14:00", "2:00 PM"),
    ("15:00", "3:00 PM"),
    ("16:00", "4:00 PM"),
    ("17:00", "5:00 PM"),
    ("18:00", "6:00 PM"),
]

BUDGET_MIN = 20_000
BUDGET_MAX = 500_000

TRACK_STEPS = ["Received", "Call", "Building", "Delivered"]


def format_bdt(amount):
    """Format taka the Bangladeshi way: 5,00,000."""
    if amount is None:
        return ""
    digits = str(int(amount))
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        digits = ",".join(groups + [tail])
    return f"৳ {digits}"


class Project(models.Model):
    """A demo project shown in the Demo projects section."""

    class Category(models.TextChoices):
        WEBSITE = "website", "Website"
        APP = "app", "App"
        CHATBOT = "chatbot", "AI chatbot"

    title = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    category = models.CharField(max_length=20, choices=Category.choices)
    summary = models.CharField(max_length=220, blank=True, help_text="One line clients see under the title.")
    live_url = models.URLField("Live demo link", blank=True, help_text="Leave empty to show 'Link coming soon'.")
    tech_stack = models.CharField(max_length=200, blank=True, help_text="Comma separated, e.g. React, Django, PostgreSQL")
    is_published = models.BooleanField("Show on website", default=True)
    sort_order = models.PositiveIntegerField(default=0, help_text="Lower numbers show first.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "-created_at"]
        verbose_name = "demo project"

    def __str__(self):
        return self.title

    @property
    def domain(self):
        if not self.live_url:
            return ""
        return urlparse(self.live_url).netloc.removeprefix("www.")

    @property
    def tech_list(self):
        return [t.strip() for t in self.tech_stack.split(",") if t.strip()]


def new_reference():
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    stamp = timezone.localdate().strftime("%y%m")
    return f"AX-{stamp}-" + "".join(secrets.choice(alphabet) for _ in range(4))


class Booking(models.Model):
    """A project booking from the website. Once accepted it becomes the client's order."""

    class Status(models.TextChoices):
        NEW = "new", "New"
        CONTACTED = "contacted", "Contacted"
        CONFIRMED = "confirmed", "Call confirmed"
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"
        DECLINED = "declined", "Declined"

    class Timeline(models.TextChoices):
        ASAP = "asap", "As soon as possible"
        ONE_MONTH = "1_month", "Within 1 month"
        ONE_TO_THREE = "1_3_months", "1–3 months"
        EXPLORING = "exploring", "Just exploring"

    ACTIVE_STATUSES = [Status.NEW, Status.CONTACTED, Status.CONFIRMED, Status.IN_PROGRESS]
    WORKING_STATUSES = [Status.CONTACTED, Status.CONFIRMED, Status.IN_PROGRESS]
    CLIENT_LABELS = {
        "new": "Received",
        "contacted": "In review",
        "confirmed": "Call confirmed",
        "in_progress": "In progress",
        "completed": "Completed",
        "declined": "Closed",
    }

    reference = models.CharField(max_length=16, unique=True, editable=False)
    client = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                               related_name="orders", help_text="The client account that can see this order.")
    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField("Phone or WhatsApp", max_length=40, blank=True)
    company = models.CharField("Company or brand", max_length=120, blank=True)
    services = models.CharField(max_length=120, help_text="Comma separated service keys")
    budget_bdt = models.PositiveIntegerField(
        "Budget (BDT)",
        validators=[MinValueValidator(BUDGET_MIN), MaxValueValidator(BUDGET_MAX)],
    )
    timeline = models.CharField(max_length=20, choices=Timeline.choices, default=Timeline.ONE_MONTH)
    preferred_date = models.DateField("Preferred call date", null=True, blank=True)
    preferred_time = models.CharField("Preferred call time", max_length=5, choices=CALL_TIME_CHOICES, blank=True)
    description = models.TextField("About the work")

    # Order details the founder fills in; clients see these in their dashboard.
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW, db_index=True)
    title = models.CharField("Project name", max_length=120, blank=True)
    quoted_price_bdt = models.PositiveIntegerField("Quoted price (BDT)", null=True, blank=True)
    progress = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(100)])
    due_date = models.DateField(null=True, blank=True)
    delivery_url = models.URLField("Delivery link", blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    admin_notes = models.TextField("Private notes", blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.reference} · {self.name}"

    def save(self, *args, **kwargs):
        if not self.reference:
            ref = new_reference()
            while Booking.objects.filter(reference=ref).exists():
                ref = new_reference()
            self.reference = ref
        if self.status == self.Status.COMPLETED:
            self.progress = 100
            self.completed_at = self.completed_at or timezone.now()
        else:
            self.completed_at = None
        super().save(*args, **kwargs)

    # --- Display helpers ---------------------------------------------------------

    @property
    def service_keys(self):
        return [s for s in self.services.split(",") if s]

    @property
    def services_display(self):
        return ", ".join(SERVICE_LABELS.get(s, s) for s in self.service_keys)

    @property
    def display_title(self):
        return self.title or self.services_display or "Project"

    @property
    def budget_display(self):
        suffix = "+" if self.budget_bdt >= BUDGET_MAX else ""
        return format_bdt(self.budget_bdt) + suffix

    @property
    def quote_display(self):
        return format_bdt(self.quoted_price_bdt) if self.quoted_price_bdt else ""

    @property
    def value_bdt(self):
        return self.quoted_price_bdt or self.budget_bdt or 0

    @property
    def call_display(self):
        if not self.preferred_date:
            return "Any time"
        day = self.preferred_date.strftime("%a %d %b %Y")
        return f"{day}, {self.get_preferred_time_display() or 'any time'} (GMT+6)"

    @property
    def client_status(self):
        return self.CLIENT_LABELS.get(self.status, self.get_status_display())

    @property
    def is_open(self):
        return self.status in self.ACTIVE_STATUSES

    @property
    def stage(self):
        """Index into TRACK_STEPS; -1 when the order was closed."""
        return {"new": 0, "contacted": 0, "confirmed": 1, "in_progress": 2, "completed": 3}.get(self.status, -1)

    @property
    def track(self):
        stage = self.stage
        return [{"label": label, "done": i < stage or (stage == 3 and i == 3), "current": i == stage and stage != 3}
                for i, label in enumerate(TRACK_STEPS)]


class OrderMessage(models.Model):
    """A message or update on an order, shown to both the founder and the client."""

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="messages")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    from_founder = models.BooleanField(default=False)
    is_event = models.BooleanField(default=False, help_text="Automatic note, e.g. a status change.")
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.booking.reference}: {self.body[:40]}"
