from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import ReservationEmailDelivery


def queue_reservation_email(
    reservation, *, event, event_key, recipient_email, recipient_role,
    subject, body, cancellation=None,
):
    """Persist an idempotent delivery and send only after the surrounding transaction commits."""
    if not recipient_email:
        return None
    delivery, _created = ReservationEmailDelivery.objects.get_or_create(
        event_key=event_key,
        defaults={
            "reservation": reservation,
            "cancellation_request": cancellation,
            "event": event,
            "recipient_email": recipient_email,
            "recipient_role": recipient_role,
            "subject": subject[:200],
            "body": body,
        },
    )
    if delivery.status != ReservationEmailDelivery.Status.SENT:
        transaction.on_commit(
            lambda delivery_id=delivery.pk: send_reservation_email(delivery_id)
        )
    return delivery


def send_reservation_email(delivery_id):
    """Attempt one delivery; successful records are immutable and never resent by retries."""
    delivery = ReservationEmailDelivery.objects.get(pk=delivery_id)
    if delivery.status == ReservationEmailDelivery.Status.SENT:
        return delivery
    delivery.attempts += 1
    try:
        sent = send_mail(
            delivery.subject,
            delivery.body,
            getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@xgetawaysx.com"),
            [delivery.recipient_email],
            fail_silently=False,
        )
        if sent != 1:
            raise RuntimeError("Email backend did not accept the message.")
        delivery.status = ReservationEmailDelivery.Status.SENT
        delivery.sent_at = timezone.now()
        delivery.last_error = ""
    except Exception as exc:
        delivery.status = ReservationEmailDelivery.Status.FAILED
        delivery.last_error = str(exc)[:2000]
    delivery.save(update_fields=[
        "status", "sent_at", "attempts", "last_error", "updated_at",
    ])
    return delivery
