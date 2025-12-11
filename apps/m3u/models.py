from django.db import models
from django.core.exceptions import ValidationError
from core.models import UserAgent
import re
import logging
from django.dispatch import receiver
from apps.channels.models import StreamProfile
from django_celery_beat.models import PeriodicTask
from core.models import CoreSettings, UserAgent
from django.utils import timezone

logger = logging.getLogger(__name__)

CUSTOM_M3U_ACCOUNT_NAME = "custom"

# MAC address validation regex pattern
MAC_ADDRESS_PATTERN = re.compile(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$')


def normalize_mac_address(mac: str) -> str:
    """
    Normalize a MAC address to uppercase with colons.
    Accepts formats: AA:BB:CC:DD:EE:FF, AA-BB-CC-DD-EE-FF, AABBCCDDEEFF
    Returns: AA:BB:CC:DD:EE:FF
    """
    if not mac:
        return ""
    # Remove all separators and convert to uppercase
    clean = mac.replace(":", "").replace("-", "").upper()
    if len(clean) != 12:
        return mac.upper()  # Return as-is if invalid length
    # Insert colons
    return ":".join(clean[i:i+2] for i in range(0, 12, 2))


def validate_mac_address(mac: str) -> bool:
    """Validate MAC address format (AA:BB:CC:DD:EE:FF)."""
    if not mac:
        return False
    normalized = normalize_mac_address(mac)
    return bool(MAC_ADDRESS_PATTERN.match(normalized))


def parse_mac_list(mac_string: str) -> list:
    """
    Parse a space-separated string of MAC addresses into a list of normalized addresses.
    Returns list of valid, normalized MAC addresses.
    """
    if not mac_string:
        return []
    
    addresses = []
    for part in mac_string.strip().split():
        normalized = normalize_mac_address(part.strip())
        if normalized and validate_mac_address(normalized):
            addresses.append(normalized)
    return addresses


class M3UAccount(models.Model):
    class Types(models.TextChoices):
        STADNARD = "STD", "Standard"
        XC = "XC", "Xtream Codes"
        MAC = "MAC", "MAC / STB-Portal"

    class Status(models.TextChoices):
        IDLE = "idle", "Idle"
        FETCHING = "fetching", "Fetching"
        PARSING = "parsing", "Parsing"
        ERROR = "error", "Error"
        SUCCESS = "success", "Success"
        PENDING_SETUP = "pending_setup", "Pending Setup"
        DISABLED = "disabled", "Disabled"

    """Represents an M3U Account for IPTV streams."""
    name = models.CharField(
        max_length=255, unique=True, help_text="Unique name for this M3U account"
    )
    server_url = models.URLField(
        max_length=1000,
        blank=True,
        null=True,
        help_text="The base URL of the M3U server (optional if a file is uploaded)",
    )
    file_path = models.CharField(max_length=255, blank=True, null=True)
    server_group = models.ForeignKey(
        "ServerGroup",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="m3u_accounts",
        help_text="The server group this M3U account belongs to",
    )
    max_streams = models.PositiveIntegerField(
        default=0, help_text="Maximum number of concurrent streams (0 for unlimited)"
    )
    is_active = models.BooleanField(
        default=True, help_text="Set to false to deactivate this M3U account"
    )
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="Time when this account was created"
    )
    updated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Time when this account was last successfully refreshed",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.IDLE
    )
    last_message = models.TextField(
        null=True,
        blank=True,
        help_text="Last status message, including success results or error information",
    )
    user_agent = models.ForeignKey(
        "core.UserAgent",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="m3u_accounts",
        help_text="The User-Agent associated with this M3U account.",
    )
    locked = models.BooleanField(
        default=False, help_text="Protected - can't be deleted or modified"
    )
    stream_profile = models.ForeignKey(
        StreamProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="m3u_accounts",
    )
    account_type = models.CharField(choices=Types.choices, default=Types.STADNARD)
    username = models.CharField(max_length=255, null=True, blank=True)
    password = models.CharField(max_length=255, null=True, blank=True)
    custom_properties = models.JSONField(default=dict, blank=True, null=True)
    refresh_interval = models.IntegerField(default=0)
    refresh_task = models.ForeignKey(
        PeriodicTask, on_delete=models.SET_NULL, null=True, blank=True
    )
    stale_stream_days = models.PositiveIntegerField(
        default=7,
        help_text="Number of days after which a stream will be removed if not seen in the M3U source.",
    )
    priority = models.PositiveIntegerField(
        default=0,
        help_text="Priority for VOD provider selection (higher numbers = higher priority). Used when multiple providers offer the same content.",
    )
    mac_address = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Space-separated MAC addresses for STB-Portal accounts",
    )

    def __str__(self):
        return self.name
    
    def _ensure_macs_from_mac_address(self):
        """
        Synchronize M3UAccountMac entries from the mac_address field.
        Creates new entries for new MACs, preserves existing ones, removes stale ones.
        """
        if self.account_type != self.Types.MAC:
            return
        
        # Parse current MAC addresses from the field
        current_macs = parse_mac_list(self.mac_address or "")
        
        # Get existing MAC entries
        existing_entries = {m.address: m for m in self.macs.all()}
        
        # Track which MACs we've processed
        processed = set()
        
        # Create or update entries for each MAC in the field
        for idx, mac in enumerate(current_macs):
            if mac in existing_entries:
                # Update priority if changed
                entry = existing_entries[mac]
                if entry.priority != idx:
                    entry.priority = idx
                    entry.save(update_fields=["priority"])
            else:
                # Create new entry
                M3UAccountMac.objects.create(
                    account=self,
                    address=mac,
                    priority=idx,
                    status=M3UAccountMac.Status.UNKNOWN,
                )
            processed.add(mac)
        
        # Remove entries that are no longer in the mac_address field
        for mac, entry in existing_entries.items():
            if mac not in processed:
                entry.delete()
        
        logger.debug(
            "Synced MAC addresses for account %s: %s",
            self.id,
            current_macs,
        )
    
    def get_mac_list(self) -> list:
        """Return normalized MAC addresses in priority order (for display)."""
        if self.account_type != self.Types.MAC:
            return []
        # Ensure DB entries are in sync
        self._ensure_macs_from_mac_address()
        return [m.address for m in self.macs.order_by("priority", "id")]
    
    def get_candidate_macs_for_streaming(self) -> list:
        """Return ordered list of M3UAccountMac objects that are usable for streaming."""
        if self.account_type != self.Types.MAC:
            return []
        self._ensure_macs_from_mac_address()
        # Return MACs that are not expired or in error state
        return [
            m for m in self.macs.order_by("priority", "id")
            if m.is_valid_for_streaming
        ]

    def clean(self):
        if self.max_streams < 0:
            raise ValidationError("Max streams cannot be negative.")

    def display_action(self):
        return "Exclude" if self.exclude else "Include"

    def deactivate_streams(self):
        """Deactivate all streams linked to this account."""
        for stream in self.streams.all():
            stream.is_active = False
            stream.save()

    def reactivate_streams(self):
        """Reactivate all streams linked to this account."""
        for stream in self.streams.all():
            stream.is_active = True
            stream.save()

    @classmethod
    def get_custom_account(cls):
        return cls.objects.get(name=CUSTOM_M3U_ACCOUNT_NAME, locked=True)

    def get_user_agent(self):
        user_agent = self.user_agent
        if not user_agent:
            user_agent = UserAgent.objects.get(
                id=CoreSettings.get_default_user_agent_id()
            )

        return user_agent

    def save(self, *args, **kwargs):
        # Prevent auto_now behavior by handling updated_at manually
        if "update_fields" in kwargs and "updated_at" not in kwargs["update_fields"]:
            # Don't modify updated_at for regular updates
            kwargs.setdefault("update_fields", [])
            if "updated_at" in kwargs["update_fields"]:
                kwargs["update_fields"].remove("updated_at")
        super().save(*args, **kwargs)

    # def get_channel_groups(self):
    #     return ChannelGroup.objects.filter(m3u_account__m3u_account=self)

    # def is_channel_group_enabled(self, channel_group):
    #     """Check if the specified ChannelGroup is enabled for this M3UAccount."""
    #     return self.channel_group.filter(channel_group=channel_group, enabled=True).exists()

    # def get_enabled_streams(self):
    #     """Return all streams linked to this account with enabled ChannelGroups."""
    #     return self.streams.filter(channel_group__in=ChannelGroup.objects.filter(m3u_account__enabled=True))


class M3UFilter(models.Model):
    """Defines filters for M3U accounts based on stream name or group title."""

    FILTER_TYPE_CHOICES = (
        ("group", "Group"),
        ("name", "Stream Name"),
        ("url", "Stream URL"),
    )

    m3u_account = models.ForeignKey(
        M3UAccount,
        on_delete=models.CASCADE,
        related_name="filters",
        help_text="The M3U account this filter is applied to.",
    )
    filter_type = models.CharField(
        max_length=50,
        choices=FILTER_TYPE_CHOICES,
        default="group",
        help_text="Filter based on either group title or stream name.",
    )
    regex_pattern = models.CharField(
        max_length=200, help_text="A regex pattern to match streams or groups."
    )
    exclude = models.BooleanField(
        default=True,
        help_text="If True, matching items are excluded; if False, only matches are included.",
    )
    order = models.PositiveIntegerField(default=0)
    custom_properties = models.JSONField(default=dict, blank=True, null=True)

    def applies_to(self, stream_name, group_name):
        target = group_name if self.filter_type == "group" else stream_name
        return bool(re.search(self.regex_pattern, target, re.IGNORECASE))

    def clean(self):
        try:
            re.compile(self.regex_pattern)
        except re.error:
            raise ValidationError(f"Invalid regex pattern: {self.regex_pattern}")

    def __str__(self):
        filter_type_display = dict(self.FILTER_TYPE_CHOICES).get(
            self.filter_type, "Unknown"
        )
        exclude_status = "Exclude" if self.exclude else "Include"
        return f"[{self.m3u_account.name}] {filter_type_display}: {self.regex_pattern} ({exclude_status})"

    @staticmethod
    def filter_streams(streams, filters):
        included_streams = set()
        excluded_streams = set()

        for f in filters:
            for stream in streams:
                if f.applies_to(stream.name, stream.group_name):
                    if f.exclude:
                        excluded_streams.add(stream)
                    else:
                        included_streams.add(stream)

        # If no include filters exist, assume all non-excluded streams are valid
        if not any(not f.exclude for f in filters):
            return streams.exclude(id__in=[s.id for s in excluded_streams])

        return streams.filter(id__in=[s.id for s in included_streams])


class ServerGroup(models.Model):
    """Represents a logical grouping of servers or channels."""

    name = models.CharField(
        max_length=100, unique=True, help_text="Unique name for this server group."
    )

    def __str__(self):
        return self.name


class M3UAccountProfile(models.Model):
    """Represents a profile associated with an M3U Account."""

    m3u_account = models.ForeignKey(
        "M3UAccount",
        on_delete=models.CASCADE,
        related_name="profiles",
        help_text="The M3U account this profile belongs to.",
    )
    name = models.CharField(
        max_length=255, help_text="Name for the M3U account profile"
    )
    is_default = models.BooleanField(
        default=False, help_text="Set to false to deactivate this profile"
    )
    max_streams = models.PositiveIntegerField(
        default=0, help_text="Maximum number of concurrent streams (0 for unlimited)"
    )
    is_active = models.BooleanField(
        default=True, help_text="Set to false to deactivate this profile"
    )
    search_pattern = models.CharField(
        max_length=255,
    )
    replace_pattern = models.CharField(
        max_length=255,
    )
    current_viewers = models.PositiveIntegerField(default=0)
    custom_properties = models.JSONField(
        default=dict, 
        blank=True, 
        null=True, 
        help_text="Custom properties for storing account information from provider (e.g., XC account details, expiration dates)"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["m3u_account", "name"], name="unique_account_name"
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.m3u_account.name})"

    def get_account_expiration(self):
        """Get account expiration date from custom properties if available"""
        if not self.custom_properties:
            return None
        
        user_info = self.custom_properties.get('user_info', {})
        exp_date = user_info.get('exp_date')
        
        if exp_date:
            try:
                from datetime import datetime
                # XC exp_date is typically a Unix timestamp
                if isinstance(exp_date, (int, float)):
                    return datetime.fromtimestamp(exp_date)
                elif isinstance(exp_date, str):
                    # Try to parse as timestamp first, then as ISO date
                    try:
                        return datetime.fromtimestamp(float(exp_date))
                    except ValueError:
                        return datetime.fromisoformat(exp_date)
            except (ValueError, TypeError):
                pass
        
        return None

    def get_account_status(self):
        """Get account status from custom properties if available"""
        if not self.custom_properties:
            return None
        
        user_info = self.custom_properties.get('user_info', {})
        return user_info.get('status')

    def get_max_connections(self):
        """Get maximum connections from custom properties if available"""
        if not self.custom_properties:
            return None
        
        user_info = self.custom_properties.get('user_info', {})
        return user_info.get('max_connections')

    def get_active_connections(self):
        """Get active connections from custom properties if available"""
        if not self.custom_properties:
            return None
        
        user_info = self.custom_properties.get('user_info', {})
        return user_info.get('active_cons')

    def get_last_refresh(self):
        """Get last refresh timestamp from custom properties if available"""
        if not self.custom_properties:
            return None
        
        last_refresh = self.custom_properties.get('last_refresh')
        if last_refresh:
            try:
                from datetime import datetime
                return datetime.fromisoformat(last_refresh)
            except (ValueError, TypeError):
                pass
        
        return None


class M3UAccountMac(models.Model):
    """
    Represents a single MAC address associated with a MAC/STB-Portal account.
    Tracks status, priority, and expiry information for failover management.
    """
    
    class Status(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"  # Never checked
        VALID = "valid", "Valid"
        EXPIRED = "expired", "Expired"
        ERROR = "error", "Error"  # Other error (portal down, max connections, etc.)
    
    account = models.ForeignKey(
        M3UAccount,
        on_delete=models.CASCADE,
        related_name="macs",
        help_text="Parent MAC / STB-Portal account",
    )
    address = models.CharField(
        max_length=17,
        help_text="Normalized MAC address (AA:BB:CC:DD:EE:FF)",
    )
    priority = models.PositiveIntegerField(
        default=0,
        help_text="Order in which MACs are tried for streaming (0 = highest priority)",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UNKNOWN,
        help_text="Validation status based on last portal check",
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Parsed expiry timestamp if available",
    )
    expires_text = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Raw expiry text from portal (for UI display)",
    )
    last_checked = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of last portal validation check",
    )
    last_error = models.TextField(
        null=True,
        blank=True,
        help_text="Last error message from portal communication",
    )
    
    class Meta:
        ordering = ["priority", "id"]
        unique_together = ("account", "address")
        verbose_name = "MAC Address"
        verbose_name_plural = "MAC Addresses"
    
    def __str__(self):
        return f"{self.address} ({self.account.name})"
    
    @property
    def is_valid_for_streaming(self) -> bool:
        """Check if this MAC is currently valid for streaming attempts."""
        if self.status == self.Status.EXPIRED:
            return False
        if self.status == self.Status.ERROR:
            return False
        if self.expires_at and self.expires_at <= timezone.now():
            return False
        return True
    
    def mark_expired(self, expires_text: str = None):
        """Mark this MAC as expired."""
        self.status = self.Status.EXPIRED
        self.last_checked = timezone.now()
        if expires_text:
            self.expires_text = expires_text
        self.save(update_fields=["status", "last_checked", "expires_text"])
    
    def mark_error(self, error_message: str):
        """Mark this MAC as having an error."""
        self.status = self.Status.ERROR
        self.last_checked = timezone.now()
        self.last_error = error_message
        self.save(update_fields=["status", "last_checked", "last_error"])
    
    def mark_valid(self, expires_at=None, expires_text: str = None):
        """Mark this MAC as valid."""
        self.status = self.Status.VALID
        self.last_checked = timezone.now()
        self.last_error = None
        if expires_at:
            self.expires_at = expires_at
        if expires_text:
            self.expires_text = expires_text
        self.save(update_fields=["status", "last_checked", "last_error", "expires_at", "expires_text"])


@receiver(models.signals.post_save, sender=M3UAccount)
def create_profile_for_m3u_account(sender, instance, created, **kwargs):
    """Automatically create an M3UAccountProfile when M3UAccount is created."""
    if created:
        # Initial sync of MACs from raw field (if any)
        if instance.account_type == M3UAccount.Types.MAC:
            instance._ensure_macs_from_mac_address()
        
        M3UAccountProfile.objects.create(
            m3u_account=instance,
            name=f"{instance.name} Default",
            max_streams=instance.max_streams,
            is_default=True,
            is_active=True,
            search_pattern="^(.*)$",
            replace_pattern="$1",
        )
    else:
        profile = M3UAccountProfile.objects.get(
            m3u_account=instance,
            is_default=True,
        )

        profile.max_streams = instance.max_streams
        profile.save()
