from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    path('students/', views.admin_students_view, name='admin_students'),
    path('students/<int:student_id>/toggle-verify/', views.admin_student_toggle_verify_view, name='admin_student_toggle_verify'),
    path('recruiters/', views.admin_recruiters_view, name='admin_recruiters'),
    path('recruiters/<int:company_id>/toggle-approval/', views.admin_recruiter_toggle_approval_view, name='admin_recruiter_toggle_approval'),
    path('approvals/', views.admin_approvals_view, name='admin_approvals'),
    path('placements/', views.admin_placements_view, name='admin_placements'),
    path('placements/create/', views.admin_placement_create_view, name='admin_placement_create'),
    path('reports/', views.admin_reports_view, name='admin_reports'),
]
