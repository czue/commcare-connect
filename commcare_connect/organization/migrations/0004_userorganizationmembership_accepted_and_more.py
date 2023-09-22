# Generated by Django 4.2.5 on 2023-09-22 11:16

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("organization", "0003_organization_members_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="userorganizationmembership",
            name="accepted",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="userorganizationmembership",
            name="invite_id",
            field=models.CharField(default=uuid.uuid4, max_length=50),
        ),
        migrations.AddIndex(
            model_name="userorganizationmembership",
            index=models.Index(fields=["invite_id"], name="organizatio_invite__0504c3_idx"),
        ),
    ]
