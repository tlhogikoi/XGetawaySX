from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from partners.models import Partner
from .models import GalleryAuditEvent, GalleryHistoryPublicationConsent, GalleryMedia, GalleryStory, GalleryStoryRevision
from .serializers import GalleryAuditEventSerializer, GalleryMediaDraftSerializer, GalleryStoryDraftSerializer, GalleryStoryRevisionSerializer, PublicGalleryStorySerializer


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
            owner_approved_version=F("current_version"),
            editorial_approved_version=F("current_version"),
        ).select_related("media", "media__partner").prefetch_related("history_publication_consents")


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
        story = serializer.save(status=GalleryStory.Status.OWNER_REVIEW)
        GalleryStoryRevision.capture(story, self.request.user, "Initial owner story submission")
        GalleryAuditEvent.objects.create(
            actor=self.request.user, partner=media.partner, media=media,
            story=story, action="story_submitted",
        )


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
        story.owner_approved_version = story.current_version
        story.status = GalleryStory.Status.EDITORIAL_REVIEW
        story.save(update_fields=("owner_approved_by", "owner_approved_at", "owner_approved_version", "status", "updated_at"))
        GalleryAuditEvent.objects.create(
            actor=request.user, partner=story.media.partner, media=story.media,
            story=story, action="owner_approved",
            details={"story_version": story.current_version},
        )
        return Response({"status": story.status, "story_version": story.current_version}, status=status.HTTP_200_OK)


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
        if (
            story.status != GalleryStory.Status.EDITORIAL_REVIEW
            or not story.owner_approved_at
            or story.owner_approved_version != story.current_version
        ):
            raise ValidationError("Owner approval of the current story version is required before editorial approval.")
        if story.media.status != GalleryMedia.Status.APPROVED:
            raise ValidationError("Media must be editorially approved first.")
        if story.media.partner.gallery_status != Partner.ApprovalStatus.APPROVED:
            raise ValidationError("Partner must be approved for Gallery advertising.")
        story.editorial_approved_by = request.user
        story.editorial_approved_at = timezone.now()
        story.editorial_approved_version = story.current_version
        story.status = GalleryStory.Status.PUBLISHED
        story.published_at = timezone.now()
        story.full_clean()
        story.save()
        GalleryAuditEvent.objects.create(
            actor=request.user, partner=story.media.partner, media=story.media,
            story=story, action="story_published",
            details={"story_version": story.current_version},
        )
        return Response({"status": story.status, "published_at": story.published_at, "story_version": story.current_version})


class GalleryStoryOwnerDraftListView(generics.ListAPIView):
    serializer_class = GalleryStoryDraftSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return GalleryStory.objects.all().select_related("media", "media__partner")
        return GalleryStory.objects.filter(media__partner__owner=self.request.user).select_related("media", "media__partner")


class GalleryStoryDraftUpdateView(generics.UpdateAPIView):
    serializer_class = GalleryStoryDraftSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["put", "patch", "head", "options"]

    def get_queryset(self):
        if self.request.user.is_staff:
            return GalleryStory.objects.filter(status__in=[GalleryStory.Status.DRAFT, GalleryStory.Status.OWNER_REVIEW, GalleryStory.Status.EDITORIAL_REVIEW])
        return GalleryStory.objects.filter(
            media__partner__owner=self.request.user,
            status__in=[GalleryStory.Status.DRAFT, GalleryStory.Status.OWNER_REVIEW, GalleryStory.Status.EDITORIAL_REVIEW],
        )

    @transaction.atomic
    def perform_update(self, serializer):
        story = self.get_object()
        before = {
            "summary": story.summary,
            "owner_original_history": story.owner_original_history,
            "ai_source_facts": story.ai_source_facts,
        }
        updated = serializer.save()
        changed = (
            before["summary"] != updated.summary
            or before["owner_original_history"] != updated.owner_original_history
            or before["ai_source_facts"] != updated.ai_source_facts
        )
        if changed:
            updated.status = GalleryStory.Status.OWNER_REVIEW
            updated.owner_approved_by = None
            updated.owner_approved_at = None
            updated.owner_approved_version = None
            updated.editorial_approved_by = None
            updated.editorial_approved_at = None
            updated.editorial_approved_version = None
            updated.published_at = None
            updated.save(update_fields=(
                "status", "owner_approved_by", "owner_approved_at", "owner_approved_version",
                "editorial_approved_by", "editorial_approved_at", "editorial_approved_version",
                "published_at", "updated_at",
            ))
            GalleryStoryRevision.capture(updated, self.request.user, "Story content edited; prior approvals reset")
            GalleryAuditEvent.objects.create(
                actor=self.request.user, partner=updated.media.partner, media=updated.media,
                story=updated, action="story_edited",
                details={"story_version": updated.current_version},
            )


class GalleryStoryRevisionListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = GalleryStoryRevisionSerializer

    def get_queryset(self):
        queryset = GalleryStoryRevision.objects.select_related("story", "changed_by", "story__media", "story__media__partner")
        if self.request.user.is_staff:
            return queryset
        return queryset.filter(story__media__partner__owner=self.request.user)




class GalleryAuditEventListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = GalleryAuditEventSerializer

    def get_queryset(self):
        if not self.request.user.is_staff:
            raise PermissionDenied("Gallery audit records are restricted to authorised editorial staff.")
        return GalleryAuditEvent.objects.select_related("actor", "partner", "media", "story")


class GalleryStoryHistoryConsentView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        story = generics.get_object_or_404(
            GalleryStory.objects.select_for_update().select_related("media", "media__partner"),
            pk=pk,
        )
        if story.media.partner.owner_id != request.user.id:
            raise PermissionDenied("Only the partner owner may grant or revoke publication permission for original history.")
        decision = request.data.get("decision")
        if decision not in ("grant", "revoke"):
            raise ValidationError({"decision": "Use 'grant' or 'revoke'."})

        if decision == "grant":
            if not story.owner_original_history.strip():
                raise ValidationError("There is no original history to grant publication permission for.")
            if story.status not in (GalleryStory.Status.DRAFT, GalleryStory.Status.OWNER_REVIEW):
                raise ValidationError("Grant permission before owner approval; an approved story must be revised and reviewed again.")
            consent, created = GalleryHistoryPublicationConsent.objects.get_or_create(
                story=story,
                story_version=story.current_version,
                defaults={"granted_by": request.user, "granted_at": timezone.now()},
            )
            if not created:
                consent.granted_by = request.user
                consent.granted_at = timezone.now()
                consent.revoked_by = None
                consent.revoked_at = None
                consent.save(update_fields=("granted_by", "granted_at", "revoked_by", "revoked_at", "updated_at"))
            story.owner_history_private = False
            story.original_history_public_permission = True
            action = "history_publication_consent_granted"
        else:
            consent = GalleryHistoryPublicationConsent.objects.filter(
                story=story,
                story_version=story.current_version,
                revoked_at__isnull=True,
            ).first()
            if consent:
                consent.revoked_by = request.user
                consent.revoked_at = timezone.now()
                consent.save(update_fields=("revoked_by", "revoked_at", "updated_at"))
            story.owner_history_private = True
            story.original_history_public_permission = False
            action = "history_publication_consent_revoked"

        story.save(update_fields=("owner_history_private", "original_history_public_permission", "updated_at"))
        GalleryAuditEvent.objects.create(
            actor=request.user, partner=story.media.partner, media=story.media,
            story=story, action=action,
            details={"story_version": story.current_version},
        )
        return Response({
            "decision": decision,
            "story_version": story.current_version,
            "original_history_public": decision == "grant",
        }, status=status.HTTP_200_OK)
