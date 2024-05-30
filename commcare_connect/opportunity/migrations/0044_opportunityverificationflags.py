# Generated by Django 4.2.5 on 2024-05-02 16:24

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("opportunity", "0043_remove_uservisit_is_trial_alter_uservisit_status"),
    ]

    operations = [
        migrations.CreateModel(
            name="OpportunityVerificationFlags",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("duration", models.PositiveIntegerField(default=1)),
                ("gps", models.BooleanField(default=True)),
                ("duplicate", models.BooleanField(default=True)),
                ("location", models.PositiveIntegerField(default=10)),
                ("form_submission_start", models.TimeField(blank=True, null=True)),
                ("form_submission_end", models.TimeField(blank=True, null=True)),
                (
                    "opportunity",
                    models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to="opportunity.opportunity"),
                ),
            ],
        ),
    ]
