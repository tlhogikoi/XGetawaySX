from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("partners", "0016_reservation_installments")]

    operations = [
        migrations.AddField(
            model_name="partnerfinancialsettings",
            name="deposit_due_hours",
            field=models.PositiveSmallIntegerField(default=48),
        ),
        migrations.AddField(
            model_name="partnerfinancialsettings",
            name="balance_due_days_before",
            field=models.PositiveSmallIntegerField(default=7),
        ),
    ]
