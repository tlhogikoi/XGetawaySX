from django.db import transaction
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from partners.models import Partner
from .models import GalleryMedia, GalleryStory
from .serializers import GalleryMediaDraftSerializer, GalleryStoryDraftSerializer, PublicGalleryStorySerializer


class PublicGalleryStoriesView(generics.ListAPIView):
    serializer_class = PublicGalleryStorySerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return GalleryStory.objects.filter(
            status=GalleryStory.Status.PUBLISHED,
            media__status=GalleryMedia.Status.APPROVED,
            media__partner__gallery_status=Partner.ApprovalStatus.APPROVED,
            media__rights_confirmed=True,
            media__promotional_permission=True,
        ).select_related("media", "media__partner")


class GalleryMediaCreateView(generics.CreateAPIView):
    serializer_class = GalleryMediaDraftSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        partner = serializer.validated_data["partner"]
        if not self.request.user.is_staff and partner.owner_id != self.request.user.id:
            raise PermissionDenied("Only the partner owner may submit media.")
        serializer.save(submitted_by=self.request.user)


class GalleryStoryCreateView(generics.CreateAPIView):
    serializer_class = GalleryStoryDraftSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        media = serializer.validated_data["media"]
        if not self.request.user.is_staff and media.partner.owner_id != self.request.user.id:
            raise PermissionDenied("Only the partner owner may submit this story.")
        serializer.save(status=GalleryStory.Status.OWNER_REVIEW)


class GalleryStoryOwnerApprovalView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        story = generics.get_object_or_404(GalleryStory.objects.select_for_update(), pk=pk)
        if story.media.partner.owner_id != request.user.id:
            raise PermissionDenied("Only the partner owner may approve the story. Editorial staff cannot substitute for owner consent.")
        if story.status != GalleryStory.Status.OWNER_REVIEW:
            raise ValidationError("Story is not awaiting owner approval.")
        if story.media.partner.gallery_status != Partner.ApprovalStatus.APPROVED:
            raise ValidationError("Partner must be approved for Gallery advertising.")
        if not (story.media.rights_confirmed and story.media.promotional_permission):
            raise ValidationError("Media rights and promotional permission must be confirmed.")
        if story.media.status not in (GalleryMedia.Status.OWNER_REVIEW, GalleryMedia.Status.EDITORIAL_REVIEW, GalleryMedia.Status.APPROVED):
            raise ValidationError("Media must complete its rights review before story approval.")
        if not 30 <= len(story.summary.split()) <= 60:
            raise ValidationError("Story summary must contain 30–60 words.")
        story.owner_approved_by = request.user
        story.owner_approved_at = timezone.now()
        story.status = GalleryStory.Status.EDITORIAL_REVIEW
        story.save()
        return Response({"status": story.status}, status=status.HTTP_200_OK)


class GalleryMediaEditorialApprovalView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        if not request.user.is_staff:
            raise PermissionDenied("Editorial approval is restricted to authorised staff.")
        media = generics.get_object_or_404(GalleryMedia.objects.select_for_update(), pk=pk)
        if not (media.rights_confirmed and media.promotional_permission and media.permission_granted_at):
            raise ValidationError("Confirmed media rights and promotional permission are required.")
        if media.partner.gallery_status != Partner.ApprovalStatus.APPROVED:
            raise ValidationError("Partner must be approved for Gallery advertising.")
        media.status = GalleryMedia.Status.APPROVED
        media.full_clean()
        media.save()
        return Response({"status": media.status})


class GalleryStoryEditorialApprovalView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        if not request.user.is_staff:
            raise PermissionDenied("Editorial approval is restricted to authorised staff.")
        story = generics.get_object_or_404(GalleryStory.objects.select_for_update(), pk=pk)
        if story.status != GalleryStory.Status.EDITORIAL_REVIEW or not story.owner_approved_at:
            raise ValidationError("Owner approval is required before editorial approval.")
        if story.media.status != GalleryMedia.Status.APPROVED:
            raise ValidationError("Media must be editorially approved first.")
        if story.media.partner.gallery_status != Partner.ApprovalStatus.APPROVED:
            raise ValidationError("Partner must be approved for Gallery advertising.")
        story.editorial_approved_by = request.user
        story.editorial_approved_at = timezone.now()
        story.status = GalleryStory.Status.PUBLISHED
        story.published_at = timezone.now()
        story.full_clean()
        story.save()
        return Response({"status": story.status, "published_at": story.published_at})


class GalleryStoryOwnerDraftListView(generics.ListAPIView):
    serializer_class = GalleryStoryDraftSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return GalleryStory.objects.all().select_related("media", "media__partner")
        return GalleryStory.objects.filter(media__partner__owner=self.request.user).select_related("media", "media__partner")
