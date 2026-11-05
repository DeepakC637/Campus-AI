from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.views import (
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
)
from django.shortcuts import render, redirect
from django.urls import reverse, reverse_lazy
from .forms import RegistrationForm, LoginForm
from .models import User


def get_role_redirect_url(user):
    """Determine dashboard redirect URL based on user role."""
    if user.role == User.Role.STUDENT:
        return reverse('students:dashboard')
    elif user.role == User.Role.RECRUITER:
        return reverse('recruiters:dashboard')
    elif user.role == User.Role.ADMIN or user.is_staff or user.is_superuser:
        return reverse('core:admin_dashboard')
    return reverse('landing')


def register_view(request):
    if request.user.is_authenticated:
        return redirect(get_role_redirect_url(request.user))

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            if user.role == User.Role.STUDENT:
                auth_login(request, user)
                messages.success(request, "Account created successfully! Welcome to PlacementHub.")
                return redirect('students:dashboard')
            elif user.role == User.Role.RECRUITER:
                messages.info(
                    request,
                    "Your recruiter account has been registered and is pending administrator approval. "
                    "You will be able to access the recruiter dashboard once approved."
                )
                return render(request, 'accounts/pending_approval.html', {'email': user.email})
    else:
        initial_role = request.GET.get('role', User.Role.STUDENT)
        form = RegistrationForm(initial={'role': initial_role})

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect(get_role_redirect_url(request.user))

    next_url = request.GET.get('next') or request.POST.get('next')

    if request.method == 'POST':
        form = LoginForm(request=request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user is not None:
                auth_login(request, user)
                messages.success(request, f"Welcome back, {user.email}!")

                if user.role == User.Role.RECRUITER and not user.is_approved:
                    messages.warning(request, "Your recruiter account is pending administrator approval.")
                    return render(request, 'accounts/pending_approval.html', {'email': user.email})

                if next_url:
                    return redirect(next_url)
                return redirect(get_role_redirect_url(user))
    else:
        form = LoginForm(request=request)

    return render(request, 'accounts/login.html', {'form': form, 'next': next_url})


def logout_view(request):
    auth_logout(request)
    messages.success(request, "You have been successfully logged out.")
    return redirect('landing')


class CustomPasswordResetView(PasswordResetView):
    template_name = 'accounts/password_reset.html'
    email_template_name = 'accounts/password_reset_email.html'
    success_url = reverse_lazy('accounts:password_reset_done')


class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'accounts/password_reset_done.html'


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'accounts/password_reset_confirm.html'
    success_url = reverse_lazy('accounts:password_reset_complete')


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'accounts/password_reset_complete.html'
