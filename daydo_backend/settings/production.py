"""
Production settings for daydo_backend project.

These settings are used when DJANGO_ENV=production.
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

# Production-specific overrides
DEBUG = config('DEBUG', default=False, cast=bool)

# Ensure CORS is properly configured in production
CORS_ALLOW_ALL_ORIGINS = False

