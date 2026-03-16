from decimal import Decimal
import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from core.models import Profile, HardwareStore, Product, Order


@pytest.fixture
def fundi_user(db):
    user = User.objects.create_user(username="255700010000", password="pass1234")
    profile = Profile.objects.create(
        user=user,
        phone="255700010000",
        role="fundi",
        full_name="Fundi User",
        area="Arusha CBD",
    )
    return user, profile


@pytest.fixture
def hardware_user(db):
    user = User.objects.create_user(username="255700010001", password="pass1234")
    profile = Profile.objects.create(
        user=user,
        phone="255700010001",
        role="hardware",
        full_name="Hardware User",
        area="Arusha CBD",
    )
    store = HardwareStore.objects.create(
        owner=profile, name="Store One", area="Arusha CBD"
    )
    return user, profile, store


@pytest.fixture
def admin_user(db):
    user = User.objects.create_user(username="255700010002", password="pass1234")
    profile = Profile.objects.create(
        user=user,
        phone="255700010002",
        role="admin",
        full_name="Admin User",
        area="All",
    )
    return user, profile


@pytest.mark.django_db
def test_home_and_product_detail(client, hardware_user):
    _, _, store = hardware_user
    product = Product.objects.create(
        store=store,
        category="cement",
        name="Simba cement 42.5r",
        unit="bag",
        hardware_price_per_unit=Decimal("15000"),
        active=True,
    )

    response = client.get(reverse("home"))
    assert response.status_code == 200

    detail = client.get(reverse("product_detail", kwargs={"pk": product.id}))
    assert detail.status_code == 200


@pytest.mark.django_db
def test_login_and_register_validation(client):
    response = client.post(reverse("login"), data={"phone": "", "password": ""})
    assert response.status_code == 200

    response = client.post(
        reverse("register"),
        data={
            "full_name": "Test User",
            "phone": "invalid",
            "password": "pass1234",
            "role": "fundi",
            "area": "Arusha CBD",
        },
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_dashboard_fundi_and_hardware_views(client, fundi_user, hardware_user):
    fundi, _ = fundi_user
    hardware, _, store = hardware_user
    client.force_login(fundi)
    response = client.get(reverse("dashboard"))
    assert response.status_code == 200

    client.force_login(hardware)
    response = client.get(reverse("dashboard"))
    assert response.status_code == 200

    product = Product.objects.create(
        store=store,
        category="cement",
        name="Simba cement 42.5r",
        unit="bag",
        hardware_price_per_unit=Decimal("15000"),
        active=True,
    )
    response = client.get(reverse("dashboard"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_add_product_and_delete_product(client, hardware_user):
    hardware, _, store = hardware_user
    client.force_login(hardware)

    response = client.post(
        reverse("add_product"),
        data={
            "category": "cement",
            "name": "Simba cement 42.5r",
            "price": "15000",
            "unit": "bag",
        },
    )
    assert response.status_code == 302
    product = Product.objects.get(store=store)

    delete_url = reverse("delete_product", kwargs={"product_id": product.id})
    response = client.post(delete_url)
    assert response.status_code == 302


@pytest.mark.django_db
def test_manage_order_and_manage_page(client, hardware_user, admin_user, fundi_user):
    hardware, _, store = hardware_user
    fundi, fundi_profile = fundi_user
    client.force_login(hardware)

    order = Order.objects.create(
        fundi=fundi_profile,
        store=store,
        delivery_area="Arusha CBD",
        delivery_address_note="Near clock tower",
        status="pending",
        payment_status="unpaid",
        subtotal_hardware=Decimal("10000"),
        commission_total=Decimal("0"),
        grand_total=Decimal("10000"),
    )
    response = client.post(
        reverse("manage_order", kwargs={"order_id": order.id, "action": "confirm"})
    )
    assert response.status_code == 302

    admin, _ = admin_user
    client.force_login(admin)
    response = client.get(reverse("manage_page"))
    assert response.status_code == 200

    response = client.post(
        reverse("manage_page"),
        data={
            "action": "add_hardware",
            "phone": "0712345678",
            "full_name": "New Hardware",
            "store_name": "New Store",
            "area": "Arusha CBD",
            "password": "pass1234",
        },
    )
    assert response.status_code == 302


@pytest.mark.django_db
def test_payment_status_flow(client, fundi_user, hardware_user):
    fundi, fundi_profile = fundi_user
    _, _, store = hardware_user
    product = Product.objects.create(
        store=store,
        category="cement",
        name="Simba cement 42.5r",
        unit="bag",
        hardware_price_per_unit=Decimal("15000"),
        active=True,
    )
    client.force_login(fundi)
    response = client.post(
        reverse("checkout"),
        data={
            "product_id": str(product.id),
            "quantity": "1",
            "delivery_area": "Arusha CBD",
            "address_note": "Near clock tower",
        },
    )
    assert response.status_code == 302
    order = Order.objects.latest("created_at")

    response = client.post(
        reverse("initiate_payment", kwargs={"order_id": order.id}),
        data={"method": "mpesa", "phone": "0712345678"},
    )
    assert response.status_code == 200

    payment = order.payment_record
    status_response = client.get(
        reverse("payment_status", kwargs={"payment_id": payment.id})
    )
    assert status_response.status_code == 200


@pytest.mark.django_db
def test_map_view(client, hardware_user):
    _, _, store = hardware_user
    store.latitude = -3.0
    store.longitude = 36.0
    store.save(update_fields=["latitude", "longitude"])

    response = client.get(reverse("map_view"))
    assert response.status_code == 200
