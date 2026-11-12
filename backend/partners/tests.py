from django.test import TestCase
from rest_framework.test import APIClient

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

    def test_unapproved_partner_profile_is_not_public(self):
        partner = Partner.objects.create(
            owner=self.owner, name="Pending Profile", category=Partner.Category.ACCOMMODATION,
            gallery_status=Partner.ApprovalStatus.PENDING,
        )
        response = self.client.get(f"/api/v1/partners/{partner.slug}/")
        self.assertEqual(response.status_code, 404)
