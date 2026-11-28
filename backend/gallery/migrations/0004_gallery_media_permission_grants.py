from django.conf import settings
from django.db import migrations, models
from django.db.models import F
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("gallery", "0003_version_bound_approvals_and_history_consent"),
    ]

    operations = [
        migrations.CreateModel(
            name="GalleryMediaPermissionGrant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("purpose", models.CharField(choices=[("gallery_promotion", "XGetawaySX Gallery promotion")], default="gallery_promotion", max_length=32)),
                ("rights_holder", models.CharField(max_length=180)),
                ("permitted_channels", models.JSONField(blank=True, default=list)),
                ("evidence_reference", models.CharField(max_length=500)),
                ("granted_at", models.DateTimeField()),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("granted_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="gallery_media_permissions_granted", to=settings.AUTH_USER_MODEL)),
                ("media", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="permission_grants", to="gallery.gallerymedia")),
                ("revoked_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="gallery_media_permissions_revoked", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-granted_at",)},
        ),
        migrations.AddIndex(
            model_name="gallerymediapermissiongrant",
            index=models.Index(fields=["media", "purpose", "revoked_at"], name="gal_media_perm_active_idx"),
        ),
        migrations.AddConstraint(
            model_name="gallerymediapermissiongrant",
            constraint=models.CheckConstraint(
                condition=models.Q(("expires_at__isnull", True)) | models.Q(("expires_at__gt", F("granted_at"))),
                name="gal_media_perm_expiry_after_grant",
            ),
        ),
    ]
