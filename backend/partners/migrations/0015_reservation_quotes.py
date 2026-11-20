from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("partners", "0014_enquiry_reservation_link"),
    ]

    operations = [
        migrations.CreateModel(
            name="ReservationQuote",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("version", models.PositiveIntegerField()),
                ("status", models.CharField(choices=[("sent", "Sent to customer"), ("accepted", "Accepted by customer"), ("declined", "Declined by customer"), ("expired", "Expired")], default="sent", max_length=12)),
                ("currency", models.CharField(default="ZAR", max_length=3)),
                ("total_amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("deposit_amount", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("terms", models.TextField(blank=True, max_length=3000)),
                ("expires_at", models.DateTimeField()),
                ("responded_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="issued_reservation_quotes", to=settings.AUTH_USER_MODEL)),
                ("reservation", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="quotes", to="partners.reservationrequest")),
            ],
            options={"ordering": ("-version",)},
        ),
        migrations.AddConstraint(
            model_name="reservationquote",
            constraint=models.UniqueConstraint(fields=("reservation", "version"), name="uniq_res_quote_version"),
        ),
        migrations.AddIndex(
            model_name="reservationquote",
            index=models.Index(fields=["reservation", "status"], name="res_quote_status_idx"),
        ),
        migrations.CreateModel(
            name="ReservationQuoteItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("description", models.CharField(max_length=180)),
                ("quantity", models.DecimalField(decimal_places=2, default=1, max_digits=8)),
                ("unit_price", models.DecimalField(decimal_places=2, max_digits=12)),
                ("line_total", models.DecimalField(decimal_places=2, max_digits=12)),
                ("quote", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="partners.reservationquote")),
            ],
            options={"ordering": ("id",)},
        ),
    ]
