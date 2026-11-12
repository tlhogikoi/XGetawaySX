from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("gallery", "0007_legacy_image_url_optional"),
    ]

    operations = [
        migrations.CreateModel(
            name="GalleryPartnerNotification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[("story_published", "Story published"), ("story_changes_requested", "Changes requested")], max_length=40)),
                ("title", models.CharField(max_length=180)),
                ("message", models.TextField(max_length=1200)),
                ("read_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("partner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="gallery_notifications", to="partners.partner")),
                ("recipient", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="gallery_partner_notifications", to=settings.AUTH_USER_MODEL)),
                ("story", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="partner_notifications", to="gallery.gallerystory")),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.AddIndex(
            model_name="gallerypartnernotification",
            index=models.Index(fields=["recipient", "read_at", "created_at"], name="gal_notice_recipient_idx"),
        ),
    ]
