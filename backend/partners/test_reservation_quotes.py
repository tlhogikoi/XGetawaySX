from datetime import date, datetime, timedelta, timezone as dt_timezone
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from .models import Partner, PartnerAvailability, ReservationQuote, ReservationRequest


class ReservationQuoteWorkflowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create_user(
            email="quote-customer@example.com", password="Strong-passphrase-2026!"
        )
        self.owner = User.objects.create_user(
            email="quote-partner@example.com", password="Strong-passphrase-2026!"
        )
        self.other = User.objects.create_user(
            email="quote-other@example.com", password="Strong-passphrase-2026!"
        )
        self.partner = Partner.objects.create(
            owner=self.owner,
            name="Drakensberg Escape",
            slug="drakensberg-escape",
            category=Partner.Category.ACCOMMODATION,
            gallery_status=Partner.ApprovalStatus.APPROVED,
            booking_status=Partner.ApprovalStatus.APPROVED,
        )
        self.start = date.today() + timedelta(days=40)
        self.end = self.start + timedelta(days=2)
        for offset in range(2):
            PartnerAvailability.objects.create(
                partner=self.partner,
                date=self.start + timedelta(days=offset),
                capacity=8,
                booked_count=0,
                is_open=True,
                price_per_guest="900.00",
                currency="ZAR",
            )
        self.reservation = ReservationRequest.objects.create(
            customer=self.customer,
            partner=self.partner,
            start_date=self.start,
            end_date=self.end,
            guests=2,
            message="A short family getaway.",
        )
        self.quote_payload = {
            "currency": "ZAR",
            "items": [
                {"description": "Accommodation", "quantity": "2", "unit_price": "1200.00"},
                {"description": "Breakfast", "quantity": "4", "unit_price": "150.00"},
            ],
            "deposit_amount": "600.00",
            "terms": "Breakfast included. Balance due before arrival.",
            "expires_at": (datetime.now(dt_timezone.utc) + timedelta(days=2)).isoformat(),
        }

    def issue_quote(self):
        self.client.force_authenticate(user=self.owner)
        return self.client.post(
            f"/api/v1/partners/partner/reservations/{self.reservation.pk}/quotes/",
            self.quote_payload,
            format="json",
        )

    def test_partner_can_issue_itemised_quote_with_calculated_total(self):
        response = self.issue_quote()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["total_amount"], "3000.00")
        self.assertEqual(len(response.data["items"]), 2)
        self.assertEqual(ReservationQuote.objects.get().status, ReservationQuote.Status.SENT)

    def test_customer_acceptance_records_locked_price_but_does_not_confirm_booking(self):
        issued = self.issue_quote()
        self.assertEqual(issued.status_code, 201)
        self.client.force_authenticate(user=self.customer)
        response = self.client.post(
            f"/api/v1/partners/reservations/{self.reservation.pk}/quote-decision/",
            {"status": "accepted"}, format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.status, ReservationRequest.Status.PENDING)
        self.assertEqual(self.reservation.quoted_total, Decimal("3000.00"))
        self.assertEqual(self.reservation.quoted_deposit, Decimal("600.00"))
        self.assertEqual(response.data["status"], ReservationQuote.Status.ACCEPTED)

    def test_partner_cannot_confirm_without_customer_quote_acceptance(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            f"/api/v1/partners/partner/reservations/{self.reservation.pk}/decision/",
            {"status": "confirmed", "partner_response": "We confirm your reservation."},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.reservation.__class__.objects.get(pk=self.reservation.pk).status, "pending")

    def test_partner_can_confirm_after_customer_accepts_quote(self):
        issued = self.issue_quote()
        self.assertEqual(issued.status_code, 201)
        self.client.force_authenticate(user=self.customer)
        accepted = self.client.post(
            f"/api/v1/partners/reservations/{self.reservation.pk}/quote-decision/",
            {"status": "accepted"}, format="json",
        )
        self.assertEqual(accepted.status_code, 200)
        self.client.force_authenticate(user=self.owner)
        confirmed = self.client.post(
            f"/api/v1/partners/partner/reservations/{self.reservation.pk}/decision/",
            {"status": "confirmed", "partner_response": "Your reservation is confirmed."},
            format="json",
        )
        self.assertEqual(confirmed.status_code, 200)
        self.assertEqual(confirmed.data["status"], ReservationRequest.Status.CONFIRMED)

    def test_customer_cannot_accept_another_customers_quote(self):
        self.issue_quote()
        self.client.force_authenticate(user=self.other)
        response = self.client.post(
            f"/api/v1/partners/reservations/{self.reservation.pk}/quote-decision/",
            {"status": "accepted"}, format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_quote_expiry_is_enforced(self):
        payload = dict(self.quote_payload)
        payload["expires_at"] = (datetime.now(dt_timezone.utc) - timedelta(minutes=1)).isoformat()
        self.client.force_authenticate(user=self.owner)
        issued = self.client.post(
            f"/api/v1/partners/partner/reservations/{self.reservation.pk}/quotes/",
            payload, format="json",
        )
        self.assertEqual(issued.status_code, 400)
