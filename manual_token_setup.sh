#!/bin/bash

# Manual commands to run on Lightsail server
# Copy and paste these commands after SSH'ing into the server

MAPBOX_TOKEN="pk.eyJ1IjoiZ2VyZGlnZXJkc2VuIiwiYSI6ImNtaHV5anRidzA0bG0ybXNrNTdoZms1N2kifQ.4e-ng27Yaul9NjzDwCeUfA"
BACKEND_PATH="/home/ubuntu/daydo-backend"

echo "Run these commands on your Lightsail server:"
echo ""
echo "cd ${BACKEND_PATH}"
echo ""
echo "# Create .env if it doesn't exist"
echo "touch .env"
echo ""
echo "# Add or update MAPBOX_PUBLIC_TOKEN"
echo "if grep -q '^MAPBOX_PUBLIC_TOKEN=' .env; then"
echo "  sed -i 's|^MAPBOX_PUBLIC_TOKEN=.*|MAPBOX_PUBLIC_TOKEN=${MAPBOX_TOKEN}|' .env"
echo "else"
echo "  echo 'MAPBOX_PUBLIC_TOKEN=${MAPBOX_TOKEN}' >> .env"
echo "fi"
echo ""
echo "# Verify token was added"
echo "grep MAPBOX_PUBLIC_TOKEN .env"
echo ""
echo "# Restart Django service (choose the appropriate one):"
echo "sudo systemctl restart daydo"
echo "# OR"
echo "sudo systemctl restart gunicorn"
echo "# OR if using supervisor:"
echo "supervisorctl restart daydo"
echo ""

