import os

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from core.models import Profile


class Command(BaseCommand):
    help = "Create or update the admin user from environment variables."

    def handle(self, *args, **options):
        username = os.getenv("ADMIN_USERNAME")
        password = os.getenv("ADMIN_PASSWORD")
        phone = os.getenv("ADMIN_PHONE", "255000000000")
        full_name = os.getenv("ADMIN_FULL_NAME", "Master Admin")

        if not username or not password:
            self.stdout.write("ADMIN_USERNAME/ADMIN_PASSWORD not set. Skipping.")
            return

        user, created = User.objects.get_or_create(username=username)
        if created:
            user.set_password(password)
            user.is_staff = True
            user.is_superuser = True
            user.save()
        else:
            user.set_password(password)
            user.is_staff = True
            user.is_superuser = True
            user.save(update_fields=["password", "is_staff", "is_superuser"])

        profile, _ = Profile.objects.get_or_create(
            user=user,
            defaults={
                "phone": phone,
                "role": "admin",
                "full_name": full_name,
                "area": "All",
            },
        )
        if profile.role != "admin":
            profile.role = "admin"
            profile.save(update_fields=["role"])

        self.stdout.write(f"Admin user ready: {username}")
