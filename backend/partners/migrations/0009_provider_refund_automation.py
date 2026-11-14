import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("partners", "0008_payment_gateway_checkout_sessions")]

    operations = [
        migrations.AddField(
            model_name="reservationrefund",
            name="idempotency_key",
            field=models.CharField(default=uuid.uuid4, max_length=100, unique=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="reservationrefund",
            name="provider_status",
            field=models.CharField(blank=True, max_length=40),
        ),
    ]
