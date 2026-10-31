from django import forms
from django.contrib.auth import authenticate, get_user_model, password_validation
from django.contrib.auth.forms import PasswordResetForm

from .models import Profile
from .utils import unique_username


class LoginForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={"autocomplete": "email", "autofocus": True, "placeholder": "you@company.com"}))
    password = forms.CharField(strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "current-password", "placeholder": "Your password"}))

    error_messages = {"invalid": "Email or password is wrong."}

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        email, password = cleaned.get("email"), cleaned.get("password")
        if email and password:
            self.user = authenticate(self.request, username=email, password=password)
            if self.user is None:
                raise forms.ValidationError(self.error_messages["invalid"], code="invalid")
        return cleaned


class SignupForm(forms.Form):
    name = forms.CharField(label="Full name", max_length=120,
                           widget=forms.TextInput(attrs={"autocomplete": "name", "placeholder": "Rafiq Ahmed"}))
    email = forms.EmailField(max_length=254, widget=forms.EmailInput(attrs={"autocomplete": "email", "placeholder": "you@company.com"}))
    phone = forms.CharField(label="Phone number", max_length=40,
                            widget=forms.TextInput(attrs={"type": "tel", "autocomplete": "tel", "placeholder": "+880 1XXX-XXXXXX"}),
                            error_messages={"required": "Please enter your phone number."})
    password1 = forms.CharField(label="Password", strip=False,
                                widget=forms.PasswordInput(attrs={"autocomplete": "new-password", "placeholder": "At least 8 characters"}))
    password2 = forms.CharField(label="Confirm password", strip=False,
                                widget=forms.PasswordInput(attrs={"autocomplete": "new-password", "placeholder": "Type it again"}))

    def clean_name(self):
        return self.cleaned_data["name"].strip()

    def clean_phone(self):
        phone = self.cleaned_data["phone"].strip()
        digits = sum(ch.isdigit() for ch in phone)
        if digits < 8 or any(ch not in "0123456789+-() " for ch in phone):
            raise forms.ValidationError("Enter a valid phone number, e.g. +880 1712-345678.")
        return phone

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists. Log in, or reset your password.")
        return email

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "The two passwords don't match.")
        elif p1:
            probe = get_user_model()(email=cleaned.get("email", ""), first_name=cleaned.get("name", ""))
            try:
                password_validation.validate_password(p1, probe)
            except forms.ValidationError as exc:
                self.add_error("password1", exc)
        return cleaned

    def save(self):
        d = self.cleaned_data
        user = get_user_model().objects.create_user(
            username=unique_username(d["email"]), email=d["email"], password=d["password1"], first_name=d["name"][:150],
        )
        Profile.objects.create(user=user, phone=d["phone"])
        return user


class ProfileForm(forms.Form):
    name = forms.CharField(label="Full name", max_length=120, widget=forms.TextInput(attrs={"autocomplete": "name"}))
    phone = forms.CharField(label="Phone number", max_length=40, required=False,
                            widget=forms.TextInput(attrs={"type": "tel", "autocomplete": "tel", "placeholder": "+880 1XXX-XXXXXX"}))
    company = forms.CharField(label="Company or brand", max_length=120, required=False,
                              widget=forms.TextInput(attrs={"autocomplete": "organization", "placeholder": "Optional"}))

    def save(self, user):
        d = self.cleaned_data
        user.first_name = d["name"].strip()[:150]
        user.save(update_fields=["first_name"])
        profile = Profile.for_user(user)
        profile.phone, profile.company = d["phone"].strip(), d["company"].strip()
        profile.save(update_fields=["phone", "company"])


class AethrixPasswordResetForm(PasswordResetForm):
    """Also sends reset links to clients who were invited but never set a password."""

    email = forms.EmailField(max_length=254, widget=forms.EmailInput(attrs={"autocomplete": "email", "placeholder": "you@company.com"}))

    def get_users(self, email):
        return get_user_model()._default_manager.filter(email__iexact=email, is_active=True)
