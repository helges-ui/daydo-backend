#!/bin/bash

# Script to register the first admin user via the DayDo API
# This creates a PARENT user and automatically creates a family

API_URL="http://13.36.190.238/api/auth/register/"

# Default admin credentials (modify these as needed)
USERNAME="${1:-admin}"
EMAIL="${2:-admin@example.com}"
FIRST_NAME="${3:-Admin}"
LAST_NAME="${4:-User}"
PASSWORD="${5:-admin123456}"
FAMILY_NAME="${6:-Admin Family}"

echo "Registering admin user..."
echo "Username: $USERNAME"
echo "Email: $EMAIL"
echo "Name: $FIRST_NAME $LAST_NAME"
echo "Family: $FAMILY_NAME"
echo ""

# Register the user
response=$(curl -s -w "\n%{http_code}" -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d "{
    \"username\": \"$USERNAME\",
    \"email\": \"$EMAIL\",
    \"first_name\": \"$FIRST_NAME\",
    \"last_name\": \"$LAST_NAME\",
    \"password\": \"$PASSWORD\",
    \"password_confirm\": \"$PASSWORD\",
    \"family_name\": \"$FAMILY_NAME\",
    \"avatar\": \"superhero\",
    \"color\": \"#8C5FFF\"
  }")

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

echo "HTTP Status: $http_code"
echo ""
echo "Response:"
echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"

if [ "$http_code" -eq 201 ]; then
  echo ""
  echo "✓ Admin user created successfully!"
  echo ""
  echo "You can now login with:"
  echo "  Username: $USERNAME"
  echo "  Password: $PASSWORD"
else
  echo ""
  echo "✗ Registration failed. Check the error message above."
fi

