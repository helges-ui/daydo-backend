#!/usr/bin/env python3
"""
Script to register the first admin user via the DayDo API.
This creates a PARENT user and automatically creates a family.
"""

import sys
import json
import requests

# API Configuration
API_URL = "http://13.36.190.238/api/auth/register/"

# Default admin credentials (can be modified or passed as arguments)
default_credentials = {
    "username": "admin",
    "email": "admin@example.com",
    "first_name": "Admin",
    "last_name": "User",
    "password": "admin123456",
    "family_name": "Admin Family",
    "avatar": "superhero",
    "color": "#8C5FFF"
}


def register_admin(username=None, email=None, first_name=None, last_name=None,
                   password=None, family_name=None, avatar="superhero", color="#8C5FFF"):
    """Register an admin user via the API"""
    
    # Use provided values or defaults
    credentials = {
        "username": username or default_credentials["username"],
        "email": email or default_credentials["email"],
        "first_name": first_name or default_credentials["first_name"],
        "last_name": last_name or default_credentials["last_name"],
        "password": password or default_credentials["password"],
        "password_confirm": password or default_credentials["password"],
        "family_name": family_name or default_credentials["family_name"],
        "avatar": avatar,
        "color": color
    }
    
    print("Registering admin user...")
    print(f"Username: {credentials['username']}")
    print(f"Email: {credentials['email']}")
    print(f"Name: {credentials['first_name']} {credentials['last_name']}")
    print(f"Family: {credentials['family_name']}")
    print()
    
    try:
        response = requests.post(API_URL, json=credentials, headers={"Content-Type": "application/json"})
        
        print(f"HTTP Status: {response.status_code}")
        print()
        print("Response:")
        
        try:
            response_data = response.json()
            print(json.dumps(response_data, indent=2))
        except json.JSONDecodeError:
            print(response.text)
        
        if response.status_code == 201:
            print()
            print("✓ Admin user created successfully!")
            print()
            print("You can now login with:")
            print(f"  Username: {credentials['username']}")
            print(f"  Password: {credentials['password']}")
            return True
        else:
            print()
            print("✗ Registration failed. Check the error message above.")
            return False
            
    except requests.exceptions.ConnectionError:
        print("✗ Error: Could not connect to the API.")
        print(f"  Make sure the backend is running at: {API_URL}")
        return False
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


if __name__ == "__main__":
    # Parse command line arguments if provided
    # Usage: python register_admin.py [username] [email] [first_name] [last_name] [password] [family_name]
    if len(sys.argv) > 1:
        username = sys.argv[1] if len(sys.argv) > 1 else None
        email = sys.argv[2] if len(sys.argv) > 2 else None
        first_name = sys.argv[3] if len(sys.argv) > 3 else None
        last_name = sys.argv[4] if len(sys.argv) > 4 else None
        password = sys.argv[5] if len(sys.argv) > 5 else None
        family_name = sys.argv[6] if len(sys.argv) > 6 else None
        
        register_admin(username, email, first_name, last_name, password, family_name)
    else:
        # Use defaults
        register_admin()

