"""
AWS configuration for daydo_backend project.
"""
from decouple import config

# AWS configuration
AWS_REGION = config('AWS_REGION', default='us-east-1')
AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID', default='')
AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY', default='')

