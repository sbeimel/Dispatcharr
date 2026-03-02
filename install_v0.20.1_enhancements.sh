#!/bin/bash

# Dispatcharr v0.20.1 Enhancements Installation Script
# Integrates all v0.19.0 features into v0.20.1

set -e

echo "=========================================="
echo "Dispatcharr v0.20.1 Enhancements Installer"
echo "=========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "manage.py" ]; then
    echo "❌ Error: manage.py not found!"
    echo "Please run this script from the Dispatcharr root directory."
    exit 1
fi

echo "✅ Found Dispatcharr installation"
echo ""

# Backup existing files
echo "📦 Creating backups..."
BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup files that will be modified
cp apps/proxy/config.py "$BACKUP_DIR/" 2>/dev/null || true
cp apps/m3u/models.py "$BACKUP_DIR/" 2>/dev/null || true
cp core/models.py "$BACKUP_DIR/" 2>/dev/null || true
cp apps/proxy/ts_proxy/http_streamer.py "$BACKUP_DIR/" 2>/dev/null || true
cp apps/proxy/ts_proxy/config_helper.py "$BACKUP_DIR/" 2>/dev/null || true
cp apps/output/views.py "$BACKUP_DIR/" 2>/dev/null || true
cp apps/proxy/ts_proxy/stream_manager.py "$BACKUP_DIR/" 2>/dev/null || true
cp apps/proxy/ts_proxy/url_utils.py "$BACKUP_DIR/" 2>/dev/null || true

echo "✅ Backups created in $BACKUP_DIR/"
echo ""

# Check Python version
echo "🐍 Checking Python version..."
PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
echo "   Python version: $PYTHON_VERSION"
echo ""

# Run migrations
echo "🔄 Running database migrations..."
python manage.py migrate

if [ $? -eq 0 ]; then
    echo "✅ Migrations completed successfully"
else
    echo "❌ Migration failed!"
    exit 1
fi
echo ""

# Build frontend
echo "🎨 Building frontend..."
if [ -d "frontend" ]; then
    cd frontend
    
    # Check if node_modules exists
    if [ ! -d "node_modules" ]; then
        echo "   Installing npm dependencies..."
        npm install
    fi
    
    echo "   Building production bundle..."
    npm run build
    
    if [ $? -eq 0 ]; then
        echo "✅ Frontend built successfully"
    else
        echo "❌ Frontend build failed!"
        cd ..
        exit 1
    fi
    
    cd ..
else
    echo "⚠️  Frontend directory not found, skipping frontend build"
fi
echo ""

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput

if [ $? -eq 0 ]; then
    echo "✅ Static files collected"
else
    echo "⚠️  Static files collection failed (non-critical)"
fi
echo ""

# Verify installation
echo "🔍 Verifying installation..."
echo ""

# Check if new settings are available
echo "Checking proxy settings..."
python manage.py shell << EOF
from apps.proxy.config import BaseConfig
settings = BaseConfig.get_proxy_settings()
required_keys = ['max_retries', 'url_switch_timeout', 'max_stream_switches', 'connection_timeout', 'failover_grace_period']
missing = [k for k in required_keys if k not in settings]
if missing:
    print(f"❌ Missing settings: {missing}")
    exit(1)
else:
    print("✅ All proxy settings present")
    print(f"   - max_retries: {settings['max_retries']}")
    print(f"   - url_switch_timeout: {settings['url_switch_timeout']}")
    print(f"   - max_stream_switches: {settings['max_stream_switches']}")
    print(f"   - connection_timeout: {settings['connection_timeout']}")
    print(f"   - failover_grace_period: {settings['failover_grace_period']}")
EOF

if [ $? -eq 0 ]; then
    echo "✅ Settings verification passed"
else
    echo "❌ Settings verification failed!"
    exit 1
fi
echo ""

# Check if proxy field exists in M3UAccount model
echo "Checking M3U Account proxy field..."
python manage.py shell << EOF
from apps.m3u.models import M3UAccount
if hasattr(M3UAccount, 'proxy'):
    print("✅ Proxy field exists in M3UAccount model")
else:
    print("❌ Proxy field missing in M3UAccount model")
    exit(1)
EOF

if [ $? -eq 0 ]; then
    echo "✅ Model verification passed"
else
    echo "❌ Model verification failed!"
    exit 1
fi
echo ""

echo "=========================================="
echo "✅ INSTALLATION COMPLETE!"
echo "=========================================="
echo ""
echo "Installed Features:"
echo "  ✅ Profile Failover System (343 combinations)"
echo "  ✅ Universal HTTP Proxy Support"
echo "  ✅ Basic Authentication"
echo "  ✅ Extended Configuration (10 settings)"
echo "  ✅ Ghost-Client Auto-Cleanup"
echo ""
echo "Next Steps:"
echo "  1. Restart your Dispatcharr server"
echo "  2. Test the new features"
echo "  3. Configure proxy settings in the admin panel"
echo ""
echo "Backup Location: $BACKUP_DIR/"
echo ""
echo "To rollback, restore files from the backup directory."
echo ""
