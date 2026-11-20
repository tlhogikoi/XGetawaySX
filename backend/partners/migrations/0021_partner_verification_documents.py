import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
import gallery.validators
import partners.models


class Migration(migrations.Migration):
    dependencies = [
        ("partners", "0020_partner_verification_onboarding"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="PartnerVerificationDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("document_type", models.CharField(choices=[("business_registration", "Business registration"), ("proof_of_address", "Proof of address"), ("owner_identity", "Owner identity"), ("tax_certificate", "Tax certificate"), ("operating_licence", "Operating licence")], max_length=40)),
                ("file", models.FileField(storage=partners.models.private_partner_verification_storage, upload_to=partners.models.partner_verification_upload_path, validators=[gallery.validators.validate_gallery_evidence])),
                ("original_filename", models.CharField(max_length=255)),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                ("submission", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="documents", to="partners.partnerverificationsubmission")),
                ("uploaded_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="partner_verification_documents", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("document_type", "-uploaded_at")},
        ),
        migrations.AddIndex(
            model_name="partnerverificationdocument",
            index=models.Index(fields=["submission", "document_type"], name="partner_verify_doc_idx"),
        ),
    ]
