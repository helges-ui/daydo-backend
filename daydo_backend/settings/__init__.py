"""
Django settings for daydo_backend project.

This module combines all settings from various modules.
Import the appropriate environment-specific settings module.
"""
import os

# Determine which environment settings to use
# Use os.environ here since decouple may not be available during initial import
ENVIRONMENT = os.environ.get('DJANGO_ENV', 'development')

if ENVIRONMENT == 'production':
    from .production import *
else:
    from .development import *

