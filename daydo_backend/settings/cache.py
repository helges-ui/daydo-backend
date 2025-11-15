"""
Cache configuration for daydo_backend project.
"""
from decouple import config

# Cache configuration (Redis for production)
if not config('DEBUG', default=True, cast=bool):
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': config('CACHE_BACKEND', default='redis://localhost:6379/1'),
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }

