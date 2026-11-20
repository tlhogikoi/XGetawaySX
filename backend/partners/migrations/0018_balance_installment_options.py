from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("partners", "0017_partner_payment_deadlines")]

    operations = [
        migrations.AddField(
            model_name="partnerfinancialsettings",
            name="balance_installment_count",
            field=models.PositiveSmallIntegerField(default=1),
        ),
        migrations.AddField(
            model_name="partnerfinancialsettings",
            name="balance_installment_interval_days",
            field=models.PositiveSmallIntegerField(default=7),
        ),
    ]
