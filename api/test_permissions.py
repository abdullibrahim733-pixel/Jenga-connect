import pytest
from decimal import Decimal
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from core.models import Profile, HardwareStore, Product, Order


@pytest.mark.django_db
def test_order_queryset_scoped_to_fundi():
    fundi_user = User.objects.create_user(username="255700002000", password="pass1234")
    fundi_profile = Profile.objects.create(
        user=fundi_user,
        phone="255700002000",
        role="fundi",
        full_name="Fundi User",
        area="Arusha CBD",
    )
    hardware_user = User.objects.create_user(
        username="255700002001", password="pass1234"
    )
    hardware_profile = Profile.objects.create(
        user=hardware_user,
        phone="255700002001",
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
    Order.objects.create(
        fundi=fundi_profile,
        store=store,
        delivery_area="Arusha CBD",
        delivery_address_note="Near the clock tower",
        status="pending",
        payment_status="unpaid",
        subtotal_hardware=Decimal("10000"),
        commission_total=Decimal("0"),
        grand_total=Decimal("10000"),
    )

    client = APIClient()
    client.force_authenticate(user=fundi_user)
    response = client.get("/api/orders/")
    assert response.status_code == 200
    assert response.data["count"] == 1


@pytest.mark.django_db
def test_place_order_forbidden_for_other_user():
    fundi_user = User.objects.create_user(username="255700002100", password="pass1234")
    fundi_profile = Profile.objects.create(
        user=fundi_user,
        phone="255700002100",
        role="fundi",
        full_name="Fundi User",
        area="Arusha CBD",
    )
    other_user = User.objects.create_user(username="255700002101", password="pass1234")
    other_profile = Profile.objects.create(
        user=other_user,
        phone="255700002101",
        role="fundi",
        full_name="Other Fundi",
        area="Arusha CBD",
    )
    hardware_user = User.objects.create_user(
        username="255700002102", password="pass1234"
    )
    hardware_profile = Profile.objects.create(
        user=hardware_user,
        phone="255700002102",
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
    client.force_authenticate(user=other_user)
    response = client.post(
        "/api/orders/place_order/",
        data={
            "fundi_id": str(fundi_profile.id),
            "delivery_area": "Arusha CBD",
            "items": [{"product_id": str(product.id), "quantity": 1}],
        },
        format="json",
    )
    assert response.status_code == 403
