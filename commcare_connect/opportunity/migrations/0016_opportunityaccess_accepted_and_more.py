# Generated by Django 4.2.5 on 2023-09-12 15:11

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("opportunity", "0015_remove_opportunityaccess_date_claimed"),
    ]

    operations = [
        migrations.AddField(
            model_name="opportunityaccess",
            name="accepted",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="opportunityaccess",
            name="invite_id",
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddIndex(
            model_name="opportunityaccess",
            index=models.Index(fields=["invite_id"], name="opportunity_invite__bc4919_idx"),
        ),
    ]
