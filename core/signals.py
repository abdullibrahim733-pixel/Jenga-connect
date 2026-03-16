import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Product
from .services import enqueue_product_image_processing

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Product)
def schedule_product_image_processing(sender, instance, created, **kwargs):
    update_fields = kwargs.get("update_fields")
    if update_fields is not None and "image" not in update_fields:
        return

    if not instance.image:
        return

    enqueue_product_image_processing(instance.id)

