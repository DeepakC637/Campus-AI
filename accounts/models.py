from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    """
    Default User model untouched for Phase 3 scaffold.
    Custom fields (role, is_approved, email authentication) will be added in Phase 4.
    """
    pass
