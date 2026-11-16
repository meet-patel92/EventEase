from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from django.urls import reverse

from accounts.models import User


class AuthenticationAPITest(APITestCase):
    def setUp(self):
        self.client = APIClient()

    def test_public_registration_cannot_assign_admin_role(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "newcustomer",
                "email": "newcustomer@example.test",
                "password": "Sufficient-Pass-908!",
                "password_confirm": "Sufficient-Pass-908!",
                "role": "ADMIN",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="newcustomer@example.test")
        self.assertEqual(user.role, User.Role.CUSTOMER)
        self.assertNotEqual(user.password, "Sufficient-Pass-908!")
        self.assertTrue(user.check_password("Sufficient-Pass-908!"))

    def test_public_registration_applies_configured_password_validators(self):
        weak_passwords = (
            "password123",
            "12345678",
            "newcustomer",
        )

        for index, password in enumerate(weak_passwords):
            with self.subTest(password_category=index):
                response = self.client.post(
                    reverse("register"),
                    {
                        "username": "newcustomer",
                        "email": f"weak{index}@example.test",
                        "password": password,
                        "password_confirm": password,
                    },
                    format="json",
                )

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("password", response.data)
                self.assertFalse(User.objects.filter(email=f"weak{index}@example.test").exists())

    def test_login_token_authenticates_profile_request(self):
        user = User.objects.create_user(
            username="customer",
            email="customer@example.test",
            password="Sufficient-Pass-908!",
            role=User.Role.CUSTOMER,
        )
        login = self.client.post(
            reverse("login"),
            {"email": user.email, "password": "Sufficient-Pass-908!"},
            format="json",
        )
        self.assertEqual(login.status_code, status.HTTP_200_OK)
        self.assertIn("access", login.data["tokens"])

        profile = self.client.get(
            reverse("profile"),
            HTTP_AUTHORIZATION=f"Bearer {login.data['tokens']['access']}",
        )

        self.assertEqual(profile.status_code, status.HTTP_200_OK)
        self.assertEqual(profile.data["id"], user.id)

    def test_invalid_login_is_rejected(self):
        User.objects.create_user(
            username="customer",
            email="customer@example.test",
            password="Sufficient-Pass-908!",
            role=User.Role.CUSTOMER,
        )
        response = self.client.post(
            reverse("login"),
            {"email": "customer@example.test", "password": "wrong-password"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
