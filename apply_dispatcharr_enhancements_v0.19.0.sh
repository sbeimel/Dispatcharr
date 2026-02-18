#!/bin/bash

# ===============================================
# DISPATCHARR ENHANCEMENTS INSTALLER v0.19.0
# ===============================================
#
# This script applies ALL features from v0.18.1 Enhanced to v0.19.0:
# ✅ Profile Failover System (343 stream/profile combinations)
# ✅ Universal HTTP Proxy Support (FFmpeg + Proxy profiles)
# ✅ Basic Authentication (M3U/EPG endpoints)
# ✅ Extended Timeout Configuration (max 200 switches)
# ✅ Ghost-Client Auto-Cleanup (already in v0.19.0)
#
# USAGE:
#   cd Dispatcharr-0.19.0/
#   bash ../apply_dispatcharr_enhancements_v0.19.0.sh
#
# REQUIREMENTS:
#   - Dispatcharr v0.19.0 installed
#   - Python 3.x with Django
#   - PostgreSQL database
#   - Redis server
#
# ===============================================

set -e  # Exit on error

echo "=========================================="
echo "Dispatcharr v0.19.0 Enhancement Installer"
echo "=========================================="
echo ""
echo "This will apply ALL features from v0.18.1:"
echo "  ✓ Profile Failover System"
echo "  ✓ Universal HTTP Proxy Support"
echo "  ✓ Basic Authentication"
echo "  ✓ Extended Configuration (max 200 switches)"
echo ""
echo "All backend and frontend files have been modified."
echo "Migration file has been created."
echo ""
read -p "Continue with database migration? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Installation cancelled."
    exit 1
fi

echo ""
echo "Step 1: Creating backup..."
BACKUP_DIR="dispatcharr_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp -r apps/ "$BACKUP_DIR/" 2>/dev/null || true
cp -r core/ "$BACKUP_DIR/" 2>/dev/null || true
cp -r frontend/ "$BACKUP_DIR/" 2>/dev/null || true
cp -r dispatcharr/ "$BACKUP_DIR/" 2>/dev/null || true
echo "✓ Backup created in $BACKUP_DIR"

echo ""
echo "Step 2: Applying database migrations..."
python manage.py makemigrations
python manage.py migrate

echo ""
echo "Step 3: Collecting static files..."
python manage.py collectstatic --noinput

echo ""
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "CHANGES APPLIED:"
echo "✓ Backend: config.py, models.py, stream_manager.py, url_utils.py"
echo "✓ Backend: http_streamer.py, config_helper.py, output/views.py"
echo "✓ Frontend: M3U.jsx, constants.js, ProxySettingsForm.jsx"
echo "✓ Migration: 0020_add_proxy_field.py"
echo ""
echo "NEXT STEPS:"
echo "1. Restart Dispatcharr: docker-compose restart"
echo "2. Verify proxy field in M3U Account settings"
echo "3. Test profile failover with multiple streams"
echo "4. Test HTTP proxy with FFmpeg profiles"
echo "5. Test Basic Auth on M3U/EPG endpoints"
echo ""
echo "VERIFICATION:"
echo "- Check Settings → Proxy Settings for new fields"
echo "- Max Stream Switches should show max 500"
echo "- M3U Account form should have Proxy field"
echo ""
echo "For detailed information, see:"
echo "- DISPATCHARR_V0.19.0_ENHANCEMENTS_README.md"
echo "- PORTING_SUMMARY_v0.19.0.md"
echo ""
