from rest_framework import serializers

from .consent_models import ConsentPreference


class ConsentPreferenceSerializer(serializers.ModelSerializer):
    label = serializers.CharField(source="get_purpose_display", read_only=True)

    class Meta:
        model = ConsentPreference
        fields = ("purpose", "label", "enabled", "policy_version", "source", "updated_at")
        read_only_fields = fields


class ConsentPreferenceUpdateSerializer(serializers.Serializer):
    purpose = serializers.ChoiceField(choices=ConsentPreference.Purpose.choices)
    enabled = serializers.BooleanField()
    policy_version = serializers.CharField(max_length=40, default="2026-11")
    source = serializers.ChoiceField(choices=(("privacy_centre", "Privacy Centre"),), default="privacy_centre")
