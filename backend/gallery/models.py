from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from partners.models import Partner


class GalleryMedia(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        OWNER_REVIEW = "owner_review", "Awaiting owner approval"
        EDITORIAL_REVIEW = "editorial_review", "Awaiting editorial approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        WITHDRAWN = "withdrawn", "Withdrawn"

    partner = models.ForeignKey(Partner, on_delete=models.PROTECT, related_name="gallery_media")
    title = models.CharField(max_length=180)
    image = models.URLField(max_length=1000)
    alt_text = models.CharField(max_length=250)
    caption = models.CharField(max_length=250, blank=True)
    media_credit = models.CharField(max_length=180, blank=True)
    rights_holder = models.CharField(max_length=180)
    rights_reference = models.CharField(max_length=250, blank=True)
    rights_confirmed = models.BooleanField(default=False)
    promotional_permission = models.BooleanField(default=False)
    permission_granted_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.DRAFT)
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="gallery_media_submissions")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("partner", "status"), name="gallery_media_partner_status_idx")]

    def clean(self):
        if self.promotional_permission and not self.permission_granted_at:
            raise ValidationError({"permission_granted_at": "Record when promotional permission was granted."})
        if self.status == self.Status.APPROVED and not (self.rights_confirmed and self.promotional_permission):
            raise ValidationError("Media rights and promotional permission are required before approval.")

    def __str__(self):
        return f"{self.partner.name}: {self.title}"


class GalleryStory(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        OWNER_REVIEW = "owner_review", "Awaiting owner approval"
        EDITORIAL_REVIEW = "editorial_review", "Awaiting editorial approval"
        PUBLISHED = "published", "Published"
        REJECTED = "rejected", "Rejected"
        WITHDRAWN = "withdrawn", "Withdrawn"

    media = models.OneToOneField(GalleryMedia, on_delete=models.PROTECT, related_name="story")
    # Source facts are retained privately. They are never included in public serializers.
    owner_original_history = models.TextField(blank=True)
    owner_history_private = models.BooleanField(default=True)
    summary = models.CharField(max_length=600, blank=True)
    summary_word_count = models.PositiveSmallIntegerField(default=0)
    ai_assisted = models.BooleanField(default=False)
    ai_source_facts = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.DRAFT)
    owner_approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="gallery_owner_approvals")
    owner_approved_at = models.DateTimeField(null=True, blank=True)
    editorial_approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="gallery_editorial_approvals")
    editorial_approved_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-published_at", "-created_at")

    @staticmethod
    def word_count(value):
        return len(value.split())

    def clean(self):
        count = self.word_count(self.summary)
        if self.summary and not 30 <= count <= 60:
            raise ValidationError({"summary": "Published story summaries must contain 30–60 words."})
        if not self.owner_history_private and not self.owner_approved_at:
            raise ValidationError("Publishing the owner's original history requires explicit owner approval.")
        if self.status == self.Status.PUBLISHED:
            if not (self.owner_approved_at and self.editorial_approved_at):
                raise ValidationError("Owner and editorial approval are both required.")
            if self.media.status != GalleryMedia.Status.APPROVED:
                raise ValidationError("The associated media must be approved.")
            if self.media.partner.gallery_status != Partner.ApprovalStatus.APPROVED:
                raise ValidationError("The partner must be approved for Gallery publication.")
            if not (self.media.rights_confirmed and self.media.promotional_permission):
                raise ValidationError("Media rights and promotional permission must be confirmed.")

    def __str__(self):
        return f"Story for {self.media.title}"
