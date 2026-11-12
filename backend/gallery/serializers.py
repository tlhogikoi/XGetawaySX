from rest_framework import serializers

from .models import GalleryAuditEvent, GalleryMedia, GalleryPartnerNotification, GalleryStory, GalleryStoryRevision
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
        )
        read_only_fields = (
            "status", "owner_history_private", "original_history_public_permission",
            "ai_assisted", "current_version", "owner_approved_version",
            "editorial_approved_version", "owner_approved_at", "editorial_approved_at",
        )

    def get_editorial_feedback(self, obj):
        event = obj.audit_events.filter(action="story_changes_requested").order_by("-created_at").first()
        return event.details.get("reason") if event else None

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
        fields = ("id", "story", "version", "summary", "owner_history_private", "ai_assisted", "change_reason", "changed_by", "created_at")
        read_only_fields = fields


class GalleryAuditEventSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source="actor.email", read_only=True, allow_null=True)
    partner_name = serializers.CharField(source="partner.name", read_only=True, allow_null=True)
    class Meta:
        model = GalleryAuditEvent
        fields = ("id", "actor_email", "partner_name", "action", "details", "created_at")
        read_only_fields = fields


class GalleryPartnerNotificationSerializer(serializers.ModelSerializer):
    story_id = serializers.IntegerField(source="story_id", read_only=True)
    class Meta:
        model = GalleryPartnerNotification
        fields = ("id", "story_id", "kind", "title", "message", "read_at", "created_at")
        read_only_fields = fields
