from core.utils import validate_flexible_url
from rest_framework import serializers, status
from rest_framework.response import Response
from .models import M3UAccount, M3UFilter, ServerGroup, M3UAccountProfile
from core.models import UserAgent
from apps.channels.models import ChannelGroup, ChannelGroupM3UAccount
from apps.channels.serializers import (
    ChannelGroupM3UAccountSerializer,
)
import logging
import json

logger = logging.getLogger(__name__)


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
            'id': obj.m3u_account.id,
            'name': obj.m3u_account.name,
            'account_type': obj.m3u_account.account_type,
            'is_xtream_codes': obj.m3u_account.account_type == 'XC'
        }

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
            'search_pattern': {'required': False, 'allow_blank': True},
            'replace_pattern': {'required': False, 'allow_blank': True},
        }

    def create(self, validated_data):
        m3u_account = self.context.get("m3u_account")

        # Use the m3u_account when creating the profile
        validated_data["m3u_account_id"] = m3u_account.id

        return super().create(validated_data)

    def validate(self, data):
        """Custom validation to handle default profiles"""
        # For updates to existing instances
        if self.instance and self.instance.is_default:
            # For default profiles, search_pattern and replace_pattern are not required
            # and we don't want to validate them since they shouldn't be changed
            return data

        # For non-default profiles or new profiles, ensure required fields are present
        if not data.get('search_pattern'):
            raise serializers.ValidationError({
                'search_pattern': ['This field is required for non-default profiles.']
            })
        if not data.get('replace_pattern'):
            raise serializers.ValidationError({
                'replace_pattern': ['This field is required for non-default profiles.']
            })

        return data

    def update(self, instance, validated_data):
        if instance.is_default:
            # For default profiles, only allow updating name and custom_properties (for notes)
            allowed_fields = {'name', 'custom_properties'}

            # Remove any fields that aren't allowed for default profiles
            disallowed_fields = set(validated_data.keys()) - allowed_fields
            if disallowed_fields:
                raise serializers.ValidationError(
                    f"Default profiles can only modify name and notes. "
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
    """Serializer für M3U Account"""

    filters = serializers.SerializerMethodField()

    user_agent = serializers.PrimaryKeyRelatedField(
        queryset=UserAgent.objects.all(),
        required=False,
        allow_null=True,
    )

    profiles = M3UAccountProfileSerializer(many=True, read_only=True)

    channel_groups = ChannelGroupM3UAccountSerializer(
        source="channel_group", many=True, required=False
    )

    custom_properties = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    server_url = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        validators=[validate_flexible_url],
    )

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
            "stale_stream_days",
            "priority",
            "status",
            "last_message",
            "enable_vod",
            "auto_enable_new_groups_live",
            "auto_enable_new_groups_vod",
            "auto_enable_new_groups_series",
        ]

        extra_kwargs = {
            "password": {"required": False, "allow_blank": True},
        }

    # -------------------------------------------------------------
    # CUSTOM PROPERTIES FIX
    # -------------------------------------------------------------
    def validate_custom_properties(self, value):
        """
        - "" oder None => {}
        - dict => dict
        - JSON-String => dict(JSON)
        """
        if value in ("", None):
            return {}

        if isinstance(value, dict):
            return value

        if isinstance(value, str):
            try:
                return json.loads(value)
            except ValueError:
                raise serializers.ValidationError("Value must be valid JSON or empty.")

        raise serializers.ValidationError("Value must be valid JSON or empty.")

    def validate(self, attrs):
        """
        Standard-M3U haben keine custom_properties -> erzwinge {}
        """
        account_type = attrs.get("account_type",
                                 getattr(self.instance, "account_type", None))

        if account_type == "standard":
            attrs["custom_properties"] = {}

        return attrs

    # -------------------------------------------------------------
    # REPRESENTATION / UPDATE / CREATE BLEIBEN UNVERÄNDERT
    # -------------------------------------------------------------

    def to_representation(self, instance):
        data = super().to_representation(instance)
        custom_props = instance.custom_properties or {}

        data["enable_vod"] = custom_props.get("enable_vod", False)
        data["auto_enable_new_groups_live"] = custom_props.get("auto_enable_new_groups_live", True)
        data["auto_enable_new_groups_vod"] = custom_props.get("auto_enable_new_groups_vod", True)
        data["auto_enable_new_groups_series"] = custom_props.get("auto_enable_new_groups_series", True)

        return data

    def update(self, instance, validated_data):
        enable_vod = validated_data.pop("enable_vod", None)
        auto_enable_new_groups_live = validated_data.pop("auto_enable_new_groups_live", None)
        auto_enable_new_groups_vod = validated_data.pop("auto_enable_new_groups_vod", None)
        auto_enable_new_groups_series = validated_data.pop("auto_enable_new_groups_series", None)

        custom_props = instance.custom_properties or {}

        if enable_vod is not None:
            custom_props["enable_vod"] = enable_vod
        if auto_enable_new_groups_live is not None:
            custom_props["auto_enable_new_groups_live"] = auto_enable_new_groups_live
        if auto_enable_new_groups_vod is not None:
            custom_props["auto_enable_new_groups_vod"] = auto_enable_new_groups_vod
        if auto_enable_new_groups_series is not None:
            custom_props["auto_enable_new_groups_series"] = auto_enable_new_groups_series

        validated_data["custom_properties"] = custom_props

        # Channel-group handling bleibt unverändert
        channel_group_data = validated_data.pop("channel_group", [])

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        memberships_to_update = []
        for group_data in channel_group_data:
            group = group_data.get("channel_group")
            enabled = group_data.get("enabled")

            try:
                membership = ChannelGroupM3UAccount.objects.get(
                    m3u_account=instance, channel_group=group
                )
                membership.enabled = enabled
                memberships_to_update.append(membership)
            except ChannelGroupM3UAccount.DoesNotExist:
                pass

        if memberships_to_update:
            ChannelGroupM3UAccount.objects.bulk_update(
                memberships_to_update, ["enabled"]
            )

        return instance

    def create(self, validated_data):
        enable_vod = validated_data.pop("enable_vod", False)
        auto_enable_new_groups_live = validated_data.pop("auto_enable_new_groups_live", True)
        auto_enable_new_groups_vod = validated_data.pop("auto_enable_new_groups_vod", True)
        auto_enable_new_groups_series = validated_data.pop("auto_enable_new_groups_series", True)

        custom_props = validated_data.get("custom_properties", {})

        custom_props["enable_vod"] = enable_vod
        custom_props["auto_enable_new_groups_live"] = auto_enable_new_groups_live
        custom_props["auto_enable_new_groups_vod"] = auto_enable_new_groups_vod
        custom_props["auto_enable_new_groups_series"] = auto_enable_new_groups_series

        validated_data["custom_properties"] = custom_props

        return super().create(validated_data)

    def get_filters(self, obj):
        filters = obj.filters.order_by("order")
        return M3UFilterSerializer(filters, many=True).data



class ServerGroupSerializer(serializers.ModelSerializer):
    """Serializer for Server Group"""

    class Meta:
        model = ServerGroup
        fields = ["id", "name"]
