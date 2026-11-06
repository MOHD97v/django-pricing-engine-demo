"""Local-demo settings. This project is deliberately NOT a production deployment."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get("DEMO_SECRET_KEY", "local-only-demo-not-a-production-secret-change-before-deployment")
DEBUG = os.environ.get("DEMO_DEBUG", "1") == "1"
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver"]
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
    "apps.catalogue.apps.CatalogueConfig",
    "apps.options.apps.OptionsConfig",
    "apps.demo.apps.DemoConfig",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.template.context_processors.static",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"
DATABASES = {"default": {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": BASE_DIR / "demo.sqlite3",
}}
# Minimal extract: sync the demo models without committing the original store's
# migrations. Production B2 Store uses its normal tracked migrations instead.
MIGRATION_MODULES = {"catalogue": None, "options": None, "demo": None}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LANGUAGE_CODE = "en"
LANGUAGES = [("en", "English"), ("ar", "Arabic")]
USE_TZ = True
TIME_ZONE = "Asia/Riyadh"
STATIC_URL = "static/"
# Fixed demo VAT. Original B2 store uses Oscar's separate tax/strategy layer.
DEMO_VAT_RATE = "0.15"
# Django's built-in password validation is irrelevant: no login forms exist.
