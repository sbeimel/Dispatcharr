#!/bin/bash

# Fix Migration Conflict - Remove duplicate 0020_add_proxy_field.py

echo "🔧 Fixing migration conflict..."

# Check if running in Docker container
if [ -f "/.dockerenv" ]; then
    echo "Running inside Docker container"
    MIGRATION_FILE="/app/apps/m3u/migrations/0020_add_proxy_field.py"
else
    echo "Running on host"
    MIGRATION_FILE="apps/m3u/migrations/0020_add_proxy_field.py"
fi

# Remove duplicate migration if it exists
if [ -f "$MIGRATION_FILE" ]; then
    echo "❌ Removing duplicate migration: $MIGRATION_FILE"
    rm "$MIGRATION_FILE"
    echo "✅ Duplicate migration removed"
else
    echo "✅ No duplicate migration found"
fi

echo ""
echo "Migration conflict fixed!"
echo ""
echo "Next steps:"
echo "1. Rebuild Docker image (if using Docker)"
echo "2. Restart container"
echo "3. Migrations should run successfully"
