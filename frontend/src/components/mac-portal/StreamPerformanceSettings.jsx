/**
 * Stream Performance Settings Component
 * 
 * Configure buffer size, health check timeouts, and smart buffer clearing.
 * Requirements: 101.1, 102.1
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
  Slider,
  Alert,
  Divider,
  Box,
  Select,
} from '@mantine/core';
import { IconInfoCircle } from '@tabler/icons-react';

const StreamPerformanceSettings = ({ settings, onSave }) => {
  const [localSettings, setLocalSettings] = useState({
    buffer_chunks: 10,
    health_check_timeout: 10,
    health_check_timeout_switching: 15,
    smart_buffer_clear_enabled: true,
    buffer_clear_on_codec_change: true,
    buffer_clear_on_resolution_change: true,
    legacy_buffer_mode: false,
    failover_total_timeout: 60,
    failover_timeout_action: 'stop',
    max_failover_attempts: 10,
  });
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    if (settings) {
      setLocalSettings({
        buffer_chunks: settings.buffer_chunks ?? 10,
        health_check_timeout: settings.health_check_timeout ?? 10,
        health_check_timeout_switching: settings.health_check_timeout_switching ?? 15,
        smart_buffer_clear_enabled: settings.smart_buffer_clear_enabled ?? true,
        buffer_clear_on_codec_change: settings.buffer_clear_on_codec_change ?? true,
        buffer_clear_on_resolution_change: settings.buffer_clear_on_resolution_change ?? true,
        legacy_buffer_mode: settings.legacy_buffer_mode ?? false,
        failover_total_timeout: settings.failover_total_timeout ?? 60,
        failover_timeout_action: settings.failover_timeout_action ?? 'stop',
        max_failover_attempts: settings.max_failover_attempts ?? 10,
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
        buffer_chunks: settings.buffer_chunks ?? 10,
        health_check_timeout: settings.health_check_timeout ?? 10,
        health_check_timeout_switching: settings.health_check_timeout_switching ?? 15,
        smart_buffer_clear_enabled: settings.smart_buffer_clear_enabled ?? true,
        buffer_clear_on_codec_change: settings.buffer_clear_on_codec_change ?? true,
        buffer_clear_on_resolution_change: settings.buffer_clear_on_resolution_change ?? true,
        failover_total_timeout: settings.failover_total_timeout ?? 60,
        failover_timeout_action: settings.failover_timeout_action ?? 'stop',
        max_failover_attempts: settings.max_failover_attempts ?? 10,
      });
      setHasChanges(false);
    }
  };

  const FeatureSwitch = ({ field, label, description, disabled }) => (
    <Group justify="space-between" wrap="nowrap">
      <div>
        <Text size="sm" fw={500}>{label}</Text>
        <Text size="xs" c="dimmed">{description}</Text>
      </div>
      <Switch
        checked={localSettings[field]}
        onChange={(e) => handleChange(field, e.currentTarget.checked)}
        disabled={disabled}
      />
    </Group>
  );

  return (
    <Stack gap="md">
      <Alert icon={<IconInfoCircle size={16} />} color="blue">
        Adjust these settings based on your network conditions and hardware capabilities.
        Changes take effect immediately for new streams.
      </Alert>

      <Paper withBorder p="md">
        <Title order={4} mb="md">Buffer Settings</Title>
        <Stack gap="md">
          <div>
            <Group justify="space-between" mb="xs">
              <Text size="sm" fw={500}>Buffer Size (Chunks)</Text>
              <Text size="sm" c="dimmed">{localSettings.buffer_chunks} chunks (~{(localSettings.buffer_chunks * 0.25).toFixed(1)} MB)</Text>
            </Group>
            <Slider
              value={localSettings.buffer_chunks}
              onChange={(value) => handleChange('buffer_chunks', value)}
              min={4}
              max={20}
              step={1}
              marks={[
                { value: 4, label: '4 (Fast)' },
                { value: 10, label: '10' },
                { value: 20, label: '20 (Stable)' },
              ]}
            />
            <Text size="xs" c="dimmed" mt="xs">
              Higher = more buffering, better stability. Lower = less latency.
            </Text>
          </div>
        </Stack>
      </Paper>

      <Paper withBorder p="md">
        <Title order={4} mb="md">Health Check Settings</Title>
        <Stack gap="md">
          <div>
            <Group justify="space-between" mb="xs">
              <Text size="sm" fw={500}>Health Check Timeout</Text>
              <Text size="sm" c="dimmed">{localSettings.health_check_timeout}s</Text>
            </Group>
            <Slider
              value={localSettings.health_check_timeout}
              onChange={(value) => handleChange('health_check_timeout', value)}
              min={5}
              max={30}
              step={1}
              marks={[
                { value: 5, label: '5s' },
                { value: 10, label: '10s' },
                { value: 30, label: '30s' },
              ]}
            />
            <Text size="xs" c="dimmed" mt="xs">
              How long without data before stream is marked unhealthy.
            </Text>
          </div>

          <Divider />

          <div>
            <Group justify="space-between" mb="xs">
              <Text size="sm" fw={500}>Health Check Timeout (During Switch)</Text>
              <Text size="sm" c="dimmed">{localSettings.health_check_timeout_switching}s</Text>
            </Group>
            <Slider
              value={localSettings.health_check_timeout_switching}
              onChange={(value) => handleChange('health_check_timeout_switching', value)}
              min={10}
              max={60}
              step={1}
              marks={[
                { value: 10, label: '10s' },
                { value: 15, label: '15s' },
                { value: 60, label: '60s' },
              ]}
            />
            <Text size="xs" c="dimmed" mt="xs">
              Timeout during stream switch - should be higher to allow FFmpeg startup.
            </Text>
          </div>
        </Stack>
      </Paper>

      <Paper withBorder p="md">
        <Title order={4} mb="md">Smart Buffer Clearing</Title>
        
        <Alert icon={<IconInfoCircle size={16} />} color="gray" mb="md">
          When enabled, the buffer is only cleared when switching between streams with 
          different codecs or resolutions. This provides seamless transitions when streams are compatible.
        </Alert>

        <Stack gap="sm">
          <FeatureSwitch
            field="legacy_buffer_mode"
            label="Legacy Buffer Mode (0.12.0-04 Style)"
            description="Always clear buffer on stream switch - disables smart seamless mode"
          />

          {!localSettings.legacy_buffer_mode && (
            <>
              <Divider my="xs" />
              <FeatureSwitch
                field="smart_buffer_clear_enabled"
                label="Enable Smart Buffer Clearing"
                description="Only clear buffer when codec or resolution changes (recommended)"
              />

              {localSettings.smart_buffer_clear_enabled && (
                <Box ml="md" mt="xs">
                  <Stack gap="sm">
                    <FeatureSwitch
                      field="buffer_clear_on_codec_change"
                      label="Clear on Codec Change"
                      description="Clear buffer when codec changes (e.g., h264 → hevc)"
                    />
                    <FeatureSwitch
                      field="buffer_clear_on_resolution_change"
                      label="Clear on Resolution Change"
                      description="Clear buffer when resolution changes (e.g., 720p → 1080p)"
                    />
                  </Stack>
                </Box>
              )}
            </>
          )}
        </Stack>
      </Paper>

      <Paper withBorder p="md">
        <Title order={4} mb="md">Failover Timeout</Title>
        
        <Alert icon={<IconInfoCircle size={16} />} color="gray" mb="md">
          Configure what happens when no working stream can be found within the timeout period.
        </Alert>

        <Stack gap="md">
          <div>
            <Group justify="space-between" mb="xs">
              <Text size="sm" fw={500}>Total Failover Timeout</Text>
              <Text size="sm" c="dimmed">{localSettings.failover_total_timeout}s</Text>
            </Group>
            <Slider
              value={localSettings.failover_total_timeout}
              onChange={(value) => handleChange('failover_total_timeout', value)}
              min={10}
              max={300}
              step={5}
              marks={[
                { value: 30, label: '30s' },
                { value: 60, label: '60s' },
                { value: 120, label: '2m' },
                { value: 300, label: '5m' },
              ]}
            />
            <Text size="xs" c="dimmed" mt="xs">
              Maximum time to search for a working stream before giving up.
            </Text>
          </div>

          <Divider />

          <div>
            <Group justify="space-between" mb="xs">
              <Text size="sm" fw={500}>Max Failover Attempts</Text>
              <Text size="sm" c="dimmed">{localSettings.max_failover_attempts} attempts</Text>
            </Group>
            <Slider
              value={localSettings.max_failover_attempts}
              onChange={(value) => handleChange('max_failover_attempts', value)}
              min={1}
              max={50}
              step={1}
              marks={[
                { value: 5, label: '5' },
                { value: 10, label: '10' },
                { value: 25, label: '25' },
                { value: 50, label: '50' },
              ]}
            />
            <Text size="xs" c="dimmed" mt="xs">
              Maximum number of stream switch attempts (MAC → Profile → Stream).
            </Text>
          </div>

          <Divider />

          <div>
            <Text size="sm" fw={500} mb="xs">Timeout Action</Text>
            <Select
              value={localSettings.failover_timeout_action}
              onChange={(value) => handleChange('failover_timeout_action', value)}
              data={[
                { value: 'stop', label: 'Stop - Give up and show error' },
                { value: 'loop', label: 'Loop - Keep trying indefinitely' },
              ]}
            />
            <Text size="xs" c="dimmed" mt="xs">
              What to do when the timeout is reached without finding a working stream.
            </Text>
          </div>
        </Stack>
      </Paper>

      <Paper withBorder p="md">
        <Title order={4} mb="md">Recommended Settings</Title>
        <Stack gap="xs">
          <Group gap="xs">
            <Text size="sm" fw={600}>Fast Network (Fiber, LAN):</Text>
            <Text size="sm" c="dimmed">Buffer: 6-8, Health: 7s, Switch: 12s</Text>
          </Group>
          <Group gap="xs">
            <Text size="sm" fw={600}>Standard Network (DSL, Cable):</Text>
            <Text size="sm" c="dimmed">Buffer: 10, Health: 10s, Switch: 15s (Default)</Text>
          </Group>
          <Group gap="xs">
            <Text size="sm" fw={600}>Slow Network (Mobile, Satellite):</Text>
            <Text size="sm" c="dimmed">Buffer: 15-20, Health: 20-30s, Switch: 30-60s</Text>
          </Group>
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

export default StreamPerformanceSettings;
