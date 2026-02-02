"""
Configuration Django SÉCURISÉE pour la production
"""
from pathlib import Path
import os
from django.core.management.utils import get_random_secret_key

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SÉCURITÉ RENFORCÉE
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable must be set")

# SÉCURITÉ: DEBUG DÉSACTIVÉ EN PRODUCTION
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

# SÉCURITÉ: Hosts autorisés
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')
if not ALLOWED_HOSTS or ALLOWED_HOSTS == ['']:
    raise ValueError("ALLOWED_HOSTS must be configured for production")

# SÉCURITÉ: Headers de sécurité
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# SÉCURITÉ: HTTPS en production
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# SÉCURITÉ: Cookies
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 3600  # 1 heure
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Applications
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Applications personnalisées
    'public',
    'users',
    'missions',
    'chat',
    'ratings',
    'subscriptions',
    'location',
    'geolocation',
]

# SÉCURITÉ: Middleware avec protection renforcée
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Pour les fichiers statiques
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'Livraison_Faso.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
            ],
        },
    },
]

WSGI_APPLICATION = 'Livraison_Faso.wsgi.application'

# SÉCURITÉ: Base de données avec validation
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'CONN_MAX_AGE': 600,  # Connexions persistantes
        'OPTIONS': {
            'sslmode': 'require' if not DEBUG else 'prefer',
        }
    }
}

# Validation des variables de base de données
required_db_vars = ['DB_NAME', 'DB_USER', 'DB_PASSWORD']
for var in required_db_vars:
    if not os.environ.get(var):
        raise ValueError(f"{var} environment variable must be set")

# SÉCURITÉ: Validation des mots de passe renforcée
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 12,  # Augmenté à 12 caractères
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalisation
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Ouagadougou'
USE_I18N = True
USE_TZ = True

# SÉCURITÉ: Fichiers statiques avec WhiteNoise
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# SÉCURITÉ: Fichiers média avec validation
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB

# URLs de redirection
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'

# Messages
from django.contrib.messages import constants as messages
MESSAGE_TAGS = {
    messages.DEBUG: 'alert-info',
    messages.INFO: 'alert-info',
    messages.SUCCESS: 'alert-success',
    messages.WARNING: 'alert-warning',
    messages.ERROR: 'alert-danger',
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'users.User'

# SÉCURITÉ: Logging pour la production
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
        'security': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'security.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'WARNING',
            'propagate': True,
        },
        'django.security': {
            'handlers': ['security'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Configuration géolocalisation sécurisée
LOCATION_SETTINGS = {
    'DEFAULT_MAP_CENTER': {
        'lat': 12.3714,
        'lng': -1.5197,
        'zoom': 12
    },
    'MAP_PROVIDER': 'leaflet',
    'LEAFLET_CONFIG': {
        'DEFAULT_CENTER': (12.3714, -1.5197),
        'DEFAULT_ZOOM': 12,
        'MIN_ZOOM': 3,
        'MAX_ZOOM': 18,
        'TILES': 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
        'ATTRIBUTION': '© OpenStreetMap contributors'
    },
    'GOOGLE_MAPS_API_KEY': os.environ.get('GOOGLE_MAPS_API_KEY', ''),
    'UPDATE_INTERVAL': 30,
    'MAX_DISTANCE': 50,
}

# Configuration par défaut
DEFAULT_COUNTRY = 'BF'
DEFAULT_CITY = 'Ouagadougou'
DEFAULT_LATITUDE = 12.3714
DEFAULT_LONGITUDE = -1.5197

# SÉCURITÉ: Rate limiting (nécessite django-ratelimit)
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'

# Cache pour la production
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'livrafaso',
        'TIMEOUT': 300,
    }
}

# Email sécurisé
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@livrafaso.com')
