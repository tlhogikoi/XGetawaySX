import uuid

from django.conf import settings
from django.db import models


class PrivacyRequest(models.Model):
    class RequestType(models.TextChoices):
        ACCESS = "access", "Access my information"
        CORRECTION = "correction", "Correct my information"
        DELETION = "deletion", "Request deletion"
        CONSENT_WITHDRAWAL = "consent_withdrawal", "Withdraw consent"
        MARKETING_OPTOUT = "marketing_optout", "Opt out of marketing"

    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under review"
        AWAITING_VERIFICATION = "awaiting_verification", "Awaiting identity verification"
        FULFILLED = "fulfilled", "Completed"
        DECLINED = "declined", "Declined"
        WITHDRAWN = "withdrawn", "Withdrawn"

    reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="privacy_requests")
    request_type = models.CharField(max_length=32, choices=RequestType.choices)
    description = models.TextField(max_length=4000)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.SUBMITTED)
    staff_note = models.TextField(blank=True, max_length=4000)
    identity_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    closed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.reference} · {self.get_request_type_display()}"


class PrivacyRequestEvent(models.Model):
    request = models.ForeignKey(PrivacyRequest, on_delete=models.CASCADE, related_name="events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="privacy_request_events")
    from_status = models.CharField(max_length=32, blank=True)
    to_status = models.CharField(max_length=32)
    note = models.CharField(max_length=1000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at",)
