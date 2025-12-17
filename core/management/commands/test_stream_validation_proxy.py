"""
Management command to test stream validation with account-specific proxy configuration.
"""

from django.core.management.base import BaseCommand
from apps.m3u.models import M3UAccount
from apps.channels.models import Channel
from apps.proxy.ts_proxy.url_utils import validate_stream_url, get_channel_proxy


class Command(BaseCommand):
    help = 'Test stream validation with account-specific proxy configuration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--channel-id',
            type=str,
            help='Channel UUID to test stream validation'
        )
        parser.add_argument(
            '--test-url',
            type=str,
            help='Test URL for validation'
        )
        parser.add_argument(
            '--account-id',
            type=int,
            help='M3U Account ID to test'
        )

    def handle(self, *args, **options):
        if options['channel_id']:
            self.test_channel_validation(options['channel_id'])
        elif options['test_url'] and options['account_id']:
            self.test_url_with_account_proxy(options['test_url'], options['account_id'])
        elif options['test_url']:
            self.test_url_without_proxy(options['test_url'])
        else:
            self.stdout.write(
                self.style.ERROR('Please specify --channel-id or --test-url [--account-id]')
            )

    def test_channel_validation(self, channel_id):
        """Test stream validation for a specific channel using its account proxy."""
        try:
            channel = Channel.objects.get(uuid=channel_id)
            self.stdout.write(f"Testing channel: {channel.name}")
            
            # Get channel proxy
            channel_proxy = get_channel_proxy(channel)
            
            if channel_proxy:
                self.stdout.write(f"Channel proxy found: {channel_proxy}")
            else:
                self.stdout.write("No proxy configured for this channel")
            
            # Get a stream URL from the channel
            try:
                stream_id, m3u_profile_id, _ = channel.get_stream()
                if stream_id:
                    from apps.channels.models import Stream
                    stream = Stream.objects.get(id=stream_id)
                    test_url = stream.url
                    
                    self.stdout.write(f"Testing stream URL: {test_url}")
                    
                    # Test without proxy
                    self.stdout.write("\n--- Testing WITHOUT proxy ---")
                    is_valid, final_url, status_code, message = validate_stream_url(
                        test_url, 
                        user_agent="Dispatcharr/1.0",
                        timeout=(5, 5)
                    )
                    self.stdout.write(f"Result: {'✅ Valid' if is_valid else '❌ Invalid'}")
                    self.stdout.write(f"Status: {status_code}")
                    self.stdout.write(f"Message: {message}")
                    
                    # Test with proxy (if available)
                    if channel_proxy:
                        self.stdout.write(f"\n--- Testing WITH proxy ({channel_proxy}) ---")
                        is_valid_proxy, final_url_proxy, status_code_proxy, message_proxy = validate_stream_url(
                            test_url, 
                            user_agent="Dispatcharr/1.0",
                            timeout=(5, 5),
                            proxy=channel_proxy
                        )
                        self.stdout.write(f"Result: {'✅ Valid' if is_valid_proxy else '❌ Invalid'}")
                        self.stdout.write(f"Status: {status_code_proxy}")
                        self.stdout.write(f"Message: {message_proxy}")
                        
                        # Compare results
                        if is_valid != is_valid_proxy:
                            self.stdout.write(self.style.WARNING(
                                f"\n⚠️  Results differ! Without proxy: {is_valid}, With proxy: {is_valid_proxy}"
                            ))
                        else:
                            self.stdout.write(self.style.SUCCESS(
                                f"\n✅ Results consistent: {is_valid}"
                            ))
                else:
                    self.stdout.write("No stream found for this channel")
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error getting stream: {e}"))
                
        except Channel.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Channel with UUID {channel_id} not found"))

    def test_url_with_account_proxy(self, test_url, account_id):
        """Test URL validation with specific account proxy."""
        try:
            account = M3UAccount.objects.get(id=account_id)
            proxy = account.get_proxy()
            
            self.stdout.write(f"Testing account: {account.name} (Type: {account.get_type_display()})")
            self.stdout.write(f"Account proxy: {proxy if proxy else 'None'}")
            self.stdout.write(f"Test URL: {test_url}")
            
            # Test without proxy
            self.stdout.write("\n--- Testing WITHOUT proxy ---")
            is_valid, final_url, status_code, message = validate_stream_url(
                test_url, 
                user_agent="Dispatcharr/1.0",
                timeout=(5, 5)
            )
            self.stdout.write(f"Result: {'✅ Valid' if is_valid else '❌ Invalid'}")
            self.stdout.write(f"Status: {status_code}")
            self.stdout.write(f"Message: {message}")
            
            # Test with proxy (if available)
            if proxy:
                self.stdout.write(f"\n--- Testing WITH proxy ({proxy}) ---")
                is_valid_proxy, final_url_proxy, status_code_proxy, message_proxy = validate_stream_url(
                    test_url, 
                    user_agent="Dispatcharr/1.0",
                    timeout=(5, 5),
                    proxy=proxy
                )
                self.stdout.write(f"Result: {'✅ Valid' if is_valid_proxy else '❌ Invalid'}")
                self.stdout.write(f"Status: {status_code_proxy}")
                self.stdout.write(f"Message: {message_proxy}")
                
                # Compare results
                if is_valid != is_valid_proxy:
                    self.stdout.write(self.style.WARNING(
                        f"\n⚠️  Results differ! Without proxy: {is_valid}, With proxy: {is_valid_proxy}"
                    ))
                else:
                    self.stdout.write(self.style.SUCCESS(
                        f"\n✅ Results consistent: {is_valid}"
                    ))
            else:
                self.stdout.write("\nNo proxy configured for this account")
                
        except M3UAccount.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Account with ID {account_id} not found"))

    def test_url_without_proxy(self, test_url):
        """Test URL validation without proxy."""
        self.stdout.write(f"Testing URL without proxy: {test_url}")
        
        is_valid, final_url, status_code, message = validate_stream_url(
            test_url, 
            user_agent="Dispatcharr/1.0",
            timeout=(5, 5)
        )
        
        self.stdout.write(f"Result: {'✅ Valid' if is_valid else '❌ Invalid'}")
        self.stdout.write(f"Status: {status_code}")
        self.stdout.write(f"Message: {message}")
        if final_url != test_url:
            self.stdout.write(f"Final URL: {final_url}")