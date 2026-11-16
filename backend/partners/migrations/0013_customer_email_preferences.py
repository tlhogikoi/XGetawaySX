import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("partners", "0012_reservation_email_delivery"),
    ]

    operations = [
        migrations.CreateModel(
            name="CustomerEmailPreference",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("marketing_opt_in", models.BooleanField(default=False)),
                ("unsubscribe_token", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="email_preferences", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "customer email preference"},
        ),
    ]
