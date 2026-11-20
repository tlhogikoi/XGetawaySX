from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("partners", "0007_refunds_and_provider_event_inbox")]

    operations = [
        migrations.AddField(
            model_name="reservationpayment",
            name="checkout_session_id",
            field=models.CharField(blank=True, max_length=180),
        ),
        migrations.AddField(
            model_name="reservationpayment",
            name="checkout_url",
            field=models.URLField(blank=True),
        ),
    ]
