from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .serializers import STUDENT_GROUP_NAME


class StudentAuthenticationAPITests(TestCase):
    registration_data = {
        "username": "student-test",
        "email": "student@example.test",
        "password": "HeatShield-Student-Password-2026!",
        "confirm_password": "HeatShield-Student-Password-2026!",
    }

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.csrf_client = APIClient(enforce_csrf_checks=True)

    def get_csrf_token(self, client=None):
        client = client or self.csrf_client
        response = client.get(reverse("auth-csrf"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("csrftoken", client.cookies)
        return response.data["csrfToken"]

    def register(self, data=None, client=None):
        client = client or self.client
        return client.post(
            reverse("auth-register"),
            data or self.registration_data,
            format="json",
        )

    def login(self, username="student-test", password=None, client=None):
        client = client or self.csrf_client
        csrf_token = self.get_csrf_token(client)
        return client.post(
            reverse("auth-login"),
            {
                "username": username,
                "password": password or self.registration_data["password"],
            },
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

    def test_successful_registration_creates_student_with_hashed_password(self):
        response = self.register()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            set(response.data["user"]),
            {"id", "username", "email", "role"},
        )
        self.assertEqual(response.data["user"]["role"], "student")
        self.assertNotIn("password", response.data["user"])
        self.assertNotIn("password_hash", response.data["user"])

        user = get_user_model().objects.get(username="student-test")
        self.assertTrue(user.check_password(self.registration_data["password"]))
        self.assertNotEqual(user.password, self.registration_data["password"])
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.groups.filter(name=STUDENT_GROUP_NAME).exists())

    def test_duplicate_username_is_rejected(self):
        self.register()
        response = self.register(
            {
                **self.registration_data,
                "email": "another@example.test",
            }
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("username", response.data["error"]["details"])

    def test_duplicate_email_is_rejected_case_insensitively(self):
        self.register()
        response = self.register(
            {
                **self.registration_data,
                "username": "another-student",
                "email": self.registration_data["email"].upper(),
            }
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data["error"]["details"])

    def test_invalid_email_is_rejected(self):
        response = self.register(
            {**self.registration_data, "email": "not-an-email"}
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data["error"]["details"])

    def test_password_mismatch_is_rejected(self):
        response = self.register(
            {**self.registration_data, "confirm_password": "different-password"}
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("confirm_password", response.data["error"]["details"])

    def test_weak_password_is_rejected_by_django_validators(self):
        response = self.register(
            {
                **self.registration_data,
                "password": "123",
                "confirm_password": "123",
            }
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.data["error"]["details"])
        self.assertFalse(get_user_model().objects.filter(username="student-test").exists())

    def test_registration_rejects_privilege_assignment_fields(self):
        privilege_fields = ("is_staff", "is_superuser", "role", "groups")
        for field in privilege_fields:
            with self.subTest(field=field):
                response = self.register(
                    {
                        **self.registration_data,
                        field: True if field.startswith("is_") else "admin",
                    }
                )
                self.assertEqual(response.status_code, 400)
                self.assertFalse(
                    get_user_model().objects.filter(username="student-test").exists()
                )

    def test_successful_login_establishes_a_session(self):
        self.register()

        response = self.login()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["username"], "student-test")
        self.assertIn("sessionid", self.csrf_client.cookies)
        me_response = self.csrf_client.get(reverse("auth-me"))
        self.assertEqual(me_response.status_code, 200)
        self.assertEqual(me_response.data["user"]["username"], "student-test")

    def test_invalid_login_uses_same_message_for_unknown_user_and_wrong_password(self):
        self.register()
        wrong_password = self.login(password="incorrect-password")
        unknown_user = self.login(username="no-such-user")

        self.assertEqual(wrong_password.status_code, 401)
        self.assertEqual(unknown_user.status_code, 401)
        self.assertEqual(
            wrong_password.data["error"]["message"],
            unknown_user.data["error"]["message"],
        )

    def test_authenticated_current_user_returns_safe_profile(self):
        self.register()
        self.login()

        response = self.csrf_client.get(reverse("auth-me"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["role"], "student")
        self.assertNotIn("password", response.data["user"])
        self.assertNotIn("is_superuser", response.data["user"])
        self.assertNotIn("is_staff", response.data["user"])

    def test_anonymous_current_user_is_rejected(self):
        response = self.csrf_client.get(reverse("auth-me"))

        self.assertEqual(response.status_code, 401)

    def test_logout_destroys_session_and_rejects_later_requests(self):
        self.register()
        login_response = self.login()
        csrf_token = login_response.data["csrfToken"]
        response = self.csrf_client.post(
            reverse("auth-logout"),
            {},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["detail"], "Successfully logged out.")
        self.assertEqual(self.csrf_client.get(reverse("auth-me")).status_code, 401)

    def test_login_and_logout_require_csrf_tokens(self):
        self.register()
        login_without_csrf = self.csrf_client.post(
            reverse("auth-login"),
            {
                "username": self.registration_data["username"],
                "password": self.registration_data["password"],
            },
            format="json",
        )
        self.assertEqual(login_without_csrf.status_code, 403)

        login_response = self.login()
        self.assertEqual(login_response.status_code, 200)
        logout_without_csrf = self.csrf_client.post(
            reverse("auth-logout"),
            {},
            format="json",
        )
        self.assertEqual(logout_without_csrf.status_code, 403)

    def test_registration_requires_csrf_token(self):
        response = self.register(client=self.csrf_client)
        self.assertEqual(response.status_code, 403)

        csrf_token = self.get_csrf_token()
        response = self.csrf_client.post(
            reverse("auth-register"),
            self.registration_data,
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(response.status_code, 201)

    def test_login_is_rate_limited(self):
        csrf_token = self.get_csrf_token()
        payload = {"username": "unknown", "password": "wrong"}

        responses = [
            self.csrf_client.post(
                reverse("auth-login"),
                payload,
                format="json",
                HTTP_X_CSRFTOKEN=csrf_token,
            )
            for _ in range(6)
        ]

        self.assertTrue(all(response.status_code == 401 for response in responses[:5]))
        self.assertEqual(responses[5].status_code, 429)
