from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("gallery", "0009_gallery_story_editorial_quality_review"),
    ]

    operations = [
        migrations.AlterField(
            model_name="gallerymediapermissiongrant",
            name="evidence_reference",
            field=models.CharField(blank=True, max_length=500),
        ),
    ]
