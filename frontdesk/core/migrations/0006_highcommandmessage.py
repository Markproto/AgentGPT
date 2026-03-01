# Generated manually for HighCommandMessage model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_product'),
    ]

    operations = [
        migrations.CreateModel(
            name='HighCommandMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message', models.TextField(help_text='The alert message from High Command')),
                ('sender_name', models.CharField(help_text='Name of the person sending the message', max_length=100)),
                ('status', models.CharField(choices=[('ACTIVE', 'Active'), ('ACKNOWLEDGED', 'Acknowledged'), ('ARCHIVED', 'Archived')], default='ACTIVE', max_length=12)),
                ('response', models.TextField(blank=True, default='', help_text='Response to the message')),
                ('responder_name', models.CharField(blank=True, default='', max_length=100)),
                ('responded_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
