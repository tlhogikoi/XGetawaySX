from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db.models import Sum
from django.utils import timezone

from partners.models import (
    ReservationEmailDelivery, ReservationInstallment, ReservationPayment,
    ReservationRefund, ReservationRequest,
)
from partners.reservation_email_notifications import queue_reservation_email


class Command(BaseCommand):
    help = "Send idempotent reminders for upcoming and overdue reservation instalments."

    def add_arguments(self, parser):
        parser.add_argument("--window-hours", type=int, default=24)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        window = options["window_hours"]
        if window < 1 or window > 168:
            self.stderr.write(self.style.ERROR("--window-hours must be between 1 and 168."))
            return
        now = timezone.now()
        due_soon = overdue = queued = skipped = 0
        queryset = ReservationInstallment.objects.select_related(
            "reservation__customer", "reservation__partner__owner"
        ).filter(reservation__status=ReservationRequest.Status.CONFIRMED).order_by("due_at", "pk")
        for installment in queryset.iterator():
            reservation = installment.reservation
            captured = reservation.payments.filter(
                status=ReservationPayment.Status.CAPTURED
            ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
            refunded = ReservationRefund.objects.filter(
                payment__reservation=reservation, status=ReservationRefund.Status.REFUNDED
            ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
            paid_remaining = max(Decimal("0.00"), captured - refunded)
            prior_installments = reservation.installments.filter(
                sequence__lt=installment.sequence
            ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
            allocated = min(installment.amount, max(Decimal("0.00"), paid_remaining - prior_installments))
            outstanding = installment.amount - allocated
            if outstanding <= 0:
                skipped += 1
                continue
            if installment.due_at <= now:
                stage = "overdue"
                overdue += 1
            elif installment.due_at <= now + timezone.timedelta(hours=window):
                stage = "due_soon"
                due_soon += 1
            else:
                continue
            event_key = f"installment:{installment.pk}:{stage}"
            if ReservationEmailDelivery.objects.filter(event_key=event_key, status=ReservationEmailDelivery.Status.SENT).exists():
                skipped += 1
                continue
            subject = (
                f"XGetawaySX: overdue {installment.kind} payment"
                if stage == "overdue" else f"XGetawaySX: {installment.kind} payment due soon"
            )
            body = (
                f"Booking reference: {reservation.booking_reference or reservation.pk}\n"
                f"Partner: {reservation.partner.name}\n"
                f"Instalment: {installment.kind}\n"
                f"Amount outstanding: {installment.currency} {outstanding}\n"
                f"Due: {timezone.localtime(installment.due_at).strftime('%Y-%m-%d %H:%M %Z')}\n\n"
                "Please sign in to your XGetawaySX account to review the payment schedule. "
                "A reminder does not mean a payment has been received or that a booking has been cancelled.\n\n"
                "XGetawaySX — travel through us"
            )
            recipients = (
                ("customer", reservation.customer.email),
                ("partner", reservation.partner.owner.email),
            )
            if options["dry_run"]:
                self.stdout.write(f"Would send {stage} reminder for instalment {installment.pk} ({outstanding} {installment.currency}).")
                continue
            for role, email in recipients:
                if not email:
                    continue
                delivery = queue_reservation_email(
                    reservation, event="payment_reminder",
                    event_key=f"{event_key}:{role}", recipient_email=email,
                    recipient_role=role, subject=subject, body=body,
                )
                if delivery:
                    queued += 1
        self.stdout.write(
            f"Payment reminder run: {due_soon} due-soon instalments, {overdue} overdue, "
            f"{queued} email deliveries queued/attempted, {skipped} fully paid or already sent."
        )
