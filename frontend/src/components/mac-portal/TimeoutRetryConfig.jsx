/**
 * Timeout and Retry Configuration Component
 * 
 * Configure timeout and retry settings for MAC Portal.
 * Requirements: 45.1, 45.2, 45.3, 45.4
 */

import React, { useState, useEffect } from 'react';
import {
  Stack,
  NumberInput,
  Switch,
  Button,
  Group,
  Text,
  Paper,
  Title,
  Slider,
} from '@mantine/core';

const TimeoutRetryConfig = ({ settings, onSave }) => {
  const [localSettings, setLocalSettings] = useState({
    connection_timeout: 30,
    read_timeout: 60,
    max_retries: 3,
    retry_delay: 2.0,
    exponential_backoff: true,
  });
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    if (settings) {
      setLocalSettings({
        connection_timeout: settings.connection_timeout ?? 30,
        read_timeout: settings.read_timeout ?? 60,
        max_retries: settings.max_retries ?? 3,
        retry_delay: settings.retry_delay ?? 2.0,
        exponential_backoff: settings.exponential_backoff ?? true,
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
        connection_timeout: settings.connection_timeout ?? 30,
        read_timeout: settings.read_timeout ?? 60,
        max_retries: settings.max_retries ?? 3,
        retry_delay: settings.retry_delay ?? 2.0,
        exponential_backoff: settings.exponential_backoff ?? true,
      });
      setHasChanges(false);
    }
  };

  return (
    <Stack gap="md">
      <Text size="sm" c="dimmed">
        Configure timeout and retry behavior for portal connections.
        These settings affect how the system handles slow or failing connections.
      </Text>

      <Paper withBorder p="md">
        <Title order={4} mb="md">Connection Timeouts</Title>
        
        <Stack gap="sm">
          <NumberInput
            label="Connection Timeout (seconds)"
            description="Maximum time to wait for initial connection"
            value={localSettings.connection_timeout}
            onChange={(val) => handleChange('connection_timeout', val)}
            min={5}
            max={120}
            step={5}
          />

          <NumberInput
            label="Read Timeout (seconds)"
            description="Maximum time to wait for data after connection"
            value={localSettings.read_timeout}
            onChange={(val) => handleChange('read_timeout', val)}
            min={10}
            max={300}
            step={10}
          />
        </Stack>
      </Paper>

      <Paper withBorder p="md">
        <Title order={4} mb="md">Retry Configuration</Title>
        
        <Stack gap="sm">
          <NumberInput
            label="Maximum Retries"
            description="Number of retry attempts before giving up"
            value={localSettings.max_retries}
            onChange={(val) => handleChange('max_retries', val)}
            min={0}
            max={10}
          />

          <div>
            <Text size="sm" fw={500} mb={4}>Base Retry Delay (seconds)</Text>
            <Text size="xs" c="dimmed" mb="xs">
              Initial delay between retry attempts
            </Text>
            <Slider
              value={localSettings.retry_delay}
              onChange={(val) => handleChange('retry_delay', val)}
              min={0.5}
              max={10}
              step={0.5}
              marks={[
                { value: 1, label: '1s' },
                { value: 5, label: '5s' },
                { value: 10, label: '10s' },
              ]}
            />
            <Text size="xs" ta="center" mt="xs">
              Current: {localSettings.retry_delay}s
            </Text>
          </div>

          <Switch
            label="Exponential Backoff"
            description="Double the delay after each failed attempt"
            checked={localSettings.exponential_backoff}
            onChange={(e) => handleChange('exponential_backoff', e.currentTarget.checked)}
          />
        </Stack>
      </Paper>

      <Paper withBorder p="md" bg="gray.0">
        <Title order={5} mb="xs">Preview</Title>
        <Text size="sm" c="dimmed">
          With current settings, retry delays will be:
        </Text>
        <Text size="sm" mt="xs">
          {localSettings.exponential_backoff ? (
            <>
              Attempt 1: {localSettings.retry_delay}s, 
              Attempt 2: {localSettings.retry_delay * 2}s, 
              Attempt 3: {localSettings.retry_delay * 4}s
            </>
          ) : (
            <>
              All attempts: {localSettings.retry_delay}s delay
            </>
          )}
        </Text>
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

export default TimeoutRetryConfig;
