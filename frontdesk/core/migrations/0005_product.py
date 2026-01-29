# Generated manually for Product model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_inventoryneed_appointment_inventory'),
    ]

    operations = [
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='e.g., American Eagle, Maple Leaf, Generic Bar', max_length=255)),
                ('metal', models.CharField(choices=[('GOLD', 'Gold'), ('SILVER', 'Silver'), ('PLATINUM', 'Platinum'), ('PALLADIUM', 'Palladium')], max_length=10)),
                ('size', models.CharField(help_text='e.g., 1 oz, 10 oz, 1/2 oz, 1 kg', max_length=50)),
                ('buy_premium', models.DecimalField(decimal_places=2, default=0, help_text='Premium above/below spot when BUYING from customers (negative = below spot)', max_digits=10)),
                ('sell_premium', models.DecimalField(decimal_places=2, default=0, help_text='Premium above/below spot when SELLING to customers (negative = below spot)', max_digits=10)),
                ('is_active', models.BooleanField(default=True)),
                ('notes', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['metal', 'name', 'size'],
            },
        ),
    ]
