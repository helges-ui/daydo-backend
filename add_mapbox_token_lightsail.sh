#!/bin/bash

# Script to add Mapbox token to AWS Lightsail backend
# Server: 13.36.190.238
# User: ubuntu
# Backend path: /home/ubuntu/daydo-backend
#
# Usage: ./add_mapbox_token_lightsail.sh
# Note: Requires SSH access to the server

MAPBOX_TOKEN="pk.eyJ1IjoiZ2VyZGlnZXJkc2VuIiwiYSI6ImNtaHV5anRidzA0bG0ybXNrNTdoZms1N2kifQ.4e-ng27Yaul9NjzDwCeUfA"
SERVER="ubuntu@13.36.190.238"
BACKEND_PATH="/home/ubuntu/daydo-backend"
ENV_FILE="${BACKEND_PATH}/.env"

echo "=========================================="
echo "Adding Mapbox Token to Lightsail Backend"
echo "=========================================="
echo ""

# Check if SSH key is available
if ! ssh -o BatchMode=yes -o ConnectTimeout=5 ${SERVER} echo "Connection test" &>/dev/null; then
    echo "⚠️  SSH connection requires authentication."
    echo ""
    echo "Please run these commands manually on the server:"
    echo ""
    echo "ssh ${SERVER}"
    echo "cd ${BACKEND_PATH}"
    echo ""
    echo "# If .env doesn't exist, create it:"
    echo "touch .env"
    echo ""
    echo "# Add or update the token:"
    echo "if grep -q '^MAPBOX_PUBLIC_TOKEN=' .env; then"
    echo "  sed -i 's|^MAPBOX_PUBLIC_TOKEN=.*|MAPBOX_PUBLIC_TOKEN=${MAPBOX_TOKEN}|' .env"
    echo "else"
    echo "  echo 'MAPBOX_PUBLIC_TOKEN=${MAPBOX_TOKEN}' >> .env"
    echo "fi"
    echo ""
    echo "# Verify:"
    echo "grep MAPBOX_PUBLIC_TOKEN .env"
    echo ""
    echo "# Restart Django service:"
    echo "sudo systemctl restart daydo  # or gunicorn, or your service name"
    echo ""
    exit 0
fi

# Check if .env file exists and add/update token
echo "1. Adding/updating MAPBOX_PUBLIC_TOKEN in .env file..."

ssh -t ${SERVER} << 'REMOTE_SCRIPT'
    cd ${BACKEND_PATH}
    
    # Create .env file if it doesn't exist
    if [ ! -f .env ]; then
        echo "Creating .env file..."
        touch .env
    fi
    
    # Check if MAPBOX_PUBLIC_TOKEN already exists
    if grep -q "^MAPBOX_PUBLIC_TOKEN=" .env; then
        echo "Updating existing MAPBOX_PUBLIC_TOKEN..."
        # Update existing token
        sed -i "s|^MAPBOX_PUBLIC_TOKEN=.*|MAPBOX_PUBLIC_TOKEN=${MAPBOX_TOKEN}|" .env
    else
        echo "Adding new MAPBOX_PUBLIC_TOKEN..."
        # Append new token
        echo "MAPBOX_PUBLIC_TOKEN=${MAPBOX_TOKEN}" >> .env
    fi
    
    # Verify token was added
    echo ""
    echo "Verifying token in .env file:"
    grep "MAPBOX_PUBLIC_TOKEN" .env || echo "ERROR: Token not found in .env file!"
    
    echo ""
    echo "✅ Token added/updated successfully"
REMOTE_SCRIPT

if [ $? -eq 0 ]; then
    echo ""
    echo "2. Restarting Django application..."
    echo ""
    
    # Try to restart the service (common service names)
    ssh ${SERVER} << EOF
    # Try systemd service first
    if sudo systemctl is-active --quiet daydo 2>/dev/null || sudo systemctl is-active --quiet gunicorn 2>/dev/null || sudo systemctl is-active --quiet django 2>/dev/null; then
            echo "Restarting via systemd..."
            sudo systemctl restart daydo 2>/dev/null || \
            sudo systemctl restart gunicorn 2>/dev/null || \
            sudo systemctl restart django 2>/dev/null || \
            echo "Note: Could not find systemd service. Please restart manually."
        else
            echo "No systemd service found. Checking for supervisor or manual process..."
            # Try supervisor
            if command -v supervisorctl &> /dev/null; then
                supervisorctl restart daydo 2>/dev/null || echo "Supervisor not configured"
            fi
            echo ""
            echo "⚠️  Please restart your Django application manually:"
            echo "   Option 1: If using systemd: sudo systemctl restart <service-name>"
            echo "   Option 2: If using supervisor: supervisorctl restart daydo"
            echo "   Option 3: If running manually: kill and restart the process"
        fi
EOF
    
    echo ""
    echo "=========================================="
    echo "✅ Token Configuration Complete"
    echo "=========================================="
    echo ""
    echo "Next steps:"
    echo "1. Verify the token is working:"
    echo "   curl -H \"Authorization: Bearer YOUR_JWT\" https://api.daydo.eu/api/location/mapbox-token/"
    echo ""
    echo "2. Test the Standort page in your frontend"
    echo ""
else
    echo ""
    echo "❌ Error: Failed to add token. Please check:"
    echo "   - SSH connection to server"
    echo "   - File permissions"
    echo "   - Backend path: ${BACKEND_PATH}"
    exit 1
fi

