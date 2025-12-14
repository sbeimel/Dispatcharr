/**
 * Stream Failover Configuration Component
 * 
 * Configures stream validation and failover settings.
 * Requirements: 58.1, 58.2, 58.3, 58.4
 */

import React, { useState, useEffect } from 'react';
import {
  Stack,
  Paper,
  Title,
  Text,
  NumberInput,
  Switch,
  Group,
  Button,
  Divider,
  Alert,
} from '@mantine/core';
import { IconDeviceFloppy, IconInfoCircle } from '@tabler/icons-react';

const StreamFailoverConfig = ({ settings, onSave }) => {
  const [localSettings, setLocalSettings] = useState({
    stream_failover_enabled: true,
    stream_validation_enabled: true,
    stream_validation_timeout: 5,
    stream_max_retries: 3,
    stream_retry_different_mac: true,
    stream_retry_different_cmd: true,
  });

  useEffect(() => {
    if (settings) {
      setLocalSettings({
        stream_failover_enabled: settings.stream_failover_enabled ?? true,
        stream_validation_enabled: settings.stream_validation_enabled ?? true,
        stream_validation_timeout: settings.stream_validation_timeout ?? 5,
        stream_max_retries: settings.stream_max_retries ?? 3,
        stream_retry_different_mac: settings.stream_retry_different_mac ?? true,
        stream_retry_different_cmd: settings.stream_retry_different_cmd ?? true,
      });
    }
  }, [settings]);

  const handleChange = (field, value) => {
    setLocalSettings(prev => ({ ...prev, [field]: value }));
  };

  const handleSave = () => {
    onSave({ ...settings, ...localSettings });
  };

  return (
    <Stack gap="md">
      <Text size="sm" c="dimmed">
        Configure stream validation and failover. The system can validate streams
        before playback and automatically retry with alternatives on failure.
      </Text>

      <Paper withBorder p="md">
        <Group justify="space-between" mb="md">
          <div>
            <Title order={4}>Enable Stream Failover</Title>
            <Text size="xs" c="dimmed">
              Automatically retry streams with alternatives on failure
            </Text>
          </div>
          <Switch
            checked={localSettings.stream_failover_enabled}
            onChange={(e) => handleChange('stream_failover_enabled', e.currentTarget.checked)}
          />
        </Group>

        <Divider my="md" />

        <Stack gap="md" opacity={localSettings.stream_failover_enabled ? 1 : 0.5}>
          <Group justify="space-between">
            <div>
              <Text fw={500}>Stream Validation</Text>
              <Text size="xs" c="dimmed">
                Validate stream URLs with HEAD request before playback
              </Text>
            </div>
            <Switch
              checked={localSettings.stream_validation_enabled}
              onChange={(e) => handleChange('stream_validation_enabled', e.currentTarget.checked)}
              disabled={!localSettings.stream_failover_enabled}
            />
          </Group>

          <NumberInput
            label="Validation Timeout (seconds)"
            description="Time to wait for stream validation response"
            value={localSettings.stream_validation_timeout}
            onChange={(val) => handleChange('stream_validation_timeout', val)}
            min={1}
            max={30}
            disabled={!localSettings.stream_failover_enabled || !localSettings.stream_validation_enabled}
          />

          <NumberInput
            label="Maximum Retries"
            description="Number of times to retry before giving up"
            value={localSettings.stream_max_retries}
            onChange={(val) => handleChange('stream_max_retries', val)}
            min={1}
            max={10}
            disabled={!localSettings.stream_failover_enabled}
          />
        </Stack>
      </Paper>

      <Paper withBorder p="md" opacity={localSettings.stream_failover_enabled ? 1 : 0.5}>
        <Title order={4} mb="md">Retry Strategies</Title>
        
        <Stack gap="md">
          <Group justify="space-between">
            <div>
              <Text fw={500}>Retry with Different MAC</Text>
              <Text size="xs" c="dimmed">
                Try a different MAC address when stream fails
              </Text>
            </div>
            <Switch
              checked={localSettings.stream_retry_different_mac}
              onChange={(e) => handleChange('stream_retry_different_mac', e.currentTarget.checked)}
              disabled={!localSettings.stream_failover_enabled}
            />
          </Group>

          <Group justify="space-between">
            <div>
              <Text fw={500}>Retry with Different Command</Text>
              <Text size="xs" c="dimmed">
                Try alternative stream commands (e.g., different quality)
              </Text>
            </div>
            <Switch
              checked={localSettings.stream_retry_different_cmd}
              onChange={(e) => handleChange('stream_retry_different_cmd', e.currentTarget.checked)}
              disabled={!localSettings.stream_failover_enabled}
            />
          </Group>
        </Stack>
      </Paper>

      <Alert icon={<IconInfoCircle size={16} />} color="blue">
        Stream validation sends a HEAD request to check if the stream URL is
        accessible before returning it to the player. This adds a small delay
        but helps avoid playback errors.
      </Alert>

      <Group justify="flex-end">
        <Button leftSection={<IconDeviceFloppy size={16} />} onClick={handleSave}>
          Save Stream Failover Settings
        </Button>
      </Group>
    </Stack>
  );
};

export default StreamFailoverConfig;
