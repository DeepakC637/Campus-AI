from functools import wraps
from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse


def role_required(allowed_roles):
    """
    Decorator for views that checks whether a user is logged in, has the
    required role, and if the user is a RECRUITER, that is_approved is True.
    """
    if isinstance(allowed_roles, str):
        allowed_roles = [allowed_roles]

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(f"{reverse('accounts:login')}?next={request.path}")

            if request.user.role not in allowed_roles:
                raise PermissionDenied(f"Access denied. Required role: {', '.join(allowed_roles)}")

            if request.user.role == 'RECRUITER' and not request.user.is_approved:
                raise PermissionDenied("Access denied. Recruiter account is pending admin approval.")

            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


class RoleRequiredMixin(AccessMixin):
    """
    Mixin for class-based views that enforces role membership and recruiter approval.
    """
    allowed_roles = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        allowed = self.allowed_roles
        if isinstance(allowed, str):
            allowed = [allowed]

        if request.user.role not in allowed:
            raise PermissionDenied(f"Access denied. Required role: {', '.join(allowed)}")

        if request.user.role == 'RECRUITER' and not request.user.is_approved:
            raise PermissionDenied("Access denied. Recruiter account is pending admin approval.")

        return super().dispatch(request, *args, **kwargs)
