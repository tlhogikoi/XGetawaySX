import json

from django.db import transaction
from django.http import FileResponse, Http404
from django.db.models import F, Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.views import APIView

from partners.models import Partner
from .models import GalleryAuditEvent, GalleryHistoryPublicationConsent, GalleryMedia, GalleryMediaPermissionGrant, GalleryStory, GalleryStoryRevision
from .validators import gallery_image_content_type
from .serializers import GalleryAuditEventSerializer, GalleryMediaDraftSerializer, GalleryStoryDraftSerializer, GalleryStoryRevisionSerializer, PublicGalleryStorySerializer



def has_active_gallery_media_permission(media):
    now = timezone.now()
    return media.permission_grants.filter(
        purpose=GalleryMediaPermissionGrant.Purpose.GALLERY_PROMOTION,
        review_status=GalleryMediaPermissionGrant.ReviewStatus.APPROVED,
        revoked_at__isnull=True,
    ).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now)).exists()


class PublicGalleryStoriesView(generics.ListAPIView):
    serializer_class = PublicGalleryStorySerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return GalleryStory.objects.filter(
            Q(media__permission_grants__expires_at__isnull=True)
            | Q(media__permission_grants__expires_at__gt=timezone.now()),
            status=GalleryStory.Status.PUBLISHED,
            media__status=GalleryMedia.Status.APPROVED,
            media__partner__gallery_status=Partner.ApprovalStatus.APPROVED,
            media__permission_grants__purpose=GalleryMediaPermissionGrant.Purpose.GALLERY_PROMOTION,
            media__permission_grants__review_status=GalleryMediaPermissionGrant.ReviewStatus.APPROVED,
            media__permission_grants__revoked_at__isnull=True,
            owner_approved_version=F("current_version"),
            owner_approved_at__isnull=False,
            editorial_approved_version=F("current_version"),
            editorial_approved_at__isnull=False,
            published_at__isnull=False,
        ).select_related("media", "media__partner").prefetch_related("history_publication_consents").distinct()


class GalleryMediaCreateView(generics.CreateAPIView):
    serializer_class = GalleryMediaDraftSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def perform_create(self, serializer):
        partner = serializer.validated_data["partner"]
        if not self.request.user.is_staff and partner.owner_id != self.request.user.id:
            raise PermissionDenied("Only the partner owner may submit media.")
        media = serializer.save(submitted_by=self.request.user)
        GalleryAuditEvent.objects.create(
            actor=self.request.user, partner=partner, media=media, action="media_submitted",
        )


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
        if not has_active_gallery_media_permission(media):
            raise ValidationError("An active, evidence-backed Gallery media permission grant is required.")
        if media.partner.gallery_status != Partner.ApprovalStatus.APPROVED:
            raise ValidationError("Partner must be approved for Gallery advertising.")
        media.status = GalleryMedia.Status.APPROVED
        media.full_clean()
        media.save()
        GalleryAuditEvent.objects.create(
            actor=request.user, partner=media.partner, media=media,
            action="media_editorially_approved",
        )
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
        if not has_active_gallery_media_permission(story.media):
            raise ValidationError("An active, evidence-backed Gallery media permission grant is required.")
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


class GalleryMediaPermissionGrantView(APIView):
    """Only the partner owner can record a rights holder's Gallery permission."""
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        media = generics.get_object_or_404(
            GalleryMedia.objects.select_for_update().select_related("partner"), pk=pk
        )
        if media.partner.owner_id != request.user.id:
            raise PermissionDenied("Only the partner owner may record media publication permission.")
        rights_holder = request.data.get("rights_holder", "")
        evidence_file = request.FILES.get("evidence_file")
        if not evidence_file:
            raise ValidationError({"evidence_file": "Upload the signed rights or promotional permission document."})
        evidence_reference = request.data.get("evidence_reference", "")
        permitted_channels = request.data.get("permitted_channels", [])
        if isinstance(permitted_channels, str):
            try:
                permitted_channels = json.loads(permitted_channels)
            except json.JSONDecodeError:
                raise ValidationError({"permitted_channels": "Provide a JSON array of permitted channels."})
        expires_raw = request.data.get("expires_at")
        expires_at = parse_datetime(expires_raw) if expires_raw else None
        if expires_raw and not expires_at:
            raise ValidationError({"expires_at": "Provide a valid ISO-8601 date-time."})
        if expires_at and timezone.is_naive(expires_at):
            expires_at = timezone.make_aware(expires_at, timezone.get_current_timezone())
        if not isinstance(permitted_channels, list) or not permitted_channels:
            raise ValidationError({"permitted_channels": "Provide at least one permitted channel."})
        grant = GalleryMediaPermissionGrant(
            media=media,
            purpose=GalleryMediaPermissionGrant.Purpose.GALLERY_PROMOTION,
            rights_holder=rights_holder,
            permitted_channels=permitted_channels,
            evidence_reference=evidence_reference,
            evidence_file=evidence_file,
            granted_by=request.user,
            granted_at=timezone.now(),
            expires_at=expires_at,
        )
        grant.full_clean()
        grant.save()
        # Any new rights grant requires fresh media review and, where a story exists,
        # fresh owner/editorial approval before the media can return to public display.
        media.status = GalleryMedia.Status.OWNER_REVIEW
        media.save(update_fields=("status", "updated_at"))
        story = GalleryStory.objects.filter(media=media).first()
        if story:
            story.status = GalleryStory.Status.OWNER_REVIEW
            story.owner_approved_by = None
            story.owner_approved_at = None
            story.owner_approved_version = None
            story.editorial_approved_by = None
            story.editorial_approved_at = None
            story.editorial_approved_version = None
            story.published_at = None
            story.save(update_fields=(
                "status", "owner_approved_by", "owner_approved_at", "owner_approved_version",
                "editorial_approved_by", "editorial_approved_at", "editorial_approved_version",
                "published_at", "updated_at",
            ))
        GalleryAuditEvent.objects.create(
            actor=request.user, partner=media.partner, media=media,
            action="media_permission_granted",
            details={"permission_id": grant.pk, "purpose": grant.purpose},
        )
        return Response({
            "id": grant.pk,
            "purpose": grant.purpose,
            "rights_holder": grant.rights_holder,
            "permitted_channels": grant.permitted_channels,
            "granted_at": grant.granted_at,
            "expires_at": grant.expires_at,
            "active": grant.is_active,
        }, status=status.HTTP_201_CREATED)


class GalleryMediaPermissionRevokeView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk, grant_id):
        media = generics.get_object_or_404(
            GalleryMedia.objects.select_for_update().select_related("partner"), pk=pk
        )
        if media.partner.owner_id != request.user.id:
            raise PermissionDenied("Only the partner owner may revoke media publication permission.")
        grant = generics.get_object_or_404(
            GalleryMediaPermissionGrant.objects.select_for_update(),
            pk=grant_id, media=media,
        )
        if grant.revoked_at is None:
            grant.revoked_by = request.user
            grant.revoked_at = timezone.now()
            grant.full_clean()
            grant.save(update_fields=("revoked_by", "revoked_at", "updated_at"))
            # Rights withdrawal suspends the asset and resets both approvals.
            media.status = GalleryMedia.Status.OWNER_REVIEW
            media.save(update_fields=("status", "updated_at"))
            story = GalleryStory.objects.filter(media=media).first()
            if story:
                story.status = GalleryStory.Status.OWNER_REVIEW
                story.owner_approved_by = None
                story.owner_approved_at = None
                story.owner_approved_version = None
                story.editorial_approved_by = None
                story.editorial_approved_at = None
                story.editorial_approved_version = None
                story.published_at = None
                story.save(update_fields=(
                    "status", "owner_approved_by", "owner_approved_at", "owner_approved_version",
                    "editorial_approved_by", "editorial_approved_at", "editorial_approved_version",
                    "published_at", "updated_at",
                ))
            GalleryAuditEvent.objects.create(
                actor=request.user, partner=media.partner, media=media,
                action="media_permission_revoked",
                details={"permission_id": grant.pk, "purpose": grant.purpose},
            )
        return Response({"id": grant.pk, "active": grant.is_active, "revoked_at": grant.revoked_at})


class GalleryMediaPermissionReviewView(APIView):
    """Editorial staff verify the private evidence before a grant can authorise publication."""
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk, grant_id):
        if not request.user.is_staff:
            raise PermissionDenied("Media-rights evidence review is restricted to authorised editorial staff.")
        media = generics.get_object_or_404(
            GalleryMedia.objects.select_for_update().select_related("partner"), pk=pk
        )
        grant = generics.get_object_or_404(
            GalleryMediaPermissionGrant.objects.select_for_update(),
            pk=grant_id, media=media,
        )
        decision = request.data.get("decision")
        if decision not in ("approve", "reject"):
            raise ValidationError({"decision": "Use 'approve' or 'reject'."})
        if not grant.evidence_file:
            raise ValidationError("A private evidence document must be uploaded before review.")
        if grant.revoked_at:
            raise ValidationError("A revoked permission grant cannot be reviewed for publication.")
        if grant.expires_at and grant.expires_at <= timezone.now():
            raise ValidationError("An expired permission grant cannot be approved.")
        grant.review_status = (
            GalleryMediaPermissionGrant.ReviewStatus.APPROVED
            if decision == "approve"
            else GalleryMediaPermissionGrant.ReviewStatus.REJECTED
        )
        grant.reviewed_by = request.user
        grant.reviewed_at = timezone.now()
        grant.review_notes = str(request.data.get("review_notes", ""))[:4000]
        grant.full_clean()
        grant.save(update_fields=(
            "review_status", "reviewed_by", "reviewed_at", "review_notes", "updated_at",
        ))
        GalleryAuditEvent.objects.create(
            actor=request.user, partner=media.partner, media=media,
            action="media_permission_" + grant.review_status,
            details={"permission_id": grant.pk},
        )
        return Response({
            "id": grant.pk,
            "review_status": grant.review_status,
            "reviewed_at": grant.reviewed_at,
        })


class GalleryMediaImageView(APIView):
    """Serve an uploaded image publicly only after every Gallery publication gate passes."""
    permission_classes = [AllowAny]

    def get(self, request, pk):
        media = generics.get_object_or_404(
            GalleryMedia.objects.select_related("partner").prefetch_related("permission_grants"),
            pk=pk,
        )
        if (
            media.status != GalleryMedia.Status.APPROVED
            or media.partner.gallery_status != Partner.ApprovalStatus.APPROVED
            or not has_active_gallery_media_permission(media)
        ):
            raise Http404
        story = getattr(media, "story", None)
        if not story or (
            story.status != GalleryStory.Status.PUBLISHED
            or story.owner_approved_version != story.current_version
            or story.editorial_approved_version != story.current_version
            or not story.owner_approved_at
            or not story.editorial_approved_at
            or not story.published_at
        ):
            raise Http404
        if not media.image_file:
            raise Http404
        image_handle = media.image_file.open("rb")
        response = FileResponse(image_handle, content_type=gallery_image_content_type(image_handle))
        response["Content-Disposition"] = 'inline; filename="gallery-image"'
        response["X-Content-Type-Options"] = "nosniff"
        response["Cache-Control"] = "no-store"
        return response


class GalleryMediaPermissionEvidenceView(APIView):
    """Private evidence is visible only to the owning partner or authorised staff."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, grant_id):
        grant = generics.get_object_or_404(
            GalleryMediaPermissionGrant.objects.select_related("media", "media__partner"),
            pk=grant_id, media_id=pk,
        )
        if not request.user.is_staff and grant.media.partner.owner_id != request.user.id:
            raise PermissionDenied("Only the partner owner or authorised editorial staff may view rights evidence.")
        if not grant.evidence_file:
            raise Http404
        GalleryAuditEvent.objects.create(
            actor=request.user, partner=grant.media.partner, media=grant.media,
            action="media_permission_evidence_viewed",
            details={"permission_id": grant.pk},
        )
        response = FileResponse(grant.evidence_file.open("rb"), content_type="application/octet-stream")
        response["Content-Disposition"] = 'attachment; filename="gallery-rights-evidence"'
        response["X-Content-Type-Options"] = "nosniff"
        response["Cache-Control"] = "private, no-store"
        return response
