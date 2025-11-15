"""
Redis configuration for Django Channels
"""
from decouple import config

# Redis Configuration
REDIS_HOST = config('REDIS_HOST', default='127.0.0.1')
REDIS_PORT = config('REDIS_PORT', default=6379, cast=int)
REDIS_PASSWORD = config('REDIS_PASSWORD', default=None)
REDIS_DB = config('REDIS_DB', default=0, cast=int)

# Build Redis URL
# For localhost connections (same instance), no password or SSL needed
if REDIS_PASSWORD:
    REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
else:
    REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

# Channel Layers Configuration for Django Channels
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [
                {
                    "address": REDIS_URL,
                }
            ],
            "capacity": 1500,  # Maximum number of messages to store
            "expiry": 10,  # Message expiry in seconds
        },
    },
}

