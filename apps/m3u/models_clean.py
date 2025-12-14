class M3UAccountMac(models.Model):
    """Represents individual MAC addresses for MAC/STB portal accounts."""
    
    class Status(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        VALID = "valid", "Valid"
        EXPIRED = "expired", "Expired"
        ERROR = "error", "Error"
    
    account = models.ForeignKey(
        M3UAccount,
        on_delete=models.CASCADE,
        related_name="macs",
        help_text="The M3U account this MAC belongs to",
    )
    address = models.CharField(
        max_length=17,
        help_text="MAC address in format AA:BB:CC:DD:EE:FF",
    )
    priority = models.PositiveIntegerField(
        default=0,
        help_text="Priority order for failover (0 = highest priority)",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UNKNOWN,
        help_text="Current validation status of this MAC address",
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this MAC address expires (if known)",
    )
    expires_text = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Raw expiry text from portal for display",
    )
    last_checked = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this MAC was last validated",
    )
    last_error = models.TextField(
        null=True,
        blank=True,
        help_text="Last error message if validation failed",
    )
    
    class Meta:
        ordering = ["priority", "id"]
        unique_together = [("account", "address")]
        verbose_name = "MAC Address"
        verbose_name_plural = "MAC Addresses"
    
    def __str__(self):
        return f"{self.address} ({self.get_status_display()})"
    
    def clean(self):
        """Validate MAC address format."""
        if self.address:
            # Normalize MAC address format
            self.address = self.normalize_mac_address(self.address)
            
            # Validate format
            if not self.is_valid_mac_format(self.address):
                raise ValidationError(f"Invalid MAC address format: {self.address}")
    
    @staticmethod
    def normalize_mac_address(mac):
        """Normalize MAC address to standard format (XX:XX:XX:XX:XX:XX)."""
        if not mac:
            return mac
        
        # Remove all separators and convert to uppercase
        clean_mac = re.sub(r'[:-]', '', mac.strip().upper())
        
        # Validate length
        if len(clean_mac) != 12:
            return mac  # Return original if invalid length
        
        # Add colons every 2 characters
        return ':'.join(clean_mac[i:i+2] for i in range(0, 12, 2))
    
    @staticmethod
    def is_valid_mac_format(mac):
        """Validate MAC address format."""
        if not mac:
            return False
        
        # Check standard format XX:XX:XX:XX:XX:XX
        pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
        return bool(re.match(pattern, mac))
    
    def save(self, *args, **kwargs):
        """Override save to normalize MAC address."""
        self.full_clean()  # This will call clean() method
        super().save(*args, **kwargs)