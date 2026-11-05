"""
URL configuration for placementhub_project project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core.views import landing_page
from accounts.views import login_view, logout_view, register_view

urlpatterns = [
    # Admin site
    path('admin/', admin.site.urls),

    # Public Landing Page
    path('', landing_page, name='landing'),

    # Auth routes (/auth/)
    path('auth/', include('accounts.urls')),

    # Direct top-level auth routes
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('register/', register_view, name='register'),

    # Student Portal (/student/)
    path('student/', include('students.urls')),

    # Recruiter Portal (/recruiter/)
    path('recruiter/', include('recruiters.urls')),

    # Admin Portal (/admin-portal/)
    path('admin-portal/', include('core.urls')),

    # Additional app modules
    path('jobs/', include('jobs.urls')),
    path('applications/', include('applications.urls')),
    path('interviews/', include('interviews.urls')),
    path('placements/', include('placements.urls')),
    path('api/', include('ai_engine.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
