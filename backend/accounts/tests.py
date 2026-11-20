from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

User = get_user_model()


class CustomerAccountApiTests(APITestCase):
    def test_customer_can_register_and_password_is_not_returned(self):
        response = self.client.post("/api/v1/accounts/register/", {
            "email": "traveller@example.com",
            "first_name": "Travel",
            "last_name": "Guest",
            "password": "Strong-Passphrase-2026!",
            "password_confirm": "Strong-Passphrase-2026!",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["role"], User.Role.CUSTOMER)
        self.assertNotIn("password", response.data)
        self.assertTrue(User.objects.get(email="traveller@example.com").check_password("Strong-Passphrase-2026!"))

    def test_registration_rejects_mismatched_passwords(self):
        response = self.client.post("/api/v1/accounts/register/", {
            "email": "traveller@example.com",
            "password": "Strong-Passphrase-2026!",
            "password_confirm": "Different-Passphrase-2026!",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(email="traveller@example.com").exists())

    def test_customer_can_login_and_read_own_account(self):
        User.objects.create_user(email="guest@example.com", password="Strong-Passphrase-2026!")
        login = self.client.post("/api/v1/accounts/token/", {
            "email": "guest@example.com",
            "password": "Strong-Passphrase-2026!",
        }, format="json")
        self.assertEqual(login.status_code, status.HTTP_200_OK)
        self.assertIn("access", login.data)
        self.assertIn("refresh", login.data)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        profile = self.client.get("/api/v1/accounts/me/")
        self.assertEqual(profile.status_code, status.HTTP_200_OK)
        self.assertEqual(profile.data["email"], "guest@example.com")

    def test_account_profile_requires_authentication(self):
        response = self.client.get("/api/v1/accounts/me/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
