from django.contrib import admin
from .models import Job


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'package_lpa', 'location', 'status', 'deadline', 'created_at')
    list_filter = ('status', 'location', 'created_at')
    search_fields = ('title', 'company__company_name', 'description')
    filter_horizontal = ('required_skills',)
