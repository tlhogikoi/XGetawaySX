from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("gallery", "0008_gallery_partner_notifications"),
    ]
    operations = [
        migrations.CreateModel(
            name="GalleryStoryEditorialReview",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("story_version", models.PositiveIntegerField()),
                ("claims_verified", models.BooleanField(default=False)),
                ("source_facts_checked", models.BooleanField(default=False)),
                ("unsupported_claims_resolved", models.BooleanField(default=False)),
                ("media_context_accurate", models.BooleanField(default=False)),
                ("reviewer_notes", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("reviewer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="gallery_quality_reviews", to=settings.AUTH_USER_MODEL)),
                ("story", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="editorial_quality_reviews", to="gallery.gallerystory")),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.AddIndex(
            model_name="gallerystoryeditorialreview",
            index=models.Index(fields=["story", "story_version", "created_at"], name="gal_story_qc_version_idx"),
        ),
    ]
