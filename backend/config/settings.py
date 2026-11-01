from pathlib import Path

from app.core.config import settings as app_settings

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = app_settings.jwt_secret
DEBUG = False
ALLOWED_HOSTS = ["*"]  # the reverse proxy (Caddy) terminates TLS and routes by host
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
APPEND_SLASH = False  # routes are exact, e.g. /v1/cvs, as the frontend expects

INSTALLED_APPS = ["django.contrib.contenttypes", "rest_framework", "corsheaders", "app"]
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
]


def _sqlite_path(url: str) -> str:
    # DATABASE_URL keeps its SQLAlchemy-style form (sqlite:///./file.db) so existing .env files still work.
    if not url.startswith("sqlite:///"):
        raise ValueError("DATABASE_URL must be a sqlite:/// URL")
    return str((BASE_DIR / url.removeprefix("sqlite:///")).resolve())


DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": _sqlite_path(app_settings.database_url),
                         "OPTIONS": {"timeout": 20}}}
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

USE_TZ = True
TIME_ZONE = "UTC"

CORS_ALLOWED_ORIGINS = [o.strip() for o in app_settings.cors_origins.split(",") if o.strip()]
CORS_ALLOW_HEADERS = ["authorization", "content-type"]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],  # auth is our own JWT check in app.api.deps
    "DEFAULT_PERMISSION_CLASSES": [],
    "UNAUTHENTICATED_USER": None,
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser", "rest_framework.parsers.MultiPartParser"],
    "EXCEPTION_HANDLER": "app.api.errors.handler",
}

# Run background work inline (tests set this) instead of on a thread.
BACKGROUND_SYNC = False
