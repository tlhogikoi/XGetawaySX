from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers

from partners.models import Partner
from .models import GalleryAuditEvent, GalleryMedia, GalleryMediaPermissionGrant, GalleryPartnerNotification, GalleryStory, GalleryStoryRevision
from .validators import validate_gallery_image


class PublicGalleryStorySerializer(serializers.ModelSerializer):
    title = serializers.CharField(source="media.title", read_only=True)
    image = serializers.SerializerMethodField()
    alt_text = serializers.CharField(source="media.alt_text", read_only=True)
    partner_name = serializers.CharField(source="media.partner.name", read_only=True)
    partner_slug = serializers.CharField(source="media.partner.slug", read_only=True)
    partner_city = serializers.CharField(source="media.partner.city", read_only=True)
    owner_original_history = serializers.SerializerMethodField()

    def get_image(self, obj):
        if obj.media.image_file:
            request = self.context.get("request")
            path = f"/api/v1/gallery/media/{obj.media_id}/image/"
            return request.build_absolute_uri(path) if request else path
        return obj.media.image

    def get_owner_original_history(self, obj):
        if obj.owner_history_private or not obj.original_history_public_permission:
            return None
        has_current_version_consent = any(
            consent.story_version == obj.current_version
            and consent.revoked_at is None
            and consent.granted_by_id == obj.media.partner.owner_id
            for consent in obj.history_publication_consents.all()
        )
        return obj.owner_original_history if has_current_version_consent else None

    class Meta:
        model = GalleryStory
        fields = ("id", "title", "summary", "published_at", "image", "alt_text", "partner_name", "partner_slug", "partner_city", "owner_original_history")
        read_only_fields = fields


class GalleryStoryDraftSerializer(serializers.ModelSerializer):
    editorial_feedback = serializers.SerializerMethodField()
    publication_checks = serializers.SerializerMethodField()
    publication_ready = serializers.SerializerMethodField()
    media_status = serializers.CharField(source="media.status", read_only=True)
    partner_gallery_status = serializers.CharField(source="media.partner.gallery_status", read_only=True)

    class Meta:
        model = GalleryStory
        fields = (
            "id", "media", "owner_original_history", "owner_history_private",
            "original_history_public_permission", "summary", "ai_assisted",
            "ai_source_facts", "status", "current_version", "editorial_feedback",
            "owner_approved_version", "editorial_approved_version",
            "owner_approved_at", "editorial_approved_at", "media_status", "partner_gallery_status",
            "publication_checks", "publication_ready",
        )
        read_only_fields = (
            "status", "owner_history_private", "original_history_public_permission",
            "ai_assisted", "current_version", "owner_approved_version",
            "editorial_approved_version", "owner_approved_at", "editorial_approved_at",
        )

    def get_editorial_feedback(self, obj):
        event = obj.audit_events.filter(action="story_changes_requested").order_by("-created_at").first()
        return event.details.get("reason") if event else None

    def get_publication_checks(self, obj):
        media_items = [obj.media] + [
            attachment.media
            for attachment in obj.additional_media.select_related("media").all()
        ]
        now = timezone.now()
        website_permissions = []
        for media in media_items:
            grants = media.permission_grants.filter(
                purpose=GalleryMediaPermissionGrant.Purpose.GALLERY_PROMOTION,
                review_status=GalleryMediaPermissionGrant.ReviewStatus.APPROVED,
                revoked_at__isnull=True,
            ).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
            website_permissions.append(any(
                isinstance(channels, list) and "website" in channels
                for channels in grants.values_list("permitted_channels", flat=True)
            ))

        partner_approved = obj.media.partner.gallery_status == Partner.ApprovalStatus.APPROVED
        media_approved = all(media.status == GalleryMedia.Status.APPROVED for media in media_items)
        website_permission = all(website_permissions)
        summary_valid = 30 <= len(obj.summary.split()) <= 60
        owner_approved = bool(obj.owner_approved_at and obj.owner_approved_version == obj.current_version)
        editorial_approved = bool(obj.editorial_approved_at and obj.editorial_approved_version == obj.current_version)

        return [
            {"key": "partner_approved", "label": "Partner profile approval", "passed": partner_approved,
             "detail": "Partner profile is approved." if partner_approved else "The partner profile must be approved for Gallery publication."},
            {"key": "media_approved", "label": "All story images approved", "passed": media_approved,
             "detail": "Every image is approved." if media_approved else "Every image in this story must pass editorial media approval."},
            {"key": "website_permission", "label": "Website publication rights", "passed": website_permission,
             "detail": "Every image has active website permission." if website_permission else "Each image needs an active, approved rights grant that explicitly permits website use."},
            {"key": "summary_valid", "label": "Public story summary", "passed": summary_valid,
             "detail": "The summary meets the 30–60 word requirement." if summary_valid else "The public summary must contain 30–60 words."},
            {"key": "owner_approval", "label": "Current-version owner approval", "passed": owner_approved,
             "detail": "The current version has owner approval." if owner_approved else "Approve this exact story version in your partner workspace."},
            {"key": "editorial_approval", "label": "Current-version editorial approval", "passed": editorial_approved,
             "detail": "The current version has editorial approval." if editorial_approved else "Editorial staff must approve this exact version after completing quality checks."},
        ]

    def get_publication_ready(self, obj):
        return all(check["passed"] for check in self.get_publication_checks(obj))

    def validate_summary(self, value):
        count = len(value.split())
        if value and not 30 <= count <= 60:
            raise serializers.ValidationError("Story summary must contain 30–60 words.")
        return value

    def validate_media(self, value):
        if self.instance and value.pk != self.instance.media_id:
            raise serializers.ValidationError("A story stays attached to its image. Create a separate story for another image.")
        return value

    def validate(self, attrs):
        media = attrs.get("media", getattr(self.instance, "media", None))
        request = self.context.get("request")
        if media and request and not request.user.is_staff and media.partner.owner_id != request.user.id:
            raise serializers.ValidationError("You can only create stories for your own partner media.")
        return attrs


class GalleryMediaDraftSerializer(serializers.ModelSerializer):
    image_file = serializers.FileField(write_only=True, required=False, allow_null=True, validators=[validate_gallery_image])

    class Meta:
        model = GalleryMedia
        fields = ("id", "partner", "title", "image", "image_file", "alt_text", "caption", "media_credit", "rights_holder", "rights_reference", "rights_confirmed", "promotional_permission", "permission_granted_at", "status")
        read_only_fields = ("status",)

    def validate(self, attrs):
        if not attrs.get("image_file") and not attrs.get("image"):
            raise serializers.ValidationError("Upload an image file or provide a legacy externally hosted image URL.")
        return attrs

    def validate_partner(self, value):
        request = self.context.get("request")
        if request and not request.user.is_staff and value.owner_id != request.user.id:
            raise serializers.ValidationError("You can only submit media for your own partner entity.")
        return value


class GalleryStoryRevisionSerializer(serializers.ModelSerializer):
    changed_by = serializers.EmailField(source="changed_by.email", read_only=True, allow_null=True)
    class Meta:
        model = GalleryStoryRevision
        fields = ("id", "story", "version", "summary", "owner_history_private", "ai_assisted", "media_snapshot", "change_reason", "changed_by", "created_at")
        read_only_fields = fields


class GalleryAuditEventSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source="actor.email", read_only=True, allow_null=True)
    partner_id = serializers.IntegerField(read_only=True, allow_null=True)
    partner_name = serializers.CharField(source="partner.name", read_only=True, allow_null=True)
    media_id = serializers.IntegerField(read_only=True, allow_null=True)
    media_title = serializers.SerializerMethodField()
    story_id = serializers.IntegerField(read_only=True, allow_null=True)
    story_version = serializers.SerializerMethodField()
    safe_details = serializers.SerializerMethodField()

    def get_media_title(self, obj):
        if obj.media_id:
            return obj.media.title
        if obj.story_id:
            return obj.story.media.title
        return ""

    def get_story_version(self, obj):
        details = obj.details if isinstance(obj.details, dict) else {}
        return details.get("story_version")

    def get_safe_details(self, obj):
        details = obj.details if isinstance(obj.details, dict) else {}
        allowed = ("story_version", "permission_id", "quality_review_id", "media_id", "purpose")
        return {key: details[key] for key in allowed if key in details}

    class Meta:
        model = GalleryAuditEvent
        fields = (
            "id", "actor_email", "partner_id", "partner_name", "media_id",
            "media_title", "story_id", "story_version", "action", "safe_details", "created_at",
        )
        read_only_fields = fields


class GalleryPartnerNotificationSerializer(serializers.ModelSerializer):
    story_id = serializers.IntegerField(read_only=True)
    class Meta:
        model = GalleryPartnerNotification
        fields = ("id", "story_id", "kind", "title", "message", "read_at", "created_at")
        read_only_fields = fields


class PublicGalleryStoryDetailSerializer(PublicGalleryStorySerializer):
    caption = serializers.CharField(source="media.caption", read_only=True)
    media_credit = serializers.CharField(source="media.media_credit", read_only=True)
    images = serializers.SerializerMethodField()

    def get_images(self, obj):
        request = self.context.get("request")
        media_items = [(obj.media, 0)] + [
            (attachment.media, attachment.position)
            for attachment in obj.additional_media.all()
        ]
        result = []
        for media, position in media_items:
            if media.image_file:
                path = f"/api/v1/gallery/media/{media.pk}/image/"
                image_url = request.build_absolute_uri(path) if request else path
            else:
                image_url = media.image
            result.append({
                "id": media.pk,
                "position": position,
                "image": image_url,
                "alt_text": media.alt_text,
                "caption": media.caption,
                "media_credit": media.media_credit,
            })
        return result

    class Meta(PublicGalleryStorySerializer.Meta):
        fields = PublicGalleryStorySerializer.Meta.fields + ("caption", "media_credit", "images")
