from django import forms
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError

from .models import User


class LoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    remember_me = forms.BooleanField(required=False)


class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField()


class PasswordResetConfirmForm(forms.Form):
    otp = forms.CharField(max_length=6)
    password1 = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            raise ValidationError("Passwords do not match.")
        if p1:
            password_validation.validate_password(p1)
        return cleaned


class SignUpForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"autocomplete": "given-name", "placeholder": "First name"}),
    )
    last_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"autocomplete": "family-name", "placeholder": "Last name"}),
    )
    password1 = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password", "placeholder": "Create a password"}),
    )
    password2 = forms.CharField(
        label="Confirm password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password", "placeholder": "Enter the password again"}),
    )

    class Meta:
        model = User
        fields = ("first_name", "last_name", "username", "email")
        widgets = {
            "first_name": forms.TextInput(attrs={"autocomplete": "given-name"}),
            "last_name": forms.TextInput(attrs={"autocomplete": "family-name"}),
            "username": forms.TextInput(attrs={"autocomplete": "username", "placeholder": "Choose a username"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email", "placeholder": "you@example.com"}),
        }

    def clean_first_name(self):
        return self.cleaned_data["first_name"].strip()

    def clean_last_name(self):
        return self.cleaned_data["last_name"].strip()

    def clean_username(self):
        username = self.cleaned_data["username"].strip().lower()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("That username is already in use.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account already uses this email address.")
        return email

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("password1")
        password2 = cleaned.get("password2")
        if password1 and password2:
            if password1 != password2:
                self.add_error("password2", "The passwords do not match.")
            else:
                candidate = self.instance
                for field in ("first_name", "last_name", "username", "email"):
                    if cleaned.get(field):
                        setattr(candidate, field, cleaned[field])
                try:
                    password_validation.validate_password(password1, user=candidate)
                except ValidationError as error:
                    self.add_error("password1", error)
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user
