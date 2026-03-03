"""
Migration to create ProductToggle model and seed initial toggle entries.
"""

from django.db import migrations, models


def seed_toggles(apps, schema_editor):
    """Create default toggle entries for all product categories."""
    ProductToggle = apps.get_model("core", "ProductToggle")
    categories = [
        "SCRAP_GOLD",
        "SCRAP_SILVER",
        "GOLD_EAGLES",
        "1OZ_SILVER_ROUNDS",
        "1OZ_SILVER_EAGLES",
    ]
    for cat in categories:
        ProductToggle.objects.get_or_create(category=cat, defaults={"is_active": False})


def remove_toggles(apps, schema_editor):
    ProductToggle = apps.get_model("core", "ProductToggle")
    ProductToggle.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_highcommandmessage"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProductToggle",
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
                    "category",
                    models.CharField(
                        choices=[
                            ("SCRAP_GOLD", "Scrap Gold"),
                            ("SCRAP_SILVER", "Scrap Silver"),
                            ("GOLD_EAGLES", "Gold Eagles"),
                            ("1OZ_SILVER_ROUNDS", "1 oz Silver Rounds"),
                            ("1OZ_SILVER_EAGLES", "1 oz Silver Eagles"),
                        ],
                        max_length=30,
                        unique=True,
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=False,
                        help_text="ON = auto-schedule appointment, OFF = callback required",
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "updated_by",
                    models.CharField(blank=True, default="", max_length=100),
                ),
            ],
            options={
                "verbose_name": "Product Toggle",
                "verbose_name_plural": "Product Toggles",
                "ordering": ["category"],
            },
        ),
        migrations.RunPython(seed_toggles, remove_toggles),
    ]
