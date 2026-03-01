from django.db import migrations, models


def populate_new_fields(apps, schema_editor):
    """Populate action/metal/metal_form from legacy category and bullion_type."""
    Customer = apps.get_model("core", "Customer")
    for c in Customer.objects.all():
        changed = False
        cat = c.category or ""
        bt = c.bullion_type or ""

        # Parse action from category
        if cat.startswith("BUY"):
            c.action = "BUYING"
            changed = True
        elif cat.startswith("SELL"):
            c.action = "SELLING"
            changed = True

        # Parse metal_form from category
        if "SCRAP" in cat:
            c.metal_form = "SCRAP"
            changed = True
        elif "BULLION" in cat:
            c.metal_form = "BULLION"
            changed = True

        # Parse metal from category suffix or bullion_type
        if "GOLD" in cat:
            c.metal = "GOLD"
            changed = True
        elif "SILVER" in cat:
            c.metal = "SILVER"
            changed = True
        elif bt:
            c.metal = bt
            changed = True

        if changed:
            c.save()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_daynote"),
    ]

    operations = [
        migrations.AddField(
            model_name="customer",
            name="action",
            field=models.CharField(
                blank=True,
                choices=[("BUYING", "Buying"), ("SELLING", "Selling")],
                default="",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="customer",
            name="metal",
            field=models.CharField(
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
        migrations.AddField(
            model_name="customer",
            name="metal_form",
            field=models.CharField(
                blank=True,
                choices=[
                    ("BULLION", "Bullion"),
                    ("SCRAP", "Scrap"),
                    ("OTHER", "Other"),
                ],
                default="",
                max_length=10,
            ),
        ),
        # Make legacy fields optional
        migrations.AlterField(
            model_name="customer",
            name="category",
            field=models.CharField(
                blank=True,
                choices=[
                    ("BUY_BULLION", "Buy Bullion"),
                    ("SELL_BULLION", "Sell Bullion"),
                    ("BUY_SCRAP_GOLD", "Buy Scrap Gold"),
                    ("BUY_SCRAP_SILVER", "Buy Scrap Silver"),
                ],
                default="",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="customer",
            name="bullion_type",
            field=models.CharField(
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
        # Populate new fields from legacy data
        migrations.RunPython(populate_new_fields, migrations.RunPython.noop),
    ]
