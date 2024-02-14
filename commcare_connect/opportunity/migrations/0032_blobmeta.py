# Generated by Django 4.2.5 on 2024-02-13 23:37

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("opportunity", "0031_uservisit_flag_reason_uservisit_flagged_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="BlobMeta",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("parent_id", models.CharField(help_text="Parent primary key or unique identifier", max_length=255)),
                ("blob_id", models.CharField(default=uuid.uuid4, max_length=255)),
                ("content_length", models.IntegerField()),
                ("content_type", models.CharField(max_length=255, null=True)),
            ],
            options={
                "indexes": [models.Index(fields=["blob_id"], name="opportunity_blob_id_614ec2_idx")],
                "unique_together": {("parent_id", "name")},
            },
        ),
    ]
