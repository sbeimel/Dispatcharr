#!/bin/bash

# ===============================================
# DISPATCHARR HTTP PROXY PREVIEW QUICK FIX
# ===============================================
# 
# SIMPLE 5-MINUTE SOLUTION
# This script applies a minimal change to enable HTTP proxy
# support for preview functionality with just a few lines of code.
#
# WHAT IT DOES:
# - Adds automatic proxy detection to validate_stream_url()
# - Uses existing M3U account proxy settings
# - No complex changes, no breaking modifications
# - Works with existing installations
#
# USAGE:
#   ./apply_proxy_preview_quickfix.sh [OPTIONS]
#
# OPTIONS:
#   -d, --dry-run     Show what would be changed without applying
#   -v, --verbose     Enable verbose output
#   -h, --help        Show this help message
#
# ===============================================

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Configuration variables
DRY_RUN=false
VERBOSE=false

echo -e "${BLUE}${BOLD}===============================================${NC}"
echo -e "${BLUE}${BOLD}  DISPATCHARR PROXY PREVIEW QUICK FIX${NC}"
echo -e "${BLUE}${BOLD}===============================================${NC}"
echo ""

# Function to print usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -d, --dry-run     Show what would be changed without applying"
    echo "  -v, --verbose     Enable verbose output"
    echo "  -h, --help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                Apply the quick fix"
    echo "  $0 --dry-run      Preview changes without applying"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
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

# Display configuration
echo -e "${CYAN}Configuration:${NC}"
echo "  Dry Run: $DRY_RUN"
echo "  Verbose: $VERBOSE"
echo ""

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_verbose() {
    [ "$VERBOSE" = true ] && echo -e "${CYAN}[VERBOSE]${NC} $1"
}

# Check if we're in a Dispatcharr directory
check_dispatcharr_directory() {
    if [ ! -f "manage.py" ] || [ ! -d "apps/proxy/ts_proxy" ]; then
        log_error "This doesn't appear to be a Dispatcharr directory"
        log_error "Please run this script from the Dispatcharr root directory"
        exit 1
    fi
    log_success "Dispatcharr directory detected"
}

# Check if proxy field exists in M3U model
check_proxy_field() {
    local m3u_models="apps/m3u/models.py"
    if [ ! -f "$m3u_models" ]; then
        log_error "M3U models file not found: $m3u_models"
        exit 1
    fi
    
    if grep -q "proxy.*CharField" "$m3u_models"; then
        log_success "M3U Account proxy field exists"
        return 0
    else
        log_error "M3U Account proxy field not found"
        log_error "Please ensure the proxy field is added to the M3UAccount model first"
        log_error "You may need to apply the main dispatcharr_enhancements.patch first"
        exit 1
    fi
}

# Apply the quick fix
apply_quick_fix() {
    local url_utils="apps/proxy/ts_proxy/url_utils.py"
    
    if [ ! -f "$url_utils" ]; then
        log_error "URL utils file not found: $url_utils"
        exit 1
    fi
    
    # Check if already applied
    if grep -q "Auto-detect and use proxy from M3U account" "$url_utils"; then
        log_success "Quick fix already applied"
        return 0
    fi
    
    if [ "$DRY_RUN" = true ]; then
        log_info "Would apply quick fix to $url_utils"
        if [ -f "proxy_preview_quickfix.patch" ]; then
            if patch --dry-run -p1 < proxy_preview_quickfix.patch >/dev/null 2>&1; then
                log_success "Quick fix patch would apply cleanly"
            else
                log_warning "Quick fix patch has conflicts"
            fi
        else
            log_warning "Quick fix patch file not found"
        fi
        return 0
    fi
    
    # Create backup
    cp "$url_utils" "${url_utils}.backup.$(date +%Y%m%d-%H%M%S)"
    log_verbose "Created backup of $url_utils"
    
    # Apply patch if available
    if [ -f "proxy_preview_quickfix.patch" ]; then
        if patch -p1 < proxy_preview_quickfix.patch >/dev/null 2>&1; then
            log_success "Applied quick fix patch successfully"
            return 0
        else
            log_warning "Patch failed, applying manual fix..."
        fi
    fi
    
    # Manual application (fallback)
    log_info "Applying manual quick fix..."
    
    # Find the line where session.headers.update(headers) appears
    local line_num=$(grep -n "session.headers.update(headers)" "$url_utils" | head -1 | cut -d: -f1)
    
    if [ -z "$line_num" ]; then
        log_error "Could not find insertion point in $url_utils"
        exit 1
    fi
    
    # Insert the quick fix code after the headers line
    local temp_file=$(mktemp)
    head -n "$line_num" "$url_utils" > "$temp_file"
    
    cat >> "$temp_file" << 'EOF'

        # QUICK FIX: Auto-detect and use proxy from M3U account
        try:
            from apps.channels.models import Stream
            from urllib.parse import urlparse
            
            # Try to find stream by URL and get proxy from M3U account
            parsed_url = urlparse(url)
            if parsed_url.netloc:
                streams = Stream.objects.filter(url__icontains=parsed_url.netloc)
                if streams.exists():
                    stream = streams.first()
                    if hasattr(stream, 'm3u_account') and stream.m3u_account and stream.m3u_account.proxy:
                        proxy = stream.m3u_account.proxy.strip()
                        if proxy:
                            session.proxies = {'http': proxy, 'https': proxy}
                            logger.info(f"Using proxy for stream validation: {proxy}")
        except Exception as e:
            logger.debug(f"Could not auto-detect proxy for validation: {e}")
            # Continue without proxy - not critical
EOF
    
    tail -n +$((line_num + 1)) "$url_utils" >> "$temp_file"
    mv "$temp_file" "$url_utils"
    
    log_success "Applied manual quick fix successfully"
}

# Test the fix
test_quick_fix() {
    log_info "Testing quick fix..."
    
    if [ "$DRY_RUN" = true ]; then
        log_info "Would test the quick fix (dry run)"
        return 0
    fi
    
    # Simple syntax check
    if python3 -m py_compile apps/proxy/ts_proxy/url_utils.py 2>/dev/null; then
        log_success "Quick fix syntax is valid"
    else
        log_error "Quick fix introduced syntax errors"
        exit 1
    fi
}

# Main execution
main() {
    log_info "Starting HTTP Proxy Preview Quick Fix..."
    
    # Pre-flight checks
    check_dispatcharr_directory
    check_proxy_field
    
    # Apply the fix
    apply_quick_fix
    test_quick_fix
    
    # Summary
    echo ""
    echo -e "${BOLD}===============================================${NC}"
    echo -e "${BOLD}  QUICK FIX COMPLETED${NC}"
    echo -e "${BOLD}===============================================${NC}"
    echo ""
    
    if [ "$DRY_RUN" = true ]; then
        echo -e "${CYAN}DRY RUN COMPLETED${NC}"
        echo "No changes were made. Run without --dry-run to apply the fix."
    else
        echo -e "${GREEN}${BOLD}✓ HTTP Proxy Preview Quick Fix Applied!${NC}"
        echo ""
        echo -e "${BLUE}What was changed:${NC}"
        echo "• Added automatic proxy detection to validate_stream_url()"
        echo "• Uses existing M3U account proxy settings"
        echo "• Only ~15 lines of code added"
        echo "• No breaking changes"
        echo ""
        echo -e "${BLUE}Next Steps:${NC}"
        echo "1. Restart Dispatcharr services"
        echo "2. Configure HTTP proxy in M3U account settings"
        echo "3. Test preview functionality"
        echo "4. Check logs for proxy usage: 'Using proxy for stream validation'"
    fi
    
    echo ""
    echo -e "${CYAN}Simple and effective! 🚀${NC}"
}

# Run main function
main

exit 0