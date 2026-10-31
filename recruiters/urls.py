from django.urls import path
from django.http import HttpResponse

app_name = 'recruiters'

def placeholder(request, *args, **kwargs):
    return HttpResponse("Recruiter portal endpoint placeholder")

urlpatterns = [
    path('dashboard/', placeholder, name='dashboard'),
    path('profile/', placeholder, name='profile'),
    path('jobs/', placeholder, name='jobs'),
    path('jobs/create/', placeholder, name='job_create'),
    path('jobs/<int:pk>/edit/', placeholder, name='job_edit'),
    path('jobs/<int:pk>/applicants/', placeholder, name='job_applicants'),
    path('applications/<int:pk>/status/', placeholder, name='update_application_status'),
    path('applications/<int:pk>/interview/', placeholder, name='schedule_interview'),
]
