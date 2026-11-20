from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("partners", "0005_partner_finance_and_reservation_payments"),
    ]

    operations = [
        migrations.AddField(
            model_name="reservationrequest",
            name="quoted_total",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name="reservationrequest",
            name="quoted_deposit",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name="reservationrequest",
            name="quoted_currency",
            field=models.CharField(blank=True, max_length=3, null=True),
        ),
        migrations.AddField(
            model_name="reservationrequest",
            name="quoted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
