import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from core.models import Profile, HardwareStore


@pytest.mark.django_db
def test_admin_dashboard_access_control(client):
    user = User.objects.create_user(username="255700040000", password="pass1234")
    profile = Profile.objects.create(
        user=user,
        phone="255700040000",
        role="fundi",
        full_name="Fundi User",
        area="Arusha CBD",
    )
    client.force_login(user)
    response = client.get(reverse("admin_dashboard"))
    assert response.status_code == 302

    admin_user = User.objects.create_user(username="255700040001", password="pass1234")
    Profile.objects.create(
        user=admin_user,
        phone="255700040001",
        role="admin",
        full_name="Admin User",
        area="All",
    )
    client.force_login(admin_user)
    response = client.get(reverse("admin_dashboard"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_admin_dashboard_user_and_store_actions(client):
    admin_user = User.objects.create_user(username="255700040002", password="pass1234")
    Profile.objects.create(
        user=admin_user,
        phone="255700040002",
        role="admin",
        full_name="Admin User",
        area="All",
    )
    client.force_login(admin_user)

    response = client.post(
        reverse("admin_dashboard"),
        data={
            "action": "add_user",
            "phone": "0712345678",
            "full_name": "Hardware Owner",
            "password": "pass1234",
            "area": "Arusha CBD",
            "role": "hardware",
            "store_name": "New Store",
        },
    )
    assert response.status_code == 302

    store = HardwareStore.objects.get(name="New Store")
    response = client.post(
        reverse("admin_dashboard"),
        data={
            "action": "toggle_store",
            "store_id": str(store.id),
            "active": "on",
        },
    )
    assert response.status_code == 302
