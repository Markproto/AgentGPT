"""
Models for J. Austin Front Desk Processing - Bullion/Scrap Metal CRM.
"""

from django.db import models
from django.contrib.auth.models import User


class Customer(models.Model):
    """Customer record for bullion/scrap metal transactions."""

    class Category(models.TextChoices):
        BUY_BULLION = "BUY_BULLION", "Buy Bullion"
        SELL_BULLION = "SELL_BULLION", "Sell Bullion"
        BUY_SCRAP_GOLD = "BUY_SCRAP_GOLD", "Buy Scrap Gold"
        BUY_SCRAP_SILVER = "BUY_SCRAP_SILVER", "Buy Scrap Silver"

    class Action(models.TextChoices):
        BUYING = "BUYING", "Buying"
        SELLING = "SELLING", "Selling"

    class Metal(models.TextChoices):
        GOLD = "GOLD", "Gold"
        SILVER = "SILVER", "Silver"
        PLATINUM = "PLATINUM", "Platinum"
        PALLADIUM = "PALLADIUM", "Palladium"

    class MetalForm(models.TextChoices):
        BULLION = "BULLION", "Bullion"
        SCRAP = "SCRAP", "Scrap"
        OTHER = "OTHER", "Other"

    class BullionType(models.TextChoices):
        GOLD = "GOLD", "Gold"
        SILVER = "SILVER", "Silver"
        PLATINUM = "PLATINUM", "Platinum"
        PALLADIUM = "PALLADIUM", "Palladium"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        MATCHED = "MATCHED", "Matched"
        CLOSED = "CLOSED", "Closed"
        ACTIVE = "ACTIVE", "Active"

    class Source(models.TextChoices):
        WALK_IN = "WALK_IN", "Walk-In"
        PHONE = "PHONE", "Phone"
        TEXT = "TEXT", "Text"
        EMAIL = "EMAIL", "Email"
        FRONTDESK_AI = "FRONTDESK_AI", "Front Desk AI"

    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    # New category fields (optional - pick one from each when applicable)
    action = models.CharField(
        max_length=10, choices=Action.choices, blank=True, default=""
    )
    metal = models.CharField(
        max_length=10, choices=Metal.choices, blank=True, default=""
    )
    metal_form = models.CharField(
        max_length=10, choices=MetalForm.choices, blank=True, default=""
    )
    # Legacy category field (kept for backward compat)
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        blank=True,
        default="",
    )
    bullion_amount = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Amount in troy ounces",
    )
    bullion_type = models.CharField(
        max_length=10,
        choices=BullionType.choices,
        blank=True,
        default="",
    )
    price_per_oz = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Desired price per troy ounce",
    )
    notes = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    source = models.CharField(
        max_length=15,
        choices=Source.choices,
        default=Source.WALK_IN,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"


class Interaction(models.Model):
    """Record of interactions with customers."""

    class Type(models.TextChoices):
        CALL = "CALL", "Call"
        TEXT = "TEXT", "Text"
        EMAIL = "EMAIL", "Email"

    class Direction(models.TextChoices):
        INBOUND = "INBOUND", "Inbound"
        OUTBOUND = "OUTBOUND", "Outbound"

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="interactions",
    )
    type = models.CharField(max_length=5, choices=Type.choices)
    direction = models.CharField(max_length=10, choices=Direction.choices)
    summary = models.TextField(blank=True, default="")
    raw_data = models.JSONField(null=True, blank=True, help_text="Raw API data")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_type_display()} - {self.customer.name} ({self.created_at:%Y-%m-%d %H:%M})"


class TextTemplate(models.Model):
    """Reusable text message templates."""

    class Category(models.TextChoices):
        GENERAL = "GENERAL", "General"
        APPOINTMENT = "APPOINTMENT", "Appointment"
        PRICING = "PRICING", "Pricing"
        MATCHING = "MATCHING", "Matching"

    name = models.CharField(max_length=255)
    content = models.TextField()
    category = models.CharField(
        max_length=15,
        choices=Category.choices,
        default=Category.GENERAL,
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"


class Match(models.Model):
    """Matched buyer-seller pairs for bullion transactions."""

    class Status(models.TextChoices):
        PROPOSED = "PROPOSED", "Proposed"
        ACCEPTED = "ACCEPTED", "Accepted"
        COMPLETED = "COMPLETED", "Completed"
        CANCELED = "CANCELED", "Canceled"

    buyer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="matches_as_buyer",
    )
    seller = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="matches_as_seller",
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        help_text="Amount in troy ounces",
    )
    bullion_type = models.CharField(
        max_length=10,
        choices=Customer.BullionType.choices,
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PROPOSED,
    )
    profit_margin = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Profit margin in dollars",
    )
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "matches"

    def __str__(self):
        return f"Match: {self.buyer.name} <-> {self.seller.name} ({self.amount} oz {self.bullion_type})"


class Appointment(models.Model):
    """Scheduled appointments with customers."""

    class Status(models.TextChoices):
        SCHEDULED = "SCHEDULED", "Scheduled"
        CONFIRMED = "CONFIRMED", "Confirmed"
        COMPLETED = "COMPLETED", "Completed"
        CANCELED = "CANCELED", "Canceled"
        NO_SHOW = "NO_SHOW", "No Show"

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="appointments",
    )
    match = models.ForeignKey(
        Match,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="appointments",
    )
    datetime = models.DateTimeField()
    end_datetime = models.DateTimeField(null=True, blank=True)
    purpose = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True, default="J. Austin Office")
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.SCHEDULED,
    )
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["datetime"]

    def __str__(self):
        return f"{self.customer.name} - {self.purpose} ({self.datetime:%Y-%m-%d %H:%M})"


class DayNote(models.Model):
    """Day notes - reminders and memos that aren't appointments."""

    date = models.DateField()
    time = models.TimeField(null=True, blank=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["date", "time"]

    def __str__(self):
        return f"Note: {self.content[:50]} ({self.date})"


class CallLog(models.Model):
    """Log of phone calls, integrated with Front Desk AI."""

    class Direction(models.TextChoices):
        INBOUND = "INBOUND", "Inbound"
        OUTBOUND = "OUTBOUND", "Outbound"

    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="call_logs",
    )
    phone_number = models.CharField(max_length=20)
    direction = models.CharField(
        max_length=10,
        choices=Direction.choices,
        default=Direction.INBOUND,
    )
    duration = models.IntegerField(
        null=True,
        blank=True,
        help_text="Duration in seconds",
    )
    transcript = models.TextField(blank=True, default="")
    category_detected = models.CharField(max_length=50, blank=True, default="")
    frontdesk_ai_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="External ID from Front Desk AI",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        customer_name = self.customer.name if self.customer else "Unknown"
        return f"Call: {customer_name} - {self.phone_number} ({self.created_at:%Y-%m-%d %H:%M})"
