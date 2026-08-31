"""
Helper module to access configuration values with proper defaults.
"""

from apps.proxy.config import TSConfig as Config

class ConfigHelper:
    """
    Helper class for accessing configuration values with sensible defaults.
    This simplifies code and ensures consistent defaults across the application.
    """

    @staticmethod
    def get(name, default=None):
        """Get a configuration value with a default fallback"""
        return getattr(Config, name, default)

    # Commonly used configuration values
    @staticmethod
    def connection_timeout():
        """Get connection timeout in seconds from database or default"""
        settings = Config.get_proxy_settings()
        return settings.get("connection_timeout", 10)

    @staticmethod
    def client_wait_timeout():
        """Get client wait timeout in seconds from database or default"""
        settings = Config.get_proxy_settings()
        return settings.get("client_wait_timeout", 30)

    @staticmethod
    def stream_timeout():
        """Get stream timeout in seconds from database or default"""
        settings = Config.get_proxy_settings()
        return settings.get("stream_timeout", 60)

    @staticmethod
    def channel_shutdown_delay():
        """Get channel shutdown delay in seconds"""
        return Config.get_channel_shutdown_delay()

    @staticmethod
    def initial_behind_chunks():
        """Get number of chunks to start behind"""
        return ConfigHelper.get('INITIAL_BEHIND_CHUNKS', 4)

    @staticmethod
    def new_client_behind_seconds():
        """Get number of seconds behind live to start new clients.
        0 means start at live (buffer head).
        Loaded from DB proxy_settings so users can change it at runtime."""
        from apps.proxy.config import TSConfig
        settings = TSConfig.get_proxy_settings()
        return settings.get('new_client_behind_seconds', 5)

    @staticmethod
    def keepalive_interval():
        """Get keepalive interval in seconds"""
        return ConfigHelper.get('KEEPALIVE_INTERVAL', 0.5)

    @staticmethod
    def cleanup_check_interval():
        """Get cleanup check interval in seconds"""
        return ConfigHelper.get('CLEANUP_CHECK_INTERVAL', 3)

    @staticmethod
    def redis_chunk_ttl():
        """Get Redis chunk TTL in seconds"""
        return Config.get_redis_chunk_ttl()

    @staticmethod
    def chunk_size():
        """Get chunk size in bytes"""
        return ConfigHelper.get('CHUNK_SIZE', 8192)

    @staticmethod
    def max_retries():
        """Get maximum retry attempts from database or default"""
        settings = Config.get_proxy_settings()
        return settings.get("max_retries", 3)

    @staticmethod
    def retry_window_seconds():
        """Reset the retry counter after this many seconds without a failure."""
        settings = Config.get_proxy_settings()
        return settings.get("retry_window_seconds", 1800)

    @staticmethod
    def stable_connection_threshold():
        """Seconds of stable playback before switch rotation state resets."""
        settings = Config.get_proxy_settings()
        return settings.get("stable_connection_threshold", 30)

    @staticmethod
    def max_stream_switches():
        """Get maximum number of stream switch attempts from database or default"""
        settings = Config.get_proxy_settings()
        return settings.get("max_stream_switches", 10)

    @staticmethod
    def failover_rotation_cooldown():
        """Seconds to wait after exhausting all streams before wrapping rotation."""
        settings = Config.get_proxy_settings()
        return settings.get("failover_rotation_cooldown", 60)

    @staticmethod
    def retry_wait_interval():
        """Get wait interval between connection retries in seconds"""
        settings = Config.get_proxy_settings()
        return settings.get("retry_wait_interval", 0.5)

    @staticmethod
    def url_switch_timeout():
        """Get URL switch timeout in seconds (max time allowed for a stream switch operation)"""
        settings = Config.get_proxy_settings()
        return settings.get("url_switch_timeout", 20)

    @staticmethod
    def failover_grace_period():
        """Get extra time (in seconds) to allow for stream switching before disconnecting clients"""
        settings = Config.get_proxy_settings()
        return settings.get("failover_grace_period", 20)

    @staticmethod
    def buffering_timeout():
        """Get buffering timeout in seconds"""
        return Config.get_buffering_timeout()

    @staticmethod
    def buffering_speed():
        """Get buffering speed threshold"""
        return Config.get_buffering_speed()

    @staticmethod
    def channel_init_grace_period():
        """Max seconds to wait for initial buffer fill during channel startup."""
        return Config.get_channel_init_grace_period()

    @staticmethod
    def channel_client_wait_period():
        """Seconds to keep a ready channel alive waiting for the first client to connect."""
        return Config.get_channel_client_wait_period()

    @staticmethod
    def chunk_timeout():
        """
        Get chunk timeout in seconds (used for both socket and HTTP read timeouts).
        This controls how long we wait for each chunk before timing out.
        Set this higher (e.g., 30s) for slow providers that may have intermittent delays.
        """
        settings = Config.get_proxy_settings()
        return settings.get("chunk_timeout", 5)

    @staticmethod
    def stream_cooldown_enabled():
        """Get whether stream cooldown is enabled from database or default"""
        settings = Config.get_proxy_settings()
        return settings.get("stream_cooldown_enabled", False)

    @staticmethod
    def stream_cooldown_seconds():
        """Get stream cooldown duration in seconds (converted from minutes) from database or default"""
        settings = Config.get_proxy_settings()
        minutes = settings.get("stream_cooldown_minutes", 10)
        return int(minutes) * 60
