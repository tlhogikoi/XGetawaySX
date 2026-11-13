from django.conf import settings
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

class PartnerFinancialSettings(models.Model):
    class DepositType(models.TextChoices):
        NONE = "none", "No deposit"
        PERCENTAGE = "percentage", "Percentage"
        FIXED = "fixed", "Fixed amount"

    partner = models.OneToOneField(Partner, on_delete=models.CASCADE, related_name="financial_settings")
    deposit_type = models.CharField(max_length=12, choices=DepositType.choices, default=DepositType.NONE)
    deposit_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="ZAR")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Financial settings — {self.partner.name}"


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
            models.Index(fields=("reservation", "status"), name="reservation_payment_status_idx"),
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

