"""
Django settings for J. Austin Front Desk Processing.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    "FRONTDESK_SECRET_KEY",
    "django-insecure-change-me-in-production-jaustin-frontdesk-2024",
)

DEBUG = os.environ.get("FRONTDESK_DEBUG", "True").lower() in ("true", "1", "yes")

ALLOWED_HOSTS = [
    "agent.opentruthai.com",
    "frontdesk.huttonetwork.com",
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "192.168.1.99",
    "*",  # Allow all hosts for local development
]

ALLOWED_HOSTS += os.environ.get("FRONTDESK_ALLOWED_HOSTS", "").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "crispy_forms",
    "crispy_bootstrap5",
    "corsheaders",
    # Local
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "frontdesk.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "frontdesk.wsgi.application"

# Database - PostgreSQL
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("FRONTDESK_DB_NAME", "frontdesk"),
        "USER": os.environ.get("FRONTDESK_DB_USER", "postgres"),
        "PASSWORD": os.environ.get("FRONTDESK_DB_PASSWORD", "postgres"),
        "HOST": os.environ.get("FRONTDESK_DB_HOST", "localhost"),
        "PORT": os.environ.get("FRONTDESK_DB_PORT", "5432"),
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/Los_Angeles"
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# URL prefix - set via environment if behind reverse proxy
FORCE_SCRIPT_NAME = os.environ.get("SCRIPT_NAME", None)

# Login
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# CSRF - required for Django 4.0+ behind reverse proxy with SSL
CSRF_TRUSTED_ORIGINS = [
    "https://agent.opentruthai.com",
    "https://frontdesk.huttonetwork.com",
]

# Tell Django it's behind HTTPS proxy
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# CORS
CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS = [
    "https://agent.opentruthai.com",
    "https://frontdesk.huttonetwork.com",
]

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Celery Configuration
CELERY_BROKER_URL = os.environ.get("FRONTDESK_REDIS_URL", "redis://localhost:6379/1")
CELERY_RESULT_BACKEND = os.environ.get("FRONTDESK_REDIS_URL", "redis://localhost:6379/1")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "America/Los_Angeles"

# Third-party API Keys
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE = os.environ.get("TWILIO_PHONE", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GROK_API_KEY = os.environ.get("GROK_API_KEY", "")
FRONTDESK_AI_API_KEY = os.environ.get("FRONTDESK_AI_API_KEY", "")
