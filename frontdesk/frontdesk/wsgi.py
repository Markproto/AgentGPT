"""
WSGI config for J. Austin Front Desk Processing.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "frontdesk.settings")

application = get_wsgi_application()
