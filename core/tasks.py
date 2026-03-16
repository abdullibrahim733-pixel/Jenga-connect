import logging
from io import BytesIO

from celery import shared_task
from django.core.files.base import ContentFile

from .models import Product

logger = logging.getLogger(__name__)

ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}
MAX_IMAGE_SIZE = (600, 600)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def process_product_image(self, product_id):
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        logger.warning("Product %s not found for image processing", product_id)
        return

    if not product.image:
        return

    try:
        from PIL import Image, ImageOps, UnidentifiedImageError
    except Exception:
        logger.exception("Pillow not available for image processing")
        return

    try:
        image_field = product.image
        if not hasattr(image_field, "path") and not image_field.name:
            return

        image_field.open("rb")
        with Image.open(image_field) as img:
            img = ImageOps.exif_transpose(img)
            if img.format not in ALLOWED_IMAGE_FORMATS:
                logger.warning(
                    "Unsupported image format %s for product %s",
                    img.format,
                    product_id,
                )
                return

            if img.height > MAX_IMAGE_SIZE[1] or img.width > MAX_IMAGE_SIZE[0]:
                img.thumbnail(MAX_IMAGE_SIZE)

            buffer = BytesIO()
            img.save(buffer, format=img.format)
            buffer.seek(0)
            image_field.save(image_field.name, ContentFile(buffer.read()), save=False)

        product.save(update_fields=["image"])
    except (FileNotFoundError, UnidentifiedImageError, OSError) as exc:
        logger.warning("Image processing failed for %s: %s", product_id, exc)
    finally:
        try:
            image_field.close()
        except Exception:
            pass

