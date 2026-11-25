import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="PrivacyRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reference", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("request_type", models.CharField(choices=[("access", "Access my information"), ("correction", "Correct my information"), ("deletion", "Request deletion"), ("consent_withdrawal", "Withdraw consent"), ("marketing_optout", "Opt out of marketing")], max_length=32)),
                ("description", models.TextField(max_length=4000)),
                ("status", models.CharField(choices=[("submitted", "Submitted"), ("under_review", "Under review"), ("awaiting_verification", "Awaiting identity verification"), ("fulfilled", "Completed"), ("declined", "Declined"), ("withdrawn", "Withdrawn")], default="submitted", max_length=32)),
                ("staff_note", models.TextField(blank=True, max_length=4000)),
                ("identity_verified", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("closed_at", models.DateTimeField(blank=True, null=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="privacy_requests", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.CreateModel(
            name="PrivacyRequestEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("from_status", models.CharField(blank=True, max_length=32)),
                ("to_status", models.CharField(max_length=32)),
                ("note", models.CharField(blank=True, max_length=1000)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="privacy_request_events", to=settings.AUTH_USER_MODEL)),
                ("request", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="events", to="accounts.privacyrequest")),
            ],
            options={"ordering": ("created_at",)},
        ),
    ]
