#!/bin/bash
# Unified deployment script for DayDo backend on AWS Lightsail
# Handles: migrations, token updates, service restarts

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_IP="13.36.190.238"
SERVER_USER="ubuntu"
SSH_KEY="${SCRIPT_DIR}/LightsailDefaultKey-eu-west-3.pem"
BACKEND_DIR="/opt/daydo/app"  # Actual production path

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if SSH key exists
if [ ! -f "$SSH_KEY" ]; then
    echo -e "${RED}Error: SSH key not found at $SSH_KEY${NC}"
    exit 1
fi

# Set correct permissions for SSH key
chmod 600 "$SSH_KEY"

# Function to execute command on remote server
remote_exec() {
    ssh -i "$SSH_KEY" ${SERVER_USER}@${SERVER_IP} "$@"
}

# Function to find backend directory on server
find_backend_dir() {
    remote_exec 'if [ -d "/opt/daydo/app" ]; then echo "/opt/daydo/app"; elif [ -d "/opt/daydo" ]; then echo "/opt/daydo"; elif [ -d "/home/ubuntu/daydo-backend" ]; then echo "/home/ubuntu/daydo-backend"; else echo ""; fi'
}

# Show usage
show_usage() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  migrate          Apply database migrations (default)"
    echo "  token            Update Mapbox token in .env"
    echo "  restart          Restart Django service"
    echo "  status           Show migration and service status"
    echo "  merge            Create and apply merge migration"
    echo "  resolve          Resolve migration conflict (marks 0005 as fake)"
    echo ""
}

# Apply migrations
apply_migrations() {
    echo -e "${GREEN}=========================================="
    echo "Applying Database Migrations"
    echo "==========================================${NC}"
    echo ""

    remote_exec << 'ENDSSH'
        BACKEND_DIR=$(if [ -d "/opt/daydo/app" ]; then echo "/opt/daydo/app"; elif [ -d "/opt/daydo" ]; then echo "/opt/daydo"; elif [ -d "/home/ubuntu/daydo-backend" ]; then echo "/home/ubuntu/daydo-backend"; else echo ""; fi)
        
        if [ -z "$BACKEND_DIR" ]; then
            echo "Error: Could not find backend directory"
            exit 1
        fi
        
        cd "$BACKEND_DIR"
        echo "Working directory: $(pwd)"
        echo ""
        
        # Activate virtual environment
        if [ -d "venv" ]; then
            source venv/bin/activate
        elif [ -d ".venv" ]; then
            source .venv/bin/activate
        elif [ -d "/opt/daydo/venv" ]; then
            source /opt/daydo/venv/bin/activate
        fi
        
        # Use python3
        PYTHON_CMD="python3"
        if ! command -v python3 &> /dev/null; then
            PYTHON_CMD="python"
        fi
        
        # Pull latest changes if git repo
        if [ -d ".git" ]; then
            echo "Pulling latest changes..."
            git stash || true
            git pull origin main || git pull || true
            git stash pop || true
            echo ""
        fi
        
        # Check for pending migrations
        PENDING=$($PYTHON_CMD manage.py showmigrations daydo | grep -E "\[ \]" | wc -l)
        if [ "$PENDING" -eq 0 ]; then
            echo "No pending migrations."
            exit 0
        fi
        
        echo "Found $PENDING pending migration(s)"
        echo ""
        
        # Apply migrations
        echo "Applying migrations..."
        $PYTHON_CMD manage.py migrate daydo
        
        echo ""
        echo "Verifying migration status..."
        $PYTHON_CMD manage.py showmigrations daydo | tail -10
        
        # Restart service
        if systemctl is-active --quiet daydo-gunicorn 2>/dev/null; then
            echo ""
            echo "Restarting Gunicorn service..."
            sudo systemctl restart daydo-gunicorn
        fi
        
        echo ""
        echo "✅ Migrations applied successfully!"
ENDSSH
}

# Update Mapbox token
update_token() {
    echo -e "${GREEN}=========================================="
    echo "Updating Mapbox Token"
    echo "==========================================${NC}"
    echo ""
    
    MAPBOX_TOKEN="pk.eyJ1IjoiZ2VyZGlnZXJkc2VuIiwiYSI6ImNtaHV5anRidzA0bG0ybXNrNTdoZms1N2kifQ.4e-ng27Yaul9NjzDwCeUfA"
    
    remote_exec << ENDSSH
        BACKEND_DIR=\$(if [ -d "/opt/daydo/app" ]; then echo "/opt/daydo/app"; elif [ -d "/opt/daydo" ]; then echo "/opt/daydo"; elif [ -d "/home/ubuntu/daydo-backend" ]; then echo "/home/ubuntu/daydo-backend"; else echo ""; fi)
        
        if [ -z "\$BACKEND_DIR" ]; then
            echo "Error: Could not find backend directory"
            exit 1
        fi
        
        cd "\$BACKEND_DIR"
        
        # Create .env if needed
        if [ ! -f .env ]; then
            touch .env
        fi
        
        # Update token
        if grep -q '^MAPBOX_PUBLIC_TOKEN=' .env; then
            sed -i 's|^MAPBOX_PUBLIC_TOKEN=.*|MAPBOX_PUBLIC_TOKEN=${MAPBOX_TOKEN}|' .env
            echo "✅ Token updated"
        else
            echo "MAPBOX_PUBLIC_TOKEN=${MAPBOX_TOKEN}" >> .env
            echo "✅ Token added"
        fi
        
        echo ""
        echo "Verification:"
        grep MAPBOX_PUBLIC_TOKEN .env
        
        # Restart service
        if systemctl is-active --quiet daydo-gunicorn 2>/dev/null; then
            echo ""
            echo "Restarting Gunicorn service..."
            sudo systemctl restart daydo-gunicorn
        fi
ENDSSH
}

# Restart service
restart_service() {
    echo -e "${GREEN}Restarting Django service...${NC}"
    remote_exec "sudo systemctl restart daydo-gunicorn && sudo systemctl status daydo-gunicorn --no-pager | head -5"
}

# Show status
show_status() {
    echo -e "${GREEN}=========================================="
    echo "Backend Status"
    echo "==========================================${NC}"
    echo ""
    
    remote_exec << 'ENDSSH'
        BACKEND_DIR=$(if [ -d "/opt/daydo/app" ]; then echo "/opt/daydo/app"; elif [ -d "/opt/daydo" ]; then echo "/opt/daydo"; elif [ -d "/home/ubuntu/daydo-backend" ]; then echo "/home/ubuntu/daydo-backend"; else echo ""; fi)
        
        if [ -z "$BACKEND_DIR" ]; then
            echo "Error: Could not find backend directory"
            exit 1
        fi
        
        cd "$BACKEND_DIR"
        
        # Activate venv
        if [ -d "venv" ]; then
            source venv/bin/activate
        elif [ -d ".venv" ]; then
            source .venv/bin/activate
        elif [ -d "/opt/daydo/venv" ]; then
            source /opt/daydo/venv/bin/activate
        fi
        
        PYTHON_CMD="python3"
        if ! command -v python3 &> /dev/null; then
            PYTHON_CMD="python"
        fi
        
        echo "Migration Status:"
        $PYTHON_CMD manage.py showmigrations daydo | tail -10
        echo ""
        
        echo "Service Status:"
        sudo systemctl status daydo-gunicorn --no-pager | head -5
        echo ""
        
        echo "Token Status:"
        if [ -f .env ] && grep -q MAPBOX_PUBLIC_TOKEN .env; then
            echo "✅ Mapbox token configured"
        else
            echo "❌ Mapbox token not found"
        fi
ENDSSH
}

# Create merge migration
create_merge() {
    echo -e "${GREEN}Creating merge migration...${NC}"
    remote_exec << 'ENDSSH'
        BACKEND_DIR=$(if [ -d "/opt/daydo/app" ]; then echo "/opt/daydo/app"; elif [ -d "/opt/daydo" ]; then echo "/opt/daydo"; elif [ -d "/home/ubuntu/daydo-backend" ]; then echo "/home/ubuntu/daydo-backend"; else echo ""; fi)
        cd "$BACKEND_DIR"
        
        if [ -d "venv" ]; then source venv/bin/activate; elif [ -d ".venv" ]; then source .venv/bin/activate; elif [ -d "/opt/daydo/venv" ]; then source /opt/daydo/venv/bin/activate; fi
        
        PYTHON_CMD="python3"
        if ! command -v python3 &> /dev/null; then PYTHON_CMD="python"; fi
        
        $PYTHON_CMD manage.py makemigrations --merge daydo --noinput
        $PYTHON_CMD manage.py migrate daydo
        
        if systemctl is-active --quiet daydo-gunicorn 2>/dev/null; then
            sudo systemctl restart daydo-gunicorn
        fi
ENDSSH
}

# Resolve migration conflict
resolve_conflict() {
    echo -e "${YELLOW}Resolving migration conflict (marking 0005 as fake)...${NC}"
    remote_exec << 'ENDSSH'
        BACKEND_DIR=$(if [ -d "/opt/daydo/app" ]; then echo "/opt/daydo/app"; elif [ -d "/opt/daydo" ]; then echo "/opt/daydo"; elif [ -d "/home/ubuntu/daydo-backend" ]; then echo "/home/ubuntu/daydo-backend"; else echo ""; fi)
        cd "$BACKEND_DIR"
        
        if [ -d "venv" ]; then source venv/bin/activate; elif [ -d ".venv" ]; then source .venv/bin/activate; elif [ -d "/opt/daydo/venv" ]; then source /opt/daydo/venv/bin/activate; fi
        
        PYTHON_CMD="python3"
        if ! command -v python3 &> /dev/null; then PYTHON_CMD="python"; fi
        
        $PYTHON_CMD manage.py migrate daydo 0005_todolist_todotask --fake
        $PYTHON_CMD manage.py migrate daydo
        
        if systemctl is-active --quiet daydo-gunicorn 2>/dev/null; then
            sudo systemctl restart daydo-gunicorn
        fi
ENDSSH
}

# Main script logic
COMMAND=${1:-migrate}

case "$COMMAND" in
    migrate)
        apply_migrations
        ;;
    token)
        update_token
        ;;
    restart)
        restart_service
        ;;
    status)
        show_status
        ;;
    merge)
        create_merge
        ;;
    resolve)
        resolve_conflict
        ;;
    *)
        show_usage
        exit 1
        ;;
esac

