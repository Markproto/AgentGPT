# Generated manually based on core/models.py

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Customer",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("phone", models.CharField(blank=True, default="", max_length=20)),
                ("email", models.EmailField(blank=True, default="", max_length=254)),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("BUY_BULLION", "Buy Bullion"),
                            ("SELL_BULLION", "Sell Bullion"),
                            ("BUY_SCRAP_GOLD", "Buy Scrap Gold"),
                            ("BUY_SCRAP_SILVER", "Buy Scrap Silver"),
                        ],
                        default="BUY_BULLION",
                        max_length=20,
                    ),
                ),
                (
                    "bullion_amount",
                    models.DecimalField(
                        blank=True,
                        decimal_places=4,
                        help_text="Amount in troy ounces",
                        max_digits=12,
                        null=True,
                    ),
                ),
                (
                    "bullion_type",
                    models.CharField(
                        choices=[
                            ("GOLD", "Gold"),
                            ("SILVER", "Silver"),
                            ("PLATINUM", "Platinum"),
                        ],
                        default="GOLD",
                        max_length=10,
                    ),
                ),
                (
                    "price_per_oz",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Desired price per troy ounce",
                        max_digits=10,
                        null=True,
                    ),
                ),
                ("notes", models.TextField(blank=True, default="")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("MATCHED", "Matched"),
                            ("CLOSED", "Closed"),
                            ("ACTIVE", "Active"),
                        ],
                        default="PENDING",
                        max_length=10,
                    ),
                ),
                (
                    "source",
                    models.CharField(
                        choices=[
                            ("WALK_IN", "Walk-In"),
                            ("PHONE", "Phone"),
                            ("TEXT", "Text"),
                            ("EMAIL", "Email"),
                            ("FRONTDESK_AI", "Front Desk AI"),
                        ],
                        default="WALK_IN",
                        max_length=15,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="TextTemplate",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("content", models.TextField()),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("GENERAL", "General"),
                            ("APPOINTMENT", "Appointment"),
                            ("PRICING", "Pricing"),
                            ("MATCHING", "Matching"),
                        ],
                        default="GENERAL",
                        max_length=15,
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "ordering": ["category", "name"],
            },
        ),
        migrations.CreateModel(
            name="Match",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "amount",
                    models.DecimalField(
                        decimal_places=4,
                        help_text="Amount in troy ounces",
                        max_digits=12,
                    ),
                ),
                (
                    "bullion_type",
                    models.CharField(
                        choices=[
                            ("GOLD", "Gold"),
                            ("SILVER", "Silver"),
                            ("PLATINUM", "Platinum"),
                        ],
                        max_length=10,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PROPOSED", "Proposed"),
                            ("ACCEPTED", "Accepted"),
                            ("COMPLETED", "Completed"),
                            ("CANCELED", "Canceled"),
                        ],
                        default="PROPOSED",
                        max_length=10,
                    ),
                ),
                (
                    "profit_margin",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Profit margin in dollars",
                        max_digits=10,
                        null=True,
                    ),
                ),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "buyer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="matches_as_buyer",
                        to="core.customer",
                    ),
                ),
                (
                    "seller",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="matches_as_seller",
                        to="core.customer",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "verbose_name_plural": "matches",
            },
        ),
        migrations.CreateModel(
            name="Interaction",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("CALL", "Call"),
                            ("TEXT", "Text"),
                            ("EMAIL", "Email"),
                        ],
                        max_length=5,
                    ),
                ),
                (
                    "direction",
                    models.CharField(
                        choices=[
                            ("INBOUND", "Inbound"),
                            ("OUTBOUND", "Outbound"),
                        ],
                        max_length=10,
                    ),
                ),
                ("summary", models.TextField(blank=True, default="")),
                (
                    "raw_data",
                    models.JSONField(
                        blank=True,
                        help_text="Raw API data",
                        null=True,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "customer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="interactions",
                        to="core.customer",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="CallLog",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("phone_number", models.CharField(max_length=20)),
                (
                    "direction",
                    models.CharField(
                        choices=[
                            ("INBOUND", "Inbound"),
                            ("OUTBOUND", "Outbound"),
                        ],
                        default="INBOUND",
                        max_length=10,
                    ),
                ),
                (
                    "duration",
                    models.IntegerField(
                        blank=True,
                        help_text="Duration in seconds",
                        null=True,
                    ),
                ),
                ("transcript", models.TextField(blank=True, default="")),
                (
                    "category_detected",
                    models.CharField(blank=True, default="", max_length=50),
                ),
                (
                    "frontdesk_ai_id",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="External ID from Front Desk AI",
                        max_length=255,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "customer",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="call_logs",
                        to="core.customer",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="Appointment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("datetime", models.DateTimeField()),
                ("end_datetime", models.DateTimeField(blank=True, null=True)),
                ("purpose", models.CharField(max_length=255)),
                (
                    "location",
                    models.CharField(
                        blank=True, default="J. Austin Office", max_length=255
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("SCHEDULED", "Scheduled"),
                            ("CONFIRMED", "Confirmed"),
                            ("COMPLETED", "Completed"),
                            ("CANCELED", "Canceled"),
                            ("NO_SHOW", "No Show"),
                        ],
                        default="SCHEDULED",
                        max_length=10,
                    ),
                ),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "customer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="appointments",
                        to="core.customer",
                    ),
                ),
                (
                    "match",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="appointments",
                        to="core.match",
                    ),
                ),
            ],
            options={
                "ordering": ["datetime"],
            },
        ),
    ]
