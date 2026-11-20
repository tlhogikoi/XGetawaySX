from datetime import date, timedelta

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from .models import Partner, PartnerAvailability, PartnerEnquiry, ReservationRequest


class AcceptedEnquiryConversionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create_user(
            email="traveller-convert@example.com", password="Strong-passphrase-2026!"
        )
        self.other_customer = User.objects.create_user(
            email="other-convert@example.com", password="Strong-passphrase-2026!"
        )
        self.owner = User.objects.create_user(
            email="partner-convert@example.com", password="Strong-passphrase-2026!"
        )
        self.partner = Partner.objects.create(
            owner=self.owner,
            name="Garden Route Stay",
            slug="garden-route-stay",
            category=Partner.Category.ACCOMMODATION,
            gallery_status=Partner.ApprovalStatus.APPROVED,
            enquiry_status=Partner.ApprovalStatus.APPROVED,
            booking_status=Partner.ApprovalStatus.APPROVED,
        )
        self.start = date.today() + timedelta(days=30)
        self.end = self.start + timedelta(days=2)
        for offset in range(2):
            PartnerAvailability.objects.create(
                partner=self.partner,
                date=self.start + timedelta(days=offset),
                capacity=8,
                booked_count=0,
                is_open=True,
                price_per_guest="850.00",
                currency="ZAR",
            )
        self.enquiry = PartnerEnquiry.objects.create(
            customer=self.customer,
            partner=self.partner,
            message="We would like to arrange a family getaway.",
            requested_start_date=self.start,
            requested_end_date=self.end,
            status=PartnerEnquiry.Status.ACCEPTED,
            partner_response="We can accommodate your requested dates.",
        )
        self.client.force_authenticate(user=self.customer)

    def test_accepted_enquiry_converts_to_separate_pending_reservation(self):
        response = self.client.post(
            f"/api/v1/partners/enquiries/{self.enquiry.pk}/convert/",
            {"guests": 4},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        reservation = ReservationRequest.objects.get(pk=response.data["reservation"]["id"])
        self.assertEqual(reservation.status, ReservationRequest.Status.PENDING)
        self.assertEqual(reservation.guests, 4)
        self.assertEqual(reservation.partner, self.partner)
        self.enquiry.refresh_from_db()
        self.assertEqual(self.enquiry.reservation_request_id, reservation.pk)

    def test_conversion_is_idempotent(self):
        first = self.client.post(
            f"/api/v1/partners/enquiries/{self.enquiry.pk}/convert/",
            {"guests": 2}, format="json",
        )
        second = self.client.post(
            f"/api/v1/partners/enquiries/{self.enquiry.pk}/convert/",
            {"guests": 6}, format="json",
        )
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.data["reservation"]["id"], second.data["reservation"]["id"])
        self.assertEqual(ReservationRequest.objects.count(), 1)

    def test_pending_or_declined_enquiry_cannot_be_converted(self):
        self.enquiry.status = PartnerEnquiry.Status.PENDING
        self.enquiry.save(update_fields=["status"])
        response = self.client.post(
            f"/api/v1/partners/enquiries/{self.enquiry.pk}/convert/",
            {"guests": 2}, format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(ReservationRequest.objects.count(), 0)

    def test_unavailable_dates_are_rechecked_at_conversion(self):
        PartnerAvailability.objects.filter(partner=self.partner).delete()
        response = self.client.post(
            f"/api/v1/partners/enquiries/{self.enquiry.pk}/convert/",
            {"guests": 2}, format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(ReservationRequest.objects.count(), 0)

    def test_customer_cannot_convert_another_customers_enquiry(self):
        self.enquiry.customer = self.other_customer
        self.enquiry.save(update_fields=["customer"])
        response = self.client.post(
            f"/api/v1/partners/enquiries/{self.enquiry.pk}/convert/",
            {"guests": 2}, format="json",
        )
        self.assertEqual(response.status_code, 404)
