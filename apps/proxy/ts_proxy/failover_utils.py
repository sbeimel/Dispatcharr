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
MAX_FAILOVER_ATTEMPTS = 5  # Maximum failover attempts per channel


class FailoverManager:
    """Manages multi-level failover for streams."""
    
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
            channel = get_object_or_404(Channel, uuid=self.channel_id)
            
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
        """Try MAC-level failover first, then profile failover."""
        
        # Get MAC addresses in priority order
        macs = m3u_account.macs.filter(
            status__in=[M3UAccountMac.Status.VALID, M3UAccountMac.Status.UNKNOWN]
        ).order_by('priority')
        
        # Try MAC-level failover
        for mac_obj in macs:
            if self._is_mac_in_cooldown(mac_obj.id):
                logger.debug(f"MAC {mac_obj.address} is in cooldown, skipping")
                continue
            
            if self._is_mac_busy(mac_obj.id):
                logger.debug(f"MAC {mac_obj.address} is busy, skipping")
                continue
            
            # Try to resolve stream URL using this MAC
            try:
                stream_url = self._resolve_mac_stream_url(stream, mac_obj, m3u_account)
                if stream_url:
                    # Mark MAC as busy
                    self._mark_mac_busy(mac_obj.id)
                    
                    # Get a profile for this account (needed for tracking)
                    profile = m3u_account.profiles.filter(is_active=True, is_default=True).first()
                    profile_id = profile.id if profile else None
                    
                    logger.info(f"MAC failover successful: {mac_obj.address} for channel {self.channel_id}")
                    return stream_url, profile_id, None
                    
            except Exception as e:
                logger.error(f"MAC failover failed for {mac_obj.address}: {e}")
                self._mark_mac_cooldown(mac_obj.id)
                continue
        
        # MAC failover exhausted, try profile failover
        logger.debug(f"MAC failover exhausted for channel {self.channel_id}, trying profile failover")
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
        """Resolve stream URL using MAC portal client."""
        from apps.m3u.mac_portal_client import MacPortalClient, MacPortalError
        
        try:
            client = MacPortalClient(
                base_url=m3u_account.server_url,
                mac=mac_obj.address,
                proxy=getattr(m3u_account, 'proxy', None)
            )
            
            # For MAC accounts, we need to use the cmd field from the stream
            # This assumes the stream has been imported from a MAC portal
            cmd = getattr(stream, 'cmd', None) or stream.url
            
            if cmd and not cmd.startswith('http'):
                # This is a portal command, resolve it
                resolved_url = client.create_link(cmd)
                return resolved_url
            else:
                # This is already a direct URL
                return stream.url
                
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