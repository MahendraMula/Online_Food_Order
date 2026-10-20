import os
from decimal import Decimal
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-ofo-dbms-strong-development-fallback-key-2026-production-ready')
DEBUG = os.environ.get('DJANGO_DEBUG', 'True').lower() in ('true', '1', 'yes')

# Production Security Gate: Prevent booting with insecure default secret key when DEBUG=False
if not DEBUG and (not SECRET_KEY or SECRET_KEY.startswith('django-insecure-')):
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be explicitly set to a secure, unique production value when DEBUG=False.")
ALLOWED_HOSTS = [h.strip() for h in os.environ.get('DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost,testserver,*').split(',') if h.strip()]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Your full-stack modular apps
    'accounts.apps.AccountsConfig',
    'restaurants.apps.RestaurantsConfig',
    'orders.apps.OrdersConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'dbms_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'orders.context_processors.cart_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'dbms_project.wsgi.application'
ASGI_APPLICATION = 'dbms_project.asgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'food_ordering.db',
    },
    'django_database': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'django_database.db',
    }
}

DATABASE_ROUTERS = ['dbms_project.db_routers.DjangoFrameworkRouter']

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
MEDIA_URL = '/images/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'images')
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# Security & SSL Settings (Configured dynamically based on environment)
if not DEBUG:
    SECURE_SSL_REDIRECT = os.environ.get('DJANGO_SECURE_SSL_REDIRECT', 'True').lower() in ('true', '1', 'yes')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = int(os.environ.get('DJANGO_HSTS_SECONDS', '31536000'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
else:
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False

# Commercial Essentials: Currency, Delivery & Tax Settings
OFO_CURRENCY_SYMBOL = os.environ.get('OFO_CURRENCY_SYMBOL', '₹')
OFO_CURRENCY_CODE = os.environ.get('OFO_CURRENCY_CODE', 'INR')
OFO_BASE_DELIVERY_FEE = Decimal(os.environ.get('OFO_BASE_DELIVERY_FEE', '4.00'))
OFO_FREE_DELIVERY_THRESHOLD = Decimal(os.environ.get('OFO_FREE_DELIVERY_THRESHOLD', '50.00'))
OFO_DELIVERY_PER_KM_RATE = Decimal(os.environ.get('OFO_DELIVERY_PER_KM_RATE', '1.00'))
OFO_BASE_DELIVERY_DISTANCE_KM = Decimal(os.environ.get('OFO_BASE_DELIVERY_DISTANCE_KM', '5.0'))
OFO_GST_TAX_RATE = Decimal(os.environ.get('OFO_GST_TAX_RATE', '0.05'))  # Configurable 5% default GST assumption