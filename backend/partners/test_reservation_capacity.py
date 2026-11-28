from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from .models import Partner, PartnerAvailability, ReservationRequest


class ReservationCapacityProtectionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer_one = User.objects.create_user(
            email="capacity-customer-one@example.com", password="Strong-passphrase-2026!"
        )
        self.customer_two = User.objects.create_user(
            email="capacity-customer-two@example.com", password="Strong-passphrase-2026!"
        )
        self.owner = User.objects.create_user(
            email="capacity-owner@example.com", password="Strong-passphrase-2026!"
        )
        self.partner = Partner.objects.create(
            owner=self.owner,
            name="Capacity Test Lodge",
            slug="capacity-test-lodge",
            category=Partner.Category.ACCOMMODATION,
            gallery_status=Partner.ApprovalStatus.APPROVED,
            booking_status=Partner.ApprovalStatus.APPROVED,
        )
        self.start = timezone.localdate() + timedelta(days=45)
        self.end = self.start + timedelta(days=2)
        for offset in range(2):
            PartnerAvailability.objects.create(
                partner=self.partner,
                date=self.start + timedelta(days=offset),
                capacity=3,
                booked_count=0,
                is_open=True,
                price_per_guest=Decimal("900.00"),
                currency="ZAR",
            )

    def create_reservation_with_accepted_quote(self, customer, key):
        reservation = ReservationRequest.objects.create(
            customer=customer,
            partner=self.partner,
            start_date=self.start,
            end_date=self.end,
            guests=2,
            message="Capacity protection test.",
        )
        self.client.force_authenticate(user=self.owner)
        quote = self.client.post(
            f"/api/v1/partners/partner/reservations/{reservation.pk}/quotes/",
            {
                "currency": "ZAR",
                "items": [{"description": "Accommodation", "quantity": "1", "unit_price": "1800.00"}],
                "deposit_amount": "540.00",
                "terms": "Test quote.",
                "expires_at": (timezone.now() + timedelta(days=2)).isoformat(),
            },
            format="json",
        )
        self.assertEqual(quote.status_code, 201, quote.data)
        self.client.force_authenticate(user=customer)
        accepted = self.client.post(
            f"/api/v1/partners/reservations/{reservation.pk}/quote-decision/",
            {"status": "accepted"},
            format="json",
        )
        self.assertEqual(accepted.status_code, 200, accepted.data)
        return reservation

    def test_confirmation_rechecks_capacity_and_prevents_overbooking(self):
        first = self.create_reservation_with_accepted_quote(self.customer_one, "first")
        second = self.create_reservation_with_accepted_quote(self.customer_two, "second")

        self.client.force_authenticate(user=self.owner)
        first_response = self.client.post(
            f"/api/v1/partners/partner/reservations/{first.pk}/decision/",
            {"status": "confirmed", "partner_response": "Your booking is confirmed."},
            format="json",
        )
        self.assertEqual(first_response.status_code, 200, first_response.data)

        second_response = self.client.post(
            f"/api/v1/partners/partner/reservations/{second.pk}/decision/",
            {"status": "confirmed", "partner_response": "Your booking is confirmed."},
            format="json",
        )
        self.assertEqual(second_response.status_code, 400)
        self.assertIn("Availability or capacity has changed", str(second_response.data))

        for day in PartnerAvailability.objects.filter(partner=self.partner):
            day.refresh_from_db()
            self.assertEqual(day.booked_count, 2)
            self.assertLessEqual(day.booked_count, day.capacity)

        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(first.status, ReservationRequest.Status.CONFIRMED)
        self.assertEqual(second.status, ReservationRequest.Status.PENDING)
