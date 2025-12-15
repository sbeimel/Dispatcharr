"""
Failover utilities for multi-level stream backup system.
Implements MAC-level, Profile-level, and Stream-level failover.
"""

import logging
import re
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
                m3u_account = stream.m3u_account
                if not m3u_account or not m3u_account.is_active:
                    continue
                
                # For the current stream, try failover within the same account first
                if current_stream_id and str(stream.id) == str(current_stream_id):
                    logger.debug(f"Current stream {stream.id}: account_type={m3u_account.account_type}, is_MAC={m3u_account.account_type == M3UAccount.Types.MAC}")
                    
                    if m3u_account.account_type == M3UAccount.Types.MAC:
                        # MAC Account: Try MAC failover (next MAC in same account)
                        logger.info(f"Trying MAC failover within current stream {stream.id} for channel {self.channel_id}")
                        result = self._try_mac_account_failover(stream, m3u_account)
                        if result[0]:  # If we got a URL
                            # Reset attempt count on success
                            self.redis_client.delete(attempt_key)
                            return result
                        logger.info(f"MAC failover exhausted for stream {stream.id}, trying other streams")
                    else:
                        # Standard Account: Try profile failover
                        logger.info(f"Trying profile failover within current stream {stream.id} for channel {self.channel_id}")
                        result = self._try_standard_account_failover(stream, m3u_account)
                        if result[0]:  # If we got a URL
                            # Reset attempt count on success
                            self.redis_client.delete(attempt_key)
                            return result
                        logger.info(f"Profile failover exhausted for stream {stream.id}, trying other streams")
                    
                    # Skip to other streams after trying failover within current stream
                    continue
                
                # Handle different account types for other streams (backup streams)
                if m3u_account.account_type == M3UAccount.Types.MAC:
                    logger.info(f"Trying backup MAC stream {stream.id} for channel {self.channel_id}")
                    result = self._try_mac_account_failover(stream, m3u_account)
                else:
                    logger.info(f"Trying backup standard stream {stream.id} for channel {self.channel_id}")
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
        
        # Check if MAC failover is enabled in settings
        try:
            from apps.m3u.mac_portal_models import FailoverSettings
            settings = FailoverSettings.get_settings()
            if not settings.mac_failover_enabled:
                logger.info(f"MAC failover is disabled in settings, skipping for account {m3u_account.id}")
                return None, None, "MAC failover disabled"
        except Exception as e:
            logger.debug(f"Could not check MAC failover settings: {e}")
            # Continue with failover if settings can't be loaded
        
        # Get candidate MACs for streaming (excludes EXPIRED/ERROR and past expires_at)
        try:
            candidates = m3u_account.get_candidate_macs_for_streaming()
        except Exception as e:
            logger.error(f"Error getting candidate MACs for account {m3u_account.id}: {e}")
            candidates = []
        
        if not candidates:
            logger.error(f"No candidate MACs available for account {m3u_account.id}")
            return None, None, "No candidate MACs available"
        
        logger.info(f"MAC failover: Found {len(candidates)} candidate MACs for account {m3u_account.id}")
        
        # Get the currently used MAC for this channel (to skip it during failover)
        current_mac_id = self._get_current_mac_for_channel()
        if current_mac_id:
            logger.info(f"MAC failover: Current MAC ID is {current_mac_id}, will skip it and try others")
            # Mark current MAC in cooldown since it failed
            self._mark_mac_cooldown(current_mac_id)
            # Clear busy flag so it's not blocking other channels
            self._clear_mac_busy(current_mac_id)
        
        # Filter candidates: exclude current MAC and MACs in cooldown
        # Note: We DON'T skip busy MACs here because during failover we need to try all available MACs
        # The "busy" flag is for preventing multiple channels from using the same MAC simultaneously
        available_candidates = []
        for mac_obj in candidates:
            if current_mac_id and mac_obj.id == current_mac_id:
                logger.debug(f"MAC {mac_obj.address} is the current (failed) MAC, skipping")
                continue
            if self._is_mac_in_cooldown(mac_obj.id):
                logger.debug(f"MAC {mac_obj.address} is in cooldown, skipping")
                continue
            # For failover, we allow using MACs that are "busy" on THIS channel
            # because we're switching from one MAC to another on the same channel
            if self._is_mac_busy(mac_obj.id):
                # Check if this MAC is busy on a DIFFERENT channel
                # For now, we'll allow it since we're doing failover
                logger.debug(f"MAC {mac_obj.address} is marked busy, but allowing for failover")
            available_candidates.append(mac_obj)
        
        if not available_candidates:
            logger.warning(f"No available MACs for failover (all in cooldown, busy, or current)")
            return None, None, "No available MACs for failover"
        
        logger.info(f"MAC failover: {len(available_candidates)} MACs available to try")
        
        # Try each available MAC
        error_messages = []
        for mac_obj in available_candidates:
            try:
                logger.info(f"MAC failover: Trying MAC {mac_obj.address}")
                stream_url = self._resolve_mac_stream_url(stream, mac_obj, m3u_account)
                if stream_url:
                    # Mark MAC as busy
                    self._mark_mac_busy(mac_obj.id)
                    # Store which MAC is used for this channel
                    self._set_current_mac_for_channel(mac_obj.id)
                    
                    # Get or create a profile for this account
                    profile = self._get_or_create_mac_profile(m3u_account)
                    profile_id = profile.id if profile else None
                    
                    logger.info(f"MAC failover successful: {mac_obj.address} for channel {self.channel_id}")
                    return stream_url, profile_id, None
                    
            except Exception as e:
                error_msg = str(e)
                logger.error(f"MAC failover failed for {mac_obj.address}: {error_msg}")
                error_messages.append(f"{mac_obj.address}: {error_msg}")
                
                # Mark MAC in cooldown
                self._mark_mac_cooldown(mac_obj.id)
                continue
        
        # All MACs failed
        error_summary = "; ".join(error_messages) if error_messages else "All MACs failed"
        logger.warning(f"MAC failover exhausted for channel {self.channel_id}: {error_summary}")
        
        return None, None, f"MAC failover exhausted: {error_summary}"
    
    def _try_standard_account_failover(self, stream: Stream, m3u_account: M3UAccount) -> Tuple[Optional[str], Optional[int], Optional[str]]:
        """Try profile-level failover for standard/XC accounts."""
        
        # Get profiles in priority order (default first)
        profiles = m3u_account.profiles.filter(is_active=True)
        default_profile = profiles.filter(is_default=True).first()
        
        if default_profile:
            profile_list = [default_profile] + list(profiles.exclude(is_default=True))
        else:
            profile_list = list(profiles)
        
        logger.info(f"Profile failover for account {m3u_account.id}: found {len(profile_list)} active profiles")
        for i, p in enumerate(profile_list):
            logger.info(f"  Profile {i+1}: ID={p.id}, name='{p.name}', default={p.is_default}")
        
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
                
                # Check if the URL actually changed - if not, try next profile
                if stream_url and stream_url != stream.url:
                    # Increment profile connection count
                    self._increment_profile_connections(profile.id)
                    
                    logger.info(f"Profile failover successful: {profile.id} for channel {self.channel_id}")
                    return stream_url, profile.id, None
                elif stream_url == stream.url:
                    logger.info(f"Profile {profile.id} did not change URL, trying next profile")
                    continue
                    
            except Exception as e:
                logger.error(f"Profile failover failed for {profile.id}: {e}")
                self._mark_profile_cooldown(profile.id)
                continue
        
        return None, None, "All profiles exhausted or in cooldown"
    
    def _resolve_mac_stream_url(self, stream: Stream, mac_obj: M3UAccountMac, m3u_account: M3UAccount) -> Optional[str]:
        """Resolve stream URL using UnifiedPortalEngine with proper failover logic."""
        from apps.m3u.unified_portal_engine import UnifiedPortalEngine
        from apps.m3u.mac_portal_client import MacPortalError
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
            
            # Get engine preference from account settings
            engine_pref = props.get("portal_engine", "auto")
            from apps.m3u.unified_portal_engine import PortalEngine
            try:
                selected_engine = PortalEngine(engine_pref) if engine_pref != "auto" else PortalEngine.AUTO
            except ValueError:
                selected_engine = PortalEngine.AUTO
            
            # Try each proxy until one works
            for proxy in proxy_list:
                try:
                    # Use UnifiedPortalEngine which supports all engines (macreplay, ob2_2025, etc.)
                    engine = UnifiedPortalEngine(
                        portal_url=m3u_account.server_url,
                        mac=mac_obj.address,
                        engine=selected_engine,
                    )
                    engine.proxy = proxy  # Set proxy after initialization
                    
                    # Resolve the stream URL
                    if cmd and not cmd.startswith('http'):
                        resolved_url = engine.create_link(cmd)
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
                # Convert $1, $2, etc. to \1, \2, etc. for proper Python regex backreferences
                safe_replace_pattern = re.sub(r'\$(\d+)', r'\\\1', profile.replace_pattern)
                transformed_url = re.sub(profile.search_pattern, safe_replace_pattern, url)
                logger.info(f"Profile {profile.id} ({profile.name}) URL transformation:")
                logger.info(f"  Original URL: {url}")
                logger.info(f"  Search pattern: {profile.search_pattern}")
                logger.info(f"  Replace pattern: {profile.replace_pattern}")
                logger.info(f"  Safe replace pattern: {safe_replace_pattern}")
                logger.info(f"  Transformed URL: {transformed_url}")
                return transformed_url
            else:
                logger.warning(f"Profile {profile.id} has no search/replace patterns, returning original URL")
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
    
    def _clear_mac_busy(self, mac_id: int):
        """Clear MAC busy flag."""
        busy_key = RedisKeys.mac_busy(mac_id)
        self.redis_client.delete(busy_key)
        logger.debug(f"Cleared busy flag for MAC {mac_id}")
    
    def _get_current_mac_for_channel(self) -> Optional[int]:
        """Get the MAC ID currently used for this channel.
        
        First tries to get from Redis cache, then falls back to extracting
        from the current stream URL metadata.
        """
        # Try Redis cache first
        mac_key = f"channel:{self.channel_id}:current_mac"
        mac_id = self.redis_client.get(mac_key)
        if mac_id:
            try:
                return int(mac_id)
            except (ValueError, TypeError):
                pass
        
        # Fallback: Try to extract MAC from current stream metadata
        try:
            metadata_key = f"channel:{self.channel_id}:metadata"
            metadata = self.redis_client.hgetall(metadata_key)
            if metadata:
                # Try to get MAC from stream URL
                stream_url = metadata.get(b'stream_url') or metadata.get('stream_url')
                if stream_url:
                    if isinstance(stream_url, bytes):
                        stream_url = stream_url.decode('utf-8')
                    
                    # Extract MAC from URL (format: mac=00:1A:79:...)
                    mac_match = re.search(r'mac=([0-9A-Fa-f:]{17})', stream_url)
                    if mac_match:
                        mac_address = mac_match.group(1).upper()
                        # Find MAC ID in database
                        mac_obj = M3UAccountMac.objects.filter(address__iexact=mac_address).first()
                        if mac_obj:
                            logger.debug(f"Found current MAC {mac_address} (ID: {mac_obj.id}) from stream URL")
                            return mac_obj.id
        except Exception as e:
            logger.debug(f"Could not extract current MAC from metadata: {e}")
        
        return None
    
    def _set_current_mac_for_channel(self, mac_id: int):
        """Store which MAC is used for this channel."""
        mac_key = f"channel:{self.channel_id}:current_mac"
        self.redis_client.setex(mac_key, 3600, str(mac_id))  # 1 hour expiry
        logger.debug(f"Set current MAC {mac_id} for channel {self.channel_id}")
    
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