"""
URL configuration for core app.
All URLs are relative - nginx handles the /frontdesk prefix.
"""

from django.urls import path
from . import views, api_views

urlpatterns = [
    # Dashboard
    path("", views.dashboard, name="dashboard"),
    # Authentication
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    # Customers
    path("customers/", views.customer_list, name="customer_list"),
    path("customers/api/", views.customer_api, name="customer_api"),
    path("customers/<int:pk>/", views.customer_detail, name="customer_detail"),
    # Matching
    path("matching/", views.matching_view, name="matching"),
    path("matching/generate/", views.generate_matches, name="generate_matches"),
    path("matching/<int:pk>/<str:action>/", views.match_action, name="match_action"),
    # Appointments
    path("appointments/", views.appointment_list, name="appointment_list"),
    path("appointments/create/", views.appointment_create, name="appointment_create"),
    path("appointments/api/", views.appointment_api, name="appointment_api"),
    # Calendar
    path("calendar/", views.calendar_view, name="calendar"),
    # Texting
    path("texting/", views.texting_view, name="texting"),
    path("texting/send/", views.send_text, name="send_text"),
    path("texting/templates/", views.template_manage, name="template_manage"),
    path("texting/templates/api/", views.template_api, name="template_api"),
    # Call Log
    path("calls/", views.call_log_view, name="call_log"),
    path("calls/webhook/", views.call_webhook, name="call_webhook"),
    path("calls/sync/", views.sync_calls, name="sync_calls"),
    # CSV Import/Export
    path("import/", views.csv_import_view, name="csv_import"),
    path("export/calls/", views.csv_export_calls, name="csv_export_calls"),
    path("export/texts/", views.csv_export_texts, name="csv_export_texts"),
    # Conversation History
    path("conversation/<int:pk>/", views.conversation_view, name="conversation"),
    # Inbound SMS Webhook (Twilio)
    path("sms/webhook/", views.sms_webhook, name="sms_webhook"),
    # Additional APIs
    path("api/dashboard/stats/", api_views.dashboard_stats_api, name="dashboard_stats_api"),
    path("api/customers/search/", api_views.customer_search_api, name="customer_search_api"),
    path("api/interactions/create/", api_views.interaction_create_api, name="interaction_create_api"),
]
