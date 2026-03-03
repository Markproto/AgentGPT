"""
Migration to create CallLog model for phone call tracking.
"""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_producttoggle"),
    ]

    operations = [
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
                        choices=[("INBOUND", "Inbound"), ("OUTBOUND", "Outbound")],
                        default="INBOUND",
                        max_length=10,
                    ),
                ),
                (
                    "duration",
                    models.IntegerField(
                        blank=True,
                        null=True,
                        help_text="Duration in seconds",
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
    ]
