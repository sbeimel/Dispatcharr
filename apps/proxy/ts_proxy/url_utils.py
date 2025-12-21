"""
Utilities for handling stream URLs and transformations.
"""

import logging
import re
from typing import Optional, Tuple, List
from django.shortcuts import get_object_or_404
from apps.channels.models import Channel, Stream
from apps.m3u.models import M3UAccount, M3UAccountProfile
from core.models import UserAgent, CoreSettings, StreamProfile
from .utils import get_logger
from uuid import UUID
import requests
from .mac_state_manager import MACStateManager

logger = get_logger()

def get_stream_object(id: str):
    try:
        logger.info(f"Fetching channel ID {id}")
        return get_object_or_404(Channel, uuid=id)
    except (ValueError, Channel.DoesNotExist, Exception):
        # UUID check failed (ValueError, ValidationError, etc.), assume stream hash
        logger.info(f"Fetching stream hash {id}")
        return get_object_or_404(Stream, stream_hash=id)

def generate_stream_url(channel_id: str) -> Tuple[str, str, bool, Optional[int]]:
    """
    Generate the appropriate stream URL for a channel or stream based on its profile settings.

    Args:
        channel_id: The UUID of the channel or stream hash

    Returns:
        Tuple[str, str, bool, Optional[int]]: (stream_url, user_agent, transcode_flag, profile_id)
    """
    try:
        channel_or_stream = get_stream_object(channel_id)

        # Handle direct stream preview (custom streams)
        if isinstance(channel_or_stream, Stream):
            from core.utils import RedisClient

            stream = channel_or_stream
            logger.info(f"Previewing stream directly: {stream.id} ({stream.name})")

            # For custom streams, we need to get the M3U account and profile
            m3u_account = stream.m3u_account
            if not m3u_account:
                logger.error(f"Stream {stream.id} has no M3U account")
                return None, None, False, None

            # Get active profiles for this M3U account
            m3u_profiles = m3u_account.profiles.filter(is_active=True)
            default_profile = next((obj for obj in m3u_profiles if obj.is_default), None)

            if not default_profile:
                logger.error(f"No default active profile found for M3U account {m3u_account.id}")
                return None, None, False, None

            # Check profiles in order: default first, then others
            profiles = [default_profile] + [obj for obj in m3u_profiles if not obj.is_default]

            # Try to find an available profile with connection capacity
            redis_client = RedisClient.get_client()
            selected_profile = None

            for profile in profiles:
                logger.info(profile)

                # Check connection availability
                if redis_client:
                    profile_connections_key = f"profile_connections:{profile.id}"
                    current_connections = int(redis_client.get(profile_connections_key) or 0)

                    # Check if profile has available slots (or unlimited connections)
                    if profile.max_streams == 0 or current_connections < profile.max_streams:
                        selected_profile = profile
                        logger.debug(f"Selected profile {profile.id} with {current_connections}/{profile.max_streams} connections for stream preview")
                        break
                    else:
                        logger.debug(f"Profile {profile.id} at max connections: {current_connections}/{profile.max_streams}")
                else:
                    # No Redis available, use first active profile
                    selected_profile = profile
                    break

            if not selected_profile:
                logger.error(f"No profiles available with connection capacity for M3U account {m3u_account.id}")
                return None, None, False, None

            # Get the appropriate user agent
            stream_user_agent = m3u_account.get_user_agent().user_agent
            if stream_user_agent is None:
                stream_user_agent = UserAgent.objects.get(id=CoreSettings.get_default_user_agent_id())
                logger.debug(f"No user agent found for account, using default: {stream_user_agent}")

            # Get stream URL with the selected profile's URL transformation
            stream_url = transform_url(stream.url, selected_profile.search_pattern, selected_profile.replace_pattern, stream, m3u_account)

            # Check if the stream has its own stream_profile set, otherwise use default
            if stream.stream_profile:
                stream_profile = stream.stream_profile
                logger.debug(f"Using stream's own stream profile: {stream_profile.name}")
            else:
                stream_profile = StreamProfile.objects.get(
                    id=CoreSettings.get_default_stream_profile_id()
                )
                logger.debug(f"Using default stream profile: {stream_profile.name}")

            # Check if transcoding is needed
            if stream_profile.is_proxy() or stream_profile is None:
                transcode = False
            else:
                transcode = True

            stream_profile_id = stream_profile.id

            return stream_url, stream_user_agent, transcode, stream_profile_id

        # Handle channel preview (existing logic)
        channel = channel_or_stream

        # Get stream and profile for this channel
        # Note: get_stream now returns 3 values (stream_id, profile_id, error_reason)
        stream_id, profile_id, error_reason = channel.get_stream()

        if not stream_id or not profile_id:
            logger.error(f"No stream available for channel {channel_id}: {error_reason}")
            return None, None, False, None

        # Look up the Stream and Profile objects
        try:
            stream = Stream.objects.get(id=stream_id)
            profile = M3UAccountProfile.objects.get(id=profile_id)
        except (Stream.DoesNotExist, M3UAccountProfile.DoesNotExist) as e:
            logger.error(f"Error getting stream or profile: {e}")
            return None, None, False, None

        # Get the M3U account profile for URL pattern
        m3u_profile = profile

        # Get the appropriate user agent
        m3u_account = M3UAccount.objects.get(id=m3u_profile.m3u_account.id)
        stream_user_agent = m3u_account.get_user_agent().user_agent

        if stream_user_agent is None:
            stream_user_agent = UserAgent.objects.get(id=CoreSettings.get_default_user_agent_id())
            logger.debug(f"No user agent found for account, using default: {stream_user_agent}")

        # Generate stream URL based on the selected profile
        input_url = stream.url
        stream_url = transform_url(input_url, m3u_profile.search_pattern, m3u_profile.replace_pattern, stream, m3u_account)

        # Check if transcoding is needed
        stream_profile = channel.get_stream_profile()
        if stream_profile.is_proxy() or stream_profile is None:
            transcode = False
        else:
            transcode = True

        stream_profile_id = stream_profile.id

        return stream_url, stream_user_agent, transcode, stream_profile_id
    except Exception as e:
        logger.error(f"Error generating stream URL: {e}")
        return None, None, False, None

def transform_url(input_url: str, search_pattern: str, replace_pattern: str, stream_obj=None, m3u_account_obj=None) -> str:
    """
    Transform a URL using regex pattern replacement.
    
    For MAC portal URLs (mac://...), resolves the URL via create_link API first.
    IMPORTANT: For MAC accounts, this now uses the failover path to ensure BUSY flag is set.

    Args:
        input_url: The base URL to transform
        search_pattern: The regex search pattern
        replace_pattern: The replacement pattern
        stream_obj: Optional Stream object (needed for MAC failover)
        m3u_account_obj: Optional M3UAccount object (needed for MAC failover)

    Returns:
        str: The transformed URL
    """
    try:
        # Check if this is a MAC portal URL that needs to be resolved
        if input_url and input_url.startswith("mac://"):
            logger.info(f"Resolving MAC portal URL...")
            try:
                # CRITICAL FIX: Use failover path for MAC URLs to ensure BUSY flag is set
                # This prevents multiple streams from using the same MAC simultaneously
                if stream_obj and m3u_account_obj:
                    resolved_url, mac_entry, error_msg = _resolve_mac_stream_with_failover(
                        m3u_account=m3u_account_obj,
                        stream=stream_obj
                    )
                    if resolved_url:
                        logger.info(f"Resolved MAC URL with BUSY flag to: {resolved_url[:80]}...")
                        input_url = resolved_url
                    else:
                        logger.error(f"Failed to resolve MAC URL via failover: {error_msg}")
                        raise Exception(f"MAC failover failed: {error_msg}")
                else:
                    # CRITICAL: DO NOT use fallback that bypasses BUSY check!
                    # This would allow multiple streams to use the same MAC simultaneously.
                    # If we get here, it's a bug in the calling code.
                    logger.error("MAC URL resolution without stream/account objects - REFUSING to resolve!")
                    logger.error("This is a BUG: MAC URLs must be resolved with stream/account objects to ensure BUSY flag is checked")
                    raise Exception("Cannot resolve MAC URL without stream/account objects - BUSY check would be bypassed")
            except Exception as e:
                logger.error(f"Failed to resolve MAC URL: {e}")
                raise
        
        logger.debug("Executing URL pattern replacement:")
        logger.debug(f"  base URL: {input_url}")
        logger.debug(f"  search: {search_pattern}")

        # Handle backreferences in the replacement pattern
        safe_replace_pattern = re.sub(r'\$(\d+)', r'\\\1', replace_pattern)
        logger.debug(f"  replace: {replace_pattern}")
        logger.debug(f"  safe replace: {safe_replace_pattern}")

        # Apply the transformation
        stream_url = re.sub(search_pattern, safe_replace_pattern, input_url)
        logger.info(f"Generated stream url: {stream_url}")

        return stream_url
    except Exception as e:
        logger.error(f"Error transforming URL: {e}")
        # For MAC URLs, we MUST NOT return the original mac:// URL
        # because FFmpeg cannot handle it - re-raise the exception instead
        if input_url and input_url.startswith("mac://"):
            logger.error("Cannot return unresolved mac:// URL - re-raising exception")
            raise
        return input_url  # Return original URL on error (only for non-MAC URLs)

def get_stream_info_for_switch(channel_id: str, target_stream_id: Optional[int] = None) -> dict:
    """
    Get stream information for a channel switch, optionally to a specific stream ID.

    Args:
        channel_id: The UUID of the channel
        target_stream_id: Optional specific stream ID to switch to

    Returns:
        dict: Stream information including URL, user agent and transcode flag
    """
    try:
        from core.utils import RedisClient
        from .utils import get_channel_by_id

        # Use helper function that handles both UUID and stream_hash
        channel = get_channel_by_id(channel_id)
        if not channel:
            return {'error': f'Channel not found: {channel_id}'}
        
        redis_client = RedisClient.get_client()

        # Use the target stream if specified, otherwise use current stream
        if target_stream_id:
            stream_id = target_stream_id

            # Get the stream object
            stream = get_object_or_404(Stream, pk=stream_id)

            # Find compatible profile for this stream with connection availability check
            m3u_account = stream.m3u_account
            if not m3u_account:
                return {'error': 'Stream has no M3U account'}

            m3u_profiles = m3u_account.profiles.filter(is_active=True)
            default_profile = next((obj for obj in m3u_profiles if obj.is_default), None)

            if not default_profile:
                return {'error': 'M3U account has no default profile'}

            # Check profiles in order: default first, then others
            profiles = [default_profile] + [obj for obj in m3u_profiles if not obj.is_default]

            selected_profile = None
            for profile in profiles:

                # Check connection availability
                if redis_client:
                    profile_connections_key = f"profile_connections:{profile.id}"
                    current_connections = int(redis_client.get(profile_connections_key) or 0)

                    # Check if this channel is already using this profile
                    channel_using_profile = False
                    existing_stream_id = redis_client.get(f"channel_stream:{channel.id}")
                    if existing_stream_id:
                        # Decode bytes to string/int for proper Redis key lookup
                        existing_stream_id = existing_stream_id.decode('utf-8')
                        existing_profile_id = redis_client.get(f"stream_profile:{existing_stream_id}")
                        if existing_profile_id and int(existing_profile_id.decode('utf-8')) == profile.id:
                            channel_using_profile = True
                            logger.debug(f"Channel {channel.id} already using profile {profile.id}")

                    # Calculate effective connections (subtract 1 if channel already using this profile)
                    effective_connections = current_connections - (1 if channel_using_profile else 0)

                    # Check if profile has available slots
                    if profile.max_streams == 0 or effective_connections < profile.max_streams:
                        selected_profile = profile
                        logger.debug(f"Selected profile {profile.id} with {effective_connections}/{profile.max_streams} effective connections (current: {current_connections}, already using: {channel_using_profile})")
                        break
                    else:
                        logger.debug(f"Profile {profile.id} at max connections: {effective_connections}/{profile.max_streams} (current: {current_connections}, already using: {channel_using_profile})")
                else:
                    # No Redis available, assume first active profile is okay
                    selected_profile = profile
                    break

            if not selected_profile:
                return {'error': 'No profiles available with connection capacity'}

            m3u_profile_id = selected_profile.id
        else:
            stream_id, m3u_profile_id, error_reason = channel.get_stream()
            if stream_id is None or m3u_profile_id is None:
                return {'error': error_reason or 'No stream assigned to channel'}

        # Get the stream and profile objects directly
        stream = get_object_or_404(Stream, pk=stream_id)
        profile = get_object_or_404(M3UAccountProfile, pk=m3u_profile_id)

        # Check connections left
        m3u_account = M3UAccount.objects.get(id=profile.m3u_account.id)
        #connections_left = get_connections_left(m3u_profile_id)

        #if connections_left <= 0:
            #logger.warning(f"No connections left for M3U account {m3u_account.id}")
            #return {'error': 'No connections left'}

        # Get the user agent from the M3U account
        user_agent = m3u_account.get_user_agent().user_agent

        # Generate URL using the transform function directly
        stream_url = transform_url(stream.url, profile.search_pattern, profile.replace_pattern, stream, m3u_account)

        # Get transcode info from the channel's stream profile
        stream_profile = channel.get_stream_profile()
        transcode = not (stream_profile.is_proxy() or stream_profile is None)
        profile_value = stream_profile.id

        return {
            'url': stream_url,
            'user_agent': user_agent,
            'transcode': transcode,
            'stream_profile': profile_value,
            'stream_id': stream_id,
            'm3u_profile_id': m3u_profile_id
        }
    except Exception as e:
        logger.error(f"Error getting stream info for switch: {e}", exc_info=True)
        return {'error': f'Error: {str(e)}'}

def get_alternate_streams(channel_id: str, current_stream_id: Optional[int] = None) -> List[dict]:
    """
    Get alternative streams for a channel when the current stream fails.

    Args:
        channel_id: The UUID of the channel
        current_stream_id: The currently failing stream ID to exclude

    Returns:
        List[dict]: List of stream information dictionaries with stream_id and profile_id
    """
    try:
        from core.utils import RedisClient

        # Get channel object
        channel = get_stream_object(channel_id)
        if isinstance(channel, Stream):
            logger.error(f"Stream is not a channel")
            return []

        redis_client = RedisClient.get_client()
        logger.debug(f"Looking for alternate streams for channel {channel_id}, current stream ID: {current_stream_id}")

        # Get all assigned streams for this channel using the correct ordering
        streams = channel.streams.all().order_by('channelstream__order')
        logger.debug(f"Channel {channel_id} has {streams.count()} total assigned streams")

        if not streams.exists():
            logger.warning(f"No streams assigned to channel {channel_id}")
            return []

        alternate_streams = []

        # Process each stream in the user-defined order
        for stream in streams:
            logger.debug(f"Checking stream ID {stream.id} ({stream.name}) for channel {channel_id}")

            # Skip the current failing stream
            if current_stream_id and stream.id == current_stream_id:
                logger.debug(f"Skipping current stream ID {current_stream_id}")
                continue

            # Find compatible profiles for this stream with connection checking
            try:
                m3u_account = stream.m3u_account
                if not m3u_account:
                    logger.debug(f"Stream {stream.id} has no M3U account")
                    continue
                if m3u_account.is_active == False:
                    logger.debug(f"M3U account {m3u_account.id} is inactive, skipping.")
                    continue
                m3u_profiles = m3u_account.profiles.filter(is_active=True)
                default_profile = next((obj for obj in m3u_profiles if obj.is_default), None)

                if not default_profile:
                    logger.debug(f"M3U account {m3u_account.id} has no default profile")
                    continue

                # Check profiles in order with connection availability
                profiles = [default_profile] + [obj for obj in m3u_profiles if not obj.is_default]

                selected_profile = None
                for profile in profiles:
                    # Check connection availability
                    if redis_client:
                        profile_connections_key = f"profile_connections:{profile.id}"
                        current_connections = int(redis_client.get(profile_connections_key) or 0)

                        # Check if this channel is already using this profile
                        channel_using_profile = False
                        existing_stream_id = redis_client.get(f"channel_stream:{channel.id}")
                        if existing_stream_id:
                            # Decode bytes to string/int for proper Redis key lookup
                            existing_stream_id = existing_stream_id.decode('utf-8')
                            existing_profile_id = redis_client.get(f"stream_profile:{existing_stream_id}")
                            if existing_profile_id and int(existing_profile_id.decode('utf-8')) == profile.id:
                                channel_using_profile = True
                                logger.debug(f"Channel {channel.id} already using profile {profile.id}")

                        # Calculate effective connections (subtract 1 if channel already using this profile)
                        effective_connections = current_connections - (1 if channel_using_profile else 0)

                        # Check if profile has available slots
                        if profile.max_streams == 0 or effective_connections < profile.max_streams:
                            selected_profile = profile
                            logger.debug(f"Found available profile {profile.id} for stream {stream.id}: {effective_connections}/{profile.max_streams} effective (current: {current_connections}, already using: {channel_using_profile})")
                            break
                        else:
                            logger.debug(f"Profile {profile.id} at max connections: {effective_connections}/{profile.max_streams} (current: {current_connections}, already using: {channel_using_profile})")
                    else:
                        # No Redis available, assume first active profile is okay
                        selected_profile = profile
                        break

                if selected_profile:
                    # For MAC accounts, also check if any MACs are available (not all busy)
                    if m3u_account.account_type == M3UAccount.Types.MAC and redis_client:
                        try:
                            # Check if at least one MAC is available (not busy and not in cooldown)
                            mac_available = False
                            for mac in m3u_account.macs.all():
                                busy_key = f"mac:busy:{mac.id}"
                                cooldown_key = f"mac:cooldown:{mac.id}"
                                is_busy = redis_client.exists(busy_key)
                                is_cooldown = redis_client.exists(cooldown_key)
                                if not is_busy and not is_cooldown:
                                    mac_available = True
                                    break
                            
                            if not mac_available:
                                logger.debug(f"Stream {stream.id}: All MACs busy/cooldown for MAC account {m3u_account.id}, skipping")
                                continue
                        except Exception as mac_e:
                            logger.debug(f"Error checking MAC availability for stream {stream.id}: {mac_e}")
                            # Continue anyway - let transform_url handle it
                    
                    alternate_streams.append({
                        'stream_id': stream.id,
                        'profile_id': selected_profile.id,
                        'name': stream.name,
                        'account_type': m3u_account.account_type
                    })
                else:
                    logger.debug(f"No available profiles for stream ID {stream.id}")

            except Exception as inner_e:
                logger.error(f"Error finding profiles for stream {stream.id}: {inner_e}")
                continue

        if alternate_streams:
            stream_ids = ', '.join([str(s['stream_id']) for s in alternate_streams])
            logger.info(f"Found {len(alternate_streams)} alternate streams with available connections for channel {channel_id}: [{stream_ids}]")
        else:
            logger.warning(f"No alternate streams with available connections found for channel {channel_id}")

        return alternate_streams
    except Exception as e:
        logger.error(f"Error getting alternate streams for channel {channel_id}: {e}", exc_info=True)
        return []

def validate_stream_url(url, user_agent=None, timeout=(5, 5), proxy=None):
    """
    Validate if a stream URL is accessible without downloading the full content.

    Note: UDP/RTP/RTSP streams are automatically considered valid as they cannot
    be validated via HTTP methods.

    Args:
        url (str): The URL to validate
        user_agent (str): User agent to use for the request
        timeout (tuple): Connection and read timeout in seconds
        proxy (str): Proxy URL to use for the request (e.g., http://proxy:8080)

    Returns:
        tuple: (is_valid, final_url, status_code, message)
    """
    # Check if URL uses non-HTTP protocols (UDP/RTP/RTSP)
    # These cannot be validated via HTTP methods, so we skip validation
    if url.startswith(('udp://', 'rtp://', 'rtsp://')):
        logger.info(f"Skipping HTTP validation for non-HTTP protocol: {url}")
        return True, url, 200, "Non-HTTP protocol (UDP/RTP/RTSP) - validation skipped"

    try:
        # Create session with proper headers
        session = requests.Session()
        headers = {
            'User-Agent': user_agent,
            'Connection': 'close'  # Don't keep connection alive
        }
        session.headers.update(headers)

        # Configure proxy if provided
        proxies = None
        if proxy:
            proxies = {
                'http': proxy,
                'https': proxy
            }
            logger.debug(f"Using proxy {proxy} for stream validation")

        # Make HEAD request first as it's faster and doesn't download content
        head_response = session.head(
            url,
            timeout=timeout,
            allow_redirects=True,
            proxies=proxies
        )

        # If HEAD not supported, server will return 405 or other error
        if 200 <= head_response.status_code < 300:
            # HEAD request successful
            return True, head_response.url, head_response.status_code, "Valid (HEAD request)"

        # Try a GET request with stream=True to avoid downloading all content
        get_response = session.get(
            url,
            stream=True,
            timeout=timeout,
            allow_redirects=True,
            proxies=proxies
        )

        # IMPORTANT: Check status code first before checking content
        if not (200 <= get_response.status_code < 300):
            logger.warning(f"Stream validation failed with HTTP status {get_response.status_code}")
            return False, get_response.url, get_response.status_code, f"Invalid HTTP status: {get_response.status_code}"

        # Only check content if status code is valid
        try:
            chunk = next(get_response.iter_content(chunk_size=188*10))
            is_valid = len(chunk) > 0
            message = f"Valid (GET request, received {len(chunk)} bytes)"
        except StopIteration:
            is_valid = False
            message = "Empty response from server"

        # Check content type for additional validation
        content_type = get_response.headers.get('Content-Type', '').lower()

        # Expanded list of valid content types for streaming media
        valid_content_types = [
            'video/',
            'audio/',
            'mpegurl',
            'octet-stream',
            'mp2t',
            'mp4',
            'mpeg',
            'dash+xml',
            'application/mp4',
            'application/mpeg',
            'application/x-mpegurl',
            'application/vnd.apple.mpegurl',
            'application/ogg',
            'm3u',
            'playlist',
            'binary/',
            'rtsp',
            'rtmp',
            'hls',
            'ts'
        ]

        content_type_valid = any(type_str in content_type for type_str in valid_content_types)

        # Always consider the stream valid if we got data, regardless of content type
        # But add content type info to the message for debugging
        if content_type:
            content_type_msg = f" (Content-Type: {content_type}"
            if content_type_valid:
                content_type_msg += ", recognized as valid stream format)"
            else:
                content_type_msg += ", unrecognized but may still work)"
            message += content_type_msg

        # Clean up connection
        get_response.close()

        # If we have content, consider it valid even with unrecognized content type
        return is_valid, get_response.url, get_response.status_code, message

    except requests.exceptions.Timeout:
        return False, url, 0, "Timeout connecting to stream"
    except requests.exceptions.TooManyRedirects:
        return False, url, 0, "Too many redirects"
    except requests.exceptions.RequestException as e:
        return False, url, 0, f"Request error: {str(e)}"
    except Exception as e:
        return False, url, 0, f"Validation error: {str(e)}"
    finally:
        if 'session' in locals():
            session.close()

def get_channel_proxy(channel):
    """
    Get the proxy setting from the associated M3U account for this channel.
    
    Args:
        channel: Channel object
        
    Returns:
        str or None: Proxy URL if configured, None otherwise
    """
    try:
        # Check if channel has a channel_group
        if not channel.channel_group:
            return None
            
        # Get M3U accounts associated with this channel group
        channel_group_accounts = channel.channel_group.m3u_accounts.filter(enabled=True)
        
        for cga in channel_group_accounts:
            m3u_account = cga.m3u_account
            proxy = m3u_account.get_proxy()
            if proxy:
                logger.debug(f"Found proxy {proxy} from M3U account {m3u_account.name} (type: {m3u_account.account_type}) for channel {channel.uuid}")
                return proxy
                
        return None
        
    except Exception as e:
        logger.error(f"Error getting channel proxy for channel {channel.uuid}: {e}")
        return None

def get_connections_left(m3u_profile_id: int) -> int:
    """
    Get the number of available connections left for an M3U profile.

    Args:
        m3u_profile_id: The ID of the M3U profile

    Returns:
        int: Number of connections available (0 if none available)
    """
    try:
        from core.utils import RedisClient

        # Get the M3U profile
        m3u_profile = M3UAccountProfile.objects.get(id=m3u_profile_id)

        # If max_streams is 0, it means unlimited
        if m3u_profile.max_streams == 0:
            return 999999  # Return a large number to indicate unlimited

        # Get Redis client
        redis_client = RedisClient.get_client()
        if not redis_client:
            logger.warning("Redis not available, assuming connections available")
            return max(0, m3u_profile.max_streams - 1)  # Conservative estimate

        # Check current connections for this specific profile
        profile_connections_key = f"profile_connections:{m3u_profile_id}"
        current_connections = int(redis_client.get(profile_connections_key) or 0)

        # Calculate available connections
        connections_left = max(0, m3u_profile.max_streams - current_connections)

        logger.debug(f"M3U profile {m3u_profile_id}: {current_connections}/{m3u_profile.max_streams} used, {connections_left} available")

        return connections_left

    except M3UAccountProfile.DoesNotExist:
        logger.error(f"M3U profile {m3u_profile_id} not found")
        return 0
    except Exception as e:
        logger.error(f"Error getting connections left for M3U profile {m3u_profile_id}: {e}")
        return 0


def _resolve_mac_stream_with_failover(
    m3u_account: M3UAccount,
    stream: Stream,
) -> Tuple[Optional[str], Optional['M3UAccountMac'], Optional[str]]:
    """Resolve a MAC/STB-Portal stream URL using the first valid MAC.

    Tries MACs in priority order. Skips those marked EXPIRED/ERROR or with past expires_at.
    For each MAC, it can also try multiple HTTP proxies (if configured) before giving up
    on that MAC. On MAC-level errors (expired, unauthorized, etc.) the MAC is marked as
    EXPIRED/ERROR so it won't be retried until the next refresh.
    
    IMPORTANT: This version marks MACs as BUSY (with cooldown) instead of ERROR when they
    fail during runtime. A MAC that's streaming isn't broken, it just needs a pause.
    """
    from apps.m3u.models import M3UAccountMac
    from apps.m3u.mac_portal_client import MacPortalClient, MacPortalError
    from django.utils import timezone as django_timezone
    from .redis_keys import RedisKeys
    
    if m3u_account.account_type != M3UAccount.Types.MAC:
        return stream.url, None, None

    props = m3u_account.custom_properties or {}
    # Proxy is a direct field on M3UAccount, not in custom_properties
    proxy_value = getattr(m3u_account, 'proxy', None) or props.get("proxy")
    timezone = props.get("timezone", "Europe/Berlin")

    # Parse proxy list: support comma, whitespace or newline separated values
    proxy_list: List[Optional[str]] = []
    if isinstance(proxy_value, str):
        raw = proxy_value.replace("\r", "\n")
        raw = raw.replace(",", "\n")
        parts = [p.strip() for p in raw.split() if p.strip()]
        seen = set()
        for p in parts:
            if p not in seen:
                seen.add(p)
                proxy_list.append(p)
    elif isinstance(proxy_value, (list, tuple)):
        seen = set()
        for p in proxy_value:
            s = str(p).strip()
            if s and s not in seen:
                seen.add(s)
                proxy_list.append(s)

    # If no proxy configured at all: try direct only
    if not proxy_list:
        proxy_list = [None]

    # Try to get a Redis client for MAC busy tracking (optional).
    try:
        from core.utils import RedisClient
        redis_client = RedisClient.get_client()
    except Exception:
        redis_client = None

    # determine command for the portal
    stream_props = stream.custom_properties or {}
    cmd = stream_props.get("mac_cmd") or stream_props.get("cmd")
    
    # CRITICAL FIX: If cmd is not set, extract from mac:// URL or stream.url
    if not cmd:
        import re
        import base64
        from urllib.parse import urlparse, parse_qs
        
        try:
            # First check if stream.url is a mac:// URL
            if stream.url and stream.url.startswith("mac://"):
                # Extract cmd from mac:// URL format: mac://base64(portal_url|mac|cmd|proxy)
                encoded_data = stream.url[6:]  # Remove "mac://" prefix
                decoded_data = base64.urlsafe_b64decode(encoded_data).decode()
                parts = decoded_data.split("|", 3)
                if len(parts) >= 3:
                    cmd = parts[2]  # cmd is the third part
                    logger.debug(f"Extracted cmd '{cmd[:50]}...' from mac:// URL")
            
            # If still no cmd, try to extract stream ID from URL query parameters
            if not cmd:
                parsed = urlparse(stream.url)
                qs = parse_qs(parsed.query)
                stream_id_from_url = qs.get("stream", [None])[0] or qs.get("ch", [None])[0]
                
                if stream_id_from_url:
                    # Check if it's a simple numeric ID or base64-encoded
                    if stream_id_from_url.isdigit():
                        cmd = stream_id_from_url
                        logger.debug(f"Extracted stream ID '{cmd}' from URL for MAC failover")
                    else:
                        # It's base64 or complex - try to decode and extract
                        try:
                            decoded = base64.b64decode(stream_id_from_url).decode('utf-8')
                            # Look for stream ID pattern in decoded string
                            match = re.search(r'/ch/(\d+)', decoded)
                            if match:
                                cmd = match.group(1)
                                logger.debug(f"Extracted stream ID '{cmd}' from base64-encoded URL")
                            else:
                                # Fallback: use the original URL
                                cmd = stream.url
                                logger.warning(f"Could not extract stream ID from base64, using full URL as cmd")
                        except Exception:
                            cmd = stream.url
                            logger.warning(f"Could not decode base64 stream parameter, using full URL as cmd")
                else:
                    # No stream parameter found, use full URL as fallback
                    cmd = stream.url
                    logger.debug(f"No stream parameter in URL, using full URL as cmd")
        except Exception as e:
            logger.warning(f"Error extracting stream ID from URL: {e}, using full URL as cmd")
            cmd = stream.url

    error_messages = []

    # get candidate MACs in priority order
    try:
        candidates = m3u_account.get_candidate_macs_for_streaming()
    except Exception as e:
        logger.error(f"Error getting candidate MACs for account {m3u_account.id}: {e}")
        candidates = []

    if not candidates:
        logger.error(f"No candidate MACs available for account {m3u_account.id}")
        return None, None, "No candidate MACs available"
    
    # Limit to maximum attempts setting
    try:
        from apps.m3u.mac_portal_models import FailoverSettings
        settings = FailoverSettings.get_settings()
        max_attempts = settings.mac_max_attempts if settings.mac_max_attempts > 0 else len(candidates)
        if len(candidates) > max_attempts:
            logger.info(f"Limiting MAC attempts from {len(candidates)} to {max_attempts} for account {m3u_account.id}")
            candidates = candidates[:max_attempts]
    except Exception as e:
        logger.debug(f"Could not check MAC max attempts setting: {e}")
        # Continue with all candidates if settings can't be loaded

    # If Redis is available, filter out MACs that are:
    # 1. BUSY (actively streaming on another channel)
    # 2. In COOLDOWN (failed recently and need a break)
    if redis_client:
        free_candidates: List[M3UAccountMac] = []
        busy_or_cooldown_candidates: List[M3UAccountMac] = []
        try:
            for m in candidates:
                try:
                    # Use MACStateManager to check BUSY and COOLDOWN flags
                    mac_state = MACStateManager(redis_client)
                    is_busy = mac_state.is_busy(m.id)
                    is_cooldown = mac_state.is_in_cooldown(m.id)
                    
                    if is_busy or is_cooldown:
                        busy_or_cooldown_candidates.append(m)
                        if is_busy:
                            logger.debug(f"MAC {m.address} (id={m.id}) is BUSY (actively streaming)")
                        if is_cooldown:
                            logger.debug(f"MAC {m.address} (id={m.id}) is in COOLDOWN (failed recently)")
                    else:
                        free_candidates.append(m)
                except Exception:
                    # If check fails, assume MAC is free (fail-safe)
                    free_candidates.append(m)
        except Exception:
            # Fallback: if anything goes wrong, use the original list
            free_candidates = candidates
            busy_or_cooldown_candidates = []

        if free_candidates:
            candidates = free_candidates
        elif candidates:
            # All MACs are busy or in cooldown → return error
            # so the caller can fall back to backup streams/other profiles.
            logger.warning(
                "All candidate MACs are currently busy or in cooldown for MAC account %s – skipping MAC usage",
                m3u_account.id,
            )
            return None, None, "All MACs busy"
    # If no Redis available, use the original candidate list.

    # Try each MAC, and for each MAC, try each configured proxy until one works
    for mac_entry in candidates:
        mac_value = mac_entry.address
        last_error_for_mac: Optional[str] = None
        
        # RACE CONDITION FIX: Set a temporary BUSY flag BEFORE trying to resolve URL
        # This prevents two streams from selecting the same MAC simultaneously.
        # The temporary flag expires after 30 seconds if connection fails.
        # stream_manager.py will set the permanent BUSY flag after connection succeeds.
        if redis_client:
            try:
                mac_state = MACStateManager(redis_client)
                # Double-check: is this MAC still free? (another stream might have grabbed it)
                if mac_state.is_busy(mac_entry.id):
                    logger.debug(f"MAC {mac_value} (id={mac_entry.id}) was grabbed by another stream, skipping")
                    continue
                # Set temporary BUSY with 30 second TTL (auto-expires if connection fails)
                temp_busy_key = f"mac:busy:{mac_entry.id}"
                redis_client.setex(temp_busy_key, 30, "1")
                logger.debug(f"MAC {mac_value} (id={mac_entry.id}) temporary BUSY set (30s TTL)")
            except Exception as e:
                logger.warning(f"Failed to set temporary BUSY for MAC {mac_value}: {e}")

        for proxy in proxy_list:
            try:
                client = MacPortalClient(
                    base_url=m3u_account.server_url,
                    mac=mac_value,
                    proxy=proxy,
                    timezone=timezone,
                )
                url = client.create_link(cmd)
                
                # URL successfully resolved!
                # The temporary BUSY flag (30s TTL) is already set.
                # stream_manager.py will upgrade it to permanent BUSY after connection succeeds.
                # If connection fails within 30s, the temporary flag auto-expires.
                
                # Successfully built link → mark valid and return
                try:
                    mac_entry.status = M3UAccountMac.Status.VALID
                    mac_entry.last_checked = django_timezone.now()
                    mac_entry.last_error = None
                    mac_entry.save(update_fields=["status", "last_checked", "last_error"])
                except Exception:
                    pass

                return url, mac_entry, None

            except MacPortalError as e:
                # MAC-level error (expired / unauthorized / blocked / etc.) → mark MAC and stop trying further proxies for it
                msg = str(e)
                logger.warning(
                    "MAC portal error for MAC %s on account %s with proxy %s: %s",
                    mac_value,
                    m3u_account.id,
                    proxy,
                    msg,
                )
                error_messages.append(f"{mac_value}: {msg}")
                last_error_for_mac = msg
                status = M3UAccountMac.Status.ERROR
                lowered = msg.lower()
                
                # Detect error type for appropriate cooldown
                is_block_error = False
                if "expir" in lowered or "no active" in lowered or "trial ended" in lowered:
                    status = M3UAccountMac.Status.EXPIRED
                elif any(keyword in lowered for keyword in [
                    "device in use", "device conflict", "already connected",
                    "mac blocked", "blocked", "banned", "max connections"
                ]):
                    is_block_error = True
                    logger.warning(f"MAC {mac_value}: Block/Device conflict detected")
                
                try:
                    mac_entry.status = status
                    mac_entry.last_error = msg
                    mac_entry.last_checked = django_timezone.now()
                    mac_entry.save(update_fields=["status", "last_error", "last_checked"])
                except Exception:
                    pass
                
                # Set COOLDOWN with appropriate duration
                # Note: No need to clear BUSY flag here since it's not set yet
                # (BUSY flag is set by stream_manager.py after connection succeeds)
                if redis_client:
                    try:
                        mac_state = MACStateManager(redis_client)
                        mac_state.mark_cooldown(mac_entry.id, is_block=is_block_error)
                        cooldown_type = "block (30 min)" if is_block_error else "failure (5 min)"
                        logger.info(f"MAC {mac_value}: COOLDOWN set ({cooldown_type})")
                    except Exception:
                        pass
                # MAC is obviously not valid → don't try other proxies
                break
            except Exception as e:
                # Network/proxy error: just log, try next proxy or MAC
                msg = str(e)
                logger.warning(
                    "Network/proxy error for MAC %s on account %s with proxy %s: %s",
                    mac_value,
                    m3u_account.id,
                    proxy,
                    msg,
                )
                last_error_for_mac = msg
                # Note: No need to clear BUSY flag here since it's not set yet
                # (BUSY flag is set by stream_manager.py after connection succeeds)
                continue

        # If we've tried all proxies and didn't get a URL, but it wasn't a
        # clear MAC error, log the last error for this MAC.
        if last_error_for_mac and mac_entry.status not in (M3UAccountMac.Status.ERROR, M3UAccountMac.Status.EXPIRED):
            error_messages.append(f"{mac_value}: {last_error_for_mac}")

    if error_messages:
        return None, None, "; ".join(error_messages)

    return None, None, "No usable MAC found"


def get_stream_info_for_profile(channel_id: str, stream_id: int, m3u_profile_id: int) -> dict:
    """
    Build URL/User-Agent/Transcode for a fixed combination of Stream + M3U profile.
    Return schema compatible with get_stream_info_for_switch(...).
    
    For MAC accounts, uses _resolve_mac_stream_with_failover to get the next available MAC.
    """
    try:
        obj = get_stream_object(channel_id)
        if isinstance(obj, Channel):
            channel = obj
        else:
            logger.info(
                "get_stream_info_for_profile: %s refers to a Stream, skipping profile failover",
                channel_id,
            )
            return {"error": "Channel ID refers to a Stream, not a Channel"}
        
        stream = get_object_or_404(Stream, pk=stream_id)
        m3u_profile = get_object_or_404(M3UAccountProfile, pk=m3u_profile_id)

        m3u_account = m3u_profile.m3u_account

        if m3u_account.account_type == M3UAccount.Types.MAC:
            # Use the simpler 0.12.0-04 style MAC resolution
            stream_url, mac_entry, error = _resolve_mac_stream_with_failover(m3u_account, stream)
            if not stream_url:
                return {"error": error or "Failed to resolve MAC stream"}
        else:
            input_url = stream.url
            stream_url = transform_url(input_url, m3u_profile.search_pattern, m3u_profile.replace_pattern, stream, m3u_account)

        stream_profile = channel.get_stream_profile()
        transcode = False if (stream_profile is None or stream_profile.is_proxy()) else True
        profile_value = stream_profile.id if stream_profile else None

        # Get user agent
        user_agent = m3u_account.get_user_agent().user_agent
        if not user_agent:
            default_ua = UserAgent.objects.filter(is_active=True).first()
            user_agent = default_ua.user_agent if default_ua else None

        return {
            "url": stream_url,
            "user_agent": user_agent,
            "transcode": transcode,
            "stream_profile": profile_value,
            "stream_id": stream.id,
            "m3u_profile_id": m3u_profile.id,
        }
    except Exception as e:
        logger.error(f"Error in get_stream_info_for_profile: {e}")
        return {"error": str(e)}


# === BEGIN: profile-first failover helpers ===
def get_next_profiles_for_stream(channel_id: str, stream_id: int, exclude_profile_id: Optional[int] = None) -> List[dict]:
    """
    Return available M3U profiles for THIS stream in order (default first),
    respecting max_streams, current usage, and cooldown markers. Optionally exclude the current profile.
    """
    try:
        from core.utils import RedisClient
        from .redis_keys import RedisKeys

        obj = get_stream_object(channel_id)
        if isinstance(obj, Channel):
            channel = obj
        else:
            logger.info(
                "get_next_profiles_for_stream: %s refers to a Stream, skipping profile failover",
                channel_id,
            )
            return []
        stream = get_object_or_404(Stream, pk=stream_id)
        m3u_account = stream.m3u_account
        if not m3u_account:
            return []

        profiles_qs = m3u_account.profiles.filter(is_active=True)
        default_profile = next((p for p in profiles_qs if getattr(p, "is_default", False)), None)
        other_profiles = [p for p in profiles_qs if not getattr(p, "is_default", False)]
        ordered = ([default_profile] if default_profile else []) + other_profiles

        try:
            redis_client = RedisClient.get_client()
        except Exception:
            redis_client = None

        result: List[dict] = []
        for p in ordered:
            if not p:
                continue
            if exclude_profile_id and int(p.id) == int(exclude_profile_id):
                continue

            # Skip profiles that are on cooldown
            if redis_client:
                try:
                    cooldown_key = RedisKeys.m3u_profile_cooldown(p.id)
                    if redis_client.exists(cooldown_key):
                        logger.info(
                            "Skipping M3U profile %s for stream %s on channel %s due to active cooldown",
                            p.id,
                            stream.id,
                            channel.id,
                        )
                        continue
                except Exception:
                    # Ignore cooldown check failures, fall back to normal behavior
                    pass

            allowed = True
            if redis_client:
                try:
                    current = int(redis_client.get(f"profile_connections:{p.id}") or 0)
                except Exception:
                    current = 0

                channel_using_profile = False
                try:
                    existing_stream_id = redis_client.get(f"channel_stream:{channel.id}")
                    if existing_stream_id:
                        existing_stream_id = existing_stream_id.decode("utf-8")
                        existing_profile_id = redis_client.get(f"stream_profile:{existing_stream_id}")
                        if existing_profile_id and int(existing_profile_id.decode("utf-8")) == p.id:
                            channel_using_profile = True
                except Exception:
                    pass

                effective = current - (1 if channel_using_profile else 0)
                if p.max_streams > 0 and effective >= p.max_streams:
                    allowed = False

            if allowed:
                result.append({"profile_id": p.id, "name": getattr(p, "name", str(p.id))})

        return result
    except Exception as e:
        logger.error(f"Error in get_next_profiles_for_stream: {e}", exc_info=True)
        return []
# === END: profile-first failover helpers ===
