from django.core.management.base import BaseCommand, CommandError

from partners.models import RefundAuditEmail
from partners.refund_notifications import send_refund_audit_email


class Command(BaseCommand):
    help = "Retry pending, partial, or failed refund audit emails."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit", type=int, default=100,
            help="Maximum records to process (0 means no limit).",
        )
        parser.add_argument(
            "--max-attempts", type=int, default=10,
            help="Do not retry records that have reached this attempt count.",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Report eligible records without sending emails.",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        max_attempts = options["max_attempts"]
        if limit < 0:
            raise CommandError("--limit must be zero or a positive integer.")
        if max_attempts < 1:
            raise CommandError("--max-attempts must be at least 1.")

        queryset = RefundAuditEmail.objects.filter(
            status__in=(
                RefundAuditEmail.Status.PENDING,
                RefundAuditEmail.Status.PARTIAL,
                RefundAuditEmail.Status.FAILED,
            ),
            refund__status="refunded",
            attempts__lt=max_attempts,
        ).order_by("created_at", "pk")

        eligible = queryset.count()
        selected = queryset[:limit] if limit else queryset
        selected_count = min(eligible, limit) if limit else eligible

        if options["dry_run"]:
            self.stdout.write(
                f"Dry run: {selected_count} of {eligible} eligible refund audit "
                f"email record(s) would be processed (max attempts: {max_attempts})."
            )
            return

        attempted = sent = partial_or_failed = 0
        for audit in selected.iterator():
            result = send_refund_audit_email(audit.pk)
            attempted += 1
            if result.status == RefundAuditEmail.Status.SENT:
                sent += 1
            else:
                partial_or_failed += 1

        summary = (
            f"Refund audit email retry complete: {attempted} attempted, "
            f"{sent} fully delivered, {partial_or_failed} still pending/partial/failed. "
            f"{max(0, eligible - selected_count)} eligible record(s) left for a later run."
        )
        if partial_or_failed:
            self.stdout.write(self.style.WARNING(summary))
        else:
            self.stdout.write(self.style.SUCCESS(summary))
