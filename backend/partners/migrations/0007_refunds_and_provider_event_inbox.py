from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("partners", "0006_reservation_financial_quote_snapshot"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ReservationRefund",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("currency", models.CharField(max_length=3)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("refunded", "Refunded"), ("failed", "Failed")], default="pending", max_length=12)),
                ("provider", models.CharField(max_length=40)),
                ("provider_reference", models.CharField(blank=True, max_length=160, null=True, unique=True)),
                ("reason", models.CharField(blank=True, max_length=500)),
                ("reconciled_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("payment", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="refunds", to="partners.reservationpayment")),
                ("reconciled_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="reconciled_reservation_refunds", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.CreateModel(
            name="PartnerCommissionAdjustment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("gross_refund", models.DecimalField(decimal_places=2, max_digits=12)),
                ("commission_reversal", models.DecimalField(decimal_places=2, max_digits=12)),
                ("partner_net_reversal", models.DecimalField(decimal_places=2, max_digits=12)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("partner", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="commission_adjustments", to="partners.partner")),
                ("refund", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="commission_adjustment", to="partners.reservationrefund")),
            ],
        ),
        migrations.CreateModel(
            name="PaymentProviderEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("provider", models.CharField(max_length=40)),
                ("event_id", models.CharField(max_length=180)),
                ("payload_sha256", models.CharField(max_length=64)),
                ("signature_verified", models.BooleanField(default=False)),
                ("processed_at", models.DateTimeField(blank=True, null=True)),
                ("received_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.AddIndex(
            model_name="reservationrefund",
            index=models.Index(fields=["payment", "status"], name="refund_payment_status_idx"),
        ),
        migrations.AddConstraint(
            model_name="paymentproviderevent",
            constraint=models.UniqueConstraint(fields=("provider", "event_id"), name="uniq_provider_event_id"),
        ),
        migrations.AddIndex(
            model_name="paymentproviderevent",
            index=models.Index(fields=["provider", "received_at"], name="provider_event_received_idx"),
        ),
    ]
