#!/bin/bash
# Script to finish merge migration on Lightsail server

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_IP="13.36.190.238"
SERVER_USER="ubuntu"
SSH_KEY="${SCRIPT_DIR}/LightsailDefaultKey-eu-west-3.pem"

chmod 600 "$SSH_KEY"

echo "Finishing merge migration on server..."

ssh -i "$SSH_KEY" ${SERVER_USER}@${SERVER_IP} << 'ENDSSH'
if [ -d "/opt/daydo/app" ]; then
    cd /opt/daydo/app
elif [ -d "/opt/daydo" ]; then
    cd /opt/daydo
elif [ -d "/home/ubuntu/daydo-backend" ]; then
    cd /home/ubuntu/daydo-backend
else
    echo "Error: Could not find backend directory"
    exit 1
fi

if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

echo "Marking 0005_todolist_todotask as applied (fake)..."
$PYTHON_CMD manage.py migrate daydo 0005_todolist_todotask --fake

echo "Applying merge migration..."
$PYTHON_CMD manage.py migrate daydo

echo "Verifying migration status..."
$PYTHON_CMD manage.py showmigrations daydo | tail -10

if systemctl is-active --quiet daydo-gunicorn; then
    sudo systemctl restart daydo-gunicorn
fi

echo "Done!"
ENDSSH

echo "Merge migration finished!"

