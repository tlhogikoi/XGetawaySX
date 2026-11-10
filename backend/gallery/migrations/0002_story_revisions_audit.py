from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("partners", "0001_initial"),
        ("gallery", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="GalleryStoryRevision",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("version", models.PositiveIntegerField()),
                ("summary", models.CharField(blank=True, max_length=600)),
                ("owner_original_history_snapshot", models.TextField(blank=True)),
                ("owner_history_private", models.BooleanField(default=True)),
                ("original_history_public_permission", models.BooleanField(default=False)),
                ("ai_assisted", models.BooleanField(default=False)),
                ("ai_source_facts_snapshot", models.JSONField(blank=True, default=list)),
                ("change_reason", models.CharField(blank=True, max_length=250)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("changed_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name="gallery_story_revisions", to=settings.AUTH_USER_MODEL)),
                ("story", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="revisions", to="gallery.gallerystory")),
            ],
            options={"ordering": ("-version",)},
        ),
        migrations.AddConstraint(
            model_name="gallerystoryrevision",
            constraint=models.UniqueConstraint(fields=("story", "version"), name="gal_story_version_unique"),
        ),
        migrations.CreateModel(
            name="GalleryAuditEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(max_length=60)),
                ("details", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name="gallery_audit_events", to=settings.AUTH_USER_MODEL)),
                ("media", models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name="audit_events", to="gallery.gallerymedia")),
                ("partner", models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name="gallery_audit_events", to="partners.partner")),
                ("story", models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name="audit_events", to="gallery.gallerystory")),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.AddIndex(
            model_name="galleryauditevent",
            index=models.Index(fields=["action", "created_at"], name="gal_audit_action_date_idx"),
        ),
    ]
