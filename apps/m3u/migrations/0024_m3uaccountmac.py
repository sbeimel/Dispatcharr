from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """
    Migration to create the M3UAccountMac model for tracking individual MAC addresses
    associated with MAC/STB-Portal accounts. Each MAC address has its own status,
    priority, and expiry information for failover management.
    """

    dependencies = [
        ("m3u", "0023_add_proxy_field"),
    ]

    operations = [
        migrations.CreateModel(
            name="M3UAccountMac",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "address",
                    models.CharField(
                        max_length=17,
                        help_text="Normalized MAC address (AA:BB:CC:DD:EE:FF)",
                    ),
                ),
                (
                    "priority",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Order in which MACs are tried for streaming (0 = highest priority)",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        max_length=20,
                        choices=[
                            ("unknown", "Unknown"),
                            ("valid", "Valid"),
                            ("expired", "Expired"),
                            ("error", "Error"),
                        ],
                        default="unknown",
                        help_text="Validation status based on last portal check",
                    ),
                ),
                (
                    "expires_at",
                    models.DateTimeField(
                        null=True,
                        blank=True,
                        help_text="Parsed expiry timestamp if available",
                    ),
                ),
                (
                    "expires_text",
                    models.CharField(
                        max_length=255,
                        null=True,
                        blank=True,
                        help_text="Raw expiry text from portal (for UI display)",
                    ),
                ),
                (
                    "last_checked",
                    models.DateTimeField(
                        null=True,
                        blank=True,
                        help_text="Timestamp of last portal validation check",
                    ),
                ),
                (
                    "last_error",
                    models.TextField(
                        null=True,
                        blank=True,
                        help_text="Last error message from portal communication",
                    ),
                ),
                (
                    "account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="macs",
                        help_text="Parent MAC / STB-Portal account",
                        to="m3u.m3uaccount",
                    ),
                ),
            ],
            options={
                "ordering": ["priority", "id"],
                "unique_together": {("account", "address")},
                "verbose_name": "MAC Address",
                "verbose_name_plural": "MAC Addresses",
            },
        ),
        # Add index for efficient lookups by account and priority
        migrations.AddIndex(
            model_name="m3uaccountmac",
            index=models.Index(
                fields=["account", "priority"],
                name="m3u_mac_account_priority_idx",
            ),
        ),
        # Add index for status-based queries (e.g., finding valid MACs)
        migrations.AddIndex(
            model_name="m3uaccountmac",
            index=models.Index(
                fields=["account", "status"],
                name="m3u_mac_account_status_idx",
            ),
        ),
    ]
