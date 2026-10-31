from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.utils.text import slugify

from accounts.models import Profile
from accounts.utils import unique_username

from studio.models import Booking, Project, format_bdt

CLIENT_FIELDS = {
    "status": "Status",
    "title": "Project name",
    "quoted_price_bdt": "Quoted price",
    "progress": "Progress",
    "due_date": "Due date",
    "delivery_url": "Delivery link",
}


class OrderForm(forms.ModelForm):
    notify_client = forms.BooleanField(required=False, initial=True, label="Email the client about these changes")
    note = forms.CharField(required=False, label="Note for the client",
                           widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Optional, e.g. 'Homepage design is ready for review.'"}))

    class Meta:
        model = Booking
        fields = ["status", "title", "quoted_price_bdt", "progress", "due_date", "delivery_url", "admin_notes"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "e.g. Turf booking website"}),
            "quoted_price_bdt": forms.NumberInput(attrs={"min": 0, "step": 1000, "placeholder": "e.g. 120000"}),
            "progress": forms.NumberInput(attrs={"type": "range", "min": 0, "max": 100, "step": 5, "data-out": "progOut", "data-bar": "progBar"}),
            "due_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "delivery_url": forms.URLInput(attrs={"placeholder": "https://"}),
            "admin_notes": forms.Textarea(attrs={"rows": 3, "placeholder": "Only the founder and admins see this."}),
        }

    def client_changes(self):
        """(label, new value) for each field the client can see that changed."""
        b = self.instance
        out = []
        for name in self.changed_data:
            if name not in CLIENT_FIELDS:
                continue
            if name == "status":
                value = b.client_status
            elif name == "quoted_price_bdt":
                value = format_bdt(b.quoted_price_bdt) if b.quoted_price_bdt else "Removed"
            elif name == "progress":
                value = f"{b.progress}%"
            elif name == "due_date":
                value = b.due_date.strftime("%d %b %Y") if b.due_date else "Removed"
            else:
                value = getattr(b, name) or "Removed"
            out.append((CLIENT_FIELDS[name], value))
        return out


class FounderMessageForm(forms.Form):
    body = forms.CharField(label="Message to the client", max_length=4000,
                           widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Write an update or a question for the client."}))
    notify = forms.BooleanField(required=False, initial=True, label="Also email it to the client")


class ProjectForm(forms.ModelForm):
    slug = forms.SlugField(required=False, max_length=140, help_text="Leave empty to make one from the title.")

    class Meta:
        model = Project
        fields = ["title", "slug", "category", "summary", "description", "features_title", "features",
                  "roadmap_title", "roadmap", "roadmap_note", "closing_title", "closing",
                  "live_url", "tech_stack", "is_published", "sort_order"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "e.g. Floodlit"}),
            "summary": forms.TextInput(attrs={"placeholder": "e.g. An online booking platform for football turfs in Dhaka."}),
            "description": forms.Textarea(attrs={"rows": 4}),
            "features": forms.Textarea(attrs={"rows": 7, "placeholder": "Live slot availability across multiple turfs\nSmart search — Type what you want and it filters for you"}),
            "roadmap": forms.Textarea(attrs={"rows": 5}),
            "closing": forms.Textarea(attrs={"rows": 4}),
            "live_url": forms.URLInput(attrs={"placeholder": "https://"}),
            "tech_stack": forms.TextInput(attrs={"placeholder": "e.g. Django, Tailwind, PostgreSQL"}),
            "sort_order": forms.NumberInput(attrs={"min": 0}),
        }

    def clean(self):
        cleaned = super().clean()
        base = cleaned.get("slug") or slugify(cleaned.get("title") or "")[:130] or "project"
        slug, n = base, 2
        others = Project.objects.exclude(pk=self.instance.pk)
        while others.filter(slug=slug).exists():
            slug = f"{base}-{n}"
            n += 1
        cleaned["slug"] = slug
        self.instance.slug = slug
        return cleaned


class AdminCreateForm(forms.Form):
    """The founder adds a team admin who can handle orders in the admin dashboard."""

    name = forms.CharField(label="Full name", max_length=120, widget=forms.TextInput(attrs={"placeholder": "e.g. Rafi Ahmed"}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={"placeholder": "admin@example.com"}))
    phone = forms.CharField(label="Phone number", max_length=40, required=False, widget=forms.TextInput(attrs={"type": "tel"}))
    password = forms.CharField(label="Temporary password", strip=False,
                               widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
                               help_text="Share it with them privately. They can change it in their Account page.")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password"):
            probe = get_user_model()(email=cleaned.get("email", ""), first_name=cleaned.get("name", ""))
            try:
                password_validation.validate_password(cleaned["password"], probe)
            except forms.ValidationError as exc:
                self.add_error("password", exc)
        return cleaned

    def save(self):
        d = self.cleaned_data
        user = get_user_model().objects.create_user(
            username=unique_username(d["email"]), email=d["email"], password=d["password"],
            first_name=d["name"].strip()[:150], is_staff=True,
        )
        Profile.objects.create(user=user, phone=d["phone"].strip(), email_verified=True)
        return user


class AdminEditForm(forms.Form):
    """The founder edits an admin's name and phone."""

    name = forms.CharField(label="Full name", max_length=120)
    phone = forms.CharField(label="Phone number", max_length=40, required=False, widget=forms.TextInput(attrs={"type": "tel"}))


class AdminPasswordForm(forms.Form):
    """The founder gives an admin a new password (for example, if they forgot it)."""

    password1 = forms.CharField(label="New password", strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))
    password2 = forms.CharField(label="Type it again", strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "The two passwords don't match.")
        elif p1:
            try:
                password_validation.validate_password(p1, self.user)
            except forms.ValidationError as exc:
                self.add_error("password1", exc)
        return cleaned
