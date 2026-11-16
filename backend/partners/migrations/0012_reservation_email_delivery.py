from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("partners", "0011_refund_audit_email"),
    ]

    operations = [
        migrations.CreateModel(
            name="ReservationEmailDelivery",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event", models.CharField(max_length=40)),
                ("event_key", models.CharField(max_length=180, unique=True)),
                ("recipient_email", models.EmailField(max_length=254)),
                ("recipient_role", models.CharField(max_length=20)),
                ("subject", models.CharField(max_length=200)),
                ("body", models.TextField()),
                ("status", models.CharField(choices=[("pending", "Pending"), ("sent", "Accepted by email backend"), ("failed", "Failed")], default="pending", max_length=12)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("attempts", models.PositiveIntegerField(default=0)),
                ("last_error", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("cancellation_request", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="email_deliveries", to="partners.reservationcancellationrequest")),
                ("reservation", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="email_deliveries", to="partners.reservationrequest")),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.AddIndex(
            model_name="reservationemaildelivery",
            index=models.Index(fields=["status", "created_at"], name="res_email_status_idx"),
        ),
    ]
