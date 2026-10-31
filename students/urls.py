from django.urls import path
from django.http import HttpResponse

app_name = 'students'

def placeholder(request, *args, **kwargs):
    return HttpResponse("Student portal endpoint placeholder")

urlpatterns = [
    path('dashboard/', placeholder, name='dashboard'),
    path('profile/edit/', placeholder, name='profile_edit'),
    path('resume/upload/', placeholder, name='resume_upload'),
    path('jobs/', placeholder, name='jobs'),
    path('jobs/<int:pk>/', placeholder, name='job_detail'),
    path('jobs/<int:pk>/apply/', placeholder, name='apply_job'),
    path('applications/', placeholder, name='applications'),
    path('skill-gap/<int:job_id>/', placeholder, name='skill_gap'),
    path('interviews/', placeholder, name='interviews'),
]
