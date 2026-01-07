#!/bin/bash

# Dispatcharr Enhancement Patch Application Script
# This script applies the enhancements patch and allows configuration of key parameters

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration values
DEFAULT_MAX_RETRIES=2
DEFAULT_URL_SWITCH_TIMEOUT=8
DEFAULT_FAILOVER_GRACE_PERIOD=20

# Configuration variables (can be overridden by environment variables or command line)
MAX_RETRIES=${MAX_RETRIES:-$DEFAULT_MAX_RETRIES}
URL_SWITCH_TIMEOUT=${URL_SWITCH_TIMEOUT:-$DEFAULT_URL_SWITCH_TIMEOUT}
FAILOVER_GRACE_PERIOD=${FAILOVER_GRACE_PERIOD:-$DEFAULT_FAILOVER_GRACE_PERIOD}

echo -e "${BLUE}=== Dispatcharr Enhancement Patch Application ===${NC}"
echo ""

# Function to print usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -r, --max-retries NUM          Set maximum retry attempts (default: $DEFAULT_MAX_RETRIES)"
    echo "  -t, --url-switch-timeout NUM   Set URL switch timeout in seconds (default: $DEFAULT_URL_SWITCH_TIMEOUT)"
    echo "  -f, --failover-grace NUM       Set failover grace period in seconds (default: $DEFAULT_FAILOVER_GRACE_PERIOD)"
    echo "  -h, --help                     Show this help message"
    echo ""
    echo "Environment variables:"
    echo "  MAX_RETRIES                    Override max retries"
    echo "  URL_SWITCH_TIMEOUT             Override URL switch timeout"
    echo "  FAILOVER_GRACE_PERIOD          Override failover grace period"
    echo ""
    echo "Examples:"
    echo "  $0                             Apply patch with default settings"
    echo "  $0 -r 3 -t 10 -f 30           Apply patch with custom settings"
    echo "  MAX_RETRIES=1 $0               Apply patch with 1 retry via environment variable"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -r|--max-retries)
            MAX_RETRIES="$2"
            shift 2
            ;;
        -t|--url-switch-timeout)
            URL_SWITCH_TIMEOUT="$2"
            shift 2
            ;;
        -f|--failover-grace)
            FAILOVER_GRACE_PERIOD="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            usage
            exit 1
            ;;
    esac
done

# Validate numeric inputs
if ! [[ "$MAX_RETRIES" =~ ^[0-9]+$ ]] || [ "$MAX_RETRIES" -lt 1 ] || [ "$MAX_RETRIES" -gt 10 ]; then
    echo -e "${RED}Error: MAX_RETRIES must be a number between 1 and 10${NC}"
    exit 1
fi

if ! [[ "$URL_SWITCH_TIMEOUT" =~ ^[0-9]+$ ]] || [ "$URL_SWITCH_TIMEOUT" -lt 1 ] || [ "$URL_SWITCH_TIMEOUT" -gt 60 ]; then
    echo -e "${RED}Error: URL_SWITCH_TIMEOUT must be a number between 1 and 60${NC}"
    exit 1
fi

if ! [[ "$FAILOVER_GRACE_PERIOD" =~ ^[0-9]+$ ]] || [ "$FAILOVER_GRACE_PERIOD" -lt 1 ] || [ "$FAILOVER_GRACE_PERIOD" -gt 120 ]; then
    echo -e "${RED}Error: FAILOVER_GRACE_PERIOD must be a number between 1 and 120${NC}"
    exit 1
fi

echo -e "${YELLOW}Configuration:${NC}"
echo "  Max Retries: $MAX_RETRIES"
echo "  URL Switch Timeout: ${URL_SWITCH_TIMEOUT}s"
echo "  Failover Grace Period: ${FAILOVER_GRACE_PERIOD}s"
echo ""

# Check if patch file exists
if [ ! -f "dispatcharr_enhancements.patch" ]; then
    echo -e "${RED}Error: dispatcharr_enhancements.patch not found in current directory${NC}"
    exit 1
fi

# Check if we're in a git repository (optional, for safety)
if [ -d ".git" ]; then
    echo -e "${YELLOW}Git repository detected. Creating backup branch...${NC}"
    BACKUP_BRANCH="backup-before-enhancement-$(date +%Y%m%d-%H%M%S)"
    git checkout -b "$BACKUP_BRANCH" 2>/dev/null || echo -e "${YELLOW}Warning: Could not create backup branch${NC}"
    git checkout - 2>/dev/null || true
fi

# Apply the patch
echo -e "${BLUE}Applying enhancement patch...${NC}"
if patch -p1 < dispatcharr_enhancements.patch; then
    echo -e "${GREEN}✓ Patch applied successfully${NC}"
else
    echo -e "${RED}✗ Failed to apply patch${NC}"
    echo -e "${YELLOW}This might be due to:${NC}"
    echo "  - Files already modified"
    echo "  - Different version of Dispatcharr"
    echo "  - Patch already applied"
    exit 1
fi

# Update configuration values in the patched files
echo -e "${BLUE}Updating configuration values...${NC}"

# Update apps/proxy/config.py with custom values
if [ -f "apps/proxy/config.py" ]; then
    sed -i "s/MAX_RETRIES = 2/MAX_RETRIES = $MAX_RETRIES/g" apps/proxy/config.py
    sed -i "s/URL_SWITCH_TIMEOUT = 8/URL_SWITCH_TIMEOUT = $URL_SWITCH_TIMEOUT/g" apps/proxy/config.py
    sed -i "s/FAILOVER_GRACE_PERIOD = 20/FAILOVER_GRACE_PERIOD = $FAILOVER_GRACE_PERIOD/g" apps/proxy/config.py
    echo -e "${GREEN}✓ Updated apps/proxy/config.py${NC}"
fi

# Update frontend default values
if [ -f "frontend/src/utils/forms/settings/ProxySettingsFormUtils.js" ]; then
    sed -i "s/max_retries: 2/max_retries: $MAX_RETRIES/g" frontend/src/utils/forms/settings/ProxySettingsFormUtils.js
    sed -i "s/url_switch_timeout: 8/url_switch_timeout: $URL_SWITCH_TIMEOUT/g" frontend/src/utils/forms/settings/ProxySettingsFormUtils.js
    sed -i "s/failover_grace_period: 20/failover_grace_period: $FAILOVER_GRACE_PERIOD/g" frontend/src/utils/forms/settings/ProxySettingsFormUtils.js
    echo -e "${GREEN}✓ Updated frontend default values${NC}"
fi

# Handle database migration for M3U proxy field
echo -e "${BLUE}Handling database migration...${NC}"
if command -v python3 &> /dev/null && [ -f "manage.py" ]; then
    # Check if migration 0019 already exists
    if [ -f "apps/m3u/migrations/0019_m3uaccount_proxy.py" ]; then
        echo -e "${YELLOW}Migration 0019_m3uaccount_proxy.py already exists${NC}"
        
        # Check if it's already applied
        MIGRATION_STATUS=$(python3 manage.py showmigrations m3u --plan 2>/dev/null | grep "0019_m3uaccount_proxy" || echo "not_found")
        
        if [[ "$MIGRATION_STATUS" == *"[X]"* ]]; then
            echo -e "${GREEN}✓ Migration already applied to database${NC}"
        elif [[ "$MIGRATION_STATUS" == *"[ ]"* ]]; then
            echo -e "${YELLOW}Migration exists but not applied. Running migration...${NC}"
            python3 manage.py migrate m3u 2>/dev/null && echo -e "${GREEN}✓ Migration applied successfully${NC}" || echo -e "${RED}✗ Migration failed${NC}"
        else
            echo -e "${YELLOW}Could not determine migration status. Please run 'python manage.py migrate' manually${NC}"
        fi
    else
        echo -e "${GREEN}✓ New migration included in patch (0019_m3uaccount_proxy.py)${NC}"
        echo -e "${BLUE}Applying migration...${NC}"
        python3 manage.py migrate m3u 2>/dev/null && echo -e "${GREEN}✓ Migration applied successfully${NC}" || echo -e "${RED}✗ Migration failed - please run 'python manage.py migrate' manually${NC}"
    fi
else
    echo -e "${YELLOW}Warning: Python3 or manage.py not found${NC}"
    echo -e "${YELLOW}Please run 'python manage.py migrate' manually after applying patch${NC}"
fi

# Create summary of changes
echo ""
echo -e "${GREEN}=== Enhancement Summary ===${NC}"
echo -e "${GREEN}✓ Profile Failover System:${NC}"
echo "  - Enhanced stream switching with profile failover"
echo "  - Tries alternative profiles before switching streams"
echo "  - Improved error tracking and logging"
echo ""
echo -e "${GREEN}✓ Basic Authentication for M3U/EPG:${NC}"
echo "  - Added HTTP Basic Auth support for /output/m3u endpoints"
echo "  - Integrates with existing user management system"
echo "  - Maintains backward compatibility"
echo ""
echo -e "${GREEN}✓ FFmpeg Proxy Support:${NC}"
echo "  - Added proxy field to M3U accounts"
echo "  - Frontend form updated with proxy configuration"
echo "  - Proxy support in stream profile command building"
echo ""
echo -e "${GREEN}✓ Configurable Settings:${NC}"
echo "  - Max retries: $MAX_RETRIES (reduced from 3)"
echo "  - URL switch timeout: ${URL_SWITCH_TIMEOUT}s"
echo "  - Failover grace period: ${FAILOVER_GRACE_PERIOD}s"
echo "  - All settings configurable via frontend"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo "1. Run database migration: ${YELLOW}python manage.py migrate${NC}"
echo "2. Restart Dispatcharr services"
echo "3. Configure proxy settings in M3U accounts via frontend"
echo "4. Test stream failover functionality"
echo ""
echo -e "${GREEN}Enhancement patch applied successfully!${NC}"

# Optional: Show git diff if in git repo
if [ -d ".git" ] && command -v git &> /dev/null; then
    echo ""
    echo -e "${BLUE}Git diff summary:${NC}"
    git diff --stat 2>/dev/null || true
fi