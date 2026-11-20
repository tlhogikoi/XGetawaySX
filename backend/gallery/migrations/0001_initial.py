from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("partners", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="GalleryMedia",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=180)),
                ("image", models.URLField(max_length=1000)),
                ("alt_text", models.CharField(max_length=250)),
                ("caption", models.CharField(blank=True, max_length=250)),
                ("media_credit", models.CharField(blank=True, max_length=180)),
                ("rights_holder", models.CharField(max_length=180)),
                ("rights_reference", models.CharField(blank=True, max_length=250)),
                ("rights_confirmed", models.BooleanField(default=False)),
                ("promotional_permission", models.BooleanField(default=False)),
                ("permission_granted_at", models.DateTimeField(blank=True, null=True)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("owner_review", "Awaiting owner approval"), ("editorial_review", "Awaiting editorial approval"), ("approved", "Approved"), ("rejected", "Rejected"), ("withdrawn", "Withdrawn")], default="draft", max_length=24)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("partner", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="gallery_media", to="partners.partner")),
                ("submitted_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="gallery_media_submissions", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.AddIndex(
            model_name="gallerymedia",
            index=models.Index(fields=["partner", "status"], name="gal_media_partner_status_idx"),
        ),
        migrations.CreateModel(
            name="GalleryStory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("owner_original_history", models.TextField(blank=True)),
                ("owner_history_private", models.BooleanField(default=True)),
                ("original_history_public_permission", models.BooleanField(default=False)),
                ("summary", models.CharField(blank=True, max_length=600)),
                ("summary_word_count", models.PositiveSmallIntegerField(default=0)),
                ("ai_assisted", models.BooleanField(default=False)),
                ("ai_source_facts", models.JSONField(blank=True, default=list)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("owner_review", "Awaiting owner approval"), ("editorial_review", "Awaiting editorial approval"), ("published", "Published"), ("rejected", "Rejected"), ("withdrawn", "Withdrawn")], default="draft", max_length=24)),
                ("owner_approved_at", models.DateTimeField(blank=True, null=True)),
                ("editorial_approved_at", models.DateTimeField(blank=True, null=True)),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("editorial_approved_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="gallery_editorial_approvals", to=settings.AUTH_USER_MODEL)),
                ("media", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="story", to="gallery.gallerymedia")),
                ("owner_approved_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="gallery_owner_approvals", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-published_at", "-created_at")},
        ),
    ]
