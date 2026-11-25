from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .privacy_models import PrivacyRequest, PrivacyRequestEvent
from .privacy_serializers import PrivacyRequestSerializer, PrivacyRequestStaffUpdateSerializer


class PrivacyRequestListCreateView(generics.ListCreateAPIView):
    serializer_class = PrivacyRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = PrivacyRequest.objects.select_related("user").prefetch_related("events")
        return queryset if self.request.user.is_staff else queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        obj = serializer.save(user=self.request.user)
        PrivacyRequestEvent.objects.create(
            request=obj, actor=self.request.user, to_status=obj.status,
            note="Request submitted by account holder.",
        )


class PrivacyRequestDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, request, reference):
        try:
            obj = PrivacyRequest.objects.select_related("user").prefetch_related("events").get(reference=reference)
        except (PrivacyRequest.DoesNotExist, ValueError):
            return None
        if not request.user.is_staff and obj.user_id != request.user.id:
            return None
        return obj

    def get(self, request, reference):
        obj = self.get_object(request, reference)
        if obj is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(PrivacyRequestSerializer(obj).data)

    def patch(self, request, reference):
        obj = self.get_object(request, reference)
        if obj is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        if not request.user.is_staff:
            if obj.status != PrivacyRequest.Status.SUBMITTED:
                return Response({"detail": "Only submitted requests can be withdrawn."}, status=status.HTTP_409_CONFLICT)
            if request.data.get("status") != PrivacyRequest.Status.WITHDRAWN:
                return Response({"detail": "You may only withdraw your own submitted request."}, status=status.HTTP_403_FORBIDDEN)
            previous = obj.status
            obj.status = PrivacyRequest.Status.WITHDRAWN
            obj.closed_at = timezone.now()
            obj.save(update_fields=("status", "closed_at", "updated_at"))
            PrivacyRequestEvent.objects.create(request=obj, actor=request.user, from_status=previous, to_status=obj.status, note="Withdrawn by account holder.")
            return Response(PrivacyRequestSerializer(obj).data)

        serializer = PrivacyRequestStaffUpdateSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        previous = obj.status
        updated = serializer.save()
        terminal = (PrivacyRequest.Status.FULFILLED, PrivacyRequest.Status.DECLINED, PrivacyRequest.Status.WITHDRAWN)
        updated.closed_at = updated.closed_at or timezone.now() if updated.status in terminal else None
        updated.save(update_fields=("status", "staff_note", "identity_verified", "closed_at", "updated_at"))
        if previous != updated.status or serializer.validated_data:
            PrivacyRequestEvent.objects.create(request=updated, actor=request.user, from_status=previous, to_status=updated.status, note=updated.staff_note[:1000])
        return Response(PrivacyRequestSerializer(updated).data)
