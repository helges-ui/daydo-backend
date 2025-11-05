#!/bin/bash
# Script to apply Phase 2 & 3 migrations on the server
# Run this on the Lightsail server

set -e  # Exit on error

echo "=========================================="
echo "Applying Phase 2 & 3 Database Migrations"
echo "=========================================="

# Navigate to backend directory
cd /home/ubuntu/daydo-backend || cd ~/daydo-backend || {
    echo "Error: Could not find backend directory"
    exit 1
}

echo "Current directory: $(pwd)"
echo ""

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
    echo "Pulling latest changes from git..."
    git pull || echo "Warning: Git pull failed, continuing anyway..."
    echo ""
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

