# Generated for Dev 44 partner verification onboarding.
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("partners", "0019_alter_reservationnotification_event"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="PartnerVerificationSubmission",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("legal_business_name", models.CharField(blank=True, max_length=180)),
                ("registration_number", models.CharField(blank=True, max_length=80)),
                ("is_sole_proprietor", models.BooleanField(default=False)),
                ("tax_number", models.CharField(blank=True, max_length=80)),
                ("contact_person", models.CharField(blank=True, max_length=160)),
                ("contact_email", models.EmailField(blank=True, max_length=254)),
                ("contact_phone", models.CharField(blank=True, max_length=40)),
                ("physical_address", models.TextField(blank=True, max_length=1000)),
                ("document_checklist", models.JSONField(blank=True, default=list)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("submitted", "Submitted for review"), ("changes_requested", "Changes requested"), ("approved", "Verified"), ("rejected", "Rejected")], default="draft", max_length=24)),
                ("submitted_at", models.DateTimeField(blank=True, null=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("review_notes", models.TextField(blank=True, max_length=2000)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("partner", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="verification_submission", to="partners.partner")),
                ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="partner_verifications_reviewed", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-updated_at",)},
        ),
        migrations.AddIndex(
            model_name="partnerverificationsubmission",
            index=models.Index(fields=["status", "submitted_at"], name="partner_verify_queue_idx"),
        ),
        migrations.CreateModel(
            name="PartnerVerificationEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_type", models.CharField(max_length=40)),
                ("details", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name="partner_verification_events", to=settings.AUTH_USER_MODEL)),
                ("submission", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="events", to="partners.partnerverificationsubmission")),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.AddIndex(
            model_name="partnerverificationevent",
            index=models.Index(fields=["submission", "created_at"], name="partner_verify_event_idx"),
        ),
    ]
