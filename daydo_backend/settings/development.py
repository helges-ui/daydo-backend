"""
Development settings for daydo_backend project.

These settings are used when DJANGO_ENV=development (default).
"""
from .base import *
from .database import *
from .security import *
from .rest_framework import *
from .cors import *
from .logging import *
from .cache import *
from .email import *
from .aws import *
from .mapbox import *

# Override JWT signing key
SIMPLE_JWT['SIGNING_KEY'] = SECRET_KEY

# Development-specific overrides
DEBUG = True

# Allow all origins in development (for local testing)
CORS_ALLOW_ALL_ORIGINS = config('CORS_ALLOW_ALL_ORIGINS', default=True, cast=bool)

