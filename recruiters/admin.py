from django.contrib import admin
from .models import Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'user', 'industry', 'contact_person', 'is_approved', 'website')
    search_fields = ('company_name', 'user__email', 'contact_person', 'industry')
    list_filter = ('is_approved', 'industry')
