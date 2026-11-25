from django.db import transaction
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .consent_models import ConsentEvent, ConsentPreference
from .consent_serializers import ConsentPreferenceSerializer, ConsentPreferenceUpdateSerializer


class ConsentPreferenceView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        existing = {
            item.purpose: item
            for item in ConsentPreference.objects.filter(user=request.user)
        }
        rows = []
        for purpose, label in ConsentPreference.Purpose.choices:
            item = existing.get(purpose)
            rows.append({
                "purpose": purpose,
                "label": label,
                "enabled": item.enabled if item else False,
                "policy_version": item.policy_version if item else "2026-11",
                "source": item.source if item else "default",
                "updated_at": item.updated_at if item else None,
            })
        return Response(rows)

    def post(self, request):
        serializer = ConsentPreferenceUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        with transaction.atomic():
            preference, created = ConsentPreference.objects.select_for_update().get_or_create(
                user=request.user,
                purpose=data["purpose"],
                defaults={
                    "enabled": False,
                    "policy_version": data["policy_version"],
                    "source": data["source"],
                    "updated_by": request.user,
                },
            )
            previous = preference.enabled
            preference.enabled = data["enabled"]
            preference.policy_version = data["policy_version"]
            preference.source = data["source"]
            preference.updated_by = request.user
            preference.save(update_fields=("enabled", "policy_version", "source", "updated_by", "updated_at"))
            ConsentEvent.objects.create(
                preference=preference,
                actor=request.user,
                previous_value=previous,
                new_value=preference.enabled,
                purpose=preference.purpose,
                policy_version=preference.policy_version,
                source=preference.source,
            )
        return Response(ConsentPreferenceSerializer(preference).data, status=status.HTTP_200_OK)
