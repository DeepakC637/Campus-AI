"""
Development settings for placementhub_project.
Safe defaults for local development and test runs.
"""
from .base import *

DEBUG = True

ALLOWED_HOSTS = ['*']

# Local development database (SQLite by default)
DATABASES = {
    'default': env.db('DATABASE_URL', default=f'sqlite:///{BASE_DIR / "db.sqlite3"}')
}

# Development-friendly cookies & redirect settings (no SSL redirect locally)
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
