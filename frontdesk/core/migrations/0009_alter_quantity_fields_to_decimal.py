"""
Migration to alter quantity fields from IntegerField to DecimalField.

The InventoryNeed and Appointment models had quantity fields changed
from IntegerField to DecimalField to support fractional ounce amounts.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0008_calllog"),
    ]

    operations = [
        migrations.AlterField(
            model_name="inventoryneed",
            name="quantity_needed",
            field=models.DecimalField(
                decimal_places=4,
                default=1,
                max_digits=10,
            ),
        ),
        migrations.AlterField(
            model_name="inventoryneed",
            name="quantity_fulfilled",
            field=models.DecimalField(
                decimal_places=4,
                default=0,
                max_digits=10,
            ),
        ),
        migrations.AlterField(
            model_name="appointment",
            name="quantity",
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                help_text="Quantity of product for this appointment (oz)",
                max_digits=10,
                null=True,
            ),
        ),
    ]
