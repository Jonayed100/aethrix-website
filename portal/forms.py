from django import forms

from studio.models import BUDGET_MAX, BUDGET_MIN, SERVICE_CHOICES, Booking


class NewOrderForm(forms.ModelForm):
    """What a signed-in client fills in to order a project. Their name, email and
    phone come from their account, so they never type them twice."""

    services = forms.ChoiceField(
        label="What do you need?", choices=SERVICE_CHOICES, widget=forms.RadioSelect, initial="website",
        error_messages={"required": "Pick one: web development, application development or AI chatbot."},
    )

    class Meta:
        model = Booking
        fields = ["title", "services", "description", "budget_bdt", "timeline"]
        labels = {
            "title": "Project name",
            "description": "Project details",
            "budget_bdt": "Budget",
            "timeline": "When do you need it?",
        }
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "e.g. Turf booking website", "autofocus": True}),
            "description": forms.Textarea(attrs={
                "rows": 6,
                "placeholder": "What should it do? Who will use it? Any websites you like?\n\n"
                               "e.g. We run two turfs in Mirpur and want a booking website with online payment, "
                               "a slot calendar and an admin page for our staff.",
            }),
            "budget_bdt": forms.NumberInput(attrs={"type": "range", "min": BUDGET_MIN, "max": BUDGET_MAX, "step": 10000}),
        }
        error_messages = {
            "title": {"required": "Give your project a name."},
            "description": {"required": "Tell us about your project."},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["title"].required = True
        if not self.is_bound:
            self.initial.setdefault("budget_bdt", 80000)

    def clean_title(self):
        return self.cleaned_data["title"].strip()

    def clean_description(self):
        text = self.cleaned_data["description"].strip()
        if len(text) < 20:
            raise forms.ValidationError("Tell us a little more, at least a sentence or two.")
        return text


class ClientMessageForm(forms.Form):
    body = forms.CharField(label="Message", max_length=4000,
                           widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Ask a question, or share links, feedback or changes."}))
