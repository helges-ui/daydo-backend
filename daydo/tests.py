from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Family, Role, User, UserRole, SharingStatus, Location


SQLITE_TEST_DB = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}


@override_settings(DATABASES=SQLITE_TEST_DB)
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


@override_settings(DATABASES=SQLITE_TEST_DB)
class FamilyLocationViewTests(APITestCase):
    def setUp(self):
        self.family = Family.objects.create(name="Test Family")
        self.parent_role = Role.objects.create(key="PARENT", name="Parent")
        self.user = User.objects.create_user(
            username="parent_primary",
            email="primary@example.com",
            password="password123",
            first_name="Primary",
            last_name="Parent",
            family=self.family,
            role="PARENT",
        )
        UserRole.objects.create(user=self.user, role=self.parent_role)
        SharingStatus.objects.create(
            user=self.user,
            is_sharing_live=True,
            sharing_type="always",
        )

        self.stale_user = User.objects.create_user(
            username="parent_secondary",
            email="secondary@example.com",
            password="password123",
            first_name="Secondary",
            last_name="Parent",
            family=self.family,
            role="PARENT",
        )
        UserRole.objects.create(user=self.stale_user, role=self.parent_role)
        SharingStatus.objects.create(
            user=self.stale_user,
            is_sharing_live=True,
            sharing_type="always",
        )

        self.url = reverse("daydo:location-family")

    def test_family_locations_include_accuracy_and_stale_flag(self):
        self.client.force_authenticate(user=self.user)

        Location.objects.create(
            sharing_user=self.user,
            latitude=50.1109,
            longitude=8.6821,
            accuracy=5.5,
        )
        stale_timestamp = timezone.now() - timedelta(minutes=20)
        stale_location = Location.objects.create(
            sharing_user=self.stale_user,
            latitude=48.1351,
            longitude=11.5820,
            accuracy=15.2,
        )
        Location.objects.filter(id=stale_location.id).update(timestamp=stale_timestamp)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(isinstance(response.data, list))

        data_by_user = {item["user_id"]: item for item in response.data}
        fresh_entry = data_by_user[str(self.user.id)]
        stale_entry = data_by_user[str(self.stale_user.id)]

        self.assertIn("accuracy", fresh_entry)
        self.assertEqual(float(fresh_entry["accuracy"]), 5.5)
        self.assertFalse(fresh_entry.get("is_stale"))

        self.assertIn("accuracy", stale_entry)
        self.assertEqual(float(stale_entry["accuracy"]), 15.2)
        self.assertTrue(stale_entry.get("is_stale"))
