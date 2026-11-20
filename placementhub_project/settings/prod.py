"""
Production settings for placementhub_project.
Configured for deployment on Render (free tier) with Render PostgreSQL.
"""
from .base import *
import dj_database_url
import environ
import os

env = environ.Env()

DEBUG = False

# SECURITY WARNING: keep the secret key used in production secret!
# Must be set in Render environment variables.
SECRET_KEY = env('SECRET_KEY')

# ALLOWED_HOSTS: Set via environment variable (e.g., 'placementhub.onrender.com')
# Default safely permits Render subdomains and custom domains
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['.onrender.com'])

# CSRF Trusted Origins for Render HTTPS domain
csrf_env = env.list('CSRF_TRUSTED_ORIGINS', default=[])
if csrf_env:
    CSRF_TRUSTED_ORIGINS = csrf_env
else:
    # Auto-generate https origins from ALLOWED_HOSTS (filtering local names)
    CSRF_TRUSTED_ORIGINS = [
        f"https://{host.lstrip('.')}"
        for host in ALLOWED_HOSTS
        if host not in ('localhost', '127.0.0.1', '*')
    ]

# Database configuration using dj-database-url
# Render automatically injects DATABASE_URL for attached Postgres instances
DATABASE_URL = env('DATABASE_URL', default=None)
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
            ssl_require=True,
        )
    }
else:
    DATABASES = {
        'default': env.db('DATABASE_URL', default=f'sqlite:///{BASE_DIR / "db.sqlite3"}')
    }

# WhiteNoise Static Files Storage for Production
# Serves compressed, cache-busted static files directly via WhiteNoise
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Production Security Hardening
SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=True)
SESSION_COOKIE_SECURE = env.bool('SESSION_COOKIE_SECURE', default=True)
CSRF_COOKIE_SECURE = env.bool('CSRF_COOKIE_SECURE', default=True)
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# =============================================================================
# MEDIA FILES LIMITATION (RENDER FREE TIER):
# Render's free tier uses an ephemeral filesystem. Any uploaded files (such as
# student resumes in media/resumes/ or company logos in media/company_logos/)
# will NOT persist across server redeploys, service restarts, or daily spin-downs.
# For persistent file storage in a commercial production deployment, an external
# object storage service must be used (e.g. AWS S3, Cloudflare R2, or Supabase Storage).
# For academic project demonstration purposes on Render free tier, ephemeral local
# filesystem storage is acceptable and functional during an active review session.
# =============================================================================
