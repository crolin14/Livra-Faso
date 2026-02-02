
# Settings d'optimisation pour le développement
import os
from .settings import *

# Cache en mémoire pour le développement
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'livrafaso-cache',
        'TIMEOUT': 300,
        'OPTIONS': {
            'MAX_ENTRIES': 1000,
        }
    }
}

# Optimisation des sessions
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# Optimisation des templates
TEMPLATES[0]['OPTIONS']['context_processors'] = [
    'django.template.context_processors.debug',
    'django.template.context_processors.request',
    'django.contrib.auth.context_processors.auth',
    'django.contrib.messages.context_processors.messages',
]

# Compression des fichiers statiques en développement
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Optimisation des requêtes DB
if DEBUG:
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
            },
        },
        'loggers': {
            'django.db.backends': {
                'handlers': ['console'],
                'level': 'WARNING',  # Réduire les logs DB
            },
        },
    }
