from django import forms
from django.contrib.auth import authenticate
from .models import User


class RegistrationForm(forms.Form):
    ROLE_CHOICES = (
        (User.Role.STUDENT, 'Student'),
        (User.Role.RECRUITER, 'Recruiter'),
    )
    role = forms.ChoiceField(choices=ROLE_CHOICES, initial=User.Role.STUDENT)
    email = forms.EmailField(required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)
    confirm_password = forms.CharField(widget=forms.PasswordInput, required=True)

    def clean_email(self):
        email = self.cleaned_data.get('email', '').lower().strip()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data

    def save(self):
        data = self.cleaned_data
        role = data['role']
        is_approved = False if role == User.Role.RECRUITER else True
        user = User.objects.create_user(
            email=data['email'],
            password=data['password'],
            role=role,
            is_approved=is_approved,
            username=data['email'].split('@')[0]
        )
        return user


class LoginForm(forms.Form):
    email = forms.EmailField(required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')
        if email and password:
            email = email.lower().strip()
            self.user_cache = authenticate(self.request, username=email, password=password)
            if self.user_cache is None:
                # Also try passing email keyword
                self.user_cache = authenticate(self.request, email=email, password=password)

            if self.user_cache is None:
                raise forms.ValidationError("Invalid email or password.")
            elif not self.user_cache.is_active:
                raise forms.ValidationError("This account is inactive.")
        return cleaned_data

    def get_user(self):
        return self.user_cache
