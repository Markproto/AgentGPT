"""
Admin configuration for J. Austin Front Desk Processing.
"""

from django.contrib import admin
from .models import Customer, Interaction, TextTemplate, Match, Appointment, CallLog


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "phone",
        "email",
        "category",
        "bullion_type",
        "bullion_amount",
        "status",
        "source",
        "created_at",
    ]
    list_filter = ["category", "bullion_type", "status", "source"]
    search_fields = ["name", "phone", "email", "notes"]
    list_editable = ["status"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Interaction)
class InteractionAdmin(admin.ModelAdmin):
    list_display = ["customer", "type", "direction", "summary", "created_at"]
    list_filter = ["type", "direction"]
    search_fields = ["customer__name", "summary"]
    readonly_fields = ["created_at"]


@admin.register(TextTemplate)
class TextTemplateAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "is_active"]
    list_filter = ["category", "is_active"]
    search_fields = ["name", "content"]


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = [
        "buyer",
        "seller",
        "amount",
        "bullion_type",
        "status",
        "profit_margin",
        "created_at",
    ]
    list_filter = ["status", "bullion_type"]
    search_fields = ["buyer__name", "seller__name", "notes"]
    readonly_fields = ["created_at"]


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = [
        "customer",
        "datetime",
        "end_datetime",
        "purpose",
        "location",
        "status",
    ]
    list_filter = ["status", "location"]
    search_fields = ["customer__name", "purpose", "notes"]
    readonly_fields = ["created_at"]


@admin.register(CallLog)
class CallLogAdmin(admin.ModelAdmin):
    list_display = [
        "customer",
        "phone_number",
        "direction",
        "duration",
        "category_detected",
        "created_at",
    ]
    list_filter = ["direction", "category_detected"]
    search_fields = ["phone_number", "transcript", "customer__name"]
    readonly_fields = ["created_at"]
