from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("partners", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="DestinationPage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=160)),
                ("slug", models.SlugField(max_length=180, unique=True)),
                ("introduction", models.CharField(blank=True, max_length=280)),
                ("description", models.TextField(blank=True)),
                ("city", models.CharField(blank=True, max_length=100)),
                ("province", models.CharField(blank=True, max_length=100)),
                ("country", models.CharField(default="South Africa", max_length=100)),
                ("is_published", models.BooleanField(default=False)),
                ("display_order", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("partners", models.ManyToManyField(blank=True, related_name="destination_pages", to="partners.partner")),
            ],
            options={"ordering": ("display_order", "name")},
        ),
        migrations.CreateModel(
            name="ExperienceCollection",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=160)),
                ("slug", models.SlugField(max_length=180, unique=True)),
                ("summary", models.CharField(max_length=280)),
                ("description", models.TextField(blank=True)),
                ("is_published", models.BooleanField(default=False)),
                ("display_order", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("destination", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="collections", to="partners.destinationpage")),
                ("partners", models.ManyToManyField(blank=True, related_name="experience_collections", to="partners.partner")),
            ],
            options={"ordering": ("display_order", "title")},
        ),
    ]
