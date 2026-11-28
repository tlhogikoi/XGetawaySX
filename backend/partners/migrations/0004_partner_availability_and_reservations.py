import django.db.models.deletion
import django.db.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("partners", "0003_trip_plans_and_partner_enquiries"),
    ]

    operations = [
        migrations.CreateModel(
            name="PartnerAvailability",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField()),
                ("capacity", models.PositiveIntegerField()),
                ("booked_count", models.PositiveIntegerField(default=0)),
                ("is_open", models.BooleanField(default=True)),
                ("price_per_guest", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("currency", models.CharField(default="ZAR", max_length=3)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("partner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="availability_days", to="partners.partner")),
            ],
            options={"ordering": ("date",)},
        ),
        migrations.AddConstraint(
            model_name="partneravailability",
            constraint=models.UniqueConstraint(fields=("partner", "date"), name="uniq_partner_avail_day"),
        ),
        migrations.AddConstraint(
            model_name="partneravailability",
            constraint=models.CheckConstraint(condition=models.Q(("booked_count__lte", models.F("capacity"))), name="avail_booked_lte_cap"),
        ),
        migrations.AddIndex(
            model_name="partneravailability",
            index=models.Index(fields=["partner", "date", "is_open"], name="partner_availability_day_idx"),
        ),
        migrations.CreateModel(
            name="ReservationRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("start_date", models.DateField()),
                ("end_date", models.DateField(help_text="Checkout date; exclusive.")),
                ("guests", models.PositiveIntegerField()),
                ("message", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("confirmed", "Confirmed"), ("declined", "Declined"), ("cancelled", "Cancelled")], default="pending", max_length=20)),
                ("booking_reference", models.UUIDField(blank=True, null=True, unique=True)),
                ("partner_response", models.TextField(blank=True)),
                ("responded_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="reservation_requests", to=settings.AUTH_USER_MODEL)),
                ("partner", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="reservation_requests", to="partners.partner")),
                ("trip_plan", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reservation_requests", to="partners.tripplan")),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.AddIndex(
            model_name="reservationrequest",
            index=models.Index(fields=["partner", "status", "start_date"], name="partner_res_status_idx"),
        ),
        migrations.AddIndex(
            model_name="reservationrequest",
            index=models.Index(fields=["customer", "created_at"], name="customer_reservation_date_idx"),
        ),
    ]
