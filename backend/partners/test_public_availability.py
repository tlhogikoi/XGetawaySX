from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from .models import Partner, PartnerAvailability


class PublicPartnerAvailabilityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        owner = User.objects.create_user(
            email="availability-owner@example.com",
            password="Strong-passphrase-2026!",
        )
        self.partner = Partner.objects.create(
            owner=owner,
            name="Garden Route Retreat",
            slug="garden-route-retreat",
            category=Partner.Category.ACCOMMODATION,
            gallery_status=Partner.ApprovalStatus.APPROVED,
            booking_status=Partner.ApprovalStatus.APPROVED,
        )
        self.start = timezone.localdate() + timedelta(days=30)
        PartnerAvailability.objects.create(
            partner=self.partner, date=self.start, capacity=6, booked_count=2,
            is_open=True, price_per_guest="850.00", currency="ZAR",
        )
        PartnerAvailability.objects.create(
            partner=self.partner, date=self.start + timedelta(days=1),
            capacity=6, booked_count=0, is_open=False,
            price_per_guest="850.00", currency="ZAR",
        )
        # The third night is intentionally not published.

    def url(self, guests=2):
        return (
            f"/api/v1/partners/availability/?partner_id={self.partner.pk}"
            f"&start_date={self.start.isoformat()}"
            f"&end_date={(self.start + timedelta(days=3)).isoformat()}"
            f"&guests={guests}"
        )

    def test_availability_returns_every_night_and_marks_unavailable_dates(self):
        response = self.client.get(self.url(guests=3))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 3)
        self.assertEqual(
            [item["is_available"] for item in response.data],
            [True, False, False],
        )
        self.assertEqual(response.data[0]["available_guests"], 4)
        self.assertEqual(response.data[0]["requested_guests"], 3)
        self.assertEqual(response.data[1]["available_guests"], 0)
        self.assertIsNone(response.data[2]["price_per_guest"])

    def test_availability_is_guest_count_aware(self):
        response = self.client.get(self.url(guests=5))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data[0]["is_available"])

    def test_invalid_guest_count_is_rejected(self):
        for guests in ("0", "101", "two"):
            with self.subTest(guests=guests):
                response = self.client.get(self.url(guests=guests))
                self.assertEqual(response.status_code, 400)

    def test_unapproved_partner_availability_is_not_public(self):
        self.partner.booking_status = Partner.ApprovalStatus.SUSPENDED
        self.partner.save(update_fields=["booking_status", "updated_at"])
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 404)
