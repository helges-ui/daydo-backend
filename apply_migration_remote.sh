#!/bin/bash
# Script to apply Phase 2 & 3 migrations on Lightsail server
# Server IP: 13.36.190.238

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_IP="13.36.190.238"
SERVER_USER="ubuntu"
SSH_KEY="${SCRIPT_DIR}/LightsailDefaultKey-eu-west-3.pem"
BACKEND_DIR="/home/ubuntu/daydo-backend"

# Check if SSH key exists
if [ ! -f "$SSH_KEY" ]; then
    echo "Error: SSH key not found at $SSH_KEY"
    exit 1
fi

# Set correct permissions for SSH key
chmod 600 "$SSH_KEY"

echo "=========================================="
echo "Applying Phase 2 & 3 Migrations"
echo "Server: ${SERVER_USER}@${SERVER_IP}"
echo "SSH Key: $SSH_KEY"
echo "=========================================="
echo ""

echo "Connecting to server and applying migration..."
echo ""

# SSH to server and run migration
ssh -i "$SSH_KEY" ${SERVER_USER}@${SERVER_IP} << 'ENDSSH'
# Try to find the backend directory
if [ -d "/opt/daydo/app" ]; then
    cd /opt/daydo/app
elif [ -d "/opt/daydo" ]; then
    cd /opt/daydo
elif [ -d "/home/ubuntu/daydo-backend" ]; then
    cd /home/ubuntu/daydo-backend
elif [ -d "~/daydo-backend" ]; then
    cd ~/daydo-backend
else
    echo "Error: Could not find backend directory"
    echo "Searched: /opt/daydo/app, /opt/daydo, /home/ubuntu/daydo-backend, ~/daydo-backend"
    exit 1
fi

echo "Current directory: $(pwd)"
echo ""

# Check if manage.py exists
if [ ! -f "manage.py" ]; then
    echo "Error: manage.py not found in $(pwd)"
    echo "Directory contents:"
    ls -la
    exit 1
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Pull latest changes (if using git)
if [ -d ".git" ]; then
    echo "Checking git status..."
    git status --short || true
    echo ""
    
    echo "Stashing local changes (if any)..."
    git stash || echo "No local changes to stash"
    echo ""
    
    echo "Pulling latest changes from git..."
    git pull origin main || git pull || {
        echo "Warning: Git pull failed, trying to continue..."
        echo "Checking if migration file exists..."
    }
    echo ""
    
    # Restore stashed changes if they exist
    if git stash list | grep -q "stash@{0}"; then
        echo "Restoring stashed changes..."
        git stash pop || echo "Could not restore stashed changes"
        echo ""
    fi
fi

# Check if migration file exists
if [ ! -f "daydo/migrations/0003_event_eventassignment_role_task_userrole_and_more.py" ]; then
    echo "Error: Migration file not found!"
    echo "Please ensure the migration file is present in daydo/migrations/"
    exit 1
fi

echo "Migration file found:"
echo "  daydo/migrations/0003_event_eventassignment_role_task_userrole_and_more.py"
echo ""

# Show pending migrations
echo "Checking for pending migrations..."
python manage.py showmigrations daydo | grep -E "\[ \]" || echo "No pending migrations found"
echo ""

# Apply migrations
echo "Applying migrations..."
python manage.py migrate daydo

echo ""
echo "=========================================="
echo "Migration completed successfully!"
echo "=========================================="

# Verify migration
echo ""
echo "Verifying migration status..."
python manage.py showmigrations daydo | tail -5

echo ""
echo "Done! Phase 2 & 3 migrations have been applied."
ENDSSH

echo ""
echo "=========================================="
echo "Migration deployment completed!"
echo "=========================================="

