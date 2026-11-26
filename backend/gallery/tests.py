from django.test import TestCase
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
import base64
import shutil
import tempfile
from rest_framework.test import APIClient
from django.utils import timezone

from accounts.models import User
from partners.models import Partner
from .models import GalleryAuditEvent, GalleryHistoryPublicationConsent, GalleryMedia, GalleryMediaPermissionGrant, GalleryStory, GalleryStoryEditorialReview, GalleryStoryMedia, GalleryStoryRevision


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



    def test_public_story_detail_returns_approved_content_without_private_history(self):
        self.media.caption = "Morning light across the lodge grounds."
        self.media.media_credit = "Lodge photography team"
        self.media.save(update_fields=("caption", "media_credit", "updated_at"))
        story = GalleryStory.objects.create(
            media=self.media, owner_original_history="Private notes must remain private.",
            owner_history_private=True,
            summary=" ".join(["A verified short story about this place and its setting."] * 5),
            status=GalleryStory.Status.PUBLISHED, owner_approved_by=self.owner,
            owner_approved_at=timezone.now(), owner_approved_version=1,
            editorial_approved_by=self.editor, editorial_approved_at=timezone.now(),
            editorial_approved_version=1, published_at=timezone.now(),
        )
        response = self.client.get(f"/api/v1/gallery/stories/{story.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["caption"], "Morning light across the lodge grounds.")
        self.assertEqual(response.data["media_credit"], "Lodge photography team")
        self.assertIsNone(response.data["owner_original_history"])
        self.assertNotIn("ai_source_facts", response.data)

    def test_public_story_detail_hides_unpublished_story(self):
        story = GalleryStory.objects.create(
            media=self.media,
            summary=" ".join(["A verified short story about this place and its setting."] * 5),
            status=GalleryStory.Status.DRAFT,
        )
        response = self.client.get(f"/api/v1/gallery/stories/{story.id}/")
        self.assertEqual(response.status_code, 404)

    def test_social_media_only_permission_does_not_publish_story_on_website(self):
        self.permission.permitted_channels = ["social_media"]
        self.permission.save(update_fields=("permitted_channels",))
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
        response = self.client.get("/api/v1/gallery/stories/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_website_permission_is_required_before_editorial_media_approval(self):
        self.permission.permitted_channels = ["social_media"]
        self.permission.save(update_fields=("permitted_channels",))
        self.media.status = GalleryMedia.Status.OWNER_REVIEW
        self.media.save(update_fields=("status", "updated_at"))
        self.client.force_authenticate(self.editor)
        response = self.client.post(
            f"/api/v1/gallery/media/{self.media.id}/editorial-approve/"
        )
        self.assertEqual(response.status_code, 400)
        self.media.refresh_from_db()
        self.assertNotEqual(self.media.status, GalleryMedia.Status.APPROVED)

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

    def test_latest_failed_quality_review_supersedes_earlier_pass(self):
        story = GalleryStory.objects.create(
            media=self.media,
            summary=" ".join(["A verified short story about this place and its setting."] * 5),
            status=GalleryStory.Status.EDITORIAL_REVIEW,
            owner_approved_by=self.owner,
            owner_approved_at=timezone.now(),
            owner_approved_version=1,
        )
        review_fields = {
            "story": story,
            "story_version": story.current_version,
            "reviewer": self.editor,
            "claims_verified": True,
            "source_facts_checked": True,
            "unsupported_claims_resolved": True,
            "media_context_accurate": True,
            "reviewer_notes": "All source facts and media context have been checked.",
        }
        GalleryStoryEditorialReview.objects.create(**review_fields)
        failed_review = GalleryStoryEditorialReview.objects.create(
            **{**review_fields, "claims_verified": False,
               "reviewer_notes": "A factual claim still needs verification."}
        )
        self.client.force_authenticate(self.editor)
        response = self.client.post(f"/api/v1/gallery/stories/{story.id}/editorial-approve/")
        self.assertEqual(response.status_code, 400)
        story.refresh_from_db()
        self.assertEqual(story.status, GalleryStory.Status.EDITORIAL_REVIEW)
        self.assertIsNone(story.editorial_approved_version)
        self.assertEqual(
            story.editorial_quality_reviews.order_by("-created_at", "-pk").first().pk,
            failed_review.pk,
        )

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


    def test_social_media_only_permission_blocks_public_image_delivery(self):
        self.permission.permitted_channels = ["social_media"]
        self.permission.save(update_fields=("permitted_channels",))
        self.media.image_file = SimpleUploadedFile(
            "social-only.png",
            base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4//8/AAX+Av4N70a4AAAAAElFTkSuQmCC"),
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
        self.assertEqual(response.status_code, 404)

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


    def test_revoking_permission_after_publication_immediately_hides_story_and_image(self):
        self.media.image_file = SimpleUploadedFile(
            "published.png",
            base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4//8/AAX+Av4N70a4AAAAAElFTkSuQmCC"),
        )
        self.media.save()
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

        self.assertEqual(self.client.get("/api/v1/gallery/stories/").data[0]["id"], story.id)
        self.assertEqual(self.client.get(f"/api/v1/gallery/stories/{story.id}/").status_code, 200)
        self.assertEqual(self.client.get(f"/api/v1/gallery/media/{self.media.id}/image/").status_code, 200)

        self.client.force_authenticate(self.owner)
        revoked = self.client.post(
            f"/api/v1/gallery/media/{self.media.id}/permissions/{self.permission.id}/revoke/",
            format="json",
        )
        self.assertEqual(revoked.status_code, 200)

        self.assertEqual(self.client.get("/api/v1/gallery/stories/").data, [])
        self.assertEqual(self.client.get(f"/api/v1/gallery/stories/{story.id}/").status_code, 404)
        self.assertEqual(self.client.get(f"/api/v1/gallery/media/{self.media.id}/image/").status_code, 404)


    def test_suspending_partner_after_publication_hides_story_and_image(self):
        self.media.image_file = SimpleUploadedFile(
            "published.png",
            base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4//8/AAX+Av4N70a4AAAAAElFTkSuQmCC"),
        )
        self.media.save()
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

        self.assertEqual(self.client.get("/api/v1/gallery/stories/").data[0]["id"], story.id)
        self.assertEqual(self.client.get(f"/api/v1/gallery/stories/{story.id}/").status_code, 200)
        self.assertEqual(self.client.get(f"/api/v1/gallery/media/{self.media.id}/image/").status_code, 200)

        self.partner.gallery_status = Partner.ApprovalStatus.SUSPENDED
        self.partner.save(update_fields=("gallery_status", "updated_at"))

        self.assertEqual(self.client.get("/api/v1/gallery/stories/").data, [])
        self.assertEqual(self.client.get(f"/api/v1/gallery/stories/{story.id}/").status_code, 404)
        self.assertEqual(self.client.get(f"/api/v1/gallery/media/{self.media.id}/image/").status_code, 404)


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
        from .models import GalleryPartnerNotification
        notice = GalleryPartnerNotification.objects.get(story=self.story)
        self.assertEqual(notice.recipient, self.owner)
        self.assertEqual(notice.kind, GalleryPartnerNotification.Kind.STORY_CHANGES_REQUESTED)
        self.assertIn("verify the stated property history", notice.message)

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



class GalleryPartnerNotificationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(email="notification-owner@example.com", password="test-password")
        self.other = User.objects.create_user(email="notification-other@example.com", password="test-password")
        self.partner = Partner.objects.create(
            owner=self.owner, name="Notification Lodge",
            category=Partner.Category.ACCOMMODATION,
            gallery_status=Partner.ApprovalStatus.APPROVED,
        )
        self.media = GalleryMedia.objects.create(
            partner=self.partner, title="Notification image",
            image="https://images.example.test/notification.jpg",
            alt_text="A lodge garden", rights_holder="Owner", submitted_by=self.owner,
        )
        self.story = GalleryStory.objects.create(
            media=self.media,
            summary="A verified description of the property and its garden, based on information supplied by the owner and checked by the editorial team before it is shared with visitors.",
        )
        from .models import GalleryPartnerNotification
        self.notification = GalleryPartnerNotification.objects.create(
            recipient=self.owner, partner=self.partner, story=self.story,
            kind=GalleryPartnerNotification.Kind.STORY_CHANGES_REQUESTED,
            title="Your Gallery story needs changes",
            message="Please clarify the dates in the submitted story.",
        )

    def test_partner_can_list_only_own_notifications(self):
        self.client.force_authenticate(self.owner)
        response = self.client.get("/api/v1/gallery/notifications/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["story_id"], self.story.id)

    def test_other_partner_cannot_read_or_mark_notification(self):
        self.client.force_authenticate(self.other)
        response = self.client.get("/api/v1/gallery/notifications/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)
        denied = self.client.post(f"/api/v1/gallery/notifications/{self.notification.id}/read/")
        self.assertEqual(denied.status_code, 404)

    def test_partner_can_mark_notification_as_read(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(f"/api/v1/gallery/notifications/{self.notification.id}/read/")
        self.assertEqual(response.status_code, 200)
        self.notification.refresh_from_db()
        self.assertIsNotNone(self.notification.read_at)


class GalleryPartnerActivityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(email="activity-owner@example.com", password="test-password")
        self.other = User.objects.create_user(email="activity-other@example.com", password="test-password")
        self.partner = Partner.objects.create(
            owner=self.owner, name="Activity Lodge",
            category=Partner.Category.ACCOMMODATION,
            gallery_status=Partner.ApprovalStatus.APPROVED,
        )
        self.media = GalleryMedia.objects.create(
            partner=self.partner, title="Garden view",
            image="https://images.example.test/activity.jpg",
            alt_text="A garden view", rights_holder="Owner",
            submitted_by=self.owner,
        )
        self.story = GalleryStory.objects.create(
            media=self.media,
            summary="A verified account of the garden and its surroundings, based on facts supplied by the partner and reviewed before publication for visitors.",
        )
        self.event = GalleryAuditEvent.objects.create(
            actor=self.owner, partner=self.partner, media=self.media,
            story=self.story, action="story_submitted",
            details={"story_version": 1, "internal_editorial_note": "CONFIDENTIAL REVIEW NOTE"},
        )

    def test_partner_owner_can_view_safe_submission_activity(self):
        self.client.force_authenticate(self.owner)
        response = self.client.get(f"/api/v1/gallery/partners/{self.partner.id}/activity/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        item = response.data[0]
        self.assertEqual(item["event_type"], "story_submitted")
        self.assertEqual(item["story_id"], self.story.id)
        self.assertEqual(item["media_title"], "Garden view")
        self.assertEqual(item["story_version"], 1)
        self.assertNotIn("details", item)
        self.assertNotIn("CONFIDENTIAL REVIEW NOTE", str(response.data))

    def test_another_partner_owner_cannot_view_activity(self):
        self.client.force_authenticate(self.other)
        response = self.client.get(f"/api/v1/gallery/partners/{self.partner.id}/activity/")
        self.assertEqual(response.status_code, 403)

    def test_anonymous_user_cannot_view_partner_activity(self):
        response = self.client.get(f"/api/v1/gallery/partners/{self.partner.id}/activity/")
        # DRF's IsAuthenticated permission returns 401 when no authentication
        # challenge is configured for the request.
        self.assertEqual(response.status_code, 401)


    def test_partner_can_view_current_submission_status_without_internal_review_notes(self):
        from .models import GalleryMediaPermissionGrant
        GalleryMediaPermissionGrant.objects.create(
            media=self.media, rights_holder="Owner", permitted_channels=["website"],
            evidence_reference="evidence-ref", granted_by=self.owner,
            granted_at=timezone.now(), review_status=GalleryMediaPermissionGrant.ReviewStatus.REJECTED,
            reviewed_by=User.objects.create_superuser(email="submission-editor@example.com", password="test-password"),
            reviewed_at=timezone.now(), review_notes="CONFIDENTIAL INTERNAL REVIEW NOTE",
        )
        self.client.force_authenticate(self.owner)
        response = self.client.get(f"/api/v1/gallery/partners/{self.partner.id}/submissions/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        item = response.data[0]
        self.assertEqual(item["media_id"], self.media.id)
        self.assertEqual(item["media_status"], GalleryMedia.Status.DRAFT)
        self.assertEqual(item["rights_status"], GalleryMediaPermissionGrant.ReviewStatus.REJECTED)
        self.assertEqual(item["story_id"], self.story.id)
        self.assertNotIn("review_notes", item)
        self.assertNotIn("CONFIDENTIAL INTERNAL REVIEW NOTE", str(response.data))

    def test_another_partner_owner_cannot_view_submission_status(self):
        self.client.force_authenticate(self.other)
        response = self.client.get(f"/api/v1/gallery/partners/{self.partner.id}/submissions/")
        self.assertEqual(response.status_code, 403)


class GalleryStoryEditorialQualityReviewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(email="qc-owner@example.com", password="test-password")
        self.editor = User.objects.create_superuser(email="qc-editor@example.com", password="test-password")
        self.partner = Partner.objects.create(owner=self.owner, name="QC Lodge", category=Partner.Category.ACCOMMODATION, gallery_status=Partner.ApprovalStatus.APPROVED)
        self.media = GalleryMedia.objects.create(partner=self.partner, title="QC image", image="https://images.example.test/qc.jpg", alt_text="A garden", rights_holder="Owner", submitted_by=self.owner, status=GalleryMedia.Status.APPROVED)
        GalleryMediaPermissionGrant.objects.create(media=self.media, rights_holder="Owner", permitted_channels=["website"], evidence_file=SimpleUploadedFile("qc.pdf", b"%PDF-1.4 evidence"), granted_by=self.owner, granted_at=timezone.now(), review_status=GalleryMediaPermissionGrant.ReviewStatus.APPROVED, reviewed_by=self.editor, reviewed_at=timezone.now())
        self.story = GalleryStory.objects.create(media=self.media, summary="A carefully checked account of the lodge and its garden, using information supplied by the owner and reviewed for accuracy before visitors see the story. The description highlights the property without adding unsupported claims or details.", status=GalleryStory.Status.EDITORIAL_REVIEW, owner_approved_by=self.owner, owner_approved_at=timezone.now(), owner_approved_version=1)

    def payload(self, **overrides):
        data = {"story_version": self.story.current_version, "claims_verified": True, "source_facts_checked": True, "unsupported_claims_resolved": True, "media_context_accurate": True, "reviewer_notes": "All claims checked against owner supplied facts and image context."}
        data.update(overrides)
        return data

    def test_only_staff_can_submit_quality_review(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(f"/api/v1/gallery/stories/{self.story.id}/quality-review/", self.payload(), format="json")
        self.assertEqual(response.status_code, 403)

    def test_all_checks_and_current_version_are_required(self):
        self.client.force_authenticate(self.editor)
        bad = self.client.post(f"/api/v1/gallery/stories/{self.story.id}/quality-review/", self.payload(source_facts_checked=False), format="json")
        self.assertEqual(bad.status_code, 400)
        stale = self.client.post(f"/api/v1/gallery/stories/{self.story.id}/quality-review/", self.payload(story_version=0), format="json")
        self.assertEqual(stale.status_code, 400)

    def test_publication_requires_passing_current_version_quality_review(self):
        self.client.force_authenticate(self.editor)
        publish = self.client.post(f"/api/v1/gallery/stories/{self.story.id}/editorial-approve/")
        self.assertEqual(publish.status_code, 400)
        review = self.client.post(f"/api/v1/gallery/stories/{self.story.id}/quality-review/", self.payload(), format="json")
        self.assertEqual(review.status_code, 201)
        publish = self.client.post(f"/api/v1/gallery/stories/{self.story.id}/editorial-approve/")
        self.assertEqual(publish.status_code, 200)


class GalleryAIDraftingSafetyTests(TestCase):
    def test_ai_drafting_fails_closed_without_provider(self):
        from django.test import override_settings
        from rest_framework.exceptions import APIException
        from .story_drafting import StoryDraftingUnavailable, draft_story_summary

        class Story:
            ai_source_facts = ["The lodge opened in 2018.", "It is family-owned."]

        with override_settings(GALLERY_STORY_DRAFTER=""):
            with self.assertRaises(StoryDraftingUnavailable):
                draft_story_summary(Story())

    def test_ai_drafting_rejects_empty_owner_facts(self):
        from django.test import override_settings
        from rest_framework.exceptions import ValidationError
        from .story_drafting import draft_story_summary

        class Story:
            ai_source_facts = []

        with override_settings(GALLERY_STORY_DRAFTER="builtins.str"):
            with self.assertRaises(ValidationError):
                draft_story_summary(Story())



class GalleryMultiImageExperienceTests(TestCase):
    PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4//8/AAX+Av4N70a4AAAAAElFTkSuQmCC")
    SUMMARY = "A carefully verified account of this partner experience, using details supplied by the owner and reviewed by the editorial team before publication for visitors."

    def setUp(self):
        self.private_storage_dir = tempfile.mkdtemp(prefix="xgetawaysx-gallery-multi-image-")
        self.storage_settings = override_settings(PRIVATE_GALLERY_STORAGE_ROOT=self.private_storage_dir)
        self.storage_settings.enable()
        self.client = APIClient()
        self.owner = User.objects.create_user(email="multi-image-owner@example.com", password="test-password")
        self.editor = User.objects.create_superuser(email="multi-image-editor@example.com", password="test-password")
        self.partner = Partner.objects.create(
            owner=self.owner,
            name="Multi Image Lodge",
            category=Partner.Category.ACCOMMODATION,
            gallery_status=Partner.ApprovalStatus.APPROVED,
        )
        self.cover = self.create_media("Cover image", "website")
        self.additional = self.create_media("Garden image", "website")
        self.story = GalleryStory.objects.create(
            media=self.cover,
            summary=self.SUMMARY,
            status=GalleryStory.Status.PUBLISHED,
            owner_approved_by=self.owner,
            owner_approved_at=timezone.now(),
            owner_approved_version=1,
            editorial_approved_by=self.editor,
            editorial_approved_at=timezone.now(),
            editorial_approved_version=1,
            published_at=timezone.now(),
        )

    def tearDown(self):
        self.storage_settings.disable()
        shutil.rmtree(self.private_storage_dir, ignore_errors=True)

    def create_media(self, title, channel):
        media = GalleryMedia.objects.create(
            partner=self.partner,
            title=title,
            image_file=SimpleUploadedFile(f"{title.lower().replace(' ', '-')}.png", self.PNG, content_type="image/png"),
            alt_text=f"Photograph: {title}",
            caption=f"Caption for {title}",
            media_credit=f"Credit for {title}",
            rights_holder="Multi Image Lodge",
            status=GalleryMedia.Status.APPROVED,
            submitted_by=self.owner,
        )
        GalleryMediaPermissionGrant.objects.create(
            media=media,
            rights_holder="Multi Image Lodge",
            permitted_channels=[channel],
            evidence_file=SimpleUploadedFile("rights.pdf", b"%PDF-1.4 signed image permission"),
            granted_by=self.owner,
            granted_at=timezone.now(),
            review_status=GalleryMediaPermissionGrant.ReviewStatus.APPROVED,
            reviewed_by=self.editor,
            reviewed_at=timezone.now(),
        )
        return media

    def test_owner_can_preview_private_unapproved_image(self):
        pending = self.create_media("Private preview image", "website")
        pending.status = GalleryMedia.Status.OWNER_REVIEW
        pending.save(update_fields=("status",))
        self.client.force_authenticate(self.owner)
        response = self.client.get(f"/api/v1/gallery/media/{pending.id}/private-preview/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(b"".join(response.streaming_content)[:8], self.PNG[:8])
        self.assertTrue(GalleryAuditEvent.objects.filter(
            media=pending, actor=self.owner, action="media_private_previewed"
        ).exists())

    def test_other_partner_cannot_preview_private_image(self):
        other = User.objects.create_user(email="private-preview-other@example.com", password="test-password")
        self.client.force_authenticate(other)
        response = self.client.get(f"/api/v1/gallery/media/{self.additional.id}/private-preview/")
        self.assertEqual(response.status_code, 403)

    def test_owner_can_review_rights_submission_status_without_exposing_evidence_file(self):
        self.client.force_authenticate(self.owner)
        response = self.client.get(f"/api/v1/gallery/media/{self.additional.id}/permissions/")
        self.assertEqual(response.status_code, 200)
        grant = response.data["permissions"][0]
        self.assertEqual(grant["review_status"], GalleryMediaPermissionGrant.ReviewStatus.APPROVED)
        self.assertTrue(grant["evidence_available"])
        self.assertIn(f"/api/v1/gallery/media/{self.additional.id}/permissions/{grant['id']}/evidence/", grant["evidence_url"])
        self.assertNotIn("evidence_file", grant)

    def test_other_partner_cannot_view_rights_submission_status(self):
        other = User.objects.create_user(email="rights-status-other@example.com", password="test-password")
        self.client.force_authenticate(other)
        response = self.client.get(f"/api/v1/gallery/media/{self.additional.id}/permissions/")
        self.assertEqual(response.status_code, 403)

    def test_public_story_detail_returns_ordered_images_with_individual_credits(self):
        GalleryStoryMedia.objects.create(story=self.story, media=self.additional, position=1)
        response = self.client.get(f"/api/v1/gallery/stories/{self.story.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data["images"]], [self.cover.id, self.additional.id])
        self.assertEqual(response.data["images"][1]["caption"], "Caption for Garden image")
        self.assertEqual(response.data["images"][1]["media_credit"], "Credit for Garden image")
        self.assertTrue(response.data["images"][1]["image"].endswith(f"/gallery/media/{self.additional.id}/image/"))

    def test_each_additional_image_is_independently_checked_for_website_permission(self):
        social_only = self.create_media("Social only image", "social_media")
        GalleryStoryMedia.objects.create(story=self.story, media=social_only, position=1)
        detail = self.client.get(f"/api/v1/gallery/stories/{self.story.id}/")
        image = self.client.get(f"/api/v1/gallery/media/{social_only.id}/image/")
        self.assertEqual(detail.status_code, 404)
        self.assertEqual(image.status_code, 404)

    def test_owner_can_add_image_and_image_change_creates_new_approval_version(self):
        self.story.status = GalleryStory.Status.OWNER_REVIEW
        self.story.save(update_fields=("status",))
        GalleryStoryRevision.objects.create(
            story=self.story,
            version=self.story.current_version,
            summary=self.story.summary,
            media_snapshot=[self.cover.id],
            changed_by=self.owner,
            change_reason="Initial story version",
        )
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            f"/api/v1/gallery/stories/{self.story.id}/media/",
            {"media_id": self.additional.id},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.story.refresh_from_db()
        self.assertEqual(response.data["story_version"], 2)
        self.assertEqual(self.story.current_version, 2)
        self.assertEqual(self.story.status, GalleryStory.Status.OWNER_REVIEW)
        self.assertIsNone(self.story.owner_approved_version)
        self.assertTrue(GalleryStoryMedia.objects.filter(story=self.story, media=self.additional).exists())
        revision = self.story.revisions.get(version=2)
        self.assertEqual(revision.media_snapshot, [self.cover.id, self.additional.id])

    def test_partner_can_view_image_library_with_per_image_rights_status(self):
        GalleryStoryMedia.objects.create(story=self.story, media=self.additional, position=1)
        self.client.force_authenticate(self.owner)
        response = self.client.get(f"/api/v1/gallery/stories/{self.story.id}/media/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data["images"]], [self.cover.id, self.additional.id])
        self.assertTrue(response.data["images"][0]["is_cover"])
        self.assertFalse(response.data["images"][1]["is_cover"])
        self.assertTrue(response.data["images"][1]["website_permission_active"])
        self.assertEqual(response.data["images"][1]["rights_review_status"], GalleryMediaPermissionGrant.ReviewStatus.APPROVED)

    def test_other_partner_cannot_view_image_library(self):
        other = User.objects.create_user(email="multi-image-library-other@example.com", password="test-password")
        self.client.force_authenticate(other)
        response = self.client.get(f"/api/v1/gallery/stories/{self.story.id}/media/")
        self.assertEqual(response.status_code, 403)

    def test_owner_can_reorder_all_additional_images_and_approvals_reset(self):
        third = self.create_media("Pool image", "website")
        GalleryStoryMedia.objects.create(story=self.story, media=self.additional, position=1)
        GalleryStoryMedia.objects.create(story=self.story, media=third, position=2)
        self.story.status = GalleryStory.Status.OWNER_REVIEW
        self.story.save(update_fields=("status",))
        GalleryStoryRevision.objects.create(
            story=self.story, version=self.story.current_version, summary=self.story.summary,
            media_snapshot=[self.cover.id, self.additional.id, third.id],
            changed_by=self.owner, change_reason="Initial story version",
        )
        self.client.force_authenticate(self.owner)
        response = self.client.patch(
            f"/api/v1/gallery/stories/{self.story.id}/media/",
            {"ordered_media_ids": [third.id, self.additional.id]},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["ordered_media_ids"], [third.id, self.additional.id])
        self.story.refresh_from_db()
        self.assertEqual(self.story.current_version, 2)
        self.assertEqual(self.story.status, GalleryStory.Status.OWNER_REVIEW)
        self.assertIsNone(self.story.owner_approved_version)
        self.assertEqual(list(self.story.additional_media.values_list("media_id", flat=True)), [third.id, self.additional.id])
        self.assertEqual(self.story.revisions.get(version=2).media_snapshot, [self.cover.id, third.id, self.additional.id])

    def test_reorder_rejects_missing_or_duplicate_image_ids(self):
        GalleryStoryMedia.objects.create(story=self.story, media=self.additional, position=1)
        self.story.status = GalleryStory.Status.OWNER_REVIEW
        self.story.save(update_fields=("status",))
        self.client.force_authenticate(self.owner)
        response = self.client.patch(
            f"/api/v1/gallery/stories/{self.story.id}/media/",
            {"ordered_media_ids": []},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_owner_cannot_attach_another_partners_image(self):
        other_owner = User.objects.create_user(email="multi-image-other@example.com", password="test-password")
        other_partner = Partner.objects.create(
            owner=other_owner,
            name="Other Partner",
            category=Partner.Category.ACCOMMODATION,
            gallery_status=Partner.ApprovalStatus.APPROVED,
        )
        other_media = GalleryMedia.objects.create(
            partner=other_partner,
            title="Other partner image",
            image="https://images.example.test/other.jpg",
            alt_text="Other partner photograph",
            rights_holder="Other Partner",
            submitted_by=other_owner,
        )
        self.story.status = GalleryStory.Status.OWNER_REVIEW
        self.story.save(update_fields=("status",))
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            f"/api/v1/gallery/stories/{self.story.id}/media/",
            {"media_id": other_media.id},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(GalleryStoryMedia.objects.filter(story=self.story, media=other_media).exists())


class GalleryPublicationReadinessTests(TestCase):
    def setUp(self):
        self.private_storage_dir = tempfile.mkdtemp(prefix="xgetawaysx-readiness-tests-")
        self.storage_settings = override_settings(PRIVATE_GALLERY_STORAGE_ROOT=self.private_storage_dir)
        self.storage_settings.enable()
        self.client = APIClient()
        self.owner = User.objects.create_user(email="readiness-owner@example.com", password="test-password")
        self.editor = User.objects.create_superuser(email="readiness-editor@example.com", password="test-password")
        self.partner = Partner.objects.create(
            owner=self.owner,
            name="Readiness Lodge",
            category=Partner.Category.ACCOMMODATION,
            gallery_status=Partner.ApprovalStatus.APPROVED,
        )
        self.cover = GalleryMedia.objects.create(
            partner=self.partner,
            title="Readiness cover",
            image="https://images.example.test/readiness-cover.jpg",
            alt_text="A lodge beside a mountain",
            rights_holder="Readiness Lodge",
            status=GalleryMedia.Status.APPROVED,
            submitted_by=self.owner,
        )
        self.cover_grant = GalleryMediaPermissionGrant.objects.create(
            media=self.cover,
            rights_holder="Readiness Lodge",
            permitted_channels=["website"],
            evidence_file=SimpleUploadedFile("cover-rights.pdf", b"%PDF-1.4 cover rights"),
            granted_by=self.owner,
            granted_at=timezone.now(),
            review_status=GalleryMediaPermissionGrant.ReviewStatus.APPROVED,
            reviewed_by=self.editor,
            reviewed_at=timezone.now(),
        )

    def tearDown(self):
        self.storage_settings.disable()
        shutil.rmtree(self.private_storage_dir, ignore_errors=True)

    def test_partner_draft_explains_each_publication_gate_and_checks_every_story_image(self):
        story = GalleryStory.objects.create(
            media=self.cover,
            owner_original_history="Private owner notes must never be included in public readiness diagnostics.",
            summary=" ".join(["A verified short story describing the lodge, its surroundings and guest experience."] * 5),
            status=GalleryStory.Status.OWNER_REVIEW,
        )
        additional = GalleryMedia.objects.create(
            partner=self.partner,
            title="Social-only additional image",
            image="https://images.example.test/social-only.jpg",
            alt_text="A second image for social channels",
            rights_holder="Readiness Lodge",
            status=GalleryMedia.Status.APPROVED,
            submitted_by=self.owner,
        )
        GalleryMediaPermissionGrant.objects.create(
            media=additional,
            rights_holder="Readiness Lodge",
            permitted_channels=["social_media"],
            evidence_file=SimpleUploadedFile("social-rights.pdf", b"%PDF-1.4 social rights"),
            granted_by=self.owner,
            granted_at=timezone.now(),
            review_status=GalleryMediaPermissionGrant.ReviewStatus.APPROVED,
            reviewed_by=self.editor,
            reviewed_at=timezone.now(),
        )
        GalleryStoryMedia.objects.create(story=story, media=additional, position=1)

        self.client.force_authenticate(self.owner)
        response = self.client.get("/api/v1/gallery/stories/drafts/")
        self.assertEqual(response.status_code, 200)
        payload = next(item for item in response.data if item["id"] == story.id)
        checks = {item["key"]: item for item in payload["publication_checks"]}

        self.assertFalse(payload["publication_ready"])
        self.assertTrue(checks["partner_approved"]["passed"])
        self.assertTrue(checks["media_approved"]["passed"])
        self.assertFalse(checks["website_permission"]["passed"])
        self.assertIn("website use", checks["website_permission"]["detail"])
        self.assertTrue(checks["summary_valid"]["passed"])
        self.assertFalse(checks["owner_approval"]["passed"])
        self.assertFalse(checks["editorial_approval"]["passed"])
        self.assertNotIn("reviewer_notes", payload)
        self.assertTrue(all("ai_source_facts" not in check for check in payload["publication_checks"]))



class GalleryEditorialAuditReportingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(email="audit-owner@example.com", password="test-password")
        self.editor = User.objects.create_superuser(email="audit-reviewer@example.com", password="test-password")
        self.partner = Partner.objects.create(
            owner=self.owner, name="Audit Trail Lodge",
            category=Partner.Category.ACCOMMODATION,
            gallery_status=Partner.ApprovalStatus.APPROVED,
        )
        self.media = GalleryMedia.objects.create(
            partner=self.partner, title="Audit garden image",
            image="https://images.example.test/audit.jpg", alt_text="A garden",
            rights_holder="Photographer", submitted_by=self.owner,
        )
        self.story = GalleryStory.objects.create(
            media=self.media,
            owner_original_history="PRIVATE OWNER HISTORY MUST NOT APPEAR IN AUDIT REPORTS",
            summary="A verified description of the property garden and nearby landscape for travellers considering a visit.",
            status=GalleryStory.Status.EDITORIAL_REVIEW,
        )
        self.submitted = GalleryAuditEvent.objects.create(
            actor=self.owner, partner=self.partner, media=self.media, story=self.story,
            action="story_submitted", details={"story_version": 1},
        )
        self.decision = GalleryAuditEvent.objects.create(
            actor=self.editor, partner=self.partner, media=self.media, story=self.story,
            action="story_changes_requested",
            details={"story_version": 1, "reason": "PRIVATE REVIEW NOTES SHOULD NOT BE EXPORTED"},
        )

    def test_audit_history_is_staff_only(self):
        self.client.force_authenticate(self.owner)
        response = self.client.get("/api/v1/gallery/audit/")
        self.assertEqual(response.status_code, 403)
        report = self.client.get("/api/v1/gallery/audit/report/")
        self.assertEqual(report.status_code, 403)

    def test_staff_can_search_audit_history_and_get_reviewer_context(self):
        self.client.force_authenticate(self.editor)
        response = self.client.get("/api/v1/gallery/audit/?q=audit-reviewer")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        event = response.data["results"][0]
        self.assertEqual(event["actor_email"], self.editor.email)
        self.assertEqual(event["partner_name"], self.partner.name)
        self.assertEqual(event["media_title"], self.media.title)
        self.assertEqual(event["story_id"], self.story.id)
        self.assertEqual(event["story_version"], 1)
        self.assertNotIn("reason", event["safe_details"])

    def test_staff_can_filter_by_action_and_export_csv_without_private_fields(self):
        self.client.force_authenticate(self.editor)
        response = self.client.get("/api/v1/gallery/audit/?action=story_changes_requested")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

        report = self.client.get("/api/v1/gallery/audit/report/")
        self.assertEqual(report.status_code, 200)
        self.assertIn("text/csv", report["Content-Type"])
        csv_text = report.content.decode("utf-8")
        self.assertIn("story_changes_requested", csv_text)
        self.assertIn(self.editor.email, csv_text)
        self.assertIn("turnaround_hours", csv_text)
        self.assertNotIn("PRIVATE OWNER HISTORY", csv_text)
        self.assertNotIn("PRIVATE REVIEW NOTES", csv_text)
        self.assertNotIn("evidence_file", csv_text)

    def test_audit_events_cannot_be_updated_or_deleted(self):
        self.submitted.action = "rewritten_event"
        with self.assertRaises(ValidationError):
            self.submitted.save()
        with self.assertRaises(ValidationError):
            self.submitted.delete()
        with self.assertRaises(ValidationError):
            GalleryAuditEvent.objects.filter(pk=self.submitted.pk).update(action="rewritten_event")
        with self.assertRaises(ValidationError):
            GalleryAuditEvent.objects.filter(pk=self.submitted.pk).delete()
        self.submitted.refresh_from_db()
        self.assertEqual(self.submitted.action, "story_submitted")
