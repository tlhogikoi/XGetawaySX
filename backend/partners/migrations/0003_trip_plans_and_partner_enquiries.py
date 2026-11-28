from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("partners", "0002_destination_pages_and_experience_collections"),
    ]

    operations = [
        migrations.CreateModel(
            name="TripPlan",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(default="My getaway", max_length=160)),
                ("notes", models.TextField(blank=True)),
                ("start_date", models.DateField(blank=True, null=True)),
                ("end_date", models.DateField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="trip_plans", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-updated_at",)},
        ),
        migrations.CreateModel(
            name="TripPlanItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("note", models.CharField(blank=True, max_length=500)),
                ("display_order", models.PositiveIntegerField(default=0)),
                ("added_at", models.DateTimeField(auto_now_add=True)),
                ("partner", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="trip_plan_items", to="partners.partner")),
                ("plan", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="partners.tripplan")),
            ],
            options={"ordering": ("display_order", "added_at")},
        ),
        migrations.AddConstraint(
            model_name="tripplanitem",
            constraint=models.UniqueConstraint(fields=("plan", "partner"), name="unique_partner_per_trip_plan"),
        ),
        migrations.CreateModel(
            name="PartnerEnquiry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("message", models.TextField()),
                ("requested_start_date", models.DateField(blank=True, null=True)),
                ("requested_end_date", models.DateField(blank=True, null=True)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("responded", "Responded"), ("accepted", "Accepted"), ("declined", "Declined"), ("closed", "Closed")], default="pending", max_length=20)),
                ("partner_response", models.TextField(blank=True)),
                ("responded_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="partner_enquiries", to=settings.AUTH_USER_MODEL)),
                ("partner", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="customer_enquiries", to="partners.partner")),
                ("trip_plan", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="enquiries", to="partners.tripplan")),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.AddIndex(
            model_name="partnerenquiry",
            index=models.Index(fields=["partner", "status", "created_at"], name="partner_enquiry_status_idx"),
        ),
        migrations.AddIndex(
            model_name="partnerenquiry",
            index=models.Index(fields=["customer", "created_at"], name="customer_enquiry_date_idx"),
        ),
    ]
