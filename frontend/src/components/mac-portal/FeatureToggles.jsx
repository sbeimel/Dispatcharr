/**
 * Feature Toggles Component
 * 
 * Enable/disable optional MAC Portal features.
 * Requirements: 47.1, 47.2, 47.3, 47.4, 100.1
 */

import React, { useState, useEffect } from 'react';
import {
  Stack,
  Switch,
  Button,
  Group,
  Text,
  Paper,
  Title,
  Badge,
  Divider,
} from '@mantine/core';
import PortalEngineSelector from './PortalEngineSelector';

const FeatureToggles = ({ settings, onSave }) => {
  const [localSettings, setLocalSettings] = useState({
    cloudscraper_enabled: true,
    vod_support_enabled: true,
    series_support_enabled: true,
    epg_download_enabled: true,
    short_epg_enabled: true,
    picon_download_enabled: true,
    tmdb_integration_enabled: false,
    stream_validation_enabled: true,
    multi_mac_rotation_enabled: true,
    token_auto_refresh_enabled: true,
    debug_logging_enabled: false,
    ob2_2025_engine_enabled: false,
    portal_engine: 'auto',
  });
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    if (settings) {
      setLocalSettings({
        cloudscraper_enabled: settings.cloudscraper_enabled ?? true,
        vod_support_enabled: settings.vod_support_enabled ?? true,
        series_support_enabled: settings.series_support_enabled ?? true,
        epg_download_enabled: settings.epg_download_enabled ?? true,
        short_epg_enabled: settings.short_epg_enabled ?? true,
        picon_download_enabled: settings.picon_download_enabled ?? true,
        tmdb_integration_enabled: settings.tmdb_integration_enabled ?? false,
        stream_validation_enabled: settings.stream_validation_enabled ?? true,
        multi_mac_rotation_enabled: settings.multi_mac_rotation_enabled ?? true,
        token_auto_refresh_enabled: settings.token_auto_refresh_enabled ?? true,
        debug_logging_enabled: settings.debug_logging_enabled ?? false,
        ob2_2025_engine_enabled: settings.ob2_2025_engine_enabled ?? false,
        portal_engine: settings.portal_engine ?? 'auto',
      });
      setHasChanges(false);
    }
  }, [settings]);

  const handleChange = (field, value) => {
    setLocalSettings(prev => ({
      ...prev,
      [field]: value,
    }));
    setHasChanges(true);
  };

  const handleSave = () => {
    onSave(localSettings);
    setHasChanges(false);
  };

  const handleReset = () => {
    if (settings) {
      setLocalSettings({
        cloudscraper_enabled: settings.cloudscraper_enabled ?? true,
        vod_support_enabled: settings.vod_support_enabled ?? true,
        series_support_enabled: settings.series_support_enabled ?? true,
        epg_download_enabled: settings.epg_download_enabled ?? true,
        short_epg_enabled: settings.short_epg_enabled ?? true,
        picon_download_enabled: settings.picon_download_enabled ?? true,
        tmdb_integration_enabled: settings.tmdb_integration_enabled ?? false,
        stream_validation_enabled: settings.stream_validation_enabled ?? true,
        multi_mac_rotation_enabled: settings.multi_mac_rotation_enabled ?? true,
        token_auto_refresh_enabled: settings.token_auto_refresh_enabled ?? true,
        debug_logging_enabled: settings.debug_logging_enabled ?? false,
        ob2_2025_engine_enabled: settings.ob2_2025_engine_enabled ?? false,
        portal_engine: settings.portal_engine ?? 'auto',
      });
      setHasChanges(false);
    }
  };

  const FeatureSwitch = ({ field, label, description, badge }) => (
    <Group justify="space-between" wrap="nowrap">
      <div>
        <Group gap="xs">
          <Text size="sm" fw={500}>{label}</Text>
          {badge && <Badge size="xs" color={badge.color}>{badge.text}</Badge>}
        </Group>
        <Text size="xs" c="dimmed">{description}</Text>
      </div>
      <Switch
        checked={localSettings[field]}
        onChange={(e) => handleChange(field, e.currentTarget.checked)}
      />
    </Group>
  );

  return (
    <Stack gap="md">
      <Text size="sm" c="dimmed">
        Enable or disable optional features. Disabling unused features can improve
        performance and reduce resource usage.
      </Text>

      <Paper withBorder p="md">
        <Title order={4} mb="md">Connection Features</Title>
        <Stack gap="sm">
          <FeatureSwitch
            field="cloudscraper_enabled"
            label="Cloudscraper"
            description="Automatically bypass Cloudflare protection"
          />
          <FeatureSwitch
            field="stream_validation_enabled"
            label="Stream Validation"
            description="Validate stream URLs before playback"
          />
          <FeatureSwitch
            field="multi_mac_rotation_enabled"
            label="Multi-MAC Rotation"
            description="Rotate between multiple MAC addresses"
          />
          <FeatureSwitch
            field="token_auto_refresh_enabled"
            label="Token Auto-Refresh"
            description="Automatically refresh tokens before expiry"
          />
        </Stack>
      </Paper>

      <Paper withBorder p="md">
        <Title order={4} mb="md">Content Features</Title>
        <Stack gap="sm">
          <FeatureSwitch
            field="vod_support_enabled"
            label="VOD Support"
            description="Enable Video on Demand content"
          />
          <FeatureSwitch
            field="series_support_enabled"
            label="Series Support"
            description="Enable TV series content"
          />
          <FeatureSwitch
            field="epg_download_enabled"
            label="EPG Download"
            description="Download EPG data from portals"
          />
          <FeatureSwitch
            field="short_epg_enabled"
            label="Short EPG"
            description="Fetch current/next program info"
          />
          <FeatureSwitch
            field="picon_download_enabled"
            label="Picon Download"
            description="Download and cache channel logos"
          />
          <FeatureSwitch
            field="tmdb_integration_enabled"
            label="TMDB Integration"
            description="Enrich VOD metadata from TMDB"
            badge={{ text: 'Optional', color: 'gray' }}
          />
        </Stack>
      </Paper>

      <Paper withBorder p="md">
        <Title order={4} mb="md">Portal Engine</Title>
        <PortalEngineSelector
          value={localSettings.portal_engine}
          onChange={(value) => handleChange('portal_engine', value)}
        />
      </Paper>

      <Paper withBorder p="md">
        <Title order={4} mb="md">Advanced Features</Title>
        <Stack gap="sm">
          <FeatureSwitch
            field="debug_logging_enabled"
            label="Debug Logging"
            description="Enable detailed debug logs"
            badge={{ text: 'Dev', color: 'yellow' }}
          />
        </Stack>
      </Paper>

      <Group justify="flex-end">
        <Button variant="outline" onClick={handleReset} disabled={!hasChanges}>
          Reset
        </Button>
        <Button onClick={handleSave} disabled={!hasChanges}>
          Save Changes
        </Button>
      </Group>
    </Stack>
  );
};

export default FeatureToggles;
