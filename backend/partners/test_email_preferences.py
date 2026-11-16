from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from partners.models import CustomerEmailPreference


class CustomerEmailPreferenceAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="traveller@example.com", password="test-password"
        )

    def test_preferences_default_to_marketing_opt_out(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/v1/partners/email-preferences/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["marketing_opt_in"])
        self.assertTrue(response.data["essential_transactional_emails"])

    def test_customer_can_opt_in_and_out_of_marketing(self):
        self.client.force_authenticate(user=self.user)
        enabled = self.client.patch(
            "/api/v1/partners/email-preferences/",
            {"marketing_opt_in": True},
            format="json",
        )
        self.assertEqual(enabled.status_code, 200)
        self.assertTrue(enabled.data["marketing_opt_in"])

        disabled = self.client.patch(
            "/api/v1/partners/email-preferences/",
            {"marketing_opt_in": False},
            format="json",
        )
        self.assertEqual(disabled.status_code, 200)
        self.assertFalse(disabled.data["marketing_opt_in"])
        self.assertTrue(disabled.data["essential_transactional_emails"])

    def test_preference_endpoint_rejects_non_boolean_consent(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            "/api/v1/partners/email-preferences/",
            {"marketing_opt_in": "yes"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_public_unsubscribe_link_revokes_marketing_consent(self):
        preference = CustomerEmailPreference.objects.create(
            user=self.user, marketing_opt_in=True
        )
        response = self.client.post(
            f"/api/v1/partners/email-unsubscribe/{preference.unsubscribe_token}/"
        )
        self.assertEqual(response.status_code, 200)
        preference.refresh_from_db()
        self.assertFalse(preference.marketing_opt_in)
        self.assertTrue(response.data["essential_transactional_emails"])

    def test_invalid_unsubscribe_token_returns_not_found(self):
        response = self.client.post(
            "/api/v1/partners/email-unsubscribe/00000000-0000-0000-0000-000000000000/"
        )
        self.assertEqual(response.status_code, 404)


class BrandedReservationEmailTests(TestCase):
    def test_transactional_email_is_multipart_and_not_suppressed_by_marketing_opt_out(self):
        from datetime import date, timedelta
        from django.core import mail
        from django.test import override_settings
        from accounts.models import User
        from partners.models import Partner, ReservationRequest, ReservationEmailDelivery
        from partners.reservation_email_notifications import send_reservation_email

        customer = User.objects.create_user(
            email="no-marketing@example.com", password="test-password"
        )
        owner = User.objects.create_user(
            email="partner-owner@example.com", password="test-password"
        )
        CustomerEmailPreference.objects.create(user=customer, marketing_opt_in=False)
        partner = Partner.objects.create(
            owner=owner, name="Blue Mountain Stay",
            category=Partner.Category.ACCOMMODATION,
            gallery_status=Partner.ApprovalStatus.APPROVED,
        )
        reservation = ReservationRequest.objects.create(
            customer=customer, partner=partner,
            start_date=date.today() + timedelta(days=30),
            end_date=date.today() + timedelta(days=32), guests=2,
        )
        delivery = ReservationEmailDelivery.objects.create(
            reservation=reservation, event="reservation_confirmed",
            event_key="test-reservation-confirmed-customer",
            recipient_email=customer.email, recipient_role="customer",
            subject="Your getaway is confirmed",
            body="Your stay at Blue Mountain Stay is confirmed.",
        )
        with override_settings(
            EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
            DEFAULT_FROM_EMAIL="bookings@xgetawaysx.example",
        ):
            result = send_reservation_email(delivery.pk)

        self.assertEqual(result.status, ReservationEmailDelivery.Status.SENT)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [customer.email])
        self.assertEqual(len(mail.outbox[0].alternatives), 1)
        self.assertIn("XGetawaySX", mail.outbox[0].alternatives[0][0])
        self.assertIn("travel through us", mail.outbox[0].alternatives[0][0])
