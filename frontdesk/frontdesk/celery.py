"""
Celery configuration for J. Austin Front Desk Processing.
"""

import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "frontdesk.settings")

app = Celery("frontdesk")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
