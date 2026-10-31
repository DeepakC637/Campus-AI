from django.urls import path
from django.http import HttpResponse

app_name = 'accounts'

def placeholder(request):
    return HttpResponse("Auth endpoint placeholder")

urlpatterns = [
    path('login/', placeholder, name='login'),
    path('logout/', placeholder, name='logout'),
    path('register/', placeholder, name='register'),
    path('password-reset/', placeholder, name='password_reset'),
]
