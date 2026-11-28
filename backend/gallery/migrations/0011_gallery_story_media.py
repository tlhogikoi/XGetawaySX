from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("gallery", "0010_alter_gallerymediapermissiongrant_evidence_reference"),
    ]

    operations = [
        migrations.CreateModel(
            name="GalleryStoryMedia",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("position", models.PositiveSmallIntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("media", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="story_attachment", to="gallery.gallerymedia")),
                ("story", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="additional_media", to="gallery.gallerystory")),
            ],
            options={
                "ordering": ("position", "created_at"),
                "constraints": [
                    models.UniqueConstraint(fields=("story", "position"), name="gal_story_media_position_unique"),
                ],
            },
        ),
        migrations.AddField(
            model_name="gallerystoryrevision",
            name="media_snapshot",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
