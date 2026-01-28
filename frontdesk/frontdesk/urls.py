"""
URL configuration for J. Austin Front Desk Processing.
All URLs are served under '' - nginx handles the /frontdesk prefix.
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
]
