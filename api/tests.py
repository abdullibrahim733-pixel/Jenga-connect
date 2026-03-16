import pytest
from decimal import Decimal
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from core.models import Profile, HardwareStore, Product, Order


@pytest.mark.django_db
def test_health_check_ok():
    client = APIClient()
    response = client.get("/api/health/")
    assert response.status_code in (200, 503)
    assert "status" in response.data


@pytest.mark.django_db
def test_place_order_creates_order_and_items():
    fundi_user = User.objects.create_user(username="255700000111", password="pass1234")
    fundi_profile = Profile.objects.create(
        user=fundi_user,
        phone="255700000111",
        role="fundi",
        full_name="Fundi User",
        area="Arusha CBD",
    )

    hardware_user = User.objects.create_user(
        username="255700000222", password="pass1234"
    )
    hardware_profile = Profile.objects.create(
        user=hardware_user,
        phone="255700000222",
        role="hardware",
        full_name="Hardware User",
        area="Arusha CBD",
    )
    store = HardwareStore.objects.create(
        owner=hardware_profile, name="Store One", area="Arusha CBD"
    )
    product = Product.objects.create(
        store=store,
        category="cement",
        name="Simba cement 42.5r",
        unit="bag",
        hardware_price_per_unit=Decimal("15000"),
        active=True,
    )

    client = APIClient()
    client.force_authenticate(user=fundi_user)
    response = client.post(
        "/api/orders/place_order/",
        data={
            "fundi_id": str(fundi_profile.id),
            "delivery_area": "Arusha CBD",
            "delivery_address_note": "Near the clock tower",
            "items": [{"product_id": str(product.id), "quantity": 2}],
        },
        format="json",
    )

    assert response.status_code == 201
    order = Order.objects.get(id=response.data["id"])
    assert order.grand_total == Decimal("30000")
    assert order.items.count() == 1


@pytest.mark.django_db
def test_place_order_rejects_unknown_product():
    fundi_user = User.objects.create_user(username="255700000333", password="pass1234")
    fundi_profile = Profile.objects.create(
        user=fundi_user,
        phone="255700000333",
        role="fundi",
        full_name="Fundi User",
        area="Arusha CBD",
    )

    client = APIClient()
    client.force_authenticate(user=fundi_user)
    response = client.post(
        "/api/orders/place_order/",
        data={
            "fundi_id": str(fundi_profile.id),
            "delivery_area": "Arusha CBD",
            "items": [{"product_id": "00000000-0000-0000-0000-000000000000", "quantity": 1}],
        },
        format="json",
    )

    assert response.status_code == 400
