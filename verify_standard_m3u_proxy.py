#!/usr/bin/env python3
"""
Verification script for Standard M3U Proxy Support
Checks if proxy fields are available for all account types
"""

import re
import sys

def check_frontend():
    """Check if frontend has proxy fields outside XC condition"""
    print("=" * 80)
    print("FRONTEND VERIFICATION")
    print("=" * 80)
    print()
    
    filepath = "frontend/src/components/forms/M3U.jsx"
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        all_pass = True
        
        # Check 1: Proxy TextInput exists
        print("--- Check 1: HTTP Proxy Field ---")
        if re.search(r'<TextInput\s+label="HTTP Proxy"', content):
            print("✅ HTTP Proxy TextInput found")
        else:
            print("❌ HTTP Proxy TextInput not found")
            all_pass = False
        
        # Check 2: Proxy for API Switch exists
        print("\n--- Check 2: Proxy for API Switch ---")
        if re.search(r'<Switch\s+label="Use Proxy for API Calls"', content):
            print("✅ Use Proxy for API Calls Switch found")
        else:
            print("❌ Use Proxy for API Calls Switch not found")
            all_pass = False
        
        # Check 3: Proxy fields BEFORE XC condition
        print("\n--- Check 3: Field Position ---")
        
        # Find proxy field position
        proxy_match = re.search(r'<TextInput\s+label="HTTP Proxy"', content)
        # Find XC condition position
        xc_match = re.search(r"form\.getValues\(\)\.account_type\s*==\s*['\"]XC['\"]", content)
        
        if proxy_match and xc_match:
            proxy_pos = proxy_match.start()
            xc_pos = xc_match.start()
            
            if proxy_pos < xc_pos:
                print("✅ Proxy fields are BEFORE XC condition (available for all account types)")
            else:
                print("❌ Proxy fields are INSIDE XC condition (only for Xtream Codes)")
                all_pass = False
        else:
            print("❌ Could not determine field positions")
            all_pass = False
        
        # Check 4: Comment indicating availability for all types
        print("\n--- Check 4: Documentation Comment ---")
        if re.search(r'available for ALL account types|HTTP Proxy fields.*ALL', content, re.IGNORECASE):
            print("✅ Comment indicates proxy fields are for all account types")
        else:
            print("⚠️  No comment found (optional)")
        
        # Check 5: Description updated
        print("\n--- Check 5: Field Description ---")
        proxy_desc_match = re.search(
            r'<TextInput\s+label="HTTP Proxy".*?description="([^"]+)"',
            content,
            re.DOTALL
        )
        if proxy_desc_match:
            desc = proxy_desc_match.group(1)
            print(f"✅ Description: {desc}")
            if "Live TV" in desc or "VOD" in desc or "streaming" in desc.lower():
                print("✅ Description mentions streaming types")
            else:
                print("⚠️  Description could be more specific (optional)")
        else:
            print("⚠️  Could not extract description")
        
        return all_pass
        
    except FileNotFoundError:
        print(f"❌ File not found: {filepath}")
        print("   Make sure you're in the Dispatcharr root directory")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def check_backend():
    """Verify backend already supports proxy for all types"""
    print("\n" + "=" * 80)
    print("BACKEND VERIFICATION (Should already work)")
    print("=" * 80)
    print()
    
    filepath = "apps/m3u/models.py"
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        all_pass = True
        
        # Check 1: get_proxy_for_streaming exists
        print("--- Check 1: get_proxy_for_streaming() ---")
        if re.search(r'def get_proxy_for_streaming\(self\):', content):
            print("✅ get_proxy_for_streaming() method exists")
        else:
            print("❌ get_proxy_for_streaming() method not found")
            all_pass = False
        
        # Check 2: No account_type check in get_proxy_for_streaming
        print("\n--- Check 2: Account Type Independence ---")
        method_match = re.search(
            r'def get_proxy_for_streaming\(self\):.*?(?=def\s|\Z)',
            content,
            re.DOTALL
        )
        if method_match:
            method_body = method_match.group(0)
            if 'account_type' not in method_body:
                print("✅ get_proxy_for_streaming() is account-type independent")
            else:
                print("❌ get_proxy_for_streaming() checks account_type (should not)")
                all_pass = False
        else:
            print("⚠️  Could not extract method body")
        
        # Check 3: proxy field exists
        print("\n--- Check 3: Proxy Field in Model ---")
        if re.search(r'proxy\s*=\s*models\.CharField', content):
            print("✅ proxy field exists in M3UAccount model")
        else:
            print("❌ proxy field not found in M3UAccount model")
            all_pass = False
        
        # Check 4: proxy_for_api field exists
        print("\n--- Check 4: Proxy for API Field ---")
        if re.search(r'proxy_for_api\s*=\s*models\.BooleanField', content):
            print("✅ proxy_for_api field exists in M3UAccount model")
        else:
            print("❌ proxy_for_api field not found in M3UAccount model")
            all_pass = False
        
        return all_pass
        
    except FileNotFoundError:
        print(f"❌ File not found: {filepath}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def check_serializer():
    """Check if serializer includes proxy fields"""
    print("\n" + "=" * 80)
    print("SERIALIZER VERIFICATION")
    print("=" * 80)
    print()
    
    filepath = "apps/m3u/serializers.py"
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        all_pass = True
        
        # Find M3UAccountSerializer fields list
        print("--- M3UAccountSerializer Fields ---")
        fields_match = re.search(
            r'class M3UAccountSerializer.*?fields\s*=\s*\[(.*?)\]',
            content,
            re.DOTALL
        )
        
        if fields_match:
            fields_str = fields_match.group(1)
            
            if '"proxy"' in fields_str or "'proxy'" in fields_str:
                print("✅ 'proxy' field in serializer")
            else:
                print("❌ 'proxy' field missing from serializer")
                all_pass = False
            
            if '"proxy_for_api"' in fields_str or "'proxy_for_api'" in fields_str:
                print("✅ 'proxy_for_api' field in serializer")
            else:
                print("❌ 'proxy_for_api' field missing from serializer")
                all_pass = False
        else:
            print("⚠️  Could not find M3UAccountSerializer fields list")
        
        return all_pass
        
    except FileNotFoundError:
        print(f"❌ File not found: {filepath}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    frontend_ok = check_frontend()
    backend_ok = check_backend()
    serializer_ok = check_serializer()
    
    print("\n" + "=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)
    
    if frontend_ok and backend_ok and serializer_ok:
        print("\n✅ ALL CHECKS PASSED")
        print("\nStandard M3U Proxy Support is implemented correctly!")
        print("\nNext steps:")
        print("1. Build frontend: cd frontend && npm run build")
        print("2. Restart service: docker-compose restart")
        print("3. Test in WebUI:")
        print("   - Create/Edit Standard M3U Account")
        print("   - Verify HTTP Proxy fields are visible")
        print("   - Enter proxy URL and save")
        print("   - Start stream and check logs for 'Using proxy'")
        return 0
    else:
        print("\n❌ SOME CHECKS FAILED")
        print("\nIssues found:")
        if not frontend_ok:
            print("- Frontend: Proxy fields may not be properly positioned")
        if not backend_ok:
            print("- Backend: Proxy support may not be complete")
        if not serializer_ok:
            print("- Serializer: Proxy fields may not be exposed in API")
        return 1

if __name__ == '__main__':
    sys.exit(main())
