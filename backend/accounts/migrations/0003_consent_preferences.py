import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_privacy_requests"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ConsentPreference",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("purpose", models.CharField(choices=[("marketing_email", "Marketing email"), ("marketing_sms", "Marketing SMS"), ("marketing_whatsapp", "Marketing WhatsApp")], max_length=32)),
                ("enabled", models.BooleanField(default=False)),
                ("policy_version", models.CharField(default="2026-11", max_length=40)),
                ("source", models.CharField(default="privacy_centre", max_length=40)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="consent_updates", to=settings.AUTH_USER_MODEL)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="consent_preferences", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("purpose",)},
        ),
        migrations.AddConstraint(
            model_name="consentpreference",
            constraint=models.UniqueConstraint(fields=("user", "purpose"), name="unique_user_consent_purpose"),
        ),
        migrations.CreateModel(
            name="ConsentEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("previous_value", models.BooleanField()),
                ("new_value", models.BooleanField()),
                ("purpose", models.CharField(max_length=32)),
                ("policy_version", models.CharField(max_length=40)),
                ("source", models.CharField(max_length=40)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="consent_events", to=settings.AUTH_USER_MODEL)),
                ("preference", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="events", to="accounts.consentpreference")),
            ],
            options={"ordering": ("-created_at",)},
        ),
    ]
