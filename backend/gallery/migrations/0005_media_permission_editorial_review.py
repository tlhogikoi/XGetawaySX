from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("gallery", "0004_gallery_media_permission_grants"),
    ]

    operations = [
        migrations.AddField(
            model_name="gallerymediapermissiongrant",
            name="review_status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending editorial rights review"),
                    ("approved", "Rights approved"),
                    ("rejected", "Rights rejected"),
                ],
                default="pending",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="gallerymediapermissiongrant",
            name="reviewed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="gallerymediapermissiongrant",
            name="review_notes",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="gallerymediapermissiongrant",
            name="reviewed_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="gallery_media_permissions_reviewed",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
