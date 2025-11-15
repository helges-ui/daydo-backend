"""
Mapbox configuration for daydo_backend project.
"""
from decouple import config

# Mapbox configuration
MAPBOX_PUBLIC_TOKEN = config('MAPBOX_PUBLIC_TOKEN', default='')

