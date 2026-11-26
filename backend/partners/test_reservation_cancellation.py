from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from .models import (
    Partner,
    PartnerAvailability,
    ReservationCancellationRequest,
    ReservationPayment,
    ReservationRequest,
)
from .views import _complete_approved_cancellation


class ReservationCancellationReconciliationTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            email="cancel-uat-customer@example.com",
            password="Strong-passphrase-2026!",
        )
        self.owner = User.objects.create_user(
            email="cancel-uat-owner@example.com",
            password="Strong-passphrase-2026!",
        )
        self.partner = Partner.objects.create(
            owner=self.owner,
            name="Cancellation Reconciliation Lodge",
            slug="cancellation-reconciliation-lodge",
            category=Partner.Category.ACCOMMODATION,
            booking_status=Partner.ApprovalStatus.APPROVED,
        )
        self.start = timezone.localdate() + timedelta(days=60)
        self.days = [
            PartnerAvailability.objects.create(
                partner=self.partner,
                date=self.start + timedelta(days=offset),
                capacity=4,
                booked_count=2,
                is_open=True,
                price_per_guest=Decimal("1000.00"),
                currency="ZAR",
            )
            for offset in range(2)
        ]
        self.reservation = ReservationRequest.objects.create(
            customer=self.customer,
            partner=self.partner,
            start_date=self.start,
            end_date=self.start + timedelta(days=2),
            guests=2,
            status=ReservationRequest.Status.CONFIRMED,
        )
        self.cancellation = ReservationCancellationRequest.objects.create(
            reservation=self.reservation,
            customer=self.customer,
            reason="Change of travel plans.",
            status=ReservationCancellationRequest.Status.APPROVED,
            decided_by=self.owner,
            decided_at=timezone.now(),
        )
        self.payments = [
            ReservationPayment.objects.create(
                reservation=self.reservation,
                customer=self.customer,
                partner=self.partner,
                kind=ReservationPayment.Kind.DEPOSIT if index == 0 else ReservationPayment.Kind.BALANCE,
                status=ReservationPayment.Status.CAPTURED,
                amount=amount,
                currency="ZAR",
                idempotency_key=f"cancel-uat-payment-{index}",
                provider="sandbox_test",
                provider_reference=f"cancel-uat-reference-{index}",
                captured_at=timezone.now(),
            )
            for index, amount in enumerate((Decimal("300.00"), Decimal("700.00")))
        ]

    def test_capacity_is_held_until_every_captured_payment_is_refunded(self):
        self.payments[0].status = ReservationPayment.Status.REFUNDED
        self.payments[0].save(update_fields=["status", "updated_at"])

        still_pending = _complete_approved_cancellation(self.cancellation)
        self.reservation.refresh_from_db()
        self.cancellation.refresh_from_db()
        self.assertEqual(still_pending.status, ReservationCancellationRequest.Status.APPROVED)
        self.assertEqual(self.reservation.status, ReservationRequest.Status.CONFIRMED)
        for day in self.days:
            day.refresh_from_db()
            self.assertEqual(day.booked_count, 2)

        self.payments[1].status = ReservationPayment.Status.REFUNDED
        self.payments[1].save(update_fields=["status", "updated_at"])
        completed = _complete_approved_cancellation(self.cancellation)

        self.reservation.refresh_from_db()
        self.cancellation.refresh_from_db()
        self.assertEqual(completed.status, ReservationCancellationRequest.Status.COMPLETED)
        self.assertEqual(self.reservation.status, ReservationRequest.Status.CANCELLED)
        for day in self.days:
            day.refresh_from_db()
            self.assertEqual(day.booked_count, 0)

        # A repeated completion attempt must not release the same capacity twice.
        _complete_approved_cancellation(self.cancellation)
        for day in self.days:
            day.refresh_from_db()
            self.assertEqual(day.booked_count, 0)


    def test_customer_cannot_create_payment_during_approved_cancellation(self):
        self.reservation.quoted_total = Decimal("1000.00")
        self.reservation.quoted_deposit = Decimal("300.00")
        self.reservation.quoted_currency = "ZAR"
        self.reservation.quoted_at = timezone.now()
        self.reservation.save(update_fields=[
            "quoted_total", "quoted_deposit", "quoted_currency", "quoted_at", "updated_at",
        ])
        client = APIClient()
        client.force_authenticate(self.customer)
        response = client.post(
            "/api/v1/partners/payments/",
            {"reservation_id": self.reservation.pk, "idempotency_key": "blocked-during-cancel"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("cancellation request", str(response.data).lower())
        self.assertFalse(self.reservation.payments.filter(
            idempotency_key="blocked-during-cancel"
        ).exists())

    def test_admin_cannot_manually_capture_payment_during_approved_cancellation(self):
        staff = User.objects.create_user(
            email="cancel-uat-staff@example.com",
            password="Strong-passphrase-2026!",
            is_staff=True,
        )
        pending = ReservationPayment.objects.create(
            reservation=self.reservation,
            customer=self.customer,
            partner=self.partner,
            kind=ReservationPayment.Kind.BALANCE,
            status=ReservationPayment.Status.PENDING,
            amount=Decimal("100.00"),
            currency="ZAR",
            idempotency_key="manual-capture-blocked",
        )
        client = APIClient()
        client.force_authenticate(staff)
        response = client.post(
            f"/api/v1/partners/payments/{pending.pk}/reconcile/",
            {
                "status": "captured",
                "provider": "sandbox_test",
                "provider_reference": "blocked-capture-reference",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        pending.refresh_from_db()
        self.assertEqual(pending.status, ReservationPayment.Status.PENDING)
        self.assertFalse(hasattr(pending, "commission_entry"))
