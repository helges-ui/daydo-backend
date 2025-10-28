#!/usr/bin/env python3
"""
Production Environment Validation Script
This script validates that all required environment variables are set correctly.
"""

import os
import sys
from decouple import config

def validate_environment():
    """Validate production environment configuration."""
    print("🔍 DayDo Production Environment Validation")
    print("=" * 50)
    
    errors = []
    warnings = []
    
    # Required environment variables
    required_vars = {
        'SECRET_KEY': 'Django secret key for production',
        'DEBUG': 'Debug mode (should be False)',
        'ALLOWED_HOSTS': 'Allowed hosts for Django',
        'DB_NAME': 'Database name',
        'DB_USER': 'Database user',
        'DB_PASSWORD': 'Database password',
        'DB_HOST': 'Database host',
        'DB_PORT': 'Database port',
        'CORS_ALLOWED_ORIGINS': 'CORS allowed origins',
    }
    
    # Check required variables
    for var, description in required_vars.items():
        value = config(var, default=None)
        if value is None:
            errors.append(f"❌ {var}: {description} - NOT SET")
        else:
            print(f"✅ {var}: {description} - SET")
    
    # Validate specific values
    debug = config('DEBUG', default=True, cast=bool)
    if debug:
        warnings.append("⚠️  DEBUG is True - should be False in production")
    else:
        print("✅ DEBUG is False - correct for production")
    
    secret_key = config('SECRET_KEY', default='')
    if len(secret_key) < 20:
        errors.append("❌ SECRET_KEY is too short - should be at least 20 characters")
    elif 'django-insecure' in secret_key:
        errors.append("❌ SECRET_KEY contains 'django-insecure' - use a secure key")
    else:
        print("✅ SECRET_KEY is secure")
    
    allowed_hosts = config('ALLOWED_HOSTS', default='')
    if 'localhost' in allowed_hosts or '127.0.0.1' in allowed_hosts:
        warnings.append("⚠️  ALLOWED_HOSTS contains localhost - remove for production")
    else:
        print("✅ ALLOWED_HOSTS configured for production")
    
    cors_origins = config('CORS_ALLOWED_ORIGINS', default='')
    if 'http://' in cors_origins:
        warnings.append("⚠️  CORS_ALLOWED_ORIGINS contains HTTP - use HTTPS only")
    else:
        print("✅ CORS_ALLOWED_ORIGINS uses HTTPS")
    
    # Database validation
    db_host = config('DB_HOST', default='')
    if 'localhost' in db_host or '127.0.0.1' in db_host:
        warnings.append("⚠️  DB_HOST is localhost - use production database")
    else:
        print("✅ DB_HOST configured for production")
    
    # Print results
    print("\n" + "=" * 50)
    print("📊 VALIDATION RESULTS")
    print("=" * 50)
    
    if errors:
        print("\n❌ ERRORS (Must be fixed):")
        for error in errors:
            print(f"  {error}")
    
    if warnings:
        print("\n⚠️  WARNINGS (Should be reviewed):")
        for warning in warnings:
            print(f"  {warning}")
    
    if not errors and not warnings:
        print("\n🎉 All validations passed! Environment is ready for production.")
        return True
    elif not errors:
        print("\n✅ No critical errors found. Environment is ready with warnings.")
        return True
    else:
        print("\n❌ Critical errors found. Please fix before deploying.")
        return False

if __name__ == '__main__':
    success = validate_environment()
    sys.exit(0 if success else 1)
