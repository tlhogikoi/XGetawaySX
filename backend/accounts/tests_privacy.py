from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from .privacy_models import PrivacyRequest

User = get_user_model()


class PrivacyRequestApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="traveller@example.com", password="Strong-Passphrase-2026!")
        self.other = User.objects.create_user(email="other@example.com", password="Strong-Passphrase-2026!")
        self.staff = User.objects.create_user(email="staff@example.com", password="Strong-Passphrase-2026!", is_staff=True)

    def test_requests_require_authentication(self):
        response = self.client.get("/api/v1/accounts/privacy-requests/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_can_submit_and_view_own_request(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post("/api/v1/accounts/privacy-requests/", {
            "request_type": "access",
            "description": "Please provide a copy of my account information."
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], PrivacyRequest.Status.SUBMITTED)
        self.assertEqual(len(response.data["events"]), 1)
        self.assertEqual(self.client.get("/api/v1/accounts/privacy-requests/").data[0]["reference"], response.data["reference"])

    def test_user_cannot_view_another_users_request(self):
        obj = PrivacyRequest.objects.create(user=self.other, request_type="access", description="Please provide my account information.")
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"/api/v1/accounts/privacy-requests/{obj.reference}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_can_withdraw_own_submitted_request(self):
        obj = PrivacyRequest.objects.create(user=self.user, request_type="deletion", description="Please review my deletion request.")
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(f"/api/v1/accounts/privacy-requests/{obj.reference}/", {"status": "withdrawn"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        obj.refresh_from_db()
        self.assertEqual(obj.status, PrivacyRequest.Status.WITHDRAWN)
        self.assertEqual(obj.events.count(), 1)

    def test_staff_can_review_and_record_identity_verification(self):
        obj = PrivacyRequest.objects.create(user=self.user, request_type="correction", description="Please correct my profile details.")
        self.client.force_authenticate(user=self.staff)
        response = self.client.patch(f"/api/v1/accounts/privacy-requests/{obj.reference}/", {
            "status": "awaiting_verification",
            "identity_verified": False,
            "staff_note": "Please complete identity checks."
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        obj.refresh_from_db()
        self.assertEqual(obj.status, PrivacyRequest.Status.AWAITING_VERIFICATION)
        self.assertTrue(obj.events.exists())

    def test_regular_user_cannot_mark_request_completed(self):
        obj = PrivacyRequest.objects.create(user=self.user, request_type="access", description="Please provide my account information.")
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(f"/api/v1/accounts/privacy-requests/{obj.reference}/", {"status": "fulfilled"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        obj.refresh_from_db()
        self.assertEqual(obj.status, PrivacyRequest.Status.SUBMITTED)

    def test_staff_can_list_all_requests(self):
        PrivacyRequest.objects.create(user=self.user, request_type="access", description="Please provide my account information.")
        PrivacyRequest.objects.create(user=self.other, request_type="correction", description="Please correct my profile information.")
        self.client.force_authenticate(user=self.staff)
        response = self.client.get("/api/v1/accounts/privacy-requests/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_short_description_is_rejected(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post("/api/v1/accounts/privacy-requests/", {"request_type": "access", "description": "Help"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
