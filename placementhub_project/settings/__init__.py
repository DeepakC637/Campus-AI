"""
Settings package for placementhub_project.
Defaults to dev settings for local development safety.
"""
import os

settings_module = os.environ.get('DJANGO_SETTINGS_MODULE', 'placementhub_project.settings.dev')
if settings_module in ('placementhub_project.settings', 'placementhub_project.settings.dev'):
    from .dev import *  # noqa: F401, F403
