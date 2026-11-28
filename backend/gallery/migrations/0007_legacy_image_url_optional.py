from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("gallery", "0006_private_gallery_file_storage"),
    ]

    operations = [
        migrations.AlterField(
            model_name="gallerymedia",
            name="image",
            field=models.URLField(blank=True, max_length=1000),
        ),
    ]
