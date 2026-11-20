from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from .models import Partner, ReservationRequest, ReservationQuote, ReservationInstallment, PartnerFinancialSettings, ReservationPayment
from .views import _create_reservation_installments


class ReservationInstallmentScheduleTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(email="traveller@example.com", password="test-password")
        self.partner_owner = User.objects.create_user(email="host@example.com", password="test-password")
        self.other = User.objects.create_user(email="other@example.com", password="test-password")
        self.partner = Partner.objects.create(
            owner=self.partner_owner, name="Coastal Lodge",
            category=Partner.Category.ACCOMMODATION,
            booking_status=Partner.ApprovalStatus.APPROVED,
        )
        self.reservation = ReservationRequest.objects.create(
            customer=self.customer, partner=self.partner,
            start_date=timezone.localdate() + timedelta(days=30),
            end_date=timezone.localdate() + timedelta(days=33), guests=2,
            status=ReservationRequest.Status.CONFIRMED,
        )
        self.quote = ReservationQuote.objects.create(
            reservation=self.reservation, version=1,
            status=ReservationQuote.Status.ACCEPTED, currency="ZAR",
            total_amount=Decimal("10000.00"), deposit_amount=Decimal("2500.00"),
            expires_at=timezone.now() + timedelta(days=1), created_by=self.partner_owner,
            responded_at=timezone.now(),
        )

    def test_accepted_partner_deposit_is_used_and_balance_is_scheduled(self):
        _create_reservation_installments(self.reservation, self.quote)
        items = list(self.reservation.installments.all())
        self.assertEqual([item.kind for item in items], ["deposit", "balance"])
        self.assertEqual([item.amount for item in items], [Decimal("2500.00"), Decimal("7500.00")])
        self.assertEqual(sum((item.amount for item in items), Decimal("0.00")), Decimal("10000.00"))

    def test_thirty_percent_default_when_quote_has_no_deposit(self):
        self.quote.deposit_amount = Decimal("0.00")
        self.quote.save(update_fields=["deposit_amount"])
        _create_reservation_installments(self.reservation, self.quote)
        items = list(self.reservation.installments.all())
        self.assertEqual(items[0].amount, Decimal("3000.00"))
        self.assertEqual(items[1].amount, Decimal("7000.00"))



    def test_partner_deposit_policy_applies_when_quote_has_no_deposit(self):
        self.quote.deposit_amount = Decimal("0.00")
        self.quote.save(update_fields=["deposit_amount"])
        PartnerFinancialSettings.objects.create(
            partner=self.partner,
            deposit_type=PartnerFinancialSettings.DepositType.PERCENTAGE,
            deposit_value=Decimal("20.00"),
        )
        _create_reservation_installments(self.reservation, self.quote)
        first = self.reservation.installments.order_by("sequence").first()
        self.assertEqual(first.amount, Decimal("2000.00"))

    def test_partner_can_configure_deposit_and_balance_deadlines(self):
        policy = PartnerFinancialSettings.objects.create(
            partner=self.partner, deposit_due_hours=72, balance_due_days_before=14
        )
        before = timezone.now()
        _create_reservation_installments(self.reservation, self.quote)
        items = list(self.reservation.installments.all())
        self.assertGreaterEqual(items[0].due_at, before + timedelta(hours=71, minutes=59))
        self.assertEqual(
            timezone.localtime(items[1].due_at).date(),
            self.reservation.start_date - timedelta(days=14),
        )
        self.assertEqual(policy.deposit_due_hours, 72)


    def test_partner_can_split_balance_into_multiple_instalments(self):
        PartnerFinancialSettings.objects.create(
            partner=self.partner, balance_installment_count=3,
            balance_installment_interval_days=7,
        )
        _create_reservation_installments(self.reservation, self.quote)
        items = list(self.reservation.installments.all())
        self.assertEqual(len(items), 4)
        self.assertEqual(items[0].kind, "deposit")
        self.assertEqual([item.sequence for item in items], [1, 2, 3, 4])
        self.assertEqual(
            sum((item.amount for item in items[1:]), Decimal("0.00")),
            Decimal("7500.00"),
        )
        self.assertEqual(
            sum((item.amount for item in items), Decimal("0.00")),
            Decimal("10000.00"),
        )


    def test_checkout_selects_the_next_scheduled_balance_instalment(self):
        PartnerFinancialSettings.objects.create(
            partner=self.partner, balance_installment_count=3,
            balance_installment_interval_days=7,
        )
        self.reservation.quoted_total = self.quote.total_amount
        self.reservation.quoted_deposit = self.quote.deposit_amount
        self.reservation.quoted_currency = self.quote.currency
        self.reservation.quoted_at = timezone.now()
        self.reservation.save(update_fields=[
            "quoted_total", "quoted_deposit", "quoted_currency", "quoted_at", "updated_at",
        ])
        _create_reservation_installments(self.reservation, self.quote)
        client = APIClient()
        client.force_authenticate(self.customer)
        first = client.post("/api/v1/partners/payments/", {
            "reservation_id": self.reservation.pk, "idempotency_key": "instalment-first-001",
        }, format="json")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.data["kind"], ReservationPayment.Kind.DEPOSIT)
        self.assertEqual(Decimal(first.data["amount"]), Decimal("2500.00"))
        payment = ReservationPayment.objects.get(pk=first.data["id"])
        payment.status = ReservationPayment.Status.CAPTURED
        payment.provider_reference = "test-capture-first"
        payment.captured_at = timezone.now()
        payment.save(update_fields=["status", "provider_reference", "captured_at"])
        second = client.post("/api/v1/partners/payments/", {
            "reservation_id": self.reservation.pk, "idempotency_key": "instalment-second-002",
        }, format="json")
        self.assertEqual(second.status_code, 201)
        self.assertEqual(second.data["kind"], ReservationPayment.Kind.BALANCE)
        self.assertEqual(Decimal(second.data["amount"]), Decimal("2500.00"))

    def test_schedule_creation_is_idempotent(self):
        _create_reservation_installments(self.reservation, self.quote)
        _create_reservation_installments(self.reservation, self.quote)
        self.assertEqual(self.reservation.installments.count(), 2)

    def test_schedule_visible_only_to_customer_or_partner_owner(self):
        _create_reservation_installments(self.reservation, self.quote)
        client = APIClient()
        client.force_authenticate(self.other)
        response = client.get(f"/api/v1/partners/reservations/{self.reservation.pk}/payment-schedule/")
        self.assertEqual(response.status_code, 404)
        client.force_authenticate(self.customer)
        response = client.get(f"/api/v1/partners/reservations/{self.reservation.pk}/payment-schedule/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["installments"]), 2)
        client.force_authenticate(self.partner_owner)
        response = client.get(f"/api/v1/partners/reservations/{self.reservation.pk}/payment-schedule/")
        self.assertEqual(response.status_code, 200)

    def test_zero_percent_deposit_creates_balance_only_schedule(self):
        self.quote.deposit_amount = Decimal("0.00")
        self.quote.save(update_fields=["deposit_amount"])
        PartnerFinancialSettings.objects.create(
            partner=self.partner,
            deposit_type=PartnerFinancialSettings.DepositType.PERCENTAGE,
            deposit_value=Decimal("0.00"),
        )
        _create_reservation_installments(self.reservation, self.quote)
        items = list(self.reservation.installments.all())
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].kind, ReservationInstallment.Kind.BALANCE)
        self.assertEqual(items[0].amount, Decimal("10000.00"))

    def test_small_balance_reduces_instalment_count_to_positive_cents(self):
        self.quote.total_amount = Decimal("0.01")
        self.quote.deposit_amount = Decimal("0.00")
        self.quote.save(update_fields=["total_amount", "deposit_amount"])
        PartnerFinancialSettings.objects.create(
            partner=self.partner,
            deposit_type=PartnerFinancialSettings.DepositType.PERCENTAGE,
            deposit_value=Decimal("0.00"),
            balance_installment_count=6,
        )
        _create_reservation_installments(self.reservation, self.quote)
        items = list(self.reservation.installments.all())
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].amount, Decimal("0.01"))
        self.assertEqual(items[0].kind, ReservationInstallment.Kind.BALANCE)
