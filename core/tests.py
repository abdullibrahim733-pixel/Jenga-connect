from decimal import Decimal
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Profile, HardwareStore, Product, Order
from .services import normalize_phone_number, create_order_with_items
import pytest


class CheckoutFlowTests(TestCase):
    def setUp(self):
        self.fundi_user = User.objects.create_user(username='255700000001', password='pass1234')
        self.fundi_profile = Profile.objects.create(
            user=self.fundi_user,
            phone='255700000001',
            role='fundi',
            full_name='Fundi User',
            area='Arusha CBD',
        )

        self.hardware_user = User.objects.create_user(username='255700000002', password='pass1234')
        self.hardware_profile = Profile.objects.create(
            user=self.hardware_user,
            phone='255700000002',
            role='hardware',
            full_name='Hardware User',
            area='Arusha CBD',
        )
        self.store = HardwareStore.objects.create(
            owner=self.hardware_profile,
            name='Store One',
            area='Arusha CBD',
        )
        self.product = Product.objects.create(
            store=self.store,
            category='cement',
            name='simba    cement   42.5r',
            unit='bag',
            hardware_price_per_unit=Decimal('15000'),
            active=True,
        )

    def test_product_name_is_normalized_on_save(self):
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, 'Simba Cement 42.5R')

    def test_checkout_redirects_to_initiate_payment(self):
        self.client.login(username='255700000001', password='pass1234')

        response = self.client.post(
            reverse('checkout'),
            data={
                'product_id': str(self.product.id),
                'quantity': '2',
                'delivery_area': 'Arusha CBD',
                'address_note': 'Near clock tower',
            },
        )

        order = Order.objects.latest('created_at')
        expected_url = reverse('initiate_payment', kwargs={'order_id': order.id})
        self.assertRedirects(response, expected_url)

    def test_initiate_payment_url_reverses_with_uuid_order_id(self):
        order = Order.objects.create(
            fundi=self.fundi_profile,
            store=self.store,
            delivery_area='Arusha CBD',
            delivery_address_note='Near clock tower',
            status='pending',
            payment_status='unpaid',
            subtotal_hardware=Decimal('10000'),
            commission_total=Decimal('0'),
            grand_total=Decimal('10000'),
        )
        self.assertEqual(
            reverse('initiate_payment', kwargs={'order_id': order.id}),
            f'/payment/initiate/{order.id}/'
        )

    def test_manage_order_requires_post(self):
        order = Order.objects.create(
            fundi=self.fundi_profile,
            store=self.store,
            delivery_area='Arusha CBD',
            delivery_address_note='Near clock tower',
            status='pending',
            payment_status='unpaid',
            subtotal_hardware=Decimal('10000'),
            commission_total=Decimal('0'),
            grand_total=Decimal('10000'),
        )
        self.client.login(username='255700000002', password='pass1234')
        url = reverse('manage_order', kwargs={'order_id': order.id, 'action': 'confirm'})

        get_response = self.client.get(url)
        self.assertEqual(get_response.status_code, 405)

        post_response = self.client.post(url)
        self.assertEqual(post_response.status_code, 302)
        order.refresh_from_db()
        self.assertEqual(order.status, 'confirmed')


@pytest.mark.django_db
def test_normalize_phone_number_accepts_local_and_international():
    assert normalize_phone_number("0712345678") == "255712345678"
    assert normalize_phone_number("255712345678") == "255712345678"
    assert normalize_phone_number("+255 712 345 678") == "255712345678"
    assert normalize_phone_number("invalid") == ""


@pytest.mark.django_db
def test_create_order_with_items_requires_single_store():
    fundi_user = User.objects.create_user(username="255700000444", password="pass1234")
    fundi_profile = Profile.objects.create(
        user=fundi_user,
        phone="255700000444",
        role="fundi",
        full_name="Fundi User",
        area="Arusha CBD",
    )
    hardware_user = User.objects.create_user(
        username="255700000555", password="pass1234"
    )
    hardware_profile = Profile.objects.create(
        user=hardware_user,
        phone="255700000555",
        role="hardware",
        full_name="Hardware User",
        area="Arusha CBD",
    )
    store_a = HardwareStore.objects.create(
        owner=hardware_profile, name="Store A", area="Arusha CBD"
    )
    store_b = HardwareStore.objects.create(
        owner=hardware_profile, name="Store B", area="Arusha CBD"
    )
    product_a = Product.objects.create(
        store=store_a,
        category="cement",
        name="Simba cement 42.5r",
        unit="bag",
        hardware_price_per_unit=Decimal("15000"),
        active=True,
    )
    product_b = Product.objects.create(
        store=store_b,
        category="cement",
        name="Tembo cement 42.5r",
        unit="bag",
        hardware_price_per_unit=Decimal("15000"),
        active=True,
    )

    with pytest.raises(ValueError):
        create_order_with_items(
            fundi=fundi_profile,
            delivery_area="Arusha CBD",
            delivery_address_note="Near the clock tower",
            items=[
                {"product": product_a, "quantity": 1},
                {"product": product_b, "quantity": 1},
            ],
        )
