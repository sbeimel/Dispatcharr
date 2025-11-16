from core.utils import validate_flexible_url
from rest_framework import serializers, status
from rest_framework.response import Response

from .models import M3UAccount, M3UFilter, ServerGroup, M3UAccountProfile, M3UAccountMac, parse_mac_list
from core.models import UserAgent
from apps.channels.models import ChannelGroupM3UAccount
from apps.channels.serializers import ChannelGroupM3UAccountSerializer

import logging
import json

logger = logging.getLogger(__name__)


class RelaxedJSONField(serializers.JSONField):
    """
    JSONField, das auch "", null und JSON-Strings akzeptiert.

    Speziell für custom_properties:

    - "" oder null      -> {}
    - dict / list       -> wird direkt übernommen
    - JSON-String       -> dict(JSON)
    - sonstiger String  -> WARNING loggen, {} zurückgeben (keinen Fehler werfen!)
    """

    def to_internal_value(self, data):
        # komplett leer -> leeres dict
        if data in ("", None, {}):
            return {}

        # Falls Frontend schon ein dict/list schickt
        if isinstance(data, (dict, list)):
            return data

        # Wenn ein String ankommt, versuchen wir JSON zu parsen
        if isinstance(data, str):
            try:
                return json.loads(data)
            except ValueError:
                # Hier NICHT mehr abbrechen, sondern einfach {} verwenden
                logger.warning(
                    "RelaxedJSONField: could not parse custom_properties '%s', using {} instead",
                    data,
                )
                return {}

        # Fallback: alles andere einfach {} (maximal tolerant)
        logger.warning(
            "RelaxedJSONField: unexpected type %s for custom_properties, using {} instead",
            type(data),
        )
        return {}


class M3UFilterSerializer(serializers.ModelSerializer):
    """Serializer for M3U Filters"""

    class Meta:
        model = M3UFilter
        fields = [
            "id",
            "filter_type",
            "regex_pattern",
            "exclude",
            "order",
            "custom_properties",
        ]


class M3UAccountProfileSerializer(serializers.ModelSerializer):
    account = serializers.SerializerMethodField()

    def get_account(self, obj):
        """Include basic account information for frontend use"""
        return {
            "id": obj.m3u_account.id,
            "name": obj.m3u_account.name,
            "account_type": obj.m3u_account.account_type,
            "is_xtream_codes": obj.m3u_account.account_type == "XC",
        }
class M3UAccountMacSerializer(serializers.ModelSerializer):
    class Meta:
        model = M3UAccountMac
        fields = [
            "id",
            "address",
            "status",
            "expires_text",
            "expires_at",
            "priority",
            "last_error",
        ]
        
    class Meta:
        model = M3UAccountProfile
        fields = [
            "id",
            "name",
            "max_streams",
            "is_active",
            "is_default",
            "current_viewers",
            "search_pattern",
            "replace_pattern",
            "custom_properties",
            "account",
        ]
        read_only_fields = ["id", "account"]
        extra_kwargs = {
            "search_pattern": {"required": False, "allow_blank": True},
            "replace_pattern": {"required": False, "allow_blank": True},
        }

    def create(self, validated_data):
        m3u_account = self.context.get("m3u_account")
        validated_data["m3u_account_id"] = m3u_account.id
        return super().create(validated_data)

    def validate(self, data):
        """Custom validation to handle default profiles"""
        # Updates auf bestehende Instanz
        if self.instance and self.instance.is_default:
            # Default-Profile: search/replace dürfen nicht geändert werden
            return data

        # Nicht-Default oder neu: search und replace werden benötigt
        if not data.get("search_pattern"):
            raise serializers.ValidationError(
                {"search_pattern": ["This field is required for non-default profiles."]}
            )
        if not data.get("replace_pattern"):
            raise serializers.ValidationError(
                {"replace_pattern": ["This field is required for non-default profiles."]}
            )

        return data

    def update(self, instance, validated_data):
        if instance.is_default:
            # Default-Profile: nur name + custom_properties (Notizen)
            allowed_fields = {"name", "custom_properties"}

            disallowed_fields = set(validated_data.keys()) - allowed_fields
            if disallowed_fields:
                raise serializers.ValidationError(
                    "Default profiles can only modify name and notes. "
                    f"Cannot modify: {', '.join(disallowed_fields)}"
                )

        return super().update(instance, validated_data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_default:
            return Response(
                {"error": "Default profiles cannot be deleted."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)


class M3UAccountSerializer(serializers.ModelSerializer):
    """Serializer for M3U Account"""

    filters = serializers.SerializerMethodField()

    user_agent = serializers.PrimaryKeyRelatedField(
        queryset=UserAgent.objects.all(),
        required=False,
        allow_null=True,
    )

    profiles = M3UAccountProfileSerializer(many=True, read_only=True)

        macs = M3UAccountMacSerializer(many=True, read_only=True)  # <--- NEU


    # channel_groups werden über Join-Tabelle abgebildet
    channel_groups = ChannelGroupM3UAccountSerializer(
        source="channel_group", many=True, required=False
    )

    server_url = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        validators=[validate_flexible_url],
    )

    # Unser maximal toleranter JSON-Field
    custom_properties = RelaxedJSONField(required=False, allow_null=True)

    enable_vod = serializers.BooleanField(required=False, write_only=True)
    auto_enable_new_groups_live = serializers.BooleanField(required=False, write_only=True)
    auto_enable_new_groups_vod = serializers.BooleanField(required=False, write_only=True)
    auto_enable_new_groups_series = serializers.BooleanField(required=False, write_only=True)

    class Meta:
        model = M3UAccount
        fields = [
            "id",
            "name",
            "server_url",
            "file_path",
            "server_group",
            "max_streams",
            "is_active",
            "created_at",
            "updated_at",
            "filters",
            "user_agent",
            "profiles",
            "locked",
            "channel_groups",
            "refresh_interval",
            "custom_properties",
            "account_type",
            "username",
            "password",
            "mac_address",
            "macs",              # <--- NEU
            "stale_stream_days",
            "priority",
            "status",
            "last_message",
            "enable_vod",
            "auto_enable_new_groups_live",
            "auto_enable_new_groups_vod",
            "auto_enable_new_groups_series",
        ]
        read_only_fields = ["created_at", "updated_at", "locked"]
        extra_kwargs = {
            "password": {
                "required": False,
                "allow_blank": True,
            },
        }

    # ----------- Output (GET) -----------

    # ----------- MAC Sync Helper -----------

    def _sync_macs_from_mac_address(self, account, macs_text):
        """
        Nimmt den String aus mac_address (Komma / ; / Zeilen) und
        synchronisiert die M3UAccountMac-Objekte:
        - Reihenfolge → priority
        - Nicht mehr vorhandene MACs → löschen
        """
        if macs_text is None:
            return

        mac_addresses = parse_mac_list(macs_text)
        existing = {m.address: m for m in account.macs.all()}

        kept = set()
        for idx, addr in enumerate(mac_addresses):
            kept.add(addr)
            mac = existing.get(addr)
            if mac is None:
                mac = M3UAccountMac(account=account, address=addr)
            mac.priority = idx
            mac.save()

        # alles, was nicht mehr in der Liste ist, löschen
        for addr, mac in existing.items():
            if addr not in kept:
                mac.delete()
                
    def to_representation(self, instance):
        data = super().to_representation(instance)

        # custom_properties kann None sein → zu {}
        custom_props = instance.custom_properties or {}

        # Backend-Defaults für UI
        data["enable_vod"] = custom_props.get("enable_vod", False)
        data["auto_enable_new_groups_live"] = custom_props.get("auto_enable_new_groups_live", True)
        data["auto_enable_new_groups_vod"] = custom_props.get("auto_enable_new_groups_vod", True)
        data["auto_enable_new_groups_series"] = custom_props.get("auto_enable_new_groups_series", True)

        return data

    # ----------- Input (POST/PUT/PATCH) -----------

    def _extract_feature_flags(self, validated_data):
        """Hilfsfunktion: Flags aus validated_data holen und entfernen."""
        flags = {}
        for key, default in [
            ("enable_vod", False),
            ("auto_enable_new_groups_live", True),
            ("auto_enable_new_groups_vod", True),
            ("auto_enable_new_groups_series", True),
        ]:
            flags[key] = validated_data.pop(key, default)
        return flags

    def _merge_custom_properties(self, instance, validated_data, flags):
        # Basis: vorhandene custom_properties (bei Update) oder aus validated_data bzw. {} (bei Create)
        if instance is not None:
            custom_props = instance.custom_properties or {}
        else:
            custom_props = validated_data.get("custom_properties") or {}

        if not isinstance(custom_props, dict):
            # falls z.B. ein String kam, unseren RelaxedJSONField-Fallback respektieren
            custom_props = {}

        # Flags in custom_properties schreiben
        custom_props["enable_vod"] = flags["enable_vod"]
        custom_props["auto_enable_new_groups_live"] = flags["auto_enable_new_groups_live"]
        custom_props["auto_enable_new_groups_vod"] = flags["auto_enable_new_groups_vod"]
        custom_props["auto_enable_new_groups_series"] = flags["auto_enable_new_groups_series"]

        validated_data["custom_properties"] = custom_props

    def create(self, validated_data):
        # Flags holen
        flags = self._extract_feature_flags(validated_data)

        # custom_properties korrekt aufbauen
        self._merge_custom_properties(instance=None, validated_data=validated_data, flags=flags)

        # MACs-Text vor create sichern
        macs_text = validated_data.get("mac_address", "") or ""

        account = super().create(validated_data)

        # Multi-MACs anlegen / synchronisieren
        self._sync_macs_from_mac_address(account, macs_text)

        return account
        
   def update(self, instance, validated_data):
        # Flags holen
        flags = self._extract_feature_flags(validated_data)

        # custom_properties mergen
        self._merge_custom_properties(instance=instance, validated_data=validated_data, flags=flags)

        # channel_group-Daten getrennt verarbeiten
        channel_group_data = validated_data.pop("channel_group", [])

        # MACs-Text aus validated_data holen (kann None sein, wenn Feld nicht geschickt wurde)
        macs_text = validated_data.get("mac_address", None)

        # Erst das M3UAccount-Objekt selbst updaten
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # MACs nur synchronisieren, wenn das Feld im Request überhaupt vorhanden war
        if "mac_address" in getattr(self, "initial_data", {}):
            self._sync_macs_from_mac_address(instance, macs_text or "")

        # ChannelGroupM3UAccount-Relationen aktualisieren (bestehende Logik)
        memberships_to_update = []
        for group_data in channel_group_data:
            group = group_data.get("channel_group")
            enabled = group_data.get("enabled")

            try:
                membership = ChannelGroupM3UAccount.objects.get(
                    channel_group=group, m3u_account=instance
                )
                membership.enabled = enabled
                memberships_to_update.append(membership)
            except ChannelGroupM3UAccount.DoesNotExist:
                continue

        ChannelGroupM3UAccount.objects.bulk_update(
            memberships_to_update, ["enabled"]
        )

        return instance

    # ----------- Hilfsfelder -----------

    def get_filters(self, obj):
        filters = obj.filters.order_by("order")
        return M3UFilterSerializer(filters, many=True).data


class ServerGroupSerializer(serializers.ModelSerializer):
    """Serializer for Server Group"""

    class Meta:
        model = ServerGroup
        fields = ["id", "name"]
