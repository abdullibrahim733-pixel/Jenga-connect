from decimal import Decimal
import pytest
from django.contrib.auth.models import User

from core.models import Profile, HardwareStore, Product, CommissionSetting
from core.services import (
    latest_commission_per_unit,
    create_order_with_items,
    enqueue_product_image_processing,
)


@pytest.mark.django_db
def test_latest_commission_per_unit_uses_most_recent_active():
    user = User.objects.create_user(username="255700001000", password="pass1234")
    profile = Profile.objects.create(
        user=user,
        phone="255700001000",
        role="hardware",
        full_name="Hardware User",
        area="Arusha CBD",
    )
    store = HardwareStore.objects.create(
        owner=profile, name="Store One", area="Arusha CBD"
    )
    product = Product.objects.create(
        store=store,
        category="cement",
        name="Simba cement 42.5r",
        unit="bag",
        hardware_price_per_unit=Decimal("15000"),
        active=True,
    )

    CommissionSetting.objects.create(
        category="cement",
        unit="bag",
        commission_per_unit=Decimal("200"),
        active=True,
    )
    CommissionSetting.objects.create(
        category="cement",
        unit="bag",
        commission_per_unit=Decimal("300"),
        active=True,
    )

    assert latest_commission_per_unit(product) == Decimal("300")


@pytest.mark.django_db
def test_create_order_with_items_calculates_totals():
    fundi_user = User.objects.create_user(username="255700001111", password="pass1234")
    fundi_profile = Profile.objects.create(
        user=fundi_user,
        phone="255700001111",
        role="fundi",
        full_name="Fundi User",
        area="Arusha CBD",
    )
    hardware_user = User.objects.create_user(
        username="255700001222", password="pass1234"
    )
    hardware_profile = Profile.objects.create(
        user=hardware_user,
        phone="255700001222",
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
    CommissionSetting.objects.create(
        category="cement",
        unit="bag",
        commission_per_unit=Decimal("1000"),
        active=True,
    )

    order = create_order_with_items(
        fundi=fundi_profile,
        delivery_area="Arusha CBD",
        delivery_address_note="Near the clock tower",
        items=[{"product": product, "quantity": 2}],
    )

    order.refresh_from_db()
    assert order.subtotal_hardware == Decimal("30000")
    assert order.commission_total == Decimal("2600")
    assert order.grand_total == Decimal("32600")
    assert order.items.count() == 1


@pytest.mark.django_db
def test_enqueue_product_image_processing_handles_failure(monkeypatch):
    calls = {"count": 0}

    class DummyTask:
        def delay(self, product_id):
            calls["count"] += 1
            raise RuntimeError("queue down")

    monkeypatch.setattr(
        "core.services.process_product_image", DummyTask(), raising=False
    )
    enqueue_product_image_processing("00000000-0000-0000-0000-000000000000")
    assert calls["count"] == 1
