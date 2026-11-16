from django.core.management.base import BaseCommand

from partners.models import ReservationEmailDelivery
from partners.reservation_email_notifications import send_reservation_email


class Command(BaseCommand):
    help = "Retry failed XGetawaySX reservation lifecycle emails."

    def handle(self, *args, **options):
        queryset = ReservationEmailDelivery.objects.filter(
            status=ReservationEmailDelivery.Status.FAILED
        ).order_by("created_at")
        count = 0
        for delivery in queryset.iterator():
            send_reservation_email(delivery.pk)
            count += 1
        self.stdout.write(self.style.SUCCESS(
            f"Processed {count} failed reservation email delivery record(s)."
        ))
