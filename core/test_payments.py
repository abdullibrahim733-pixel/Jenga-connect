import hmac
import hashlib
import os
import json
import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from core.models import Profile, HardwareStore, Product, Order, Payment
from core.payments import initiate_payment, get_gateway


@pytest.mark.django_db
def test_initiate_payment_returns_payload():
    user = User.objects.create_user(username="255700050000", password="pass1234")
    profile = Profile.objects.create(
        user=user,
        phone="255700050000",
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
        hardware_price_per_unit="15000",
        active=True,
    )
    order = Order.objects.create(
        fundi=profile,
        store=store,
        delivery_area="Arusha CBD",
        delivery_address_note="Near clock tower",
        status="pending",
        payment_status="unpaid",
        subtotal_hardware="15000",
        commission_total="300",
        grand_total="15300",
    )
    payment = Payment.objects.create(
        order=order,
        method="mpesa",
        phone_number="255700050000",
        amount="15300",
        status="initiated",
    )

    payload = initiate_payment(payment)
    assert payload["status"] == "initiated"


@pytest.mark.django_db
def test_payment_webhook_updates_payment(monkeypatch):
    os.environ["PAYMENT_WEBHOOK_SECRET"] = "testsecret"

    user = User.objects.create_user(username="255700050001", password="pass1234")
    profile = Profile.objects.create(
        user=user,
        phone="255700050001",
        role="fundi",
        full_name="Fundi User",
        area="Arusha CBD",
    )
    store = HardwareStore.objects.create(
        owner=profile, name="Store One", area="Arusha CBD"
    )
    order = Order.objects.create(
        fundi=profile,
        store=store,
        delivery_area="Arusha CBD",
        delivery_address_note="Near clock tower",
        status="pending",
        payment_status="unpaid",
        subtotal_hardware="15000",
        commission_total="300",
        grand_total="15300",
    )
    payment = Payment.objects.create(
        order=order,
        method="mpesa",
        phone_number="255700050001",
        amount="15300",
        status="initiated",
    )

    payload = {
        "method": "mpesa",
        "payment_id": str(payment.id),
        "status": "completed",
        "transaction_id": "TXN-123",
    }
    body = json.dumps(payload).encode()
    signature = hmac.new(b"testsecret", body, hashlib.sha256).hexdigest()

    client = APIClient()
    response = client.post(
        "/api/payments/webhook/",
        data=body,
        content_type="application/json",
        HTTP_X_PAYMENT_SIGNATURE=signature,
    )
    assert response.status_code == 200
    payment.refresh_from_db()
    order.refresh_from_db()
    assert payment.status == "completed"
    assert order.payment_status == "paid"
