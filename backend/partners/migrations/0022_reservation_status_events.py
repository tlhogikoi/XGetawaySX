from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("partners", "0021_partner_verification_documents"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ReservationStatusEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("from_status", models.CharField(blank=True, max_length=20)),
                ("to_status", models.CharField(max_length=20)),
                ("actor_role", models.CharField(default="system", max_length=30)),
                ("reason", models.CharField(blank=True, max_length=1000)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reservation_status_events", to=settings.AUTH_USER_MODEL)),
                ("reservation", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="status_events", to="partners.reservationrequest")),
            ],
            options={"ordering": ("created_at", "id")},
        ),
        migrations.AddIndex(
            model_name="reservationstatusevent",
            index=models.Index(fields=["reservation", "created_at"], name="res_status_event_idx"),
        ),
    ]
