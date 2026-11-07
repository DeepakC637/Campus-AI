from django.urls import path
from . import views

app_name = 'students'

urlpatterns = [
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_view, name='profile_edit'),
    path('resume/', views.resume_view, name='resume'),
    path('resume/upload/', views.resume_view, name='resume_upload'),
    path('jobs/', views.jobs_view, name='jobs'),
    path('jobs/<int:pk>/', views.job_detail_view, name='job_detail'),
    path('jobs/<int:pk>/apply/', views.apply_job_view, name='apply_job'),
    path('applications/', views.applications_view, name='applications'),
    path('applications/<int:pk>/withdraw/', views.withdraw_application_view, name='withdraw_application'),
    path('skill-gap/<int:job_id>/', views.skill_gap_view, name='skill_gap'),
    path('interviews/', views.interviews_view, name='interviews'),
]
