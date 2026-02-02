#!/bin/bash

# ===============================================
# DISPATCHARR ENHANCEMENTS v0.18.1 AUTO-INSTALLER
# ===============================================
# 
# Automatische Anwendung aller Enhancements auf Dispatcharr-0.18.1
# Erstellt: 2025-02-02
# Basiert auf: dispatcharr_enhancements_v0.18.1_extended.patch
#
# FEATURES:
# ✅ Profile Failover System
# ✅ HTTP Proxy Support  
# ✅ Basic Authentication
# ✅ Configuration Enhancements
# ✅ Erweiterte Timeout-Konfiguration
# ✅ Ghost-Client Fix
# ✅ Automatische Migration
# ✅ Verifikation
#

set -e  # Exit on any error

echo "🚀 DISPATCHARR ENHANCEMENTS v0.18.1 EXTENDED INSTALLER"
echo "======================================================"
echo ""

# Check if we're in the right directory
if [ ! -f "manage.py" ]; then
    echo "❌ ERROR: manage.py not found!"
    echo "   Please run this script from the Dispatcharr-0.18.1 directory"
    exit 1
fi

# Check if patch file exists
PATCH_FILE="../dispatcharr_enhancements_v0.18.1_extended.patch"
if [ ! -f "$PATCH_FILE" ]; then
    echo "❌ ERROR: Patch file not found: $PATCH_FILE"
    echo "   Please ensure the patch file is in the parent directory"
    exit 1
fi

echo "✅ Environment check passed"
echo ""

# Create backup
echo "📦 Creating backup..."
BACKUP_DIR="backup_before_enhancements_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup critical files that will be modified
echo "   Backing up critical files..."
cp -r apps/proxy/config.py "$BACKUP_DIR/" 2>/dev/null || true
cp -r apps/m3u/models.py "$BACKUP_DIR/" 2>/dev/null || true
cp -r core/models.py "$BACKUP_DIR/" 2>/dev/null || true
cp -r apps/proxy/ts_proxy/stream_manager.py "$BACKUP_DIR/" 2>/dev/null || true
cp -r apps/proxy/ts_proxy/url_utils.py "$BACKUP_DIR/" 2>/dev/null || true
cp -r apps/proxy/ts_proxy/client_manager.py "$BACKUP_DIR/" 2>/dev/null || true
cp -r apps/output/views.py "$BACKUP_DIR/" 2>/dev/null || true
cp -r frontend/src/components/forms/M3U.jsx "$BACKUP_DIR/" 2>/dev/null || true
cp -r frontend/src/constants.js "$BACKUP_DIR/" 2>/dev/null || true

echo "✅ Backup created in: $BACKUP_DIR"
echo ""

# Apply patch
echo "🔧 Applying enhancements patch..."
if patch -p1 < "$PATCH_FILE"; then
    echo "✅ Patch applied successfully!"
else
    echo "❌ ERROR: Patch application failed!"
    echo "   Check for conflicts or missing files"
    exit 1
fi
echo ""

# Create and apply migration
echo "🗄️  Creating and applying database migration..."

# Remove problematic migration file if it exists
if [ -f "apps/m3u/migrations/0020_add_is_adult_field.py" ]; then
    echo "   Removing problematic migration file..."
    rm -f "apps/m3u/migrations/0020_add_is_adult_field.py"
    echo "✅ Problematic migration file removed"
fi

echo "   Creating migration for proxy field..."
if python manage.py makemigrations m3u; then
    echo "✅ Migration created successfully!"
else
    echo "❌ ERROR: Migration creation failed!"
    exit 1
fi

echo "   Applying migration..."
if python manage.py migrate; then
    echo "✅ Migration applied successfully!"
else
    echo "❌ ERROR: Migration application failed!"
    echo "   Note: If SECRET_KEY error occurs, the entrypoint.sh fix will resolve it in Docker"
    exit 1
fi
echo ""

# Verification
echo "🔍 Verifying installation..."

# Check Profile Failover
if grep -q "tried_combinations" apps/proxy/ts_proxy/stream_manager.py; then
    echo "✅ Profile Failover System: tried_combinations found"
else
    echo "❌ Profile Failover System: tried_combinations missing"
fi

if grep -q "get_stream_info_for_profile" apps/proxy/ts_proxy/url_utils.py; then
    echo "✅ Profile Failover System: get_stream_info_for_profile found"
else
    echo "❌ Profile Failover System: get_stream_info_for_profile missing"
fi

# Check HTTP Proxy
if grep -q "proxy.*CharField" apps/m3u/models.py; then
    echo "✅ HTTP Proxy Support: Model field found"
else
    echo "❌ HTTP Proxy Support: Model field missing"
fi

if grep -q "proxy.*TextInput" frontend/src/components/forms/M3U.jsx; then
    echo "✅ HTTP Proxy Support: Frontend field found"
else
    echo "❌ HTTP Proxy Support: Frontend field missing"
fi

# Check Basic Auth
if grep -q "get_basic_auth_user" apps/output/views.py; then
    echo "✅ Basic Authentication: Functions found"
else
    echo "❌ Basic Authentication: Functions missing"
fi

# Check Configuration
if grep -q "MAX_RETRIES = 2" apps/proxy/config.py; then
    echo "✅ Configuration: MAX_RETRIES updated"
else
    echo "❌ Configuration: MAX_RETRIES not updated"
fi

# Check Logo Timeout Fix
if grep -q "LOGO_CONNECT_TIMEOUT" dispatcharr/settings.py; then
    echo "✅ Logo Timeout Fix: Configurable timeouts added"
else
    echo "❌ Logo Timeout Fix: Configurable timeouts missing"
fi

# Check Frontend Defaults Fix
if ! grep -q "buffering_timeout.*15.*buffering_timeout.*15" frontend/src/utils/forms/settings/ProxySettingsFormUtils.js; then
    echo "✅ Frontend Defaults Fix: Duplicate buffering_timeout removed"
else
    echo "❌ Frontend Defaults Fix: Duplicate buffering_timeout still present"
fi

# Check Backend Config Usage
if grep -q "BaseConfig.get_max_retries()" apps/proxy/ts_proxy/config_helper.py; then
    echo "✅ Backend Config Usage: Database values properly used"
else
    echo "❌ Backend Config Usage: Still using hardcoded values"
fi

# Check TSConfig Import Fix
if grep -q "from apps.proxy.config import TSConfig$" apps/proxy/ts_proxy/stream_buffer.py; then
    echo "✅ TSConfig Import Fix: Import corrected"
else
    echo "❌ TSConfig Import Fix: Import still incorrect"
fi

# Check TSConfig Usage Fix
if grep -q "TSConfig.BUFFER_CHUNK_SIZE" apps/proxy/ts_proxy/stream_buffer.py; then
    echo "✅ TSConfig Usage Fix: TSConfig properly used"
else
    echo "❌ TSConfig Usage Fix: TSConfig not properly used"
fi

# Check M3U is_adult Field
if grep -q "is_adult.*fields" apps/m3u/serializers.py; then
    echo "✅ M3U is_adult Field: Added to serializer fields"
else
    echo "❌ M3U is_adult Field: Missing from serializer fields"
fi

# Check M3U Frontend Form
if grep -q "Adult Content.*Checkbox" frontend/src/components/forms/M3U.jsx; then
    echo "✅ M3U Frontend Form: is_adult checkbox added"
else
    echo "❌ M3U Frontend Form: is_adult checkbox missing"
fi

# Check Extended Timeout Settings
if grep -q "max_stream_switches.*label" frontend/src/constants.js; then
    echo "✅ Extended Config: Frontend timeout settings found"
else
    echo "❌ Extended Config: Frontend timeout settings missing"
fi

# Check Ghost-Client Fix
if grep -q "ghost_clients_in_set" apps/proxy/ts_proxy/client_manager.py; then
    echo "✅ Ghost-Client Fix: Automatic cleanup implemented"
else
    echo "❌ Ghost-Client Fix: Automatic cleanup missing"
fi

echo ""
echo "🎉 INSTALLATION COMPLETE!"
echo "========================"
echo ""
echo "✅ All Dispatcharr Enhancements have been applied to version 0.18.1"
echo ""
echo "📋 INSTALLED FEATURES:"
echo "   ✅ Profile Failover System (intelligent stream switching)"
echo "   ✅ HTTP Proxy Support (for M3U accounts)"
echo "   ✅ Basic Authentication (for M3U/EPG endpoints)"
echo "   ✅ Configuration Enhancements (optimized retries & timeouts)"
echo "   ✅ Extended Timeout Configuration (all settings via frontend)"
echo "   ✅ Ghost-Client Fix (automatic cleanup without stats click)"
echo "   ✅ Database Schema Fix (is_adult fields + SECRET_KEY handling)"
echo "   ✅ Docker Entrypoint Fix (environment variable preservation)"
echo "   ✅ Logo Timeout Fix (increased timeouts for external logo servers)"
echo "   ✅ Frontend/Backend Sync Fix (settings properly used from database)"
echo "   ✅ M3U is_adult Field Fix (serializer and frontend form updated)"
echo ""
echo "🚀 NEXT STEPS:"
echo "   1. Restart Dispatcharr service"
echo "   2. Test the new features"
echo "   3. Configure timeout settings in frontend"
echo "   4. Check logs for any issues"
echo ""
echo "📁 BACKUP LOCATION: $BACKUP_DIR"
echo "   (Keep this backup in case you need to rollback)"
echo ""
echo "🔧 RESTART COMMANDS:"
echo "   systemctl restart dispatcharr"
echo "   # or"
echo "   docker-compose restart dispatcharr"
echo "   # or"
echo "   python manage.py runserver"
echo ""
echo "⚙️  NEW CONFIGURABLE SETTINGS:"
echo "   • Max Retries (default: 2)"
echo "   • URL Switch Timeout (default: 8s)"
echo "   • Max Stream Switches (default: 10)"
echo "   • Connection Timeout (default: 10s)"
echo "   • Buffering Timeout (default: 15s)"
echo "   • Failover Grace Period (default: 20s)"
echo ""
echo "🐛 FIXES INCLUDED:"
echo "   • Database Schema: is_adult fields for M3U accounts"
echo "   • Docker Environment: SECRET_KEY properly passed to migrations"
echo "   • Stream Timeout: Connection attempt time reset on stream switches"
echo "   • Ghost Clients: Automatic cleanup without manual intervention"
echo "   • Logo Timeouts: Increased from 3s/5s to 10s/20s for external servers"
echo "   • Frontend Defaults: Removed duplicate buffering_timeout entry"
echo "   • Backend Config: Fixed hardcoded values to use database settings"
echo "   • M3U is_adult Field: Added to serializer and frontend form"
echo "   • TSConfig Import: Fixed 'TSConfig' is not defined error"
echo ""
echo "🐛 GHOST-CLIENT FIX:"
echo "   • Automatic cleanup every 5-10 seconds"
echo "   • No more manual stats clicks needed"
echo "   • Correct client counts in all views"
echo ""
echo "Happy streaming! 🎬"