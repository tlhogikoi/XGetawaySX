import django.db.models.deletion
import django.core.validators
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("partners", "0004_partner_availability_and_reservations"),
    ]

    operations = [
        migrations.CreateModel(
            name="PartnerFinancialSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("deposit_type", models.CharField(choices=[("none", "No deposit"), ("percentage", "Percentage"), ("fixed", "Fixed amount")], default="none", max_length=12)),
                ("deposit_value", models.DecimalField(decimal_places=2, default=0, max_digits=10, validators=[django.core.validators.MinValueValidator(0)])),
                ("commission_rate", models.DecimalField(decimal_places=2, default=0, max_digits=5, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ("currency", models.CharField(default="ZAR", max_length=3)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("partner", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="financial_settings", to="partners.partner")),
            ],
        ),
        migrations.CreateModel(
            name="ReservationPayment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[("deposit", "Deposit"), ("balance", "Balance"), ("full", "Full payment")], max_length=12)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("captured", "Captured"), ("failed", "Failed"), ("refunded", "Refunded")], default="pending", max_length=12)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("currency", models.CharField(default="ZAR", max_length=3)),
                ("idempotency_key", models.CharField(max_length=100)),
                ("provider", models.CharField(default="manual_reconciliation", max_length=40)),
                ("provider_reference", models.CharField(blank=True, max_length=160, null=True, unique=True)),
                ("failure_reason", models.CharField(blank=True, max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("captured_at", models.DateTimeField(blank=True, null=True)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="reservation_payments", to=settings.AUTH_USER_MODEL)),
                ("partner", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="reservation_payments", to="partners.partner")),
                ("reservation", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="payments", to="partners.reservationrequest")),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.AddConstraint(
            model_name="reservationpayment",
            constraint=models.UniqueConstraint(fields=("customer", "idempotency_key"), name="uniq_customer_payment_key"),
        ),
        migrations.AddIndex(
            model_name="reservationpayment",
            index=models.Index(fields=["partner", "status", "created_at"], name="partner_payment_status_idx"),
        ),
        migrations.AddIndex(
            model_name="reservationpayment",
            index=models.Index(fields=["reservation", "status"], name="res_payment_status_idx"),
        ),
        migrations.CreateModel(
            name="PartnerCommissionLedger",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("gross_amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("commission_rate", models.DecimalField(decimal_places=2, max_digits=5)),
                ("commission_amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("partner_net_amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("status", models.CharField(choices=[("accrued", "Accrued"), ("paid_out", "Paid out"), ("void", "Void")], default="accrued", max_length=12)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("partner", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="commission_entries", to="partners.partner")),
                ("payment", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="commission_entry", to="partners.reservationpayment")),
            ],
            options={"ordering": ("-created_at",)},
        ),
    ]
