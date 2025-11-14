#!/bin/bash
# DEPRECATED: Use ./deploy.sh migrate instead
# This script is kept for backward compatibility

echo "⚠️  This script is deprecated. Use: ./deploy.sh migrate"
echo ""
exec ./deploy.sh migrate
