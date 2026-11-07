from django.db import models
from django.conf import settings


class Company(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='company_profile'
    )
    company_name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    website = models.URLField(blank=True, default='')
    industry = models.CharField(max_length=100, blank=True, default='')
    contact_person = models.CharField(max_length=150, blank=True, default='')
    logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)
    is_approved = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        # On creation, sync default with user.is_approved if not explicitly set
        if self._state.adding and hasattr(self, 'user') and self.user:
            if not self.is_approved:
                self.is_approved = self.user.is_approved
        super().save(*args, **kwargs)

    def __str__(self):
        return self.company_name


def set_recruiter_approval(company, approved: bool):
    """
    Single authoritative write path to keep User.is_approved and
    Company.is_approved strictly synchronized.
    """
    company.is_approved = approved
    company.save(update_fields=['is_approved'])
    company.user.is_approved = approved
    company.user.save(update_fields=['is_approved'])
