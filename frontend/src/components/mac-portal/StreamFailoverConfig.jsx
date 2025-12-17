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
  Switch,
  Group,
  Button,
  Alert,
} from '@mantine/core';
import { IconDeviceFloppy, IconInfoCircle } from '@tabler/icons-react';

const StreamFailoverConfig = ({ settings, onSave }) => {
  const [localSettings, setLocalSettings] = useState({
    stream_failover_enabled: true,
  });

  useEffect(() => {
    if (settings) {
      setLocalSettings({
        stream_failover_enabled: settings.stream_failover_enabled ?? true,
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
        Configure automatic stream failover. When enabled, the system automatically
        tries alternative streams (MAC → Profile → Stream) on failure.
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
      </Paper>

      <Alert icon={<IconInfoCircle size={16} />} color="blue">
        Stream failover uses a simple 3-step approach: First tries different MACs,
        then different profiles, and finally switches to backup streams. This ensures
        seamless playback without complex retry strategies.
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
