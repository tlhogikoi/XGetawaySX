from rest_framework import serializers

from .privacy_models import PrivacyRequest, PrivacyRequestEvent


class PrivacyRequestEventSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source="actor.email", read_only=True)

    class Meta:
        model = PrivacyRequestEvent
        fields = ("from_status", "to_status", "note", "actor_email", "created_at")


class PrivacyRequestSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    events = PrivacyRequestEventSerializer(many=True, read_only=True)

    class Meta:
        model = PrivacyRequest
        fields = (
            "reference", "request_type", "description", "status", "staff_note",
            "identity_verified", "created_at", "updated_at", "closed_at",
            "user_email", "events",
        )
        read_only_fields = (
            "reference", "status", "staff_note", "identity_verified", "created_at",
            "updated_at", "closed_at", "user_email", "events",
        )

    def validate_description(self, value):
        value = value.strip()
        if len(value) < 10:
            raise serializers.ValidationError("Please provide at least 10 characters of context.")
        return value


class PrivacyRequestStaffUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrivacyRequest
        fields = ("status", "staff_note", "identity_verified")

    def validate(self, attrs):
        next_status = attrs.get("status", self.instance.status if self.instance else None)
        identity_verified = attrs.get("identity_verified", self.instance.identity_verified if self.instance else False)
        if next_status == PrivacyRequest.Status.FULFILLED and not identity_verified:
            raise serializers.ValidationError({"identity_verified": "Identity must be verified before a request can be marked completed."})
        return attrs
