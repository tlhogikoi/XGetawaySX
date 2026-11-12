from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
import base64
import shutil
import tempfile
from rest_framework.test import APIClient
from django.utils import timezone

from accounts.models import User
from partners.models import Partner
from .models import GalleryHistoryPublicationConsent, GalleryMedia, GalleryMediaPermissionGrant, GalleryStory, GalleryStoryRevision


class GalleryPublicationTests(TestCase):
    def setUp(self):
        self.private_storage_dir = tempfile.mkdtemp(prefix="xgetawaysx-gallery-tests-")
        self.storage_settings = override_settings(PRIVATE_GALLERY_STORAGE_ROOT=self.private_storage_dir)
        self.storage_settings.enable()
        self.client = APIClient()
        self.owner = User.objects.create_user(email="gallery-owner@example.com", password="test-password")
        self.editor = User.objects.create_superuser(email="gallery-editor@example.com", password="test-password")
        self.partner = Partner.objects.create(
            owner=self.owner,
            name="Approved Nature Lodge",
            category=Partner.Category.ACCOMMODATION,
            gallery_status=Partner.ApprovalStatus.APPROVED,
        )
        self.media = GalleryMedia.objects.create(
            partner=self.partner,
            title="The lodge at sunrise",
            image="https://images.example.test/lodge.jpg",
            alt_text="A lodge surrounded by trees at sunrise",
            rights_holder="The Lodge",
            rights_confirmed=True,
            promotional_permission=True,
            permission_granted_at=timezone.now(),
            status=GalleryMedia.Status.APPROVED,
            submitted_by=self.owner,
        )
        self.permission = GalleryMediaPermissionGrant.objects.create(
            media=self.media,
            rights_holder="The Lodge",
            permitted_channels=["website", "social_media"],
            evidence_reference="",
            evidence_file=SimpleUploadedFile("rights.pdf", b"%PDF-1.4 private permission evidence"),
            granted_by=self.owner,
            granted_at=timezone.now(),
            review_status=GalleryMediaPermissionGrant.ReviewStatus.APPROVED,
            reviewed_by=self.editor,
            reviewed_at=timezone.now(),
        )

    def tearDown(self):
        self.storage_settings.disable()
        shutil.rmtree(self.private_storage_dir, ignore_errors=True)


    def test_partner_draft_list_exposes_publication_gate_status(self):
        GalleryStory.objects.create(
            media=self.media,
            summary=" ".join(["A verified short story about this place and its setting."] * 5),
            status=GalleryStory.Status.OWNER_REVIEW,
        )
        self.client.force_authenticate(self.owner)
        response = self.client.get("/api/v1/gallery/stories/drafts/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["media_status"], GalleryMedia.Status.APPROVED)
        self.assertEqual(response.data[0]["partner_gallery_status"], Partner.ApprovalStatus.APPROVED)

    def test_private_original_history_is_not_public(self):
        story = GalleryStory.objects.create(
            media=self.media,
            owner_original_history="Private owner history with source notes.",
            owner_history_private=True,
            summary=" ".join(["A verified short story about this place and its setting."] * 5),
            status=GalleryStory.Status.PUBLISHED,
            owner_approved_by=self.owner,
            owner_approved_at=timezone.now(),
            owner_approved_version=1,
            editorial_approved_by=self.editor,
            editorial_approved_at=timezone.now(),
            editorial_approved_version=1,
            published_at=timezone.now(),
        )
        response = self.client.get("/api/v1/gallery/stories/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertIsNone(response.data[0]["owner_original_history"])
        self.assertNotIn("ai_source_facts", response.data[0])

    def test_original_history_is_public_only_with_separate_current_version_consent(self):
        story = GalleryStory.objects.create(
            media=self.media,
            owner_original_history="The owner has separately permitted this original history to be published.",
            owner_history_private=False,
            original_history_public_permission=True,
            summary=" ".join(["A verified short story about this place and its setting."] * 5),
            status=GalleryStory.Status.PUBLISHED,
            owner_approved_by=self.owner,
            owner_approved_at=timezone.now(),
            owner_approved_version=1,
            editorial_approved_by=self.editor,
            editorial_approved_at=timezone.now(),
            editorial_approved_version=1,
            published_at=timezone.now(),
        )
        GalleryHistoryPublicationConsent.objects.create(
            story=story,
            story_version=1,
            granted_by=self.owner,
            granted_at=timezone.now(),
        )
        response = self.client.get("/api/v1/gallery/stories/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["owner_original_history"], story.owner_original_history)

    def test_editorial_approval_rejects_stale_owner_approved_version(self):
        story = GalleryStory.objects.create(
            media=self.media,
            summary=" ".join(["A verified short story about this place and its setting."] * 5),
            status=GalleryStory.Status.EDITORIAL_REVIEW,
            current_version=2,
            owner_approved_by=self.owner,
            owner_approved_at=timezone.now(),
            owner_approved_version=1,
        )
        self.client.force_authenticate(self.editor)
        response = self.client.post(f"/api/v1/gallery/stories/{story.id}/editorial-approve/")
        self.assertEqual(response.status_code, 400)
        story.refresh_from_db()
        self.assertEqual(story.status, GalleryStory.Status.EDITORIAL_REVIEW)

    def test_editorial_approval_rechecks_dated_media_permission(self):
        story = GalleryStory.objects.create(
            media=self.media,
            summary=" ".join(["A verified short story about this place and its setting."] * 5),
            status=GalleryStory.Status.EDITORIAL_REVIEW,
            owner_approved_by=self.owner,
            owner_approved_at=timezone.now(),
            owner_approved_version=1,
        )
        self.permission.revoked_by = self.owner
        self.permission.revoked_at = timezone.now()
        self.permission.save(update_fields=("revoked_by", "revoked_at", "updated_at"))
        self.client.force_authenticate(self.editor)
        response = self.client.post(f"/api/v1/gallery/stories/{story.id}/editorial-approve/")
        self.assertEqual(response.status_code, 400)
        story.refresh_from_db()
        self.assertEqual(story.status, GalleryStory.Status.EDITORIAL_REVIEW)



    def test_revoked_media_permission_blocks_publication(self):
        self.permission.revoked_by = self.owner
        self.permission.revoked_at = timezone.now()
        self.permission.save(update_fields=("revoked_by", "revoked_at", "updated_at"))
        story = GalleryStory.objects.create(
            media=self.media,
            summary=" ".join(["A verified short story about this place and its setting."] * 5),
            status=GalleryStory.Status.PUBLISHED,
            owner_approved_by=self.owner,
            owner_approved_at=timezone.now(),
            owner_approved_version=1,
            editorial_approved_by=self.editor,
            editorial_approved_at=timezone.now(),
            editorial_approved_version=1,
            published_at=timezone.now(),
        )
        response = self.client.get("/api/v1/gallery/stories/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_expired_media_permission_blocks_publication(self):
        self.permission.expires_at = timezone.now()
        self.permission.save(update_fields=("expires_at", "updated_at"))
        response = self.client.get("/api/v1/gallery/stories/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_partner_owner_can_grant_and_revoke_media_permission(self):
        self.client.force_authenticate(self.owner)
        url = f"/api/v1/gallery/media/{self.media.id}/permissions/"
        response = self.client.post(url, {
            "rights_holder": "Photographer",
            "evidence_file": SimpleUploadedFile("licence.pdf", b"%PDF-1.4 signed licence"),
            "permitted_channels": '["website", "social_media"]',
        }, format="multipart")
        self.assertEqual(response.status_code, 201)
        permission_id = response.data["id"]
        self.assertNotIn("evidence_reference", response.data)
        revoke = self.client.post(
            f"/api/v1/gallery/media/{self.media.id}/permissions/{permission_id}/revoke/",
            format="json",
        )
        self.assertEqual(revoke.status_code, 200)
        self.assertFalse(revoke.data["active"])

    def test_other_partner_owner_cannot_grant_media_permission(self):
        other = User.objects.create_user(email="media-other@example.com", password="test-password")
        self.client.force_authenticate(other)
        response = self.client.post(
            f"/api/v1/gallery/media/{self.media.id}/permissions/",
            {
                "rights_holder": "Photographer",
                "evidence_file": SimpleUploadedFile("licence.pdf", b"%PDF-1.4 signed licence"),
                "permitted_channels": '["website"]',
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 403)
\n\n

    def test_pending_media_rights_review_blocks_publication(self):
        self.permission.review_status = GalleryMediaPermissionGrant.ReviewStatus.PENDING
        self.permission.reviewed_by = None
        self.permission.reviewed_at = None
        self.permission.save(update_fields=("review_status", "reviewed_by", "reviewed_at", "updated_at"))
        response = self.client.get("/api/v1/gallery/stories/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_only_editorial_staff_can_approve_media_rights_evidence(self):
        grant = GalleryMediaPermissionGrant.objects.create(
            media=self.media,
            rights_holder="Independent photographer",
            permitted_channels=["website"],
            evidence_reference="",
            evidence_file=SimpleUploadedFile("photographer.pdf", b"%PDF-1.4 photographer release"),
            granted_by=self.owner,
            granted_at=timezone.now(),
        )
        url = f"/api/v1/gallery/media/{self.media.id}/permissions/{grant.id}/review/"
        self.client.force_authenticate(self.owner)
        denied = self.client.post(url, {"decision": "approve"}, format="json")
        self.assertEqual(denied.status_code, 403)
        self.client.force_authenticate(self.editor)
        approved = self.client.post(url, {
            "decision": "approve",
            "review_notes": "Licence checked; Gallery promotional use is covered.",
        }, format="json")
        self.assertEqual(approved.status_code, 200)
        grant.refresh_from_db()
        self.assertEqual(grant.review_status, GalleryMediaPermissionGrant.ReviewStatus.APPROVED)
        self.assertEqual(grant.reviewed_by, self.editor)
\n\n

    def test_new_permission_grant_resets_existing_publication_approvals(self):
        story = GalleryStory.objects.create(
            media=self.media,
            summary=" ".join(["A verified short story about this place and its setting."] * 5),
            status=GalleryStory.Status.PUBLISHED,
            owner_approved_by=self.owner,
            owner_approved_at=timezone.now(),
            owner_approved_version=1,
            editorial_approved_by=self.editor,
            editorial_approved_at=timezone.now(),
            editorial_approved_version=1,
            published_at=timezone.now(),
        )
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            f"/api/v1/gallery/media/{self.media.id}/permissions/",
            {
                "rights_holder": "Photographer",
                "evidence_file": SimpleUploadedFile("new-release.pdf", b"%PDF-1.4 new signed release"),
                "permitted_channels": '["website"]',
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)
        story.refresh_from_db()
        self.media.refresh_from_db()
        self.assertEqual(self.media.status, GalleryMedia.Status.OWNER_REVIEW)
        self.assertEqual(story.status, GalleryStory.Status.OWNER_REVIEW)
        self.assertIsNone(story.owner_approved_version)
        self.assertIsNone(story.editorial_approved_version)
\n\n


    def test_partner_image_upload_uses_private_storage_and_returns_no_file_url(self):
        valid_png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4//8/AAX+Av4N70a4AAAAAElFTkSuQmCC")
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            "/api/v1/gallery/media/create/",
            {
                "partner": self.partner.id,
                "title": "Uploaded sunrise",
                "alt_text": "Sunrise over the lodge",
                "rights_holder": "The Lodge",
                "image_file": SimpleUploadedFile("sunrise.png", valid_png, content_type="image/png"),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)
        self.assertNotIn("image_file", response.data)
        media = GalleryMedia.objects.get(pk=response.data["id"])
        self.assertTrue(media.image_file.name.startswith("gallery/media/"))
        with self.assertRaises(ValueError):
            media.image_file.url

    def test_private_evidence_is_not_downloadable_by_another_partner(self):
        other = User.objects.create_user(email="evidence-other@example.com", password="test-password")
        self.client.force_authenticate(other)
        response = self.client.get(
            f"/api/v1/gallery/media/{self.media.id}/permissions/{self.permission.id}/evidence/"
        )
        self.assertEqual(response.status_code, 403)

    def test_partner_owner_can_download_private_evidence(self):
        self.client.force_authenticate(self.owner)
        response = self.client.get(
            f"/api/v1/gallery/media/{self.media.id}/permissions/{self.permission.id}/evidence/"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")

    def test_public_image_delivery_requires_a_published_story_and_approved_media(self):
        self.media.image_file = SimpleUploadedFile(
            "sunrise.png", base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4//8/AAX+Av4N70a4AAAAAElFTkSuQmCC")
        )
        self.media.save()
        GalleryStory.objects.create(
            media=self.media,
            summary=" ".join(["A verified short story about this place and its setting."] * 5),
            status=GalleryStory.Status.PUBLISHED,
            owner_approved_by=self.owner,
            owner_approved_at=timezone.now(),
            owner_approved_version=1,
            editorial_approved_by=self.editor,
            editorial_approved_at=timezone.now(),
            editorial_approved_version=1,
            published_at=timezone.now(),
        )
        response = self.client.get(f"/api/v1/gallery/media/{self.media.id}/image/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertEqual(response["Content-Type"], "image/png")

        self.media.status = GalleryMedia.Status.DRAFT
        self.media.save()
        blocked = self.client.get(f"/api/v1/gallery/media/{self.media.id}/image/")
        self.assertEqual(blocked.status_code, 404)

    def test_image_validator_rejects_unsupported_file_content(self):
        from .validators import validate_gallery_image
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            validate_gallery_image(SimpleUploadedFile("script.svg", b"<svg></svg>"))
        valid_png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4//8/AAX+Av4N70a4AAAAAElFTkSuQmCC")
        validate_gallery_image(SimpleUploadedFile("pixel.png", valid_png))


    def test_unapproved_partner_story_is_not_public(self):
        self.partner.gallery_status = Partner.ApprovalStatus.PENDING
        self.partner.save()
        story = GalleryStory.objects.create(
            media=self.media,
            summary=" ".join(["A concise account of the place, based only on owner supplied facts."] * 5),
            status=GalleryStory.Status.PUBLISHED,
            owner_approved_by=self.owner,
            owner_approved_at=timezone.now(),
            owner_approved_version=1,
            editorial_approved_by=self.editor,
            editorial_approved_at=timezone.now(),
            editorial_approved_version=1,
            published_at=__import__("django.utils.timezone", fromlist=["now"]).now(),
        )
        response = self.client.get("/api/v1/gallery/stories/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)


class GalleryRevisionPrivacyTests(TestCase):
    def setUp(self):
        from django.utils import timezone
        self.client = APIClient()
        self.owner = User.objects.create_user(email="revision-owner@example.com", password="test-password")
        self.other = User.objects.create_user(email="other-owner@example.com", password="test-password")
        self.partner = Partner.objects.create(
            owner=self.owner,
            name="Revision Test Lodge",
            category=Partner.Category.ACCOMMODATION,
            gallery_status=Partner.ApprovalStatus.APPROVED,
        )
        self.media = GalleryMedia.objects.create(
            partner=self.partner, title="Old stone cottage",
            image="https://images.example.test/cottage.jpg",
            alt_text="A stone cottage", rights_holder="Owner",
            rights_confirmed=True, promotional_permission=True,
            permission_granted_at=timezone.now(), submitted_by=self.owner,
        )
        self.story = GalleryStory.objects.create(
            media=self.media, owner_original_history="Confidential source history",
            summary="A short summary based on facts supplied by the property owner and checked before publication. " * 2,
            status=GalleryStory.Status.OWNER_REVIEW,
        )
        GalleryStoryRevision.capture(self.story, self.owner, "Initial draft")

    def test_revision_endpoint_never_returns_original_history(self):
        self.client.force_authenticate(self.owner)
        response = self.client.get(f"/api/v1/gallery/stories/{self.story.id}/revisions/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("owner_original_history_snapshot", str(response.data))
        self.assertNotIn("Confidential source history", str(response.data))

    def test_other_partner_owner_cannot_read_revisions(self):
        self.client.force_authenticate(self.other)
        response = self.client.get(f"/api/v1/gallery/stories/{self.story.id}/revisions/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_revision_is_immutable_snapshot(self):
        from .models import GalleryStoryRevision
        first = self.story.revisions.get(version=1)
        self.story.summary = "A changed summary with verified facts from the owner and approved context for the listing."
        self.story.save()
        second = GalleryStoryRevision.capture(self.story, self.owner, "Updated draft")
        first.refresh_from_db()
        self.assertNotEqual(first.summary, second.summary)
        self.assertEqual(first.version, 1)
        self.assertEqual(second.version, 2)


class GalleryHistoryConsentTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(email="consent-owner@example.com", password="test-password")
        self.other = User.objects.create_user(email="consent-other@example.com", password="test-password")
        self.partner = Partner.objects.create(
            owner=self.owner,
            name="Consent Test Retreat",
            category=Partner.Category.ACCOMMODATION,
            gallery_status=Partner.ApprovalStatus.APPROVED,
        )
        self.media = GalleryMedia.objects.create(
            partner=self.partner,
            title="Retreat garden",
            image="https://images.example.test/garden.jpg",
            alt_text="A garden at the retreat",
            rights_holder="Retreat owner",
            rights_confirmed=True,
            promotional_permission=True,
            permission_granted_at=timezone.now(),
            submitted_by=self.owner,
        )
        self.story = GalleryStory.objects.create(
            media=self.media,
            owner_original_history="Private source history supplied by the retreat owner.",
            summary="A verified story about this partner place shares its setting, character, and guest experience using details supplied by the owner and checked by the editorial team before publication to travellers.",
            status=GalleryStory.Status.OWNER_REVIEW,
        )
        GalleryStoryRevision.capture(self.story, self.owner, "Initial draft")

    def test_only_partner_owner_can_grant_history_permission(self):
        self.client.force_authenticate(self.other)
        response = self.client.post(
            f"/api/v1/gallery/stories/{self.story.id}/history-consent/",
            {"decision": "grant"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.story.history_publication_consents.count(), 0)

    def test_owner_can_grant_and_revoke_separate_history_permission(self):
        self.client.force_authenticate(self.owner)
        url = f"/api/v1/gallery/stories/{self.story.id}/history-consent/"
        grant = self.client.post(url, {"decision": "grant"}, format="json")
        self.assertEqual(grant.status_code, 200)
        self.story.refresh_from_db()
        consent = self.story.history_publication_consents.get(story_version=1)
        self.assertFalse(self.story.owner_history_private)
        self.assertTrue(self.story.original_history_public_permission)
        self.assertIsNone(consent.revoked_at)

        revoke = self.client.post(url, {"decision": "revoke"}, format="json")
        self.assertEqual(revoke.status_code, 200)
        self.story.refresh_from_db()
        consent.refresh_from_db()
        self.assertTrue(self.story.owner_history_private)
        self.assertFalse(self.story.original_history_public_permission)
        self.assertIsNotNone(consent.revoked_at)

    def test_material_edit_creates_new_version_and_returns_history_to_private(self):
        self.client.force_authenticate(self.owner)
        url = f"/api/v1/gallery/stories/{self.story.id}/history-consent/"
        self.assertEqual(self.client.post(url, {"decision": "grant"}, format="json").status_code, 200)
        new_summary = "A carefully checked account of the property describes its setting, facilities, and guest experience using details supplied directly by the owner and reviewed for accuracy before it is shown to travellers."
        response = self.client.patch(
            f"/api/v1/gallery/stories/{self.story.id}/draft/",
            {"summary": new_summary},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.story.refresh_from_db()
        self.assertEqual(self.story.current_version, 2)
        self.assertTrue(self.story.owner_history_private)
        self.assertFalse(self.story.original_history_public_permission)
        self.assertIsNone(self.story.owner_approved_version)
        self.assertFalse(self.story.history_publication_consents.filter(story_version=2, revoked_at__isnull=True).exists())


class GalleryEditorialQueueTests(TestCase):
    def setUp(self):
        self.private_storage_dir = tempfile.mkdtemp(prefix="xgetawaysx-editorial-tests-")
        self.storage_settings = override_settings(PRIVATE_GALLERY_STORAGE_ROOT=self.private_storage_dir)
        self.storage_settings.enable()
        self.client = APIClient()
        self.owner = User.objects.create_user(email="queue-owner@example.com", password="test-password")
        self.editor = User.objects.create_superuser(email="queue-editor@example.com", password="test-password")
        self.partner = Partner.objects.create(
            owner=self.owner, name="Editorial Queue Lodge",
            category=Partner.Category.ACCOMMODATION,
            gallery_status=Partner.ApprovalStatus.APPROVED,
        )
        self.media = GalleryMedia.objects.create(
            partner=self.partner, title="Queue image", image="https://images.example.test/queue.jpg",
            alt_text="A quiet garden", rights_holder="Photographer",
            submitted_by=self.owner, status=GalleryMedia.Status.APPROVED,
        )
        self.grant = GalleryMediaPermissionGrant.objects.create(
            media=self.media, rights_holder="Photographer", permitted_channels=["website"],
            evidence_file=SimpleUploadedFile("queue.pdf", b"%PDF-1.4 rights evidence"),
            granted_by=self.owner, granted_at=timezone.now(),
        )
        self.story = GalleryStory.objects.create(
            media=self.media, owner_original_history="PRIVATE ORIGINAL HISTORY MUST NEVER APPEAR IN THE QUEUE",
            summary="A verified description of the lodge and its peaceful garden, based on information supplied by the owner and checked by the editorial team before it is shared with travellers.",
            status=GalleryStory.Status.EDITORIAL_REVIEW,
            owner_approved_by=self.owner, owner_approved_at=timezone.now(), owner_approved_version=1,
        )

    def tearDown(self):
        self.storage_settings.disable()
        shutil.rmtree(self.private_storage_dir, ignore_errors=True)

    def test_editorial_queue_is_staff_only(self):
        self.client.force_authenticate(self.owner)
        response = self.client.get("/api/v1/gallery/editorial/queue/")
        self.assertEqual(response.status_code, 403)

    def test_editorial_queue_returns_review_items_without_private_owner_history(self):
        self.client.force_authenticate(self.editor)
        response = self.client.get("/api/v1/gallery/editorial/queue/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["rights_reviews"][0]["id"], self.grant.id)
        self.assertEqual(response.data["story_reviews"][0]["id"], self.story.id)
        self.assertNotIn("owner_original_history", str(response.data))
        self.assertNotIn("PRIVATE ORIGINAL HISTORY", str(response.data))
        self.assertNotIn("ai_source_facts_snapshot", str(response.data))



    def test_revision_endpoint_returns_only_the_requested_story_versions(self):
        other_media = GalleryMedia.objects.create(
            partner=self.partner, title="Second revision image",
            image="https://images.example.test/second-revision.jpg",
            alt_text="A second garden", rights_holder="Photographer",
            submitted_by=self.owner, status=GalleryMedia.Status.APPROVED,
        )
        other_story = GalleryStory.objects.create(
            media=other_media, summary="A second verified story describing the property garden and the surrounding landscape for prospective visitors.",
            status=GalleryStory.Status.DRAFT,
        )
        GalleryStoryRevision.capture(self.story, self.owner, "First story draft")
        GalleryStoryRevision.capture(other_story, self.owner, "Second story draft")
        self.client.force_authenticate(self.owner)
        response = self.client.get(f"/api/v1/gallery/stories/{self.story.id}/revisions/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["story"], self.story.id)


class GalleryStoryRevisionWorkflowTests(TestCase):
    def setUp(self):
        self.private_storage_dir = tempfile.mkdtemp(prefix="xgetawaysx-story-revisions-")
        self.storage_settings = override_settings(PRIVATE_GALLERY_STORAGE_ROOT=self.private_storage_dir)
        self.storage_settings.enable()
        self.client = APIClient()
        self.owner = User.objects.create_user(email="revision-owner@example.com", password="test-password")
        self.editor = User.objects.create_superuser(email="revision-editor@example.com", password="test-password")
        self.partner = Partner.objects.create(
            owner=self.owner, name="Revision Workflow Lodge",
            category=Partner.Category.ACCOMMODATION,
            gallery_status=Partner.ApprovalStatus.APPROVED,
        )
        self.media = GalleryMedia.objects.create(
            partner=self.partner, title="Revision image", image="https://images.example.test/revision.jpg",
            alt_text="A garden", rights_holder="Photographer",
            submitted_by=self.owner, status=GalleryMedia.Status.APPROVED,
        )
        self.story = GalleryStory.objects.create(
            media=self.media,
            summary="A carefully verified description of the property, its garden and the surrounding landscape for visitors planning a considered stay.",
            status=GalleryStory.Status.EDITORIAL_REVIEW,
            owner_approved_by=self.owner, owner_approved_at=timezone.now(), owner_approved_version=1,
        )
        GalleryStoryRevision.capture(self.story, self.owner, "Initial owner story submission")

    def tearDown(self):
        self.storage_settings.disable()
        shutil.rmtree(self.private_storage_dir, ignore_errors=True)

    def test_editorial_staff_can_request_changes_with_reason_and_clear_approvals(self):
        self.client.force_authenticate(self.editor)
        response = self.client.post(
            f"/api/v1/gallery/stories/{self.story.id}/request-changes/",
            {"reason": "Please verify the stated property history and clarify the experience described."},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.story.refresh_from_db()
        self.assertEqual(self.story.status, GalleryStory.Status.REJECTED)
        self.assertIsNone(self.story.owner_approved_version)
        self.assertIsNone(self.story.editorial_approved_version)
        event = self.story.audit_events.get(action="story_changes_requested")
        self.assertIn("verify the stated property history", event.details["reason"])
        self.client.force_authenticate(self.owner)
        drafts = self.client.get("/api/v1/gallery/stories/drafts/")
        self.assertEqual(drafts.status_code, 200)
        self.assertIn("verify the stated property history", drafts.data[0]["editorial_feedback"])

    def test_partner_cannot_request_editorial_changes(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            f"/api/v1/gallery/stories/{self.story.id}/request-changes/",
            {"reason": "Please change the story wording."},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_rejected_story_can_be_revised_and_requires_fresh_owner_approval(self):
        self.story.status = GalleryStory.Status.REJECTED
        self.story.owner_approved_by = None
        self.story.owner_approved_at = None
        self.story.owner_approved_version = None
        self.story.save()
        self.client.force_authenticate(self.owner)
        updated_summary = "A revised and carefully verified description of the property, its garden and surrounding landscape, with clearer details supplied directly by the partner owner for visitors seeking an authentic and comfortable local stay."
        response = self.client.patch(
            f"/api/v1/gallery/stories/{self.story.id}/draft/",
            {"summary": updated_summary},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.story.refresh_from_db()
        self.assertEqual(self.story.status, GalleryStory.Status.OWNER_REVIEW)
        self.assertEqual(self.story.current_version, 2)
        self.assertIsNone(self.story.owner_approved_version)
        self.assertIsNone(self.story.editorial_approved_version)
        self.assertTrue(self.story.revisions.filter(version=2).exists())

