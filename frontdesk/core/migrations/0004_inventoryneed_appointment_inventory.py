# Generated migration for InventoryNeed and Appointment inventory fields

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_customer_action_metal_metalform"),
    ]

    operations = [
        # Create InventoryNeed model
        migrations.CreateModel(
            name="InventoryNeed",
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
                    "action",
                    models.CharField(
                        choices=[("BUY", "Buy"), ("SELL", "Sell")],
                        max_length=4,
                    ),
                ),
                (
                    "product",
                    models.CharField(
                        help_text="e.g., Gold Eagle, Silver Bar",
                        max_length=100,
                    ),
                ),
                (
                    "metal",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("GOLD", "Gold"),
                            ("SILVER", "Silver"),
                            ("PLATINUM", "Platinum"),
                            ("PALLADIUM", "Palladium"),
                        ],
                        default="",
                        max_length=10,
                    ),
                ),
                (
                    "size",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="e.g., 1 oz, 10 oz, 1 kg",
                        max_length=50,
                    ),
                ),
                ("quantity_needed", models.IntegerField(default=1)),
                ("quantity_fulfilled", models.IntegerField(default=0)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("OPEN", "Open"),
                            ("PARTIAL", "Partially Filled"),
                            ("FILLED", "Filled"),
                            ("CANCELED", "Canceled"),
                        ],
                        default="OPEN",
                        max_length=10,
                    ),
                ),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Inventory Need",
                "verbose_name_plural": "Inventory Needs",
                "ordering": ["-created_at"],
            },
        ),
        # Add inventory_need and quantity fields to Appointment
        migrations.AddField(
            model_name="appointment",
            name="inventory_need",
            field=models.ForeignKey(
                blank=True,
                help_text="Linked inventory need this appointment fulfills",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="appointments",
                to="core.inventoryneed",
            ),
        ),
        migrations.AddField(
            model_name="appointment",
            name="quantity",
            field=models.IntegerField(
                blank=True,
                help_text="Quantity of product for this appointment",
                null=True,
            ),
        ),
    ]
