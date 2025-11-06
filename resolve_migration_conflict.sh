#!/bin/bash
# Script to resolve migration conflict on Lightsail server
# Marks 0005_todolist_todotask as applied since 0009 already contains those changes

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
echo "Resolving Migration Conflict"
echo "Server: ${SERVER_USER}@${SERVER_IP}"
echo "=========================================="
echo ""

echo "Connecting to server and resolving conflict..."
echo ""

# SSH to server and resolve conflict
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
    exit 1
fi

echo "Current directory: $(pwd)"
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Use python3 if available, otherwise use python
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

echo "Using Python command: $PYTHON_CMD"
echo ""

# Mark 0005 as applied (fake migration)
echo "Marking 0005_todolist_todotask as applied..."
$PYTHON_CMD manage.py migrate daydo 0005_todolist_todotask --fake

echo ""
echo "Now applying 0010_note migration..."
$PYTHON_CMD manage.py migrate daydo

echo ""
echo "=========================================="
echo "Migration conflict resolved!"
echo "=========================================="

# Verify migration status
echo ""
echo "Verifying migration status..."
$PYTHON_CMD manage.py showmigrations daydo | tail -10

# Restart services
echo ""
echo "Restarting Gunicorn service..."
if systemctl is-active --quiet daydo-gunicorn; then
    sudo systemctl restart daydo-gunicorn || echo "Could not restart Gunicorn"
else
    echo "Gunicorn service not running or not managed by systemd"
fi

echo ""
echo "Done!"
ENDSSH

echo ""
echo "=========================================="
echo "Migration conflict resolution completed!"
echo "=========================================="

