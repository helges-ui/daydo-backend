from django.urls import reverse
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Family, Role, User, UserRole


class MapboxTokenViewTests(APITestCase):
    def setUp(self):
        self.family = Family.objects.create(name="Test Family")
        self.parent_role = Role.objects.create(key="PARENT", name="Parent")
        self.user = User.objects.create_user(
            username="parent_user",
            email="parent@example.com",
            password="password123",
            first_name="Parent",
            last_name="User",
            family=self.family,
            role="PARENT",
        )
        UserRole.objects.create(user=self.user, role=self.parent_role)
        self.url = reverse("daydo:mapbox-token")

    @override_settings(MAPBOX_PUBLIC_TOKEN="pk.test-token")
    def test_returns_token_for_authenticated_user(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"token": "pk.test-token"})

    @override_settings(MAPBOX_PUBLIC_TOKEN="")
    def test_returns_503_when_token_missing(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(
            response.data.get("detail"),
            "Mapbox token is not configured on the server.",
        )

    def test_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
