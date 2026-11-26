from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from .models import Partner, PartnerAvailability


class ReservationStatusHistoryTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create_user(
            email="history-customer@example.com", password="Strong-passphrase-2026!"
        )
        self.other_customer = User.objects.create_user(
            email="history-other@example.com", password="Strong-passphrase-2026!"
        )
        self.owner = User.objects.create_user(
            email="history-partner@example.com", password="Strong-passphrase-2026!"
        )
        self.partner = Partner.objects.create(
            owner=self.owner,
            name="History Test Lodge",
            slug="history-test-lodge",
            category=Partner.Category.ACCOMMODATION,
            gallery_status=Partner.ApprovalStatus.APPROVED,
            booking_status=Partner.ApprovalStatus.APPROVED,
        )
        self.start = timezone.localdate() + timedelta(days=35)
        PartnerAvailability.objects.create(
            partner=self.partner,
            date=self.start,
            capacity=5,
            booked_count=0,
            is_open=True,
            price_per_guest=Decimal("1200.00"),
            currency="ZAR",
        )

    def create_reservation(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.post(
            "/api/v1/partners/reservations/",
            {
                "partner_id": self.partner.pk,
                "start_date": self.start.isoformat(),
                "end_date": (self.start + timedelta(days=1)).isoformat(),
                "guests": 2,
                "message": "Reservation history test.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        return response.data["id"]

    def test_request_creation_and_withdrawal_are_audited_and_scoped(self):
        reservation_id = self.create_reservation()
        self.client.force_authenticate(user=self.customer)
        withdrawn = self.client.post(
            f"/api/v1/partners/reservations/{reservation_id}/cancel/",
            {"reason": ""},
            format="json",
        )
        self.assertEqual(withdrawn.status_code, 200, withdrawn.data)
        self.assertEqual(withdrawn.data["status"], "cancelled")

        customer_list = self.client.get("/api/v1/partners/reservations/")
        history = customer_list.data[0]["status_history"]
        self.assertEqual(
            [(event["from_status"], event["to_status"]) for event in history],
            [("", "pending"), ("pending", "cancelled")],
        )
        self.assertEqual(history[0]["actor_role"], getattr(self.customer, "role", "user"))
        self.assertIn("withdrew", history[1]["reason"].lower())

        self.client.force_authenticate(user=self.other_customer)
        self.assertEqual(self.client.get("/api/v1/partners/reservations/").data, [])

        self.client.force_authenticate(user=self.owner)
        partner_list = self.client.get("/api/v1/partners/partner/reservations/")
        self.assertEqual(len(partner_list.data), 1)
        self.assertEqual(len(partner_list.data[0]["status_history"]), 2)

    def test_confirmation_is_recorded_for_customer_and_partner(self):
        reservation_id = self.create_reservation()
        self.client.force_authenticate(user=self.owner)
        quote = self.client.post(
            f"/api/v1/partners/partner/reservations/{reservation_id}/quotes/",
            {
                "currency": "ZAR",
                "items": [{
                    "description": "One-night accommodation",
                    "quantity": "1",
                    "unit_price": "2400.00",
                }],
                "deposit_amount": "720.00",
                "terms": "History audit test.",
                "expires_at": (timezone.now() + timedelta(days=2)).isoformat(),
            },
            format="json",
        )
        self.assertEqual(quote.status_code, 201, quote.data)

        self.client.force_authenticate(user=self.customer)
        accepted = self.client.post(
            f"/api/v1/partners/reservations/{reservation_id}/quote-decision/",
            {"status": "accepted"},
            format="json",
        )
        self.assertEqual(accepted.status_code, 200, accepted.data)

        self.client.force_authenticate(user=self.owner)
        confirmed = self.client.post(
            f"/api/v1/partners/partner/reservations/{reservation_id}/decision/",
            {"status": "confirmed", "partner_response": "Your reservation is confirmed."},
            format="json",
        )
        self.assertEqual(confirmed.status_code, 200, confirmed.data)

        self.client.force_authenticate(user=self.customer)
        history = self.client.get("/api/v1/partners/reservations/").data[0]["status_history"]
        self.assertEqual(
            [(event["from_status"], event["to_status"]) for event in history],
            [("", "pending"), ("pending", "confirmed")],
        )
        self.assertEqual(history[-1]["actor_role"], getattr(self.owner, "role", "user"))
        self.assertEqual(history[-1]["reason"], "Your reservation is confirmed.")


    def test_other_customer_cannot_cancel_or_read_reservation(self):
        reservation_id = self.create_reservation()
        self.client.force_authenticate(user=self.other_customer)
        denied = self.client.post(
            f"/api/v1/partners/reservations/{reservation_id}/cancel/",
            {"reason": "Not my reservation"},
            format="json",
        )
        self.assertEqual(denied.status_code, 404)
        self.assertEqual(self.client.get("/api/v1/partners/reservations/").data, [])

        self.client.force_authenticate(user=self.customer)
        own_reservation = self.client.get("/api/v1/partners/reservations/")
        self.assertEqual(own_reservation.status_code, 200)
        self.assertEqual(own_reservation.data[0]["status"], "pending")

    def test_other_customer_cannot_decide_reservation_quote(self):
        reservation_id = self.create_reservation()
        self.client.force_authenticate(user=self.other_customer)
        denied = self.client.post(
            f"/api/v1/partners/reservations/{reservation_id}/quote-decision/",
            {"status": "accepted"},
            format="json",
        )
        self.assertEqual(denied.status_code, 404)

    def test_unrelated_user_cannot_issue_quote_or_decide_partner_reservation(self):
        reservation_id = self.create_reservation()
        self.client.force_authenticate(user=self.other_customer)
        quote = self.client.post(
            f"/api/v1/partners/partner/reservations/{reservation_id}/quotes/",
            {
                "currency": "ZAR",
                "items": [{"description": "Unauthorised quote", "quantity": "1", "unit_price": "100.00"}],
                "deposit_amount": "30.00",
                "expires_at": (timezone.now() + timedelta(days=1)).isoformat(),
            },
            format="json",
        )
        self.assertEqual(quote.status_code, 404)
        decision = self.client.post(
            f"/api/v1/partners/partner/reservations/{reservation_id}/decision/",
            {"status": "declined", "partner_response": "Unauthorised"},
            format="json",
        )
        self.assertEqual(decision.status_code, 404)

    def test_cancelled_request_rejects_repeated_cancellation(self):
        reservation_id = self.create_reservation()
        self.client.force_authenticate(user=self.customer)
        first = self.client.post(
            f"/api/v1/partners/reservations/{reservation_id}/cancel/",
            {"reason": ""},
            format="json",
        )
        self.assertEqual(first.status_code, 200)
        second = self.client.post(
            f"/api/v1/partners/reservations/{reservation_id}/cancel/",
            {"reason": ""},
            format="json",
        )
        self.assertEqual(second.status_code, 400)
