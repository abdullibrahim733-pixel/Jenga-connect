from io import BytesIO
import sys
import types
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from django.contrib.auth.models import User

from core.models import Profile, HardwareStore, Product
from core.tasks import process_product_image


@pytest.mark.django_db
def test_process_product_image_resizes_without_pillow(tmp_path, monkeypatch, settings):
    settings.MEDIA_ROOT = tmp_path

    user = User.objects.create_user(username="255700020000", password="pass1234")
    profile = Profile.objects.create(
        user=user,
        phone="255700020000",
        role="hardware",
        full_name="Hardware User",
        area="Arusha CBD",
    )
    store = HardwareStore.objects.create(
        owner=profile, name="Store One", area="Arusha CBD"
    )

    dummy_content = BytesIO(b"fake-image-bytes").getvalue()
    upload = SimpleUploadedFile("test.jpg", dummy_content, content_type="image/jpeg")
    product = Product.objects.create(
        store=store,
        category="cement",
        name="Simba cement 42.5r",
        unit="bag",
        hardware_price_per_unit="15000",
        active=True,
        image=upload,
    )

    class DummyImage:
        format = "JPEG"
        height = 800
        width = 800

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def thumbnail(self, size):
            self.height, self.width = size[1], size[0]

        def save(self, buffer, format=None):
            buffer.write(b"resized")

    pil_module = types.SimpleNamespace()
    pil_module.UnidentifiedImageError = Exception
    pil_module.Image = types.SimpleNamespace(open=lambda f: DummyImage())
    pil_module.ImageOps = types.SimpleNamespace(exif_transpose=lambda img: img)

    monkeypatch.setitem(sys.modules, "PIL", pil_module)

    process_product_image(product.id)
    product.refresh_from_db()
    assert product.image.name
