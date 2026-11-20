from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("partners", "0010_cancellation_workflow_notifications"),
    ]

    operations = [
        migrations.CreateModel(
            name="RefundAuditEmail",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("customer_email", models.EmailField(blank=True, max_length=254)),
                ("partner_email", models.EmailField(blank=True, max_length=254)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("sent", "Sent to all recipients"), ("partial", "Partially sent"), ("failed", "Failed")], default="pending", max_length=12)),
                ("customer_sent_at", models.DateTimeField(blank=True, null=True)),
                ("partner_sent_at", models.DateTimeField(blank=True, null=True)),
                ("attempts", models.PositiveIntegerField(default=0)),
                ("last_error", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("refund", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="audit_email", to="partners.reservationrefund")),
            ],
            options={"ordering": ("-created_at",)},
        ),
    ]
