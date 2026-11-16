from django.core.management.base import BaseCommand

from partners.models import RefundAuditEmail
from partners.refund_notifications import send_refund_audit_email


class Command(BaseCommand):
    help = "Retry refund audit emails that are pending, partial, or failed."

    def handle(self, *args, **options):
        queryset = RefundAuditEmail.objects.filter(
            status__in=(
                RefundAuditEmail.Status.PENDING,
                RefundAuditEmail.Status.PARTIAL,
                RefundAuditEmail.Status.FAILED,
            ),
            refund__status="refunded",
        ).order_by("created_at")
        count = 0
        for audit in queryset.iterator():
            send_refund_audit_email(audit.pk)
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Processed {count} refund audit email record(s)."))
