from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("partners", "0018_balance_installment_options")]

    operations = [
        migrations.AlterField(
            model_name="reservationnotification",
            name="event",
            field=models.CharField(
                choices=[
                    ("cancellation_requested", "Cancellation requested"),
                    ("cancellation_decision", "Cancellation decision"),
                    ("cancellation_completed", "Cancellation completed"),
                    ("payment_reminder", "Payment reminder"),
                    ("refund_update", "Refund update"),
                ],
                max_length=32,
            ),
        ),
    ]
