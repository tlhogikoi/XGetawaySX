from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("partners", "0013_customer_email_preferences"),
    ]

    operations = [
        migrations.AddField(
            model_name="partnerenquiry",
            name="reservation_request",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="source_enquiry",
                to="partners.reservationrequest",
            ),
        ),
    ]
