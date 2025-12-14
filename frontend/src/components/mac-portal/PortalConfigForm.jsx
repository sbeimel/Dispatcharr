/**
 * Portal Configuration Form Component
 * 
 * Portal-specific settings for individual MAC/STB accounts.
 * Requirements: 48.1, 48.2, 48.3, 48.4
 */

import React, { useState, useEffect } from 'react';
import {
  Stack,
  TextInput,
  Select,
  NumberInput,
  Switch,
  Button,
  Group,
  Text,
  Paper,
  Title,
  Divider,
} from '@mantine/core';

const USER_AGENT_PRESETS = [
  { value: 'MAG200', label: 'MAG200' },
  { value: 'MAG250', label: 'MAG250 (Default)' },
  { value: 'MAG254', label: 'MAG254' },
  { value: 'MAG322', label: 'MAG322' },
  { value: 'MAG424', label: 'MAG424' },
  { value: 'custom', label: 'Custom User-Agent' },
];

const PortalConfigForm = ({ account, onSave, onCancel }) => {
  const [config, setConfig] = useState({
    user_agent_preset: 'MAG250',
    custom_user_agent: '',
    use_cloudscraper: true,
    connection_timeout: 30,
    read_timeout: 60,
    max_retries: 3,
    enable_vod_scanning: false,
    enable_series_scanning: false,
    enable_epg: true,
    proxy_url: '',
  });
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    if (account) {
      setConfig({
        user_agent_preset: account.user_agent_preset ?? 'MAG250',
        custom_user_agent: account.custom_user_agent ?? '',
        use_cloudscraper: account.use_cloudscraper ?? true,
        connection_timeout: account.connection_timeout ?? 30,
        read_timeout: account.read_timeout ?? 60,
        max_retries: account.max_retries ?? 3,
        enable_vod_scanning: account.enable_vod_scanning ?? false,
        enable_series_scanning: account.enable_series_scanning ?? false,
        enable_epg: account.enable_epg ?? true,
        proxy_url: account.proxy_url ?? '',
      });
      setHasChanges(false);
    }
  }, [account]);

  const handleChange = (field, value) => {
    setConfig(prev => ({
      ...prev,
      [field]: value,
    }));
    setHasChanges(true);
  };

  const handleSave = () => {
    onSave(config);
    setHasChanges(false);
  };

  return (
    <Stack gap="md">
      <Paper withBorder p="md">
        <Title order={4} mb="md">Connection Settings</Title>
        
        <Stack gap="sm">
          <Select
            label="User-Agent Preset"
            description="Device emulation profile for portal connections"
            data={USER_AGENT_PRESETS}
            value={config.user_agent_preset}
            onChange={(val) => handleChange('user_agent_preset', val)}
          />

          {config.user_agent_preset === 'custom' && (
            <TextInput
              label="Custom User-Agent"
              description="Enter your custom User-Agent string"
              value={config.custom_user_agent}
              onChange={(e) => handleChange('custom_user_agent', e.target.value)}
              placeholder="Mozilla/5.0 ..."
            />
          )}

          <TextInput
            label="Proxy URL (Optional)"
            description="HTTP or SOCKS5 proxy for portal connections"
            value={config.proxy_url}
            onChange={(e) => handleChange('proxy_url', e.target.value)}
            placeholder="http://proxy:8080 or socks5://proxy:1080"
          />

          <Switch
            label="Use Cloudscraper"
            description="Enable Cloudflare bypass for this portal"
            checked={config.use_cloudscraper}
            onChange={(e) => handleChange('use_cloudscraper', e.currentTarget.checked)}
          />
        </Stack>
      </Paper>

      <Paper withBorder p="md">
        <Title order={4} mb="md">Timeout Settings</Title>
        <Text size="xs" c="dimmed" mb="md">
          Override global timeout settings for this portal
        </Text>
        
        <Stack gap="sm">
          <NumberInput
            label="Connection Timeout (seconds)"
            value={config.connection_timeout}
            onChange={(val) => handleChange('connection_timeout', val)}
            min={5}
            max={120}
          />

          <NumberInput
            label="Read Timeout (seconds)"
            value={config.read_timeout}
            onChange={(val) => handleChange('read_timeout', val)}
            min={10}
            max={300}
          />

          <NumberInput
            label="Max Retries"
            value={config.max_retries}
            onChange={(val) => handleChange('max_retries', val)}
            min={0}
            max={10}
          />
        </Stack>
      </Paper>

      <Paper withBorder p="md">
        <Title order={4} mb="md">Content Settings</Title>
        
        <Stack gap="sm">
          <Switch
            label="Enable VOD Scanning"
            description="Scan and import VOD content (movies) from this portal"
            checked={config.enable_vod_scanning}
            onChange={(e) => handleChange('enable_vod_scanning', e.currentTarget.checked)}
          />

          <Switch
            label="Enable Series Scanning"
            description="Scan and import TV series from this portal"
            checked={config.enable_series_scanning}
            onChange={(e) => handleChange('enable_series_scanning', e.currentTarget.checked)}
          />

          <Switch
            label="Enable EPG"
            description="Download EPG data from this portal"
            checked={config.enable_epg}
            onChange={(e) => handleChange('enable_epg', e.currentTarget.checked)}
          />
        </Stack>
      </Paper>

      <Group justify="flex-end">
        {onCancel && (
          <Button variant="outline" onClick={onCancel}>
            Cancel
          </Button>
        )}
        <Button onClick={handleSave} disabled={!hasChanges}>
          Save Configuration
        </Button>
      </Group>
    </Stack>
  );
};

export default PortalConfigForm;
