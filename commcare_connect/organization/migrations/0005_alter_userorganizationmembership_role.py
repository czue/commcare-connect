# Generated by Django 4.2.5 on 2024-06-03 08:13

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("organization", "0004_userorganizationmembership_accepted_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="userorganizationmembership",
            name="role",
            field=models.CharField(
                choices=[("admin", "Admin"), ("member", "Member"), ("viewer", "Viewer")],
                default="member",
                max_length=20,
            ),
        ),
    ]
