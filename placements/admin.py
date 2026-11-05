from django.contrib import admin
from .models import PlacementRecord


@admin.register(PlacementRecord)
class PlacementRecordAdmin(admin.ModelAdmin):
    list_display = ('student', 'company', 'package_lpa', 'offer_date', 'is_final')
    list_filter = ('is_final', 'offer_date')
    search_fields = ('student__full_name', 'student__roll_no', 'company__company_name')
