import uuid
from pathlib import Path

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.text import slugify


class Partner(models.Model):
    class ApprovalStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        SUSPENDED = "suspended", "Suspended"
        REJECTED = "rejected", "Rejected"

    class Category(models.TextChoices):
        ACCOMMODATION = "accommodation", "Accommodation"
        FAMILY_HOME = "family_home", "Family home"
        TOUR = "tour", "Tour operator"
        ACTIVITY = "activity", "Activity"
        DINING = "dining", "Dining"
        WELLNESS = "wellness", "Wellness"
        TRANSPORT = "transport", "Transport"
        DESTINATION = "destination", "Destination"
        OTHER = "other", "Other"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="partner_profiles",
    )
    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True)
    category = models.CharField(max_length=30, choices=Category.choices)
    description = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    province = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default="South Africa")
    website_url = models.URLField(blank=True)

    gallery_status = models.CharField(
        max_length=20, choices=ApprovalStatus.choices, default=ApprovalStatus.PENDING
    )
    enquiry_status = models.CharField(
        max_length=20, choices=ApprovalStatus.choices, default=ApprovalStatus.PENDING
    )
    booking_status = models.CharField(
        max_length=20, choices=ApprovalStatus.choices, default=ApprovalStatus.PENDING
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
        indexes = [
            models.Index(fields=("gallery_status", "category"), name="partners_gallery_status_idx"),
            models.Index(fields=("city", "province"), name="partners_city_province_idx"),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class DestinationPage(models.Model):
    """Editorially curated public destination landing page."""
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True)
    introduction = models.CharField(max_length=280, blank=True)
    description = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    province = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default="South Africa")
    partners = models.ManyToManyField(Partner, blank=True, related_name="destination_pages")
    is_published = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("display_order", "name")

    def __str__(self):
        return self.name


class ExperienceCollection(models.Model):
    """A manually curated set of approved partner experiences."""
    title = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True)
    summary = models.CharField(max_length=280)
    description = models.TextField(blank=True)
    destination = models.ForeignKey(
        DestinationPage, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="collections",
    )
    partners = models.ManyToManyField(Partner, blank=True, related_name="experience_collections")
    is_published = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("display_order", "title")

    def __str__(self):
        return self.title


class TripPlan(models.Model):
    """Private customer itinerary draft."""
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="trip_plans"
    )
    title = models.CharField(max_length=160, default="My getaway")
    notes = models.TextField(blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)

    def __str__(self):
        return self.title


class TripPlanItem(models.Model):
    plan = models.ForeignKey(TripPlan, on_delete=models.CASCADE, related_name="items")
    partner = models.ForeignKey(Partner, on_delete=models.PROTECT, related_name="trip_plan_items")
    note = models.CharField(max_length=500, blank=True)
    display_order = models.PositiveIntegerField(default=0)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("display_order", "added_at")
        constraints = [
            models.UniqueConstraint(fields=("plan", "partner"), name="unique_partner_per_trip_plan")
        ]

    def __str__(self):
        return f"{self.partner.name} in {self.plan.title}"


class PartnerEnquiry(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RESPONDED = "responded", "Responded"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"
        CLOSED = "closed", "Closed"

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="partner_enquiries"
    )
    partner = models.ForeignKey(
        Partner, on_delete=models.PROTECT, related_name="customer_enquiries"
    )
    trip_plan = models.ForeignKey(
        TripPlan, on_delete=models.SET_NULL, null=True, blank=True, related_name="enquiries"
    )
    message = models.TextField()
    requested_start_date = models.DateField(null=True, blank=True)
    requested_end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    partner_response = models.TextField(blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    reservation_request = models.OneToOneField(
        "ReservationRequest", on_delete=models.PROTECT, null=True, blank=True,
        related_name="source_enquiry",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("partner", "status", "created_at"), name="partner_enquiry_status_idx"),
            models.Index(fields=("customer", "created_at"), name="customer_enquiry_date_idx"),
        ]

    def __str__(self):
        return f"Enquiry {self.pk} — {self.partner.name}"

class PartnerAvailability(models.Model):
    """Partner-managed daily capacity. Checkout dates are exclusive on reservations."""
    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name="availability_days")
    date = models.DateField()
    capacity = models.PositiveIntegerField()
    booked_count = models.PositiveIntegerField(default=0)
    is_open = models.BooleanField(default=True)
    price_per_guest = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default="ZAR")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("date",)
        constraints = [
            models.UniqueConstraint(fields=("partner", "date"), name="uniq_partner_avail_day"),
            models.CheckConstraint(condition=models.Q(booked_count__lte=models.F("capacity")), name="avail_booked_lte_cap"),
        ]
        indexes = [models.Index(fields=("partner", "date", "is_open"), name="partner_availability_day_idx")]

    def __str__(self):
        return f"{self.partner.name} — {self.date}"


class ReservationRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        DECLINED = "declined", "Declined"
        CANCELLED = "cancelled", "Cancelled"

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="reservation_requests"
    )
    partner = models.ForeignKey(
        Partner, on_delete=models.PROTECT, related_name="reservation_requests"
    )
    trip_plan = models.ForeignKey(
        TripPlan, on_delete=models.SET_NULL, null=True, blank=True, related_name="reservation_requests"
    )
    start_date = models.DateField()
    end_date = models.DateField(help_text="Checkout date; exclusive.")
    guests = models.PositiveIntegerField()
    message = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    booking_reference = models.UUIDField(null=True, blank=True, unique=True)
    quoted_total = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    quoted_deposit = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    quoted_currency = models.CharField(max_length=3, null=True, blank=True)
    quoted_at = models.DateTimeField(null=True, blank=True)
    partner_response = models.TextField(blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("partner", "status", "start_date"), name="partner_res_status_idx"),
            models.Index(fields=("customer", "created_at"), name="customer_reservation_date_idx"),
        ]

    def __str__(self):
        return f"Reservation request {self.pk} — {self.partner.name}"


class ReservationQuote(models.Model):
    class Status(models.TextChoices):
        SENT = "sent", "Sent to customer"
        ACCEPTED = "accepted", "Accepted by customer"
        DECLINED = "declined", "Declined by customer"
        EXPIRED = "expired", "Expired"

    reservation = models.ForeignKey(
        ReservationRequest, on_delete=models.PROTECT, related_name="quotes"
    )
    version = models.PositiveIntegerField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.SENT)
    currency = models.CharField(max_length=3, default="ZAR")
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    deposit_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    terms = models.TextField(blank=True, max_length=3000)
    expires_at = models.DateTimeField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="issued_reservation_quotes"
    )
    responded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-version",)
        constraints = [
            models.UniqueConstraint(fields=("reservation", "version"), name="uniq_res_quote_version"),
        ]
        indexes = [models.Index(fields=("reservation", "status"), name="res_quote_status_idx")]

    def __str__(self):
        return f"Quote v{self.version} — reservation {self.reservation_id}"


class ReservationQuoteItem(models.Model):
    quote = models.ForeignKey(ReservationQuote, on_delete=models.CASCADE, related_name="items")
    description = models.CharField(max_length=180)
    quantity = models.DecimalField(max_digits=8, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ("id",)

    def __str__(self):
        return f"{self.description} — quote {self.quote_id}"


class ReservationCancellationRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending review"
        APPROVED = "approved", "Approved — refund/cancellation in progress"
        DECLINED = "declined", "Declined"
        COMPLETED = "completed", "Completed"

    reservation = models.ForeignKey(
        ReservationRequest, on_delete=models.PROTECT, related_name="cancellation_requests"
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="reservation_cancellations"
    )
    reason = models.CharField(max_length=1000)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    decision_note = models.CharField(max_length=1000, blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="decided_reservation_cancellations",
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-requested_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("reservation",),
                condition=models.Q(status__in=("pending", "approved")),
                name="uniq_active_reservation_cancel",
            )
        ]
        indexes = [models.Index(fields=("status", "requested_at"), name="cancel_status_date_idx")]

    def __str__(self):
        return f"Cancellation request {self.pk} — reservation {self.reservation_id}"


class ReservationNotification(models.Model):
    class Event(models.TextChoices):
        CANCELLATION_REQUESTED = "cancellation_requested", "Cancellation requested"
        CANCELLATION_DECISION = "cancellation_decision", "Cancellation decision"
        CANCELLATION_COMPLETED = "cancellation_completed", "Cancellation completed"
        PAYMENT_REMINDER = "payment_reminder", "Payment reminder"
        REFUND_UPDATE = "refund_update", "Refund update"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reservation_notifications"
    )
    reservation = models.ForeignKey(
        ReservationRequest, on_delete=models.CASCADE, related_name="notifications"
    )
    cancellation_request = models.ForeignKey(
        ReservationCancellationRequest, on_delete=models.CASCADE, null=True, blank=True,
        related_name="notifications",
    )
    event = models.CharField(max_length=32, choices=Event.choices)
    title = models.CharField(max_length=160)
    message = models.CharField(max_length=500)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("recipient", "read_at", "created_at"), name="res_notif_inbox_idx")]

    def __str__(self):
        return f"{self.title} — {self.recipient_id}"


class PartnerFinancialSettings(models.Model):
    class DepositType(models.TextChoices):
        NONE = "none", "No deposit"
        PERCENTAGE = "percentage", "Percentage"
        FIXED = "fixed", "Fixed amount"

    partner = models.OneToOneField(Partner, on_delete=models.CASCADE, related_name="financial_settings")
    deposit_type = models.CharField(max_length=12, choices=DepositType.choices, default=DepositType.NONE)
    deposit_value = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    currency = models.CharField(max_length=3, default="ZAR")
    deposit_due_hours = models.PositiveSmallIntegerField(default=48)
    balance_due_days_before = models.PositiveSmallIntegerField(default=7)
    balance_installment_count = models.PositiveSmallIntegerField(default=1)
    balance_installment_interval_days = models.PositiveSmallIntegerField(default=7)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Financial settings — {self.partner.name}"


class ReservationInstallment(models.Model):
    """Partner-approved payment milestones for a confirmed reservation."""
    class Kind(models.TextChoices):
        DEPOSIT = "deposit", "Deposit"
        BALANCE = "balance", "Balance"

    reservation = models.ForeignKey(
        ReservationRequest, on_delete=models.PROTECT, related_name="installments"
    )
    sequence = models.PositiveSmallIntegerField()
    kind = models.CharField(max_length=12, choices=Kind.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="ZAR")
    due_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("sequence",)
        constraints = [
            models.UniqueConstraint(fields=("reservation", "sequence"), name="uniq_res_installment_seq"),
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="res_installment_amount_positive"),
        ]
        indexes = [models.Index(fields=("due_at", "reservation"), name="res_installment_due_idx")]

    def __str__(self):
        return f"{self.kind} — reservation {self.reservation_id}"


class ReservationPayment(models.Model):
    class Kind(models.TextChoices):
        DEPOSIT = "deposit", "Deposit"
        BALANCE = "balance", "Balance"
        FULL = "full", "Full payment"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CAPTURED = "captured", "Captured"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    reservation = models.ForeignKey(ReservationRequest, on_delete=models.PROTECT, related_name="payments")
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="reservation_payments")
    partner = models.ForeignKey(Partner, on_delete=models.PROTECT, related_name="reservation_payments")
    kind = models.CharField(max_length=12, choices=Kind.choices)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="ZAR")
    idempotency_key = models.CharField(max_length=100)
    provider = models.CharField(max_length=40, default="manual_reconciliation")
    checkout_session_id = models.CharField(max_length=180, blank=True)
    checkout_url = models.URLField(blank=True)
    provider_reference = models.CharField(max_length=160, null=True, blank=True, unique=True)
    failure_reason = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    captured_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(fields=("customer", "idempotency_key"), name="uniq_customer_payment_key"),
        ]
        indexes = [
            models.Index(fields=("partner", "status", "created_at"), name="partner_payment_status_idx"),
            models.Index(fields=("reservation", "status"), name="res_payment_status_idx"),
        ]

    def __str__(self):
        return f"{self.kind} payment {self.pk} — {self.amount} {self.currency}"


class PartnerCommissionLedger(models.Model):
    class Status(models.TextChoices):
        ACCRUED = "accrued", "Accrued"
        PAID_OUT = "paid_out", "Paid out"
        VOID = "void", "Void"

    payment = models.OneToOneField(ReservationPayment, on_delete=models.PROTECT, related_name="commission_entry")
    partner = models.ForeignKey(Partner, on_delete=models.PROTECT, related_name="commission_entries")
    gross_amount = models.DecimalField(max_digits=12, decimal_places=2)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2)
    commission_amount = models.DecimalField(max_digits=12, decimal_places=2)
    partner_net_amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACCRUED)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"Commission for payment {self.payment_id}"



class ReservationRefund(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        REFUNDED = "refunded", "Refunded"
        FAILED = "failed", "Failed"

    payment = models.ForeignKey(ReservationPayment, on_delete=models.PROTECT, related_name="refunds")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    provider = models.CharField(max_length=40)
    provider_reference = models.CharField(max_length=160, null=True, blank=True, unique=True)
    idempotency_key = models.CharField(max_length=100, unique=True)
    provider_status = models.CharField(max_length=40, blank=True)
    reason = models.CharField(max_length=500, blank=True)
    reconciled_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="reconciled_reservation_refunds")
    reconciled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("payment", "status"), name="refund_payment_status_idx")]

    def __str__(self):
        return f"Refund {self.pk} — payment {self.payment_id}"


class RefundAuditEmail(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent to all recipients"
        PARTIAL = "partial", "Partially sent"
        FAILED = "failed", "Failed"

    refund = models.OneToOneField(
        ReservationRefund, on_delete=models.PROTECT, related_name="audit_email"
    )
    customer_email = models.EmailField(blank=True)
    partner_email = models.EmailField(blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    customer_sent_at = models.DateTimeField(null=True, blank=True)
    partner_sent_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"Refund audit email — refund {self.refund_id}"


class CustomerEmailPreference(models.Model):
    """Marketing consent only; essential booking and financial emails are never disabled."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="email_preferences"
    )
    marketing_opt_in = models.BooleanField(default=False)
    unsubscribe_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "customer email preference"

    def __str__(self):
        return f"Email preferences — {self.user_id}"


class ReservationEmailDelivery(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Accepted by email backend"
        FAILED = "failed", "Failed"

    reservation = models.ForeignKey(
        ReservationRequest, on_delete=models.PROTECT, related_name="email_deliveries"
    )
    cancellation_request = models.ForeignKey(
        ReservationCancellationRequest, on_delete=models.PROTECT, null=True, blank=True,
        related_name="email_deliveries",
    )
    event = models.CharField(max_length=40)
    event_key = models.CharField(max_length=180, unique=True)
    recipient_email = models.EmailField()
    recipient_role = models.CharField(max_length=20)
    subject = models.CharField(max_length=200)
    body = models.TextField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    sent_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("status", "created_at"), name="res_email_status_idx")]

    def __str__(self):
        return f"{self.event} email to {self.recipient_email}"


class PartnerCommissionAdjustment(models.Model):
    """Immutable commission reversal snapshot associated with a reconciled refund."""
    refund = models.OneToOneField(ReservationRefund, on_delete=models.PROTECT, related_name="commission_adjustment")
    partner = models.ForeignKey(Partner, on_delete=models.PROTECT, related_name="commission_adjustments")
    gross_refund = models.DecimalField(max_digits=12, decimal_places=2)
    commission_reversal = models.DecimalField(max_digits=12, decimal_places=2)
    partner_net_reversal = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Commission adjustment for refund {self.refund_id}"


class PaymentProviderEvent(models.Model):
    """Provider event inbox. Events are persisted only after adapter signature verification."""
    provider = models.CharField(max_length=40)
    event_id = models.CharField(max_length=180)
    payload_sha256 = models.CharField(max_length=64)
    signature_verified = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("provider", "event_id"), name="uniq_provider_event_id")]
        indexes = [models.Index(fields=("provider", "received_at"), name="provider_event_received_idx")]

    def __str__(self):
        return f"{self.provider} event {self.event_id}"



class PartnerVerificationSubmission(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted for review"
        CHANGES_REQUESTED = "changes_requested", "Changes requested"
        APPROVED = "approved", "Verified"
        REJECTED = "rejected", "Rejected"

    partner = models.OneToOneField(
        Partner, on_delete=models.PROTECT, related_name="verification_submission"
    )
    legal_business_name = models.CharField(max_length=180, blank=True)
    registration_number = models.CharField(max_length=80, blank=True)
    is_sole_proprietor = models.BooleanField(default=False)
    tax_number = models.CharField(max_length=80, blank=True)
    contact_person = models.CharField(max_length=160, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=40, blank=True)
    physical_address = models.TextField(blank=True, max_length=1000)
    document_checklist = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.DRAFT)
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT,
        related_name="partner_verifications_reviewed",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True, max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)
        indexes = [
            models.Index(fields=("status", "submitted_at"), name="partner_verify_queue_idx"),
        ]

    def __str__(self):
        return f"Verification — {self.partner.name} ({self.status})"


class PartnerVerificationEvent(models.Model):
    submission = models.ForeignKey(
        PartnerVerificationSubmission, on_delete=models.PROTECT, related_name="events"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT,
        related_name="partner_verification_events",
    )
    event_type = models.CharField(max_length=40)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("submission", "created_at"), name="partner_verify_event_idx"),
        ]

    def __str__(self):
        return f"{self.event_type} — verification {self.submission_id}"


from gallery.storage import PrivateGalleryStorage
from gallery.validators import validate_gallery_evidence
from django.utils import timezone

private_partner_verification_storage = PrivateGalleryStorage()


def partner_verification_upload_path(instance, filename):
    suffix = Path(filename).suffix.lower()
    return f"partners/verification/{timezone.now():%Y/%m}/{uuid.uuid4().hex}{suffix}"


class PartnerVerificationDocument(models.Model):
    submission = models.ForeignKey(
        PartnerVerificationSubmission, on_delete=models.PROTECT, related_name="documents"
    )
    document_type = models.CharField(max_length=40, choices=[
        ("business_registration", "Business registration"),
        ("proof_of_address", "Proof of address"),
        ("owner_identity", "Owner identity"),
        ("tax_certificate", "Tax certificate"),
        ("operating_licence", "Operating licence"),
    ])
    file = models.FileField(
        storage=private_partner_verification_storage,
        upload_to=partner_verification_upload_path,
        validators=[validate_gallery_evidence],
    )
    original_filename = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="partner_verification_documents",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("document_type", "-uploaded_at")
        indexes = [
            models.Index(fields=("submission", "document_type"), name="partner_verify_doc_idx"),
        ]

    def __str__(self):
        return f"{self.get_document_type_display()} — verification {self.submission_id}"
