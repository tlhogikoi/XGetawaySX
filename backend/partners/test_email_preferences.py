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
