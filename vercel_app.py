import os

from backend.wsgi import application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

app = application
