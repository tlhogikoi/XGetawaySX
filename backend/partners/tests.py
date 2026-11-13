from django.test import TestCase
from rest_framework.test import APIClient
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from gallery.models import GalleryMedia, GalleryMediaPermissionGrant, GalleryStory

from accounts.models import User
from .models import Partner


class PublicPartnerListTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(email="host@example.com", password="test-password")

    def create_partner(self, name, gallery_status):
        return Partner.objects.create(
            owner=self.owner,
            name=name,
            category=Partner.Category.ACCOMMODATION,
            gallery_status=gallery_status,
        )

    def test_only_gallery_approved_partners_are_public(self):
        self.create_partner("Approved Lodge", Partner.ApprovalStatus.APPROVED)
        self.create_partner("Pending Guesthouse", Partner.ApprovalStatus.PENDING)

        response = self.client.get("/api/v1/partners/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Approved Lodge")

    def test_discovery_filters_by_category_and_location(self):
        matched = self.create_partner("Cape Adventure", Partner.ApprovalStatus.APPROVED)
        matched.category = Partner.Category.ACTIVITY
        matched.city = "Cape Town"
        matched.province = "Western Cape"
        matched.save()
        self.create_partner("Johannesburg Lodge", Partner.ApprovalStatus.APPROVED)
        response = self.client.get("/api/v1/partners/?category=activity&city=cape&province=western")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["name"] for item in response.data], ["Cape Adventure"])

    def test_search_never_returns_unapproved_partners(self):
        self.create_partner("Approved Garden Lodge", Partner.ApprovalStatus.APPROVED)
        self.create_partner("Pending Garden Lodge", Partner.ApprovalStatus.PENDING)
        response = self.client.get("/api/v1/partners/?q=garden")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["name"] for item in response.data], ["Approved Garden Lodge"])

    def test_unknown_category_does_not_bypass_public_approval_filter(self):
        self.create_partner("Visible Lodge", Partner.ApprovalStatus.APPROVED)
        self.create_partner("Hidden Lodge", Partner.ApprovalStatus.SUSPENDED)
        response = self.client.get("/api/v1/partners/?category=not-a-category")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["name"] for item in response.data], ["Visible Lodge"])

    def test_public_serializer_does_not_expose_owner_or_private_approval_fields(self):
        self.create_partner("Public Lodge", Partner.ApprovalStatus.APPROVED)

        response = self.client.get("/api/v1/partners/")

        self.assertNotIn("owner", response.data[0])
        self.assertNotIn("booking_status", response.data[0])
        self.assertNotIn("enquiry_status", response.data[0])


class PublicPartnerDetailTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(email="profile-owner@example.com", password="test-password")

    def test_approved_partner_has_public_profile_and_empty_story_collection(self):
        partner = Partner.objects.create(
            owner=self.owner, name="Profile Lodge", category=Partner.Category.ACCOMMODATION,
            description="A public description.", city="Johannesburg",
            gallery_status=Partner.ApprovalStatus.APPROVED,
        )
        response = self.client.get(f"/api/v1/partners/{partner.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Profile Lodge")
        self.assertEqual(response.data["city"], "Johannesburg")
        self.assertEqual(response.data["stories"], [])
        self.assertNotIn("owner", response.data)
        self.assertNotIn("booking_status", response.data)
        self.assertNotIn("enquiry_status", response.data)

    def test_profile_includes_only_published_stories_with_approved_rights(self):
        partner = Partner.objects.create(
            owner=self.owner, name="Story Profile Lodge",
            category=Partner.Category.ACCOMMODATION,
            gallery_status=Partner.ApprovalStatus.APPROVED,
        )
        media = GalleryMedia.objects.create(
            partner=partner, title="Garden at sunrise",
            image="https://images.example.test/garden.jpg",
            alt_text="Garden at sunrise", rights_holder="Lodge",
            submitted_by=self.owner, status=GalleryMedia.Status.APPROVED,
        )
        GalleryMediaPermissionGrant.objects.create(
            media=media, rights_holder="Lodge", permitted_channels=["website"],
            evidence_file=SimpleUploadedFile("release.pdf", b"%PDF-1.4 signed release"),
            granted_by=self.owner, granted_at=timezone.now(),
            review_status=GalleryMediaPermissionGrant.ReviewStatus.APPROVED,
        )
        GalleryStory.objects.create(
            media=media, summary="This carefully prepared story describes the lodge garden and its setting using information supplied by the owner and approved for public visitors.",
            status=GalleryStory.Status.PUBLISHED,
            owner_approved_at=timezone.now(), owner_approved_version=1,
            editorial_approved_at=timezone.now(), editorial_approved_version=1,
            published_at=timezone.now(),
            owner_original_history="PRIVATE PARTNER HISTORY",
        )
        response = self.client.get(f"/api/v1/partners/{partner.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["stories"]), 1)
        self.assertNotIn("PRIVATE PARTNER HISTORY", str(response.data))
        self.assertNotIn("ai_source_facts", response.data["stories"][0])

    def test_unapproved_partner_profile_is_not_public(self):
        partner = Partner.objects.create(
            owner=self.owner, name="Pending Profile", category=Partner.Category.ACCOMMODATION,
            gallery_status=Partner.ApprovalStatus.PENDING,
        )
        response = self.client.get(f"/api/v1/partners/{partner.slug}/")
        self.assertEqual(response.status_code, 404)
