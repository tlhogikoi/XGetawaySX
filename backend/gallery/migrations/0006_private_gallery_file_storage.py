import gallery.storage
import gallery.models
import gallery.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("gallery", "0005_media_permission_editorial_review"),
    ]

    operations = [
        migrations.AddField(
            model_name="gallerymedia",
            name="image_file",
            field=models.FileField(
                blank=True,
                null=True,
                storage=gallery.storage.PrivateGalleryStorage(),
                upload_to=gallery.models.gallery_media_upload_path,
                validators=[gallery.validators.validate_gallery_image],
            ),
        ),
        migrations.AddField(
            model_name="gallerymediapermissiongrant",
            name="evidence_file",
            field=models.FileField(
                blank=True,
                null=True,
                storage=gallery.storage.PrivateGalleryStorage(),
                upload_to=gallery.models.gallery_evidence_upload_path,
                validators=[gallery.validators.validate_gallery_evidence],
            ),
        ),
    ]
