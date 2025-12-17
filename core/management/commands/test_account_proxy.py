"""
Management command to test account-specific proxy configuration.
"""

from django.core.management.base import BaseCommand
from apps.m3u.models import M3UAccount
from apps.channels.models import Channel
from core.models import StreamProfile


class Command(BaseCommand):
    help = 'Test account-specific proxy configuration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--account-id',
            type=int,
            help='M3U Account ID to test'
        )
        parser.add_argument(
            '--channel-id',
            type=str,
            help='Channel UUID to test'
        )
        parser.add_argument(
            '--list-accounts',
            action='store_true',
            help='List all M3U accounts with proxy settings'
        )

    def handle(self, *args, **options):
        if options['list_accounts']:
            self.list_accounts_with_proxy()
            return

        if options['account_id']:
            self.test_account_proxy(options['account_id'])
            return

        if options['channel_id']:
            self.test_channel_proxy(options['channel_id'])
            return

        self.stdout.write(
            self.style.ERROR('Please specify --account-id, --channel-id, or --list-accounts')
        )

    def list_accounts_with_proxy(self):
        """List all M3U accounts and their proxy settings."""
        self.stdout.write(self.style.SUCCESS('M3U Accounts with Proxy Configuration:'))
        self.stdout.write('-' * 60)
        
        accounts = M3UAccount.objects.all()
        for account in accounts:
            proxy = account.get_proxy()
            proxy_status = proxy if proxy else "No proxy configured"
            proxy_type = ""
            if account.account_type == account.Types.MAC and account.proxy:
                proxy_type = " (MAC/STB)"
            elif account.account_type in [account.Types.STADNARD, account.Types.XC] and account.proxy_std_xc:
                proxy_type = " (STD/XC)"
            
            self.stdout.write(f"ID: {account.id} | Name: {account.name} | Type: {account.get_account_type_display()} | Proxy: {proxy_status}{proxy_type}")

    def test_account_proxy(self, account_id):
        """Test proxy configuration for a specific account."""
        try:
            account = M3UAccount.objects.get(id=account_id)
            self.stdout.write(f"Testing account: {account.name}")
            
            proxy = account.get_proxy()
            if proxy:
                self.stdout.write(f"Account type: {account.get_account_type_display()}")
                self.stdout.write(f"Proxy configured: {proxy}")
                
                # Test build_command with proxy
                profile = StreamProfile.objects.filter(profile_name="ffmpeg").first()
                if profile:
                    test_url = "http://example.com/stream.m3u8"
                    test_user_agent = "Dispatcharr/1.0"
                    
                    # Test without proxy
                    cmd_without_proxy = profile.build_command(test_url, test_user_agent)
                    self.stdout.write(f"Command without proxy: {' '.join(cmd_without_proxy)}")
                    
                    # Test with proxy
                    cmd_with_proxy = profile.build_command(test_url, test_user_agent, proxy)
                    self.stdout.write(f"Command with proxy: {' '.join(cmd_with_proxy)}")
                else:
                    self.stdout.write(self.style.ERROR("No ffmpeg profile found"))
            else:
                self.stdout.write(f"No proxy configured for this {account.get_account_type_display()} account")
                
        except M3UAccount.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Account with ID {account_id} not found"))

    def test_channel_proxy(self, channel_id):
        """Test proxy configuration for a specific channel."""
        try:
            channel = Channel.objects.get(uuid=channel_id)
            self.stdout.write(f"Testing channel: {channel.name}")
            
            if channel.channel_group:
                self.stdout.write(f"Channel group: {channel.channel_group.name}")
                
                # Get associated M3U accounts
                channel_group_accounts = channel.channel_group.m3u_accounts.filter(enabled=True)
                
                if channel_group_accounts.exists():
                    for cga in channel_group_accounts:
                        account = cga.m3u_account
                        proxy = account.get_proxy()
                        proxy_status = proxy if proxy else "No proxy"
                        self.stdout.write(f"  - Account: {account.name} | Type: {account.get_account_type_display()} | Proxy: {proxy_status}")
                        
                        if proxy:
                            # Simulate the proxy retrieval logic
                            profile = channel.get_stream_profile()
                            test_url = "http://example.com/stream.m3u8"
                            test_user_agent = "Dispatcharr/1.0"
                            
                            cmd = profile.build_command(test_url, test_user_agent, proxy)
                            self.stdout.write(f"    Command: {' '.join(cmd)}")
                else:
                    self.stdout.write("No M3U accounts associated with this channel group")
            else:
                self.stdout.write("Channel has no channel group")
                
        except Channel.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Channel with UUID {channel_id} not found"))