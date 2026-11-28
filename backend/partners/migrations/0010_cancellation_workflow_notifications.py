from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("partners", "0009_provider_refund_automation"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ReservationCancellationRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reason", models.CharField(max_length=1000)),
                ("status", models.CharField(choices=[("pending", "Pending review"), ("approved", "Approved — refund/cancellation in progress"), ("declined", "Declined"), ("completed", "Completed")], default="pending", max_length=16)),
                ("decision_note", models.CharField(blank=True, max_length=1000)),
                ("requested_at", models.DateTimeField(auto_now_add=True)),
                ("decided_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="reservation_cancellations", to=settings.AUTH_USER_MODEL)),
                ("decided_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="decided_reservation_cancellations", to=settings.AUTH_USER_MODEL)),
                ("reservation", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="cancellation_requests", to="partners.reservationrequest")),
            ],
            options={"ordering": ("-requested_at",)},
        ),
        migrations.AddConstraint(
            model_name="reservationcancellationrequest",
            constraint=models.UniqueConstraint(condition=models.Q(("status__in", ("pending", "approved"))), fields=("reservation",), name="uniq_active_reservation_cancel"),
        ),
        migrations.AddIndex(
            model_name="reservationcancellationrequest",
            index=models.Index(fields=["status", "requested_at"], name="cancel_status_date_idx"),
        ),
        migrations.CreateModel(
            name="ReservationNotification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event", models.CharField(choices=[("cancellation_requested", "Cancellation requested"), ("cancellation_decision", "Cancellation decision"), ("cancellation_completed", "Cancellation completed"), ("refund_update", "Refund update")], max_length=32)),
                ("title", models.CharField(max_length=160)),
                ("message", models.CharField(max_length=500)),
                ("read_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("cancellation_request", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="notifications", to="partners.reservationcancellationrequest")),
                ("recipient", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reservation_notifications", to=settings.AUTH_USER_MODEL)),
                ("reservation", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notifications", to="partners.reservationrequest")),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.AddIndex(
            model_name="reservationnotification",
            index=models.Index(fields=["recipient", "read_at", "created_at"], name="res_notif_inbox_idx"),
        ),
    ]
