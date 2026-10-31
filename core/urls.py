from django.urls import path
from django.http import HttpResponse

app_name = 'core'

def placeholder(request, *args, **kwargs):
    return HttpResponse("Admin portal endpoint placeholder")

urlpatterns = [
    path('dashboard/', placeholder, name='admin_dashboard'),
    path('students/', placeholder, name='admin_students'),
    path('recruiters/', placeholder, name='admin_recruiters'),
    path('approvals/', placeholder, name='admin_approvals'),
    path('placements/', placeholder, name='admin_placements'),
    path('placements/create/', placeholder, name='admin_placement_create'),
    path('reports/', placeholder, name='admin_reports'),
    path('reports/export/', placeholder, name='admin_reports_export'),
]
