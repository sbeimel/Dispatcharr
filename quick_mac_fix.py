# Quick MAC address fix - paste this into Django shell
# python manage.py shell
# exec(open('quick_mac_fix.py').read())

from apps.m3u.models import M3UAccount, M3UAccountMac

# Find MAC accounts with mac_address but no MAC objects
accounts = M3UAccount.objects.filter(
    account_type='MAC',
    mac_address__isnull=False
).exclude(mac_address='')

print(f"Found {accounts.count()} MAC accounts")

for account in accounts:
    print(f"\n🔧 Account: {account.name}")
    print(f"   MAC field: {account.mac_address}")
    print(f"   Existing MACs: {account.macs.count()}")
    
    if account.macs.count() == 0:
        print("   Processing...")
        account._process_mac_addresses()
        print(f"   ✅ Created {account.macs.count()} MAC objects")
        
        for mac in account.macs.all():
            print(f"      - {mac.address} (priority: {mac.priority})")
    else:
        print("   ✅ Already processed")

print("\n🎯 MAC processing complete!")