from django.core.management.base import BaseCommand, CommandError

from partners.models import ReservationEmailDelivery
from partners.reservation_email_notifications import send_reservation_email


class Command(BaseCommand):
    help = "Retry pending or failed XGetawaySX reservation lifecycle emails."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit", type=int, default=100,
            help="Maximum number of delivery records to process (0 means no limit).",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Report eligible records without attempting delivery.",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        if limit < 0:
            raise CommandError("--limit must be zero or a positive integer.")

        queryset = ReservationEmailDelivery.objects.filter(
            status__in=(
                ReservationEmailDelivery.Status.PENDING,
                ReservationEmailDelivery.Status.FAILED,
            )
        ).order_by("created_at", "pk")
        eligible = queryset.count()
        if limit:
            queryset = queryset[:limit]

        if options["dry_run"]:
            self.stdout.write(
                f"Dry run: {min(eligible, limit) if limit else eligible} of {eligible} "
                "pending/failed reservation email record(s) eligible."
            )
            return

        attempted = accepted = failed = 0
        for delivery in queryset.iterator():
            result = send_reservation_email(delivery.pk)
            attempted += 1
            if result.status == ReservationEmailDelivery.Status.SENT:
                accepted += 1
            else:
                failed += 1

        summary = (
            f"Reservation email retry complete: {attempted} attempted, "
            f"{accepted} accepted by email backend, {failed} still pending/failed."
        )
        if failed:
            self.stdout.write(self.style.WARNING(summary))
        else:
            self.stdout.write(self.style.SUCCESS(summary))
