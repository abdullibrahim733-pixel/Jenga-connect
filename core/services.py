import logging
import re
from decimal import Decimal, InvalidOperation

from django.db import transaction
from .models import CommissionSetting, Order, OrderItem, Notification
from .tasks import process_product_image

logger = logging.getLogger(__name__)

PHONE_255_RE = re.compile(r"^255\d{9}$")
PHONE_0_RE = re.compile(r"^0\d{9}$")


def normalize_phone_number(raw_phone: str) -> str:
    phone = (raw_phone or "").strip().replace(" ", "").replace("-", "").replace("+", "")
    if PHONE_0_RE.match(phone):
        return f"255{phone[1:]}"
    if PHONE_255_RE.match(phone):
        return phone
    return ""


def parse_positive_decimal(raw_value):
    try:
        value = Decimal(str(raw_value))
    except (InvalidOperation, TypeError):
        return None
    if value <= 0:
        return None
    return value


def latest_commission_per_unit(product) -> Decimal:
    commission_setting = (
        CommissionSetting.objects.filter(
            category=product.category, unit=product.unit, active=True
        )
        .order_by("-effective_from")
        .first()
    )
    return commission_setting.commission_per_unit if commission_setting else Decimal("0")


def commission_with_platform_fee(product) -> Decimal:
    base_commission = latest_commission_per_unit(product)
    platform_fee = (product.hardware_price_per_unit * Decimal("0.02")).quantize(
        Decimal("0.01")
    )
    return base_commission + platform_fee


def create_order_with_items(*, fundi, delivery_area, delivery_address_note, items):
    """
    items: list of dicts -> {"product": Product, "quantity": int}
    """
    if not items:
        raise ValueError("items must not be empty")

    store = items[0]["product"].store
    subtotal_hardware = Decimal("0")
    commission_total = Decimal("0")
    order_items_to_create = []

    for item in items:
        product = item["product"]
        quantity = item["quantity"]
        if product.store_id != store.id:
            raise ValueError("All items must belong to the same hardware store.")
        comm_per_unit = commission_with_platform_fee(product)
        hw_price = product.hardware_price_per_unit
        final_price = hw_price + comm_per_unit

        order_items_to_create.append(
            {
                "product": product,
                "quantity_units": quantity,
                "hardware_price_per_unit": hw_price,
                "commission_per_unit": comm_per_unit,
                "final_price_per_unit": final_price,
            }
        )
        subtotal_hardware += hw_price * quantity
        commission_total += comm_per_unit * quantity

    with transaction.atomic():
        order = Order.objects.create(
            fundi=fundi,
            store=store,
            delivery_area=delivery_area,
            delivery_address_note=delivery_address_note,
            status="pending",
            payment_status="unpaid",
            subtotal_hardware=subtotal_hardware,
            commission_total=commission_total,
            grand_total=subtotal_hardware + commission_total,
        )

        for item_payload in order_items_to_create:
            OrderItem.objects.create(order=order, **item_payload)

        Notification.objects.create(
            user=store.owner,
            type="ORDER_CREATED",
            title="New Order Received",
            message=f"You have a new order #{order.short_id} from {fundi.full_name}",
            order=order,
        )

    return order


def enqueue_product_image_processing(product_id):
    try:
        process_product_image.delay(product_id)
    except Exception:
        logger.exception("Failed to enqueue product image processing for %s", product_id)
