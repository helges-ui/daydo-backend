#!/bin/bash

# Test script for Mapbox Token endpoint
# This verifies that the token is correctly configured in production

echo "=========================================="
echo "Mapbox Token Endpoint Test"
echo "=========================================="
echo ""

# Production API URL
API_URL="https://api.daydo.eu"

echo "Testing endpoint: ${API_URL}/api/location/mapbox-token/"
echo ""

# Test without authentication (should fail with 401)
echo "1. Testing without authentication (should return 401):"
RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" "${API_URL}/api/location/mapbox-token/")
HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS" | cut -d':' -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS/d')

if [ "$HTTP_STATUS" = "401" ]; then
    echo "   ✅ Correctly returns 401 (authentication required)"
else
    echo "   ⚠️  Unexpected status: $HTTP_STATUS"
    echo "   Response: $BODY"
fi
echo ""

# Test with invalid token (should fail with 401)
echo "2. Testing with invalid token (should return 401):"
RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
    -H "Authorization: Bearer invalid-token" \
    "${API_URL}/api/location/mapbox-token/")
HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS" | cut -d':' -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS/d')

if [ "$HTTP_STATUS" = "401" ]; then
    echo "   ✅ Correctly returns 401 (invalid token)"
else
    echo "   ⚠️  Unexpected status: $HTTP_STATUS"
    echo "   Response: $BODY"
fi
echo ""

# Instructions for testing with valid token
echo "3. To test with valid authentication:"
echo "   - Get a JWT token by logging in:"
echo "     curl -X POST ${API_URL}/api/auth/login/ \\"
echo "       -H 'Content-Type: application/json' \\"
echo "       -d '{\"username\":\"your-username\",\"password\":\"your-password\"}'"
echo ""
echo "   - Then test the endpoint:"
echo "     curl -H \"Authorization: Bearer YOUR_JWT_TOKEN\" \\"
echo "          ${API_URL}/api/location/mapbox-token/"
echo ""

# Check if token is configured (503 means not configured, 200 means configured)
echo "4. Expected behavior with valid token:"
echo "   - If token is NOT configured: HTTP 503 with message 'Mapbox token is not configured'"
echo "   - If token IS configured: HTTP 200 with JSON containing 'token' field"
echo ""

echo "=========================================="
echo "Test Complete"
echo "=========================================="
echo ""
echo "⚠️  IMPORTANT: Update the token in AWS Amplify if it's truncated!"
echo "   Full token: pk.eyJ1IjoiZ2VyZGlnZXJkc2VuIiwiYSI6ImNtaHV5anRidzA0bG0ybXNrNTdoZms1N2kifQ.4e-ng27Yaul9NjzDwCeUfA"
echo ""

