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

    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="partner_profile",
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
