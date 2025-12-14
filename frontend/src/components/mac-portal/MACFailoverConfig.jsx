/**
 * MAC Failover Configuration Component
 * 
 * Configures MAC-specific failover settings.
 * Requirements: 56.1, 56.2, 56.3, 56.4
 */

import React, { useState, useEffect } from 'react';
import {
  Stack,
  Paper,
  Title,
  Text,
  NumberInput,
  Select,
  Switch,
  Group,
  Button,
  Divider,
} from '@mantine/core';
import { IconDeviceFloppy } from '@tabler/icons-react';

const MACFailoverConfig = ({ settings, onSave }) => {
  const [localSettings, setLocalSettings] = useState({
    mac_failover_enabled: true,
    mac_max_attempts: 3,
    mac_selection_strategy: 'health_based',
    mac_cooldown_failure: 5,
    mac_cooldown_block: 30,
    mac_auto_recovery_interval: 15,
  });

  useEffect(() => {
    if (settings) {
      setLocalSettings({
        mac_failover_enabled: settings.mac_failover_enabled ?? true,
        mac_max_attempts: settings.mac_max_attempts ?? 3,
        mac_selection_strategy: settings.mac_selection_strategy ?? 'health_based',
        mac_cooldown_failure: settings.mac_cooldown_failure ?? 5,
        mac_cooldown_block: settings.mac_cooldown_block ?? 30,
        mac_auto_recovery_interval: settings.mac_auto_recovery_interval ?? 15,
      });
    }
  }, [settings]);

  const handleChange = (field, value) => {
    setLocalSettings(prev => ({ ...prev, [field]: value }));
  };

  const handleSave = () => {
    onSave({ ...settings, ...localSettings });
  };

  const selectionStrategies = [
    { value: 'round_robin', label: 'Round Robin - Rotate through MACs sequentially' },
    { value: 'health_based', label: 'Health Based - Prefer MACs with higher success rate' },
    { value: 'random', label: 'Random - Select MACs randomly' },
  ];

  return (
    <Stack gap="md">
      <Text size="sm" c="dimmed">
        Configure how the system handles MAC address failover when authentication
        or streaming errors occur.
      </Text>

      <Paper withBorder p="md">
        <Group justify="space-between" mb="md">
          <div>
            <Title order={4}>Enable MAC Failover</Title>
            <Text size="xs" c="dimmed">
              Automatically try different MAC addresses on failure
            </Text>
          </div>
          <Switch
            checked={localSettings.mac_failover_enabled}
            onChange={(e) => handleChange('mac_failover_enabled', e.currentTarget.checked)}
          />
        </Group>

        <Divider my="md" />

        <Stack gap="md" opacity={localSettings.mac_failover_enabled ? 1 : 0.5}>
          <NumberInput
            label="Maximum Attempts"
            description="Number of different MACs to try before giving up"
            value={localSettings.mac_max_attempts}
            onChange={(val) => handleChange('mac_max_attempts', val)}
            min={1}
            max={10}
            disabled={!localSettings.mac_failover_enabled}
          />

          <Select
            label="Selection Strategy"
            description="How to choose the next MAC address"
            data={selectionStrategies}
            value={localSettings.mac_selection_strategy}
            onChange={(val) => handleChange('mac_selection_strategy', val)}
            disabled={!localSettings.mac_failover_enabled}
          />

          <Divider my="sm" label="Cooldown Settings" labelPosition="center" />

          <NumberInput
            label="Failure Cooldown (minutes)"
            description="Time to wait before retrying a MAC after authentication failure"
            value={localSettings.mac_cooldown_failure}
            onChange={(val) => handleChange('mac_cooldown_failure', val)}
            min={1}
            max={60}
            disabled={!localSettings.mac_failover_enabled}
          />

          <NumberInput
            label="Block Cooldown (minutes)"
            description="Time to wait before retrying a MAC after being blocked"
            value={localSettings.mac_cooldown_block}
            onChange={(val) => handleChange('mac_cooldown_block', val)}
            min={5}
            max={120}
            disabled={!localSettings.mac_failover_enabled}
          />

          <NumberInput
            label="Auto Recovery Interval (minutes)"
            description="Interval to check if cooled-down MACs are available again"
            value={localSettings.mac_auto_recovery_interval}
            onChange={(val) => handleChange('mac_auto_recovery_interval', val)}
            min={5}
            max={60}
            disabled={!localSettings.mac_failover_enabled}
          />
        </Stack>
      </Paper>

      <Group justify="flex-end">
        <Button leftSection={<IconDeviceFloppy size={16} />} onClick={handleSave}>
          Save MAC Failover Settings
        </Button>
      </Group>
    </Stack>
  );
};

export default MACFailoverConfig;
