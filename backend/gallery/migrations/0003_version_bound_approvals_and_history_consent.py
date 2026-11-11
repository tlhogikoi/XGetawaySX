from django.conf import settings
from django.db import migrations, models
from django.db.models import F
import django.db.models.deletion


def backfill_approval_versions(apps, schema_editor):
    GalleryStory = apps.get_model("gallery", "GalleryStory")
    GalleryStory.objects.filter(owner_approved_at__isnull=False).update(
        owner_approved_version=F("current_version")
    )
    GalleryStory.objects.filter(editorial_approved_at__isnull=False).update(
        editorial_approved_version=F("current_version")
    )


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("gallery", "0002_story_revisions_audit"),
    ]

    operations = [
        migrations.AddField(
            model_name="gallerystory",
            name="current_version",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name="gallerystory",
            name="owner_approved_version",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="gallerystory",
            name="editorial_approved_version",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="GalleryHistoryPublicationConsent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("story_version", models.PositiveIntegerField()),
                ("granted_at", models.DateTimeField()),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("granted_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="gallery_history_consents_granted", to=settings.AUTH_USER_MODEL)),
                ("revoked_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="gallery_history_consents_revoked", to=settings.AUTH_USER_MODEL)),
                ("story", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="history_publication_consents", to="gallery.gallerystory")),
            ],
            options={"ordering": ("-granted_at",)},
        ),
        migrations.AddConstraint(
            model_name="galleryhistorypublicationconsent",
            constraint=models.UniqueConstraint(fields=("story", "story_version"), name="gal_history_consent_version_unique"),
        ),
        migrations.RunPython(backfill_approval_versions, migrations.RunPython.noop),
    ]
