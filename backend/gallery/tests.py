from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from partners.models import Partner
from .models import GalleryMedia, GalleryStory


class GalleryPublicationTests(TestCase):
    def setUp(self):
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
            permission_granted_at=__import__("django.utils.timezone", fromlist=["now"]).now(),
            status=GalleryMedia.Status.APPROVED,
            submitted_by=self.owner,
        )

    def test_private_original_history_is_not_public(self):
        story = GalleryStory.objects.create(
            media=self.media,
            owner_original_history="Private owner history with source notes.",
            owner_history_private=True,
            summary=" ".join(["A verified short story about this place and its setting."] * 5),
            status=GalleryStory.Status.PUBLISHED,
            owner_approved_by=self.owner,
            owner_approved_at=__import__("django.utils.timezone", fromlist=["now"]).now(),
            editorial_approved_by=self.editor,
            editorial_approved_at=__import__("django.utils.timezone", fromlist=["now"]).now(),
            published_at=__import__("django.utils.timezone", fromlist=["now"]).now(),
        )
        response = self.client.get("/api/v1/gallery/stories/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertIsNone(response.data[0]["owner_original_history"])
        self.assertNotIn("ai_source_facts", response.data[0])

    def test_unapproved_partner_story_is_not_public(self):
        self.partner.gallery_status = Partner.ApprovalStatus.PENDING
        self.partner.save()
        story = GalleryStory.objects.create(
            media=self.media,
            summary=" ".join(["A concise account of the place, based only on owner supplied facts."] * 5),
            status=GalleryStory.Status.PUBLISHED,
            owner_approved_by=self.owner,
            owner_approved_at=__import__("django.utils.timezone", fromlist=["now"]).now(),
            editorial_approved_by=self.editor,
            editorial_approved_at=__import__("django.utils.timezone", fromlist=["now"]).now(),
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
