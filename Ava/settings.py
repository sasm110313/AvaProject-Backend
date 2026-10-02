"""تنظیمات پروژه آوای انعکاس.

همه‌ی مقادیر حساس از فایل `.env` یا متغیرهای محیطی خوانده می‌شوند تا
هیچ اطلاعاتی داخل کد هاردکد نشود. برای اجرای امن در محیط واقعی (DEBUG=False)
مقدار ``SECRET_KEY`` و ``ALLOWED_HOSTS`` الزامی هستند.
"""

from datetime import timedelta
from pathlib import Path

from decouple import Csv, config
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# هسته
# ---------------------------------------------------------------------------

DEBUG = config("DEBUG", default=False, cast=bool)

SECRET_KEY = config("SECRET_KEY", default="")

if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "django-insecure-dev-only-key-do-not-use-in-production"
    else:
        raise ImproperlyConfigured(
            "SECRET_KEY تنظیم نشده است. یک کلید تصادفی طولانی بسازید و در "
            "متغیر محیطی SECRET_KEY قرار دهید."
        )

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default="localhost,127.0.0.1,[::1],testserver" if DEBUG else "",
    cast=Csv(),
)
if not DEBUG and (not ALLOWED_HOSTS or ALLOWED_HOSTS == ["*"]):
    raise ImproperlyConfigured(
        "در حالت DEBUG=False باید ALLOWED_HOSTS مشخص شود و نمی‌تواند '*' باشد."
    )

CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", default="", cast=Csv())

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "core.apps.CoreConfig",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "Ava.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "Ava.wsgi.application"
ASGI_APPLICATION = "Ava.asgi.application"

# ---------------------------------------------------------------------------
# پایگاه داده
# ---------------------------------------------------------------------------

_db_engine = config("DB_ENGINE", default="sqlite")
_db_name = config("DB_NAME", default=str(BASE_DIR / "db.sqlite3"))

if _db_engine == "postgresql":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": _db_name,
            "USER": config("DB_USER", default="postgres"),
            "PASSWORD": config("DB_PASSWORD", default=""),
            "HOST": config("DB_HOST", default="127.0.0.1"),
            "PORT": config("DB_PORT", default="5432"),
            "CONN_MAX_AGE": config("DB_CONN_MAX_AGE", default=60, cast=int),
        }
    }
elif _db_engine == "sqlite":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": _db_name,
            "OPTIONS": {
                # قفل‌گذاری روی فایل دیتابیس تا نوشتن هم‌زمان امن باشد
                "timeout": config("DB_TIMEOUT", default=20, cast=int),
            },
            "ATOMIC_REQUESTS": False,
        }
    }
else:
    raise ImproperlyConfigured(f"DB_ENGINE پشتیبانی نمی‌شود: {_db_engine}")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "core.User"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# ---------------------------------------------------------------------------
# بومی‌سازی
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "fa"
TIME_ZONE = config("TIME_ZONE", default="Asia/Tehran")
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# فایل‌های استاتیک و رسانه‌ای
# ---------------------------------------------------------------------------

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []

MEDIA_URL = "/media/"
MEDIA_ROOT = Path(config("MEDIA_ROOT", default=str(BASE_DIR / "media")))

# در محیط واقعی بهتر است فایل‌های رسانه‌ای را nginx یا یک وب‌سرور
# استاتیک سرو کند؛ مقدار پیش‌فرض فقط برای توسعه فعال است.
SERVE_MEDIA = config("SERVE_MEDIA", default=DEBUG, cast=bool)

# ---------------------------------------------------------------------------
# محدودیت آپلود (جلوگیری از سوءاستفاده و پر شدن دیسک)
# ---------------------------------------------------------------------------

MAX_UPLOAD_SIZE_MB = config("MAX_UPLOAD_SIZE_MB", default=50, cast=int)
MAX_IMAGE_SIZE_MB = config("MAX_IMAGE_SIZE_MB", default=8, cast=int)
MAX_VIDEO_SIZE_MB = config("MAX_VIDEO_SIZE_MB", default=100, cast=int)
MAX_IMAGES_PER_PRODUCT = config("MAX_IMAGES_PER_PRODUCT", default=10, cast=int)
MAX_VIDEOS_PER_ARTICLE = config("MAX_VIDEOS_PER_ARTICLE", default=10, cast=int)

FILE_UPLOAD_MAX_MEMORY_SIZE = MAX_IMAGE_SIZE_MB * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE_MB * 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FILES = MAX_IMAGES_PER_PRODUCT + MAX_VIDEOS_PER_ARTICLE + 10

FILE_UPLOAD_PERMISSIONS = 0o644

# ---------------------------------------------------------------------------
# تنظیمات امنیتی
# ---------------------------------------------------------------------------

SECURE_SSL = config("SECURE_SSL", default=False, cast=bool)

SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=SECURE_SSL, cast=bool)
SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=0 if not SECURE_SSL else 31536000, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = config("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=SECURE_SSL, cast=bool)
SECURE_HSTS_PRELOAD = config("SECURE_HSTS_PRELOAD", default=SECURE_SSL, cast=bool)

SESSION_COOKIE_SECURE = config("SESSION_COOKIE_SECURE", default=SECURE_SSL, cast=bool)
CSRF_COOKIE_SECURE = config("CSRF_COOKIE_SECURE", default=SECURE_SSL, cast=bool)
CSRF_COOKIE_HTTPONLY = config("CSRF_COOKIE_HTTPONLY", default=False, cast=bool)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = config("SESSION_COOKIE_AGE", default=60 * 60 * 24 * 30, cast=int)
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# ---------------------------------------------------------------------------
# DRF
# ---------------------------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    "DEFAULT_PAGINATION_CLASS": "core.pagination.ConditionalPageNumberPagination",
    "PAGE_SIZE": config("PAGE_SIZE", default=20, cast=int),
    "DEFAULT_THROTTLE_CLASSES": [
        "core.throttling.AnonRateThrottle",
        "core.throttling.UserRateThrottle",
        "core.throttling.BurstRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": config("THROTTLE_ANON", default="120/hour", cast=str),
        "user": config("THROTTLE_USER", default="1000/hour", cast=str),
        "burst": config("THROTTLE_BURST", default="60/minute", cast=str),
        "otp": config("THROTTLE_OTP", default="10/minute", cast=str),
        "otp_verify": config("THROTTLE_OTP_VERIFY", default="30/minute", cast=str),
        "login": config("THROTTLE_LOGIN", default="20/minute", cast=str),
        "order_create": config("THROTTLE_ORDER_CREATE", default="20/minute", cast=str),
    },
    "EXCEPTION_HANDLER": "core.exceptions.api_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DATETIME_FORMAT": "iso-8601",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=config("JWT_ACCESS_MINUTES", default=60, cast=int)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=config("JWT_REFRESH_DAYS", default=30, cast=int)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "TOKEN_TYPE_CLAIM": "token_type",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "API فروشگاه آوای انعکاس",
    "DESCRIPTION": "مستند OpenAPI بک‌اند فروشگاه آوای انعکاس",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": "/api",
    "COMPONENT_SPLIT_REQUEST": True,
    "SORT_OPERATIONS": False,
    "SWAGGER_UI_SETTINGS": {"persistAuthorization": True},
}

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:5173,http://127.0.0.1:5173,http://localhost:4000,http://127.0.0.1:4000,http://localhost:3000,http://127.0.0.1:3000,http://localhost:5174,http://127.0.0.1:5174",
    cast=Csv(),
)
CORS_ALLOW_ALL_ORIGINS = config("CORS_ALLOW_ALL_ORIGINS", default=DEBUG, cast=bool)
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = ["DELETE", "GET", "OPTIONS", "PATCH", "POST", "PUT"]
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-language",
    "authorization",
    "content-language",
    "content-type",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    "x-session-key",
]
CSRF_HEADER_NAME = "HTTP_X_CSRFTOKEN"

# ---------------------------------------------------------------------------
# OTP
# ---------------------------------------------------------------------------

OTP_TTL_MINUTES = config("OTP_TTL_MINUTES", default=10, cast=int)
OTP_RESEND_SECONDS = config("OTP_RESEND_SECONDS", default=60, cast=int)
OTP_MAX_ATTEMPTS = config("OTP_MAX_ATTEMPTS", default=5, cast=int)
# در محیط توسعه کد تایید در پاسخ API برگردانده می‌شود تا تست بدون پنل پیامکی ممکن باشد.
OTP_EXPOSE_DEV_CODE = config("OTP_EXPOSE_DEV_CODE", default=DEBUG, cast=bool)

# ---------------------------------------------------------------------------
# پنل پیامک (SMS Gateway)
# ---------------------------------------------------------------------------

SMS_PROVIDER = config("SMS_PROVIDER", default="console")  # console, kavenegar, farazsms
KAVENEGAR_API_KEY = config("KAVENEGAR_API_KEY", default="")
KAVENEGAR_SENDER = config("KAVENEGAR_SENDER", default="")
KAVENEGAR_OTP_TEMPLATE = config("KAVENEGAR_OTP_TEMPLATE", default="verify")

FARAZSMS_API_KEY = config("FARAZSMS_API_KEY", default="")
FARAZSMS_SENDER = config("FARAZSMS_SENDER", default="")
FARAZSMS_OTP_PATTERN = config("FARAZSMS_OTP_PATTERN", default="")

# ---------------------------------------------------------------------------
# لاگ
# ---------------------------------------------------------------------------

LOG_LEVEL = config("LOG_LEVEL", default="INFO").upper()
LOG_TO_FILE = config("LOG_TO_FILE", default=False, cast=bool)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        "django": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "core": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
    },
}

if LOG_TO_FILE:
    import os

    _log_dir = BASE_DIR / "logs"
    os.makedirs(_log_dir, exist_ok=True)
    LOGGING["handlers"]["file"] = {
        "class": "logging.handlers.RotatingFileHandler",
        "filename": str(_log_dir / "ava.log"),
        "maxBytes": 5 * 1024 * 1024,
        "backupCount": 5,
        "encoding": "utf-8",
        "formatter": "verbose",
    }
    for _name in ("root", "django", "core"):
        LOGGING[_name]["handlers"] = ["console", "file"]