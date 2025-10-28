#!/usr/bin/env python3
"""
Generate a secure Django secret key for production use.
Run this script to generate a new SECRET_KEY for your .env.production file.
"""

import secrets
import string

def generate_secret_key():
    """Generate a secure Django secret key."""
    # Use URL-safe characters for better compatibility
    alphabet = string.ascii_letters + string.digits + '-_'
    return ''.join(secrets.choice(alphabet) for _ in range(50))

def generate_database_password():
    """Generate a secure database password."""
    alphabet = string.ascii_letters + string.digits + '!@#$%^&*'
    return ''.join(secrets.choice(alphabet) for _ in range(20))

if __name__ == '__main__':
    print("🔐 DayDo Production Security Key Generator")
    print("=" * 50)
    
    secret_key = generate_secret_key()
    db_password = generate_database_password()
    
    print(f"SECRET_KEY={secret_key}")
    print(f"DB_PASSWORD={db_password}")
    print()
    print("📋 Copy these values to your .env.production file:")
    print("=" * 50)
    print(f"SECRET_KEY={secret_key}")
    print(f"DB_PASSWORD={db_password}")
    print()
    print("⚠️  IMPORTANT: Keep these values secure and never commit them to version control!")
