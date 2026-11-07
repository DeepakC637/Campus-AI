from django.urls import path
from . import views

app_name = 'recruiters'

urlpatterns = [
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('jobs/', views.jobs_view, name='jobs'),
    path('jobs/create/', views.job_create_view, name='job_create'),
    path('jobs/<int:pk>/edit/', views.job_edit_view, name='job_edit'),
    path('jobs/<int:pk>/applicants/', views.job_applicants_view, name='job_applicants'),
    path('applications/<int:pk>/status/', views.update_application_status_view, name='update_application_status'),
    path('applications/<int:pk>/interview/', views.schedule_interview_view, name='schedule_interview'),
]
