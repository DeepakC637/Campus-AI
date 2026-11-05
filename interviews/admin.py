from django.contrib import admin
from .models import Interview


@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = ('application', 'round_type', 'mode', 'scheduled_at', 'status', 'result')
    list_filter = ('mode', 'status', 'scheduled_at')
    search_fields = ('application__student__full_name', 'application__job__title', 'round_type')
