import pytest
from decimal import Decimal
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from core.models import Profile, HardwareStore, Notification


@pytest.mark.django_db
def test_nearby_hardware_stores_returns_sorted_results():
    user = User.objects.create_user(username="255700030000", password="pass1234")
    profile = Profile.objects.create(
        user=user,
        phone="255700030000",
        role="hardware",
        full_name="Hardware User",
        area="Arusha CBD",
    )
    store = HardwareStore.objects.create(
        owner=profile,
        name="Store One",
        area="Arusha CBD",
        latitude=-3.0,
        longitude=36.0,
        active=True,
    )

    client = APIClient()
    response = client.get(
        "/api/hardware_stores/nearby/?lat=-3.0&lng=36.0&radius=10"
    )
    assert response.status_code == 200
    assert response.data[0]["id"] == str(store.id)


@pytest.mark.django_db
def test_nearby_hardware_stores_requires_lat_lng():
    client = APIClient()
    response = client.get("/api/hardware_stores/nearby/")
    assert response.status_code == 400


@pytest.mark.django_db
def test_unread_notifications_count():
    user = User.objects.create_user(username="255700030001", password="pass1234")
    profile = Profile.objects.create(
        user=user,
        phone="255700030001",
        role="fundi",
        full_name="Fundi User",
        area="Arusha CBD",
    )
    Notification.objects.create(
        user=profile,
        type="ORDER_CREATED",
        title="New Order",
        message="New order created",
        order_id=None,
        is_read=False,
    )

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get("/api/notifications/unread_count/")
    assert response.status_code == 200
    assert response.data["unread_count"] == 1
