from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import RefundAuditEmail


def queue_refund_audit_email(refund):
    """Create a durable recipient snapshot and send only after the refund transaction commits."""
    payment = refund.payment
    audit, _created = RefundAuditEmail.objects.get_or_create(
        refund=refund,
        defaults={
            "customer_email": payment.customer.email or "",
            "partner_email": payment.partner.owner.email or "",
        },
    )
    transaction.on_commit(lambda audit_id=audit.pk: send_refund_audit_email(audit_id))
    return audit


def send_refund_audit_email(audit_id):
    """Send one separate audit email per recipient; retries never resend successful deliveries."""
    audit = RefundAuditEmail.objects.select_related(
        "refund__payment__reservation", "refund__payment__partner"
    ).get(pk=audit_id)
    if audit.refund.status != "refunded":
        return audit
    refund = audit.refund
    payment = refund.payment
    reservation = payment.reservation
    reference = str(reservation.booking_reference or reservation.pk)
    subject = f"XGetawaySX Refund Confirmation — {reference}"
    body = (
        "This is an official XGetawaySX refund confirmation for your records.\n\n"
        f"Booking reference: {reference}\n"
        f"Refund record: {refund.pk}\n"
        f"Refund amount: {refund.currency} {refund.amount}\n"
        f"Payment provider: {refund.provider}\n"
        f"Provider refund reference: {refund.provider_reference or 'Not supplied'}\n"
        f"Refund confirmed at: {refund.reconciled_at or timezone.now()}\n\n"
        "This email confirms that the refund was marked successful after verified provider "
        "confirmation or authorised staff reconciliation. Keep it with your booking records.\n\n"
        "XGetawaySX — travel through us"
    )
    errors = []
    audit.attempts += 1
    sender = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@xgetawaysx.com")
    for field, sent_field, recipient, label in (
        ("customer_email", "customer_sent_at", audit.customer_email, "customer"),
        ("partner_email", "partner_sent_at", audit.partner_email, "partner"),
    ):
        if getattr(audit, sent_field):
            continue
        if not recipient:
            errors.append(f"No {label} email address was available.")
            continue
        try:
            sent = send_mail(
                subject, body, sender, [recipient], fail_silently=False
            )
            if sent != 1:
                raise RuntimeError(f"Email backend did not accept the {label} message.")
            setattr(audit, sent_field, timezone.now())
        except Exception as exc:
            errors.append(f"{label}: {str(exc)[:500]}")
    customer_sent = bool(audit.customer_sent_at)
    partner_sent = bool(audit.partner_sent_at)
    if customer_sent and partner_sent:
        audit.status = RefundAuditEmail.Status.SENT
    elif customer_sent or partner_sent:
        audit.status = RefundAuditEmail.Status.PARTIAL
    else:
        audit.status = RefundAuditEmail.Status.FAILED
    audit.last_error = "; ".join(errors)[:2000]
    audit.save(update_fields=[
        "attempts", "customer_sent_at", "partner_sent_at", "status",
        "last_error", "updated_at",
    ])
    return audit
