#!/bin/bash

# Test script to verify Django migrations work with proper SECRET_KEY

echo "🧪 Testing Django migrations..."

# Set required environment variables
export DJANGO_SECRET_KEY="test-secret-key-for-migration-testing"
export POSTGRES_DB="dispatcharr"
export POSTGRES_USER="dispatch"
export POSTGRES_PASSWORD="secret"
export POSTGRES_HOST="localhost"
export POSTGRES_PORT="5432"
export REDIS_HOST="localhost"
export REDIS_DB="0"

# Test Django settings loading
echo "📋 Testing Django settings..."
python -c "
import os
import sys
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dispatcharr.settings')
import django
django.setup()
from django.conf import settings
print(f'✅ Django settings loaded successfully')
print(f'✅ SECRET_KEY is set: {bool(settings.SECRET_KEY)}')
print(f'✅ Database engine: {settings.DATABASES[\"default\"][\"ENGINE\"]}')
"

# Test migration dry run
echo "🔍 Testing migration dry run..."
python manage.py migrate --dry-run --verbosity=2

echo "✅ Migration test completed!"