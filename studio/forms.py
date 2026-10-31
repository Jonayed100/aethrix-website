from django import forms
from django.utils import timezone

from .models import BUDGET_MAX, BUDGET_MIN, CALL_TIME_CHOICES, SERVICE_CHOICES, Booking


class BookingForm(forms.ModelForm):
    services = forms.MultipleChoiceField(
        choices=SERVICE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        error_messages={"required": "Pick at least one: web development, application development or AI chatbot."},
    )
    preferred_time = forms.ChoiceField(
        choices=[("", "Any time")] + CALL_TIME_CHOICES, required=False, initial="15:00",
        widget=forms.Select(attrs={"aria-label": "Call time"}),
    )
    # Hidden from people; bots tend to fill it in.
    website_url = forms.CharField(required=False, label="Leave this empty")

    class Meta:
        model = Booking
        fields = [
            "name", "email", "phone", "company", "services", "budget_bdt",
            "timeline", "preferred_date", "preferred_time", "description",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"autocomplete": "name", "placeholder": "Rafiq Ahmed"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email", "placeholder": "rafiq@company.com"}),
            "phone": forms.TextInput(attrs={"type": "tel", "autocomplete": "tel", "placeholder": "+880 1XXX-XXXXXX"}),
            "company": forms.TextInput(attrs={"autocomplete": "organization", "placeholder": "Optional"}),
            "budget_bdt": forms.NumberInput(attrs={"type": "range", "min": BUDGET_MIN, "max": BUDGET_MAX, "step": 10000}),
            "preferred_date": forms.DateInput(attrs={"type": "date", "aria-label": "Call date"}, format="%Y-%m-%d"),
            "description": forms.Textarea(attrs={
                "rows": 5,
                "placeholder": "We run two turfs in Mirpur and want a booking website with online payment, "
                               "a slot calendar and an admin page for our staff.",
            }),
        }
        error_messages = {
            "name": {"required": "Please enter your name."},
            "email": {"required": "Please enter your email.", "invalid": "That email doesn't look right."},
            "description": {"required": "Please describe your work."},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound:
            self.initial.setdefault("services", ["website"])
            self.initial.setdefault("budget_bdt", 80000)
        self.fields["preferred_date"].widget.attrs["min"] = timezone.localdate().isoformat()

    @property
    def selected_services(self):
        value = self["services"].value() or []
        return [str(v) for v in value]

    def clean_name(self):
        return self.cleaned_data["name"].strip()

    def clean_description(self):
        text = self.cleaned_data["description"].strip()
        if len(text) < 20:
            raise forms.ValidationError("Tell us a little more about your work, at least a sentence or two.")
        return text

    def clean_preferred_date(self):
        day = self.cleaned_data.get("preferred_date")
        if day:
            if day < timezone.localdate():
                raise forms.ValidationError("Please pick today or a later date.")
            if day.weekday() == 4:
                raise forms.ValidationError("We are closed on Fridays. Please pick Saturday to Thursday.")
        return day

    def clean_services(self):
        return ",".join(self.cleaned_data["services"])

    def is_spam(self):
        return bool(self.cleaned_data.get("website_url"))
