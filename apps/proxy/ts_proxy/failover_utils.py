"""
Failover utilities for multi-level stream backup system.
Implements MAC-level, Profile-level, and Stream-level failover.
"""

import logging
import time
from typing import Optional, Tuple, List, Dict, Any
from django.shortcuts import get_object_or_404
from apps.channels.models import Channel, Stream
from apps.m3u.models import M3UAccount, M3UAccountProfile, M3UAccountMac
from core.utils import RedisClient
from .redis_keys import RedisKeys
from .utils import get_logger

logger = get_logger()

# Failover configuration constants
MAC_COOLDOWN_DURATION = 360  # 6 minutes
PROFILE_COOLDOWN_DURATION = 180  # 3 minutes

MAX_FAILOVER_ATTEMPTS = 15  # Maximum failover attempts per channel (allows MAC + Profile + Stream failover)


class FailoverManager:
    """Manages multi-level failover for streams with proper hierarchy."""
    
    def __init__(self, channel_id: str):
        self.channel_id = channel_id
        self.redis_client = RedisClient.get_client()
    


    def get_stream_with_failover(self, current_stream_id: Optional[str] = None) -> Tuple[Optional[str], Optional[int], Optional[str]]:
        """
        Get stream URL with multi-level failover support.
        
        Returns:
            Tuple[Optional[str], Optional[int], Optional[str]]: (stream_url, profile_id, error_reason)
        """
        try:
            # Try to get channel by UUID first, then by stream_hash for compatibility
            channel = None
            try:
                channel = Channel.objects.get(uuid=self.channel_id)
            except (Channel.DoesNotExist, ValueError):
                # channel_id might be a stream_hash, try to find channel via stream
                try:
                    stream = Stream.objects.get(stream_hash=self.channel_id)
                    # Get the channel this stream belongs to
                    channel_stream = stream.channelstream_set.first()
                    if channel_stream:
                        channel = channel_stream.channel
                except Stream.DoesNotExist:
                    pass
            
            if not channel:
                logger.error(f"Could not find channel for ID {self.channel_id}")
                return None, None, f"Channel not found: {self.channel_id}"
            
            # Check failover attempt count to prevent infinite loops
            attempt_key = RedisKeys.failover_attempt_count(self.channel_id)
            attempt_count = int(self.redis_client.get(attempt_key) or 0)
            
            if attempt_count >= MAX_FAILOVER_ATTEMPTS:
                logger.error(f"Maximum failover attempts ({MAX_FAILOVER_ATTEMPTS}) reached for channel {self.channel_id}")
                return None, None, "Maximum failover attempts reached"
            
            # Increment attempt count
            self.redis_client.setex(attempt_key, 300, attempt_count + 1)  # 5 minute expiry
            
            # Get available streams for this channel
            streams = channel.streams.all().order_by("channelstream__order")
            
            if not streams.exists():
                return None, None, "No streams assigned to channel"
            
            # Try each stream with its failover logic
            for stream in streams:
                # Skip current stream if specified
                if current_stream_id and str(stream.id) == str(current_stream_id):
                    continue
                
                m3u_account = stream.m3u_account
                if not m3u_account or not m3u_account.is_active:
                    continue
                
                # Handle different account types
                if m3u_account.account_type == M3UAccount.Types.MAC:
                    result = self._try_mac_account_failover(stream, m3u_account)
                else:
                    result = self._try_standard_account_failover(stream, m3u_account)
                
                if result[0]:  # If we got a URL
                    # Reset attempt count on success
                    self.redis_client.delete(attempt_key)
                    return result
            
            return None, None, "All streams and failover options exhausted"
            
        except Exception as e:
            logger.error(f"Error in failover manager for channel {self.channel_id}: {e}")
            return None, None, f"Failover error: {str(e)}"
    
    def _try_mac_account_failover(self, stream: Stream, m3u_account: M3UAccount) -> Tuple[Optional[str], Optional[int], Optional[str]]:
        """Try MAC-level failover using the proper MAC failover logic from the patch."""
        
        # Get candidate MACs for streaming (excludes EXPIRED/ERROR and past expires_at)
        try:
            candidates = m3u_account.get_candidate_macs_for_streaming()
        except Exception as e:
            logger.error(f"Error getting candidate MACs for account {m3u_account.id}: {e}")
            candidates = []
        
        if not candidates:
            logger.error(f"No candidate MACs available for account {m3u_account.id}")
            return None, None, "No candidate MACs available"
        
        # If Redis is available, prefer MACs that are not currently busy
        if self.redis_client:
            free_candidates = []
            busy_candidates = []
            
            for mac_obj in candidates:
                if self._is_mac_busy(mac_obj.id):
                    busy_candidates.append(mac_obj)
                else:
                    free_candidates.append(mac_obj)
            
            if free_candidates:
                candidates = free_candidates
            elif candidates:
                # All MACs are busy - return error to allow profile/stream failover
                logger.warning(f"All candidate MACs are currently busy for MAC account {m3u_account.id}")
                return None, None, "All MACs busy"
        
        # Try each MAC in priority order
        error_messages = []
        for mac_obj in candidates:
            if self._is_mac_in_cooldown(mac_obj.id):
                logger.debug(f"MAC {mac_obj.address} is in cooldown, skipping")
                continue
            
            try:
                stream_url = self._resolve_mac_stream_url(stream, mac_obj, m3u_account)
                if stream_url:
                    # Mark MAC as busy
                    self._mark_mac_busy(mac_obj.id)
                    
                    # Get or create a profile for this account
                    profile = self._get_or_create_mac_profile(m3u_account)
                    profile_id = profile.id if profile else None
                    
                    logger.info(f"MAC failover successful: {mac_obj.address} for channel {self.channel_id}")
                    return stream_url, profile_id, None
                    
            except Exception as e:
                error_msg = str(e)
                logger.error(f"MAC failover failed for {mac_obj.address}: {error_msg}")
                error_messages.append(f"{mac_obj.address}: {error_msg}")
                
                # Mark MAC in cooldown for network errors, but not for MAC-level errors
                # (MAC-level errors are already handled in _resolve_mac_stream_url)
                if "MacPortalError" not in str(type(e)):
                    self._mark_mac_cooldown(mac_obj.id)
                continue
        
        # All MACs failed
        error_summary = "; ".join(error_messages) if error_messages else "All MACs failed"
        logger.debug(f"MAC failover exhausted for channel {self.channel_id}: {error_summary}")
        
        # Try profile failover as fallback
        return self._try_standard_account_failover(stream, m3u_account)
    
    def _try_standard_account_failover(self, stream: Stream, m3u_account: M3UAccount) -> Tuple[Optional[str], Optional[int], Optional[str]]:
        """Try profile-level failover for standard/XC accounts."""
        
        # Get profiles in priority order (default first)
        profiles = m3u_account.profiles.filter(is_active=True)
        default_profile = profiles.filter(is_default=True).first()
        
        if default_profile:
            profile_list = [default_profile] + list(profiles.exclude(is_default=True))
        else:
            profile_list = list(profiles)
        
        for profile in profile_list:
            if self._is_profile_in_cooldown(profile.id):
                logger.debug(f"Profile {profile.id} is in cooldown, skipping")
                continue
            
            # Check connection capacity
            if not self._has_profile_capacity(profile):
                logger.debug(f"Profile {profile.id} at max capacity, skipping")
                continue
            
            try:
                # For standard accounts, use the stream URL with profile transformation
                stream_url = self._transform_stream_url(stream.url, profile)
                
                if stream_url:
                    # Increment profile connection count
                    self._increment_profile_connections(profile.id)
                    
                    logger.info(f"Profile failover successful: {profile.id} for channel {self.channel_id}")
                    return stream_url, profile.id, None
                    
            except Exception as e:
                logger.error(f"Profile failover failed for {profile.id}: {e}")
                self._mark_profile_cooldown(profile.id)
                continue
        
        return None, None, "All profiles exhausted or in cooldown"
    
    def _resolve_mac_stream_url(self, stream: Stream, mac_obj: M3UAccountMac, m3u_account: M3UAccount) -> Optional[str]:
        """Resolve stream URL using MAC portal client with proper failover logic."""
        from apps.m3u.mac_portal_client import MacPortalClient, MacPortalError
        from django.utils import timezone
        
        try:
            # Get proxy configuration
            props = m3u_account.custom_properties or {}
            proxy_value = props.get("proxy")
            timezone_str = props.get("timezone", "Europe/Berlin")
            
            # Parse proxy list (support multiple proxies)
            proxy_list = []
            if isinstance(proxy_value, str) and proxy_value.strip():
                raw = proxy_value.replace("\r", "\n").replace(",", "\n")
                parts = [p.strip() for p in raw.split() if p.strip()]
                proxy_list = list(dict.fromkeys(parts))  # Remove duplicates while preserving order
            
            # If no proxy configured, try direct connection
            if not proxy_list:
                proxy_list = [None]
            
            # Determine command for the portal
            stream_props = stream.custom_properties or {}
            cmd = stream_props.get("mac_cmd") or stream_props.get("cmd") or stream.url
            
            # If it's a mac:// URL, extract the cmd
            if cmd and cmd.startswith("mac://"):
                try:
                    import base64
                    encoded_data = cmd[6:]  # Remove "mac://" prefix
                    decoded_data = base64.urlsafe_b64decode(encoded_data).decode()
                    parts = decoded_data.split("|", 3)
                    if len(parts) >= 3:
                        cmd = parts[2]  # Extract cmd from mac:// URL
                except Exception as e:
                    logger.warning(f"Failed to extract cmd from mac:// URL: {e}")
                    cmd = stream.url
            
            # Try each proxy until one works
            for proxy in proxy_list:
                try:
                    client = MacPortalClient(
                        base_url=m3u_account.server_url,
                        mac=mac_obj.address,
                        proxy=proxy,
                        timezone=timezone_str,
                    )
                    
                    # Resolve the stream URL
                    if cmd and not cmd.startswith('http'):
                        resolved_url = client.create_link(cmd)
                    else:
                        resolved_url = cmd
                    
                    if resolved_url:
                        # Mark MAC as valid on success
                        try:
                            mac_obj.status = M3UAccountMac.Status.VALID
                            mac_obj.last_checked = timezone.now()
                            mac_obj.last_error = None
                            mac_obj.save(update_fields=["status", "last_checked", "last_error"])
                        except Exception:
                            pass
                        
                        logger.info(f"Successfully resolved MAC stream for {mac_obj.address} using proxy: {proxy or 'direct'}")
                        return resolved_url
                        
                except MacPortalError as e:
                    # MAC-level error (expired/unauthorized) - mark MAC and stop trying other proxies
                    msg = str(e)
                    logger.warning(f"MAC portal error for {mac_obj.address} with proxy {proxy}: {msg}")
                    
                    status = M3UAccountMac.Status.ERROR
                    lowered = msg.lower()
                    if "expir" in lowered or "no active" in lowered or "trial ended" in lowered:
                        status = M3UAccountMac.Status.EXPIRED
                    
                    try:
                        mac_obj.status = status
                        mac_obj.last_error = msg
                        mac_obj.last_checked = timezone.now()
                        mac_obj.save(update_fields=["status", "last_error", "last_checked"])
                    except Exception:
                        pass
                    
                    # Don't try other proxies for this MAC if it's a MAC-level error
                    raise MacPortalError(msg)
                    
                except Exception as e:
                    # Network/proxy error - try next proxy
                    logger.warning(f"Network error for MAC {mac_obj.address} with proxy {proxy}: {e}")
                    continue
            
            # All proxies failed
            logger.error(f"All proxies failed for MAC {mac_obj.address}")
            return None
                
        except MacPortalError as e:
            logger.error(f"MAC portal error for {mac_obj.address}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error resolving MAC stream: {e}")
            raise
    
    def _transform_stream_url(self, url: str, profile: M3UAccountProfile) -> str:
        """Transform stream URL using profile patterns."""
        import re
        
        try:
            if profile.search_pattern and profile.replace_pattern:
                transformed_url = re.sub(profile.search_pattern, profile.replace_pattern, url)
                return transformed_url
            return url
        except Exception as e:
            logger.error(f"Error transforming URL with profile {profile.id}: {e}")
            return url
    
    def _is_mac_in_cooldown(self, mac_id: int) -> bool:
        """Check if MAC is in cooldown period."""
        cooldown_key = RedisKeys.mac_cooldown(mac_id)
        return self.redis_client.exists(cooldown_key)
    
    def _is_mac_busy(self, mac_id: int) -> bool:
        """Check if MAC is currently busy."""
        busy_key = RedisKeys.mac_busy(mac_id)
        return self.redis_client.exists(busy_key)
    
    def _is_profile_in_cooldown(self, profile_id: int) -> bool:
        """Check if profile is in cooldown period."""
        cooldown_key = RedisKeys.profile_cooldown(profile_id)
        return self.redis_client.exists(cooldown_key)
    
    def _has_profile_capacity(self, profile: M3UAccountProfile) -> bool:
        """Check if profile has available connection capacity."""
        if profile.max_streams == 0:  # Unlimited
            return True
        
        connections_key = RedisKeys.profile_connections(profile.id)
        current_connections = int(self.redis_client.get(connections_key) or 0)
        return current_connections < profile.max_streams
    
    def _mark_mac_cooldown(self, mac_id: int):
        """Mark MAC as in cooldown."""
        cooldown_key = RedisKeys.mac_cooldown(mac_id)
        self.redis_client.setex(cooldown_key, MAC_COOLDOWN_DURATION, "1")
        logger.info(f"MAC {mac_id} marked for cooldown ({MAC_COOLDOWN_DURATION}s)")
    
    def _mark_mac_busy(self, mac_id: int):
        """Mark MAC as busy."""
        busy_key = RedisKeys.mac_busy(mac_id)
        self.redis_client.setex(busy_key, 3600, "1")  # 1 hour max
    
    def _mark_profile_cooldown(self, profile_id: int):
        """Mark profile as in cooldown."""
        cooldown_key = RedisKeys.profile_cooldown(profile_id)
        self.redis_client.setex(cooldown_key, PROFILE_COOLDOWN_DURATION, "1")
        logger.info(f"Profile {profile_id} marked for cooldown ({PROFILE_COOLDOWN_DURATION}s)")
    
    def _increment_profile_connections(self, profile_id: int):
        """Increment profile connection count."""
        connections_key = RedisKeys.profile_connections(profile_id)
        self.redis_client.incr(connections_key)
        self.redis_client.expire(connections_key, 3600)  # 1 hour expiry
    

    
    def _get_or_create_mac_profile(self, m3u_account: M3UAccount):
        """Get or create a default profile for MAC account."""
        from apps.m3u.models import M3UAccountProfile
        
        profile = m3u_account.profiles.filter(is_active=True, is_default=True).first()
        if not profile:
            # Create a default profile for MAC account
            profile, created = M3UAccountProfile.objects.get_or_create(
                m3u_account=m3u_account,
                is_default=True,
                defaults={
                    'is_active': True,
                    'max_streams': 1,  # MAC accounts typically support 1 stream per MAC
                    'search_pattern': r'(.*)',
                    'replace_pattern': r'\1'
                }
            )
            if created:
                logger.info(f"Created default profile for MAC account {m3u_account.id}")
        
        return profile

    def release_resources(self, profile_id: Optional[int] = None, mac_id: Optional[int] = None):
        """Release resources when stream ends."""
        if profile_id:
            connections_key = RedisKeys.profile_connections(profile_id)
            current = int(self.redis_client.get(connections_key) or 0)
            if current > 0:
                self.redis_client.decr(connections_key)
        
        if mac_id:
            busy_key = RedisKeys.mac_busy(mac_id)
            self.redis_client.delete(busy_key)
        
        # Clear failover attempt count on successful release
        attempt_key = RedisKeys.failover_attempt_count(self.channel_id)
        self.redis_client.delete(attempt_key)


def get_next_failover_stream(channel_id: str, current_stream_id: Optional[str] = None) -> Tuple[Optional[str], Optional[int], Optional[str]]:
    """
    Convenience function to get next failover stream.
    
    Args:
        channel_id: Channel UUID
        current_stream_id: Current stream ID to avoid
        
    Returns:
        Tuple[Optional[str], Optional[int], Optional[str]]: (stream_url, profile_id, error_reason)
    """
    manager = FailoverManager(channel_id)
    return manager.get_stream_with_failover(current_stream_id)


def release_failover_resources(channel_id: str, profile_id: Optional[int] = None, mac_id: Optional[int] = None):
    """
    Convenience function to release failover resources.
    
    Args:
        channel_id: Channel UUID
        profile_id: Profile ID to release
        mac_id: MAC ID to release
    """
    manager = FailoverManager(channel_id)
    manager.release_resources(profile_id, mac_id)