from rest_framework import serializers

from .models import GalleryMedia, GalleryStory


class PublicGalleryStorySerializer(serializers.ModelSerializer):
    image = serializers.URLField(source="media.image", read_only=True)
    alt_text = serializers.CharField(source="media.alt_text", read_only=True)
    partner_name = serializers.CharField(source="media.partner.name", read_only=True)
    partner_slug = serializers.CharField(source="media.partner.slug", read_only=True)
    partner_city = serializers.CharField(source="media.partner.city", read_only=True)

    class Meta:
        model = GalleryStory
        fields = ("id", "summary", "published_at", "image", "alt_text", "partner_name", "partner_slug", "partner_city")
        read_only_fields = fields


class GalleryStoryDraftSerializer(serializers.ModelSerializer):
    class Meta:
        model = GalleryStory
        fields = ("id", "media", "owner_original_history", "owner_history_private", "summary", "ai_assisted", "ai_source_facts", "status")
        read_only_fields = ("status",)

    def validate_summary(self, value):
        count = len(value.split())
        if value and not 30 <= count <= 60:
            raise serializers.ValidationError("Story summary must contain 30–60 words.")
        return value

    def validate(self, attrs):
        media = attrs.get("media", getattr(self.instance, "media", None))
        request = self.context.get("request")
        if media and request and not request.user.is_staff and media.partner.owner_id != request.user.id:
            raise serializers.ValidationError("You can only create stories for your own partner media.")
        return attrs


class GalleryMediaDraftSerializer(serializers.ModelSerializer):
    class Meta:
        model = GalleryMedia
        fields = ("id", "partner", "title", "image", "alt_text", "caption", "media_credit", "rights_holder", "rights_reference", "rights_confirmed", "promotional_permission", "permission_granted_at", "status")
        read_only_fields = ("status",)

    def validate_partner(self, value):
        request = self.context.get("request")
        if request and not request.user.is_staff and value.owner_id != request.user.id:
            raise serializers.ValidationError("You can only submit media for your own partner entity.")
        return value
