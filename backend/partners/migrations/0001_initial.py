from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.text


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Partner",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=180)),
                ("slug", models.SlugField(max_length=200, unique=True)),
                ("category", models.CharField(choices=[("accommodation", "Accommodation"), ("family_home", "Family home"), ("tour", "Tour operator"), ("activity", "Activity"), ("dining", "Dining"), ("wellness", "Wellness"), ("transport", "Transport"), ("destination", "Destination"), ("other", "Other")], max_length=30)),
                ("description", models.TextField(blank=True)),
                ("city", models.CharField(blank=True, max_length=100)),
                ("province", models.CharField(blank=True, max_length=100)),
                ("country", models.CharField(default="South Africa", max_length=100)),
                ("website_url", models.URLField(blank=True)),
                ("gallery_status", models.CharField(choices=[("pending", "Pending"), ("approved", "Approved"), ("suspended", "Suspended"), ("rejected", "Rejected")], default="pending", max_length=20)),
                ("enquiry_status", models.CharField(choices=[("pending", "Pending"), ("approved", "Approved"), ("suspended", "Suspended"), ("rejected", "Rejected")], default="pending", max_length=20)),
                ("booking_status", models.CharField(choices=[("pending", "Pending"), ("approved", "Approved"), ("suspended", "Suspended"), ("rejected", "Rejected")], default="pending", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="partner_profiles", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("name",)},
        ),
        migrations.AddIndex(
            model_name="partner",
            index=models.Index(fields=["gallery_status", "category"], name="partners_gallery_status_idx"),
        ),
        migrations.AddIndex(
            model_name="partner",
            index=models.Index(fields=["city", "province"], name="partners_city_province_idx"),
        ),
    ]
