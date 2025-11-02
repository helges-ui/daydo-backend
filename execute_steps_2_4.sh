#!/bin/bash

# Script to execute Steps 2-4: Configure Lightsail backend for Amplify frontend
# This script updates .env, Nginx config, and tests the backend

set -e

echo "=========================================="
echo "Step 2: Updating Backend Settings"
echo "=========================================="

# App directory (update this to your actual path)
APP_DIR="/opt/daydo/app"

# Backup existing .env if it exists
if [ -f $APP_DIR/.env ]; then
    echo "Backing up existing .env file..."
    sudo cp $APP_DIR/.env $APP_DIR/.env.backup.$(date +%Y%m%d_%H%M%S)
fi

# Check if we need to read existing SECRET_KEY
if [ -f $APP_DIR/.env ]; then
    EXISTING_SECRET=$(grep "^SECRET_KEY=" $APP_DIR/.env | cut -d'=' -f2- || echo "")
    if [ ! -z "$EXISTING_SECRET" ]; then
        echo "Keeping existing SECRET_KEY from .env"
        SECRET_KEY_LINE="SECRET_KEY=$EXISTING_SECRET"
    else
        SECRET_KEY_LINE="SECRET_KEY=your-super-secret-production-key-change-this"
    fi
else
    SECRET_KEY_LINE="SECRET_KEY=your-super-secret-production-key-change-this"
fi

# Create/update .env file
echo "Creating/updating .env file in $APP_DIR..."
sudo tee $APP_DIR/.env > /dev/null <<EOF
$SECRET_KEY_LINE
DEBUG=False

# ALLOWED_HOSTS - Include your Lightsail IP and all domains
ALLOWED_HOSTS=13.36.190.238,localhost,127.0.0.1,main.d2avrs8wps790i.amplifyapp.com,daydo.eu,www.daydo.eu

# Database Configuration
DB_NAME=daydo_production
DB_USER=daydo_user
DB_PASSWORD=pixvav-kugnoD-zitta0
DB_HOST=daydo-production.cd4eu622q4lx.eu-west-3.rds.amazonaws.com
DB_PORT=5432

# CORS Configuration - Add all your frontend domains
CORS_ALLOWED_ORIGINS=https://main.d2avrs8wps790i.amplifyapp.com,https://daydo.eu,https://www.daydo.eu,http://localhost:3000,http://127.0.0.1:3000

# Security Settings
SECURE_SSL_REDIRECT=False
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_CONTENT_TYPE_NOSNIFF=True
SECURE_BROWSER_XSS_FILTER=True

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/daydo/django.log
EOF

echo "✓ .env file updated"
echo ""

# Restart Gunicorn
echo "Restarting Gunicorn service..."
sudo systemctl restart daydo-gunicorn
sleep 2
sudo systemctl status daydo-gunicorn --no-pager -l || true
echo ""

echo "=========================================="
echo "Step 3: Updating Nginx Configuration"
echo "=========================================="

# Backup existing Nginx config
if [ -f /etc/nginx/sites-available/daydo ]; then
    echo "Backing up existing Nginx config..."
    sudo cp /etc/nginx/sites-available/daydo /etc/nginx/sites-available/daydo.backup.$(date +%Y%m%d_%H%M%S)
fi

# Update Nginx config
echo "Updating Nginx configuration..."
sudo tee /etc/nginx/sites-available/daydo > /dev/null <<'NGINX_EOF'
server {
    listen 80;
    server_name 13.36.190.238 daydo.eu www.daydo.eu;
    
    client_max_body_size 10M;
    
    # Gunicorn proxy
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # CORS headers (if not handled by Django)
        add_header 'Access-Control-Allow-Origin' '$http_origin' always;
        add_header 'Access-Control-Allow-Credentials' 'true' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS, PATCH' always;
        add_header 'Access-Control-Allow-Headers' 'Authorization, Content-Type, Accept, Origin' always;
        
        # Handle preflight requests
        if ($request_method = 'OPTIONS') {
            add_header 'Access-Control-Allow-Origin' '$http_origin' always;
            add_header 'Access-Control-Allow-Credentials' 'true' always;
            add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS, PATCH' always;
            add_header 'Access-Control-Allow-Headers' 'Authorization, Content-Type, Accept, Origin' always;
            add_header 'Content-Length' 0;
            add_header 'Content-Type' 'text/plain';
            return 204;
        }
    }
    
    # Static files
    location /static/ {
        alias /opt/daydo/app/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # Media files
    location /media/ {
        alias /opt/daydo/app/media/;
        expires 7d;
        add_header Cache-Control "public";
    }
}
NGINX_EOF

# Test Nginx configuration
echo "Testing Nginx configuration..."
sudo nginx -t

# Reload Nginx
echo "Reloading Nginx..."
sudo systemctl reload nginx

# Verify Nginx is running
echo "Verifying Nginx status..."
sudo systemctl status nginx --no-pager -l || true
echo ""

echo "=========================================="
echo "Step 4: Testing Backend Availability"
echo "=========================================="

# Test 1: Local health check
echo "Test 1: Local health check..."
LOCAL_HEALTH=$(curl -s http://localhost/api/health/ || echo "FAILED")
if [[ "$LOCAL_HEALTH" == *"ok"* ]] || [[ "$LOCAL_HEALTH" == *"status"* ]]; then
    echo "✓ Local health check passed: $LOCAL_HEALTH"
else
    echo "✗ Local health check failed: $LOCAL_HEALTH"
fi
echo ""

# Test 2: External health check
echo "Test 2: External health check (via IP)..."
EXTERNAL_HEALTH=$(curl -s http://13.36.190.238/api/health/ || echo "FAILED")
if [[ "$EXTERNAL_HEALTH" == *"ok"* ]] || [[ "$EXTERNAL_HEALTH" == *"status"* ]]; then
    echo "✓ External health check passed: $EXTERNAL_HEALTH"
else
    echo "✗ External health check failed: $EXTERNAL_HEALTH"
fi
echo ""

# Test 3: CORS preflight
echo "Test 3: CORS preflight check..."
CORS_TEST=$(curl -s -X OPTIONS http://localhost/api/health/ \
    -H "Origin: https://main.d2avrs8wps790i.amplifyapp.com" \
    -H "Access-Control-Request-Method: GET" \
    -H "Access-Control-Request-Headers: Content-Type" \
    -w "\n%{http_code}" || echo "FAILED")
HTTP_CODE=$(echo "$CORS_TEST" | tail -n1)
if [ "$HTTP_CODE" = "204" ] || [ "$HTTP_CODE" = "200" ]; then
    echo "✓ CORS preflight test passed (HTTP $HTTP_CODE)"
else
    echo "✗ CORS preflight test failed (HTTP $HTTP_CODE)"
fi
echo ""

# Test 4: Check service status
echo "Test 4: Service status..."
echo "Gunicorn:"
sudo systemctl is-active daydo-gunicorn && echo "  ✓ Running" || echo "  ✗ Not running"
echo "Nginx:"
sudo systemctl is-active nginx && echo "  ✓ Running" || echo "  ✗ Not running"
echo ""

echo "=========================================="
echo "Summary"
echo "=========================================="
echo "✓ Step 2: Backend settings updated"
echo "✓ Step 3: Nginx configuration updated"
echo "✓ Step 4: Backend availability tested"
echo ""
echo "Next steps:"
echo "1. Verify external access: curl http://13.36.190.238/api/health/"
echo "2. Update frontend API configuration (Step 5)"
echo "3. Set up HTTPS/SSL (Step 6 - optional but recommended)"
echo ""

