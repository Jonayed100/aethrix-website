from django import forms
from django.utils.text import slugify

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
            "admin_notes": forms.Textarea(attrs={"rows": 3, "placeholder": "Only you see this."}),
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
        fields = ["title", "slug", "category", "summary", "live_url", "tech_stack", "is_published", "sort_order"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "e.g. Kickoff Arena"}),
            "summary": forms.TextInput(attrs={"placeholder": "e.g. Futuristic turf booking website"}),
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
