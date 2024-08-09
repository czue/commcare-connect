# Generated by Django 4.2.5 on 2024-08-09 10:49

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("organization", "0006_userorganizationmembership_program_manager"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="userorganizationmembership",
            name="program_manager",
        ),
        migrations.AddField(
            model_name="organization",
            name="program_manager",
            field=models.BooleanField(default=False),
        ),
    ]
