# Generated for Development 28.
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("partners", "0015_reservation_quotes")]

    operations = [
        migrations.CreateModel(
            name="ReservationInstallment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sequence", models.PositiveSmallIntegerField()),
                ("kind", models.CharField(choices=[("deposit", "Deposit"), ("balance", "Balance")], max_length=12)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("currency", models.CharField(default="ZAR", max_length=3)),
                ("due_at", models.DateTimeField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("reservation", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="installments", to="partners.reservationrequest")),
            ],
            options={"ordering": ("sequence",)},
        ),
        migrations.AddConstraint(
            model_name="reservationinstallment",
            constraint=models.UniqueConstraint(fields=("reservation", "sequence"), name="uniq_res_installment_seq"),
        ),
        migrations.AddConstraint(
            model_name="reservationinstallment",
            constraint=models.CheckConstraint(condition=models.Q(("amount__gt", 0)), name="res_installment_amount_positive"),
        ),
        migrations.AddIndex(
            model_name="reservationinstallment",
            index=models.Index(fields=["due_at", "reservation"], name="res_installment_due_idx"),
        ),
    ]
