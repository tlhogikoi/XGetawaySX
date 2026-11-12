from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone
from pathlib import Path
from uuid import uuid4

from .storage import PrivateGalleryStorage
from .validators import validate_gallery_evidence, validate_gallery_image


private_gallery_storage = PrivateGalleryStorage()

def gallery_media_upload_path(instance, filename):
    suffix = Path(filename).suffix.lower()
    return f"gallery/media/{timezone.now():%Y/%m}/{uuid4().hex}{suffix}"

def gallery_evidence_upload_path(instance, filename):
    suffix = Path(filename).suffix.lower()
    return f"gallery/evidence/{timezone.now():%Y/%m}/{uuid4().hex}{suffix}"

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
    image = models.URLField(max_length=1000, blank=True)
    image_file = models.FileField(
        storage=private_gallery_storage, upload_to=gallery_media_upload_path,
        blank=True, null=True, validators=[validate_gallery_image],
    )
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
        indexes = [models.Index(fields=("partner", "status"), name="gal_media_partner_status_idx")]

    def clean(self):
        # Formal GalleryMediaPermissionGrant records are the publication source of truth.
        if self.status == self.Status.APPROVED and self.pk:
            now = timezone.now()
            has_active_permission = self.permission_grants.filter(
                purpose=GalleryMediaPermissionGrant.Purpose.GALLERY_PROMOTION,
                review_status=GalleryMediaPermissionGrant.ReviewStatus.APPROVED,
                revoked_at__isnull=True,
            ).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now)).exists()
            if not has_active_permission:
                raise ValidationError("Media cannot be approved without an active, editorially verified Gallery permission.")

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
    original_history_public_permission = models.BooleanField(default=False)
    summary = models.CharField(max_length=600, blank=True)
    summary_word_count = models.PositiveSmallIntegerField(default=0)
    ai_assisted = models.BooleanField(default=False)
    ai_source_facts = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.DRAFT)
    current_version = models.PositiveIntegerField(default=1)
    owner_approved_version = models.PositiveIntegerField(null=True, blank=True)
    editorial_approved_version = models.PositiveIntegerField(null=True, blank=True)
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
        if not self.owner_history_private:
            consent_exists = self.history_publication_consents.filter(
                story_version=self.current_version,
                revoked_at__isnull=True,
                granted_by_id=self.media.partner.owner_id,
            ).exists()
            if not (self.original_history_public_permission and consent_exists):
                raise ValidationError("Publishing original history requires separate, current-version owner consent.")
        if self.status == self.Status.PUBLISHED:
            if not (self.owner_approved_at and self.owner_approved_version == self.current_version):
                raise ValidationError("The current story version must have owner approval.")
            if not (self.editorial_approved_at and self.editorial_approved_version == self.current_version):
                raise ValidationError("The current story version must have editorial approval.")
            if self.media.status != GalleryMedia.Status.APPROVED:
                raise ValidationError("The associated media must be approved.")
            if self.media.partner.gallery_status != Partner.ApprovalStatus.APPROVED:
                raise ValidationError("The partner must be approved for Gallery publication.")
            now = timezone.now()
            has_active_permission = self.media.permission_grants.filter(
                purpose=GalleryMediaPermissionGrant.Purpose.GALLERY_PROMOTION,
                review_status=GalleryMediaPermissionGrant.ReviewStatus.APPROVED,
                revoked_at__isnull=True,
            ).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now)).exists()
            if not has_active_permission:
                raise ValidationError("An active, evidence-backed Gallery media permission grant is required.")

    def __str__(self):
        return f"Story for {self.media.title}"


class GalleryHistoryPublicationConsent(models.Model):
    story = models.ForeignKey(GalleryStory, on_delete=models.PROTECT, related_name="history_publication_consents")
    story_version = models.PositiveIntegerField()
    granted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="gallery_history_consents_granted")
    granted_at = models.DateTimeField()
    revoked_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="gallery_history_consents_revoked")
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-granted_at",)
        constraints = [
            models.UniqueConstraint(fields=("story", "story_version"), name="gal_history_consent_version_unique"),
        ]

    def clean(self):
        if self.granted_by_id != self.story.media.partner.owner_id:
            raise ValidationError("Only the partner owner may grant publication permission for original history.")
        if self.story_version != self.story.current_version:
            raise ValidationError("Original-history permission must apply to the current story version.")




class GalleryStoryRevision(models.Model):
    story = models.ForeignKey(GalleryStory, on_delete=models.PROTECT, related_name="revisions")
    version = models.PositiveIntegerField()
    summary = models.CharField(max_length=600, blank=True)
    owner_original_history_snapshot = models.TextField(blank=True)
    owner_history_private = models.BooleanField(default=True)
    original_history_public_permission = models.BooleanField(default=False)
    ai_assisted = models.BooleanField(default=False)
    ai_source_facts_snapshot = models.JSONField(default=list, blank=True)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name="gallery_story_revisions")
    change_reason = models.CharField(max_length=250, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-version",)
        constraints = [
            models.UniqueConstraint(fields=("story", "version"), name="gal_story_version_unique"),
        ]

    @classmethod
    @transaction.atomic
    def capture(cls, story, actor=None, reason=""):
        locked_story = GalleryStory.objects.select_for_update().get(pk=story.pk)
        latest = cls.objects.filter(story=locked_story).order_by("-version").first()
        version = (latest.version + 1) if latest else 1
        # A material content change always returns the original history to private
        # and invalidates approvals/consent associated with the previous version.
        locked_story.current_version = version
        locked_story.owner_history_private = True
        locked_story.original_history_public_permission = False
        locked_story.owner_approved_by = None
        locked_story.owner_approved_at = None
        locked_story.owner_approved_version = None
        locked_story.editorial_approved_by = None
        locked_story.editorial_approved_at = None
        locked_story.editorial_approved_version = None
        locked_story.published_at = None
        locked_story.save(update_fields=(
            "current_version", "owner_history_private", "original_history_public_permission",
            "owner_approved_by", "owner_approved_at", "owner_approved_version",
            "editorial_approved_by", "editorial_approved_at", "editorial_approved_version",
            "published_at", "updated_at",
        ))
        story.current_version = version
        story.owner_history_private = True
        story.original_history_public_permission = False
        return cls.objects.create(
            story=locked_story,
            version=version,
            summary=locked_story.summary,
            owner_original_history_snapshot=locked_story.owner_original_history,
            owner_history_private=locked_story.owner_history_private,
            original_history_public_permission=locked_story.original_history_public_permission,
            ai_assisted=locked_story.ai_assisted,
            ai_source_facts_snapshot=locked_story.ai_source_facts,
            changed_by=actor,
            change_reason=reason,
        )


class GalleryAuditEvent(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name="gallery_audit_events")
    partner = models.ForeignKey(Partner, null=True, on_delete=models.PROTECT, related_name="gallery_audit_events")
    media = models.ForeignKey(GalleryMedia, null=True, on_delete=models.PROTECT, related_name="audit_events")
    story = models.ForeignKey(GalleryStory, null=True, on_delete=models.PROTECT, related_name="audit_events")
    action = models.CharField(max_length=60)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("action", "created_at"), name="gal_audit_action_date_idx")]


class GalleryMediaPermissionGrant(models.Model):
    """Private, auditable evidence that a rights holder permits Gallery promotion."""

    class Purpose(models.TextChoices):
        GALLERY_PROMOTION = "gallery_promotion", "XGetawaySX Gallery promotion"

    class ReviewStatus(models.TextChoices):
        PENDING = "pending", "Pending editorial rights review"
        APPROVED = "approved", "Rights approved"
        REJECTED = "rejected", "Rights rejected"

    media = models.ForeignKey(
        GalleryMedia, on_delete=models.PROTECT, related_name="permission_grants"
    )
    purpose = models.CharField(
        max_length=32, choices=Purpose.choices, default=Purpose.GALLERY_PROMOTION
    )
    rights_holder = models.CharField(max_length=180)
    permitted_channels = models.JSONField(default=list, blank=True)
    evidence_reference = models.CharField(max_length=500, blank=True)
    evidence_file = models.FileField(
        storage=private_gallery_storage, upload_to=gallery_evidence_upload_path,
        blank=True, null=True, validators=[validate_gallery_evidence],
    )
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="gallery_media_permissions_granted",
    )
    granted_at = models.DateTimeField()
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT,
        related_name="gallery_media_permissions_revoked",
    )
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-granted_at",)
        indexes = [
            models.Index(fields=("media", "purpose", "revoked_at"), name="gal_media_perm_active_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=models.F("granted_at")),
                name="gal_media_perm_expiry_after_grant",
            ),
        ]

    def clean(self):
        if self.granted_by_id and self.media_id and self.granted_by_id != self.media.partner.owner_id:
            raise ValidationError({"granted_by": "Only the owning partner may grant media publication permission."})
        if not self.rights_holder.strip():
            raise ValidationError({"rights_holder": "A rights holder is required."})
        if self.review_status == self.ReviewStatus.APPROVED and not self.evidence_file:
            raise ValidationError({"evidence_file": "An uploaded evidence document is required before rights approval."})
        if not isinstance(self.permitted_channels, list) or not self.permitted_channels:
            raise ValidationError({"permitted_channels": "At least one permitted channel is required."})
        if any(not isinstance(channel, str) or not channel.strip() for channel in self.permitted_channels):
            raise ValidationError({"permitted_channels": "Channels must be non-empty strings."})
        if self.expires_at and self.granted_at and self.expires_at <= self.granted_at:
            raise ValidationError({"expires_at": "Expiry must be later than the grant date."})
        if self.revoked_at and not self.revoked_by_id:
            raise ValidationError({"revoked_by": "Record who revoked this permission."})
        if self.review_status in (self.ReviewStatus.APPROVED, self.ReviewStatus.REJECTED):
            if not self.reviewed_by_id or not self.reviewed_at:
                raise ValidationError("A completed rights review requires an editorial reviewer and timestamp.")
            if not self.reviewed_by.is_staff:
                raise ValidationError({"reviewed_by": "Only authorised editorial staff may review media rights."})
        elif self.reviewed_by_id or self.reviewed_at:
            raise ValidationError("Pending rights reviews cannot have a reviewer or review timestamp.")

    @property
    def is_active(self):
        return (
            self.revoked_at is None
            and (self.expires_at is None or self.expires_at > timezone.now())
            and self.purpose == self.Purpose.GALLERY_PROMOTION
            and self.review_status == self.ReviewStatus.APPROVED
        )

    def __str__(self):
        return f"{self.media_id}: {self.purpose} ({self.rights_holder})"
