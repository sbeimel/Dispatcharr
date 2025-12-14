/**
 * Cooldown Configuration Component
 * 
 * Configure cooldown times for MAC addresses after failures.
 * Requirements: 46.1, 46.2, 46.3, 46.4
 */

import React, { useState, useEffect } from 'react';
import {
  Stack,
  NumberInput,
  Button,
  Group,
  Text,
  Paper,
  Title,
  Alert,
} from '@mantine/core';
import { IconInfoCircle } from '@tabler/icons-react';

const CooldownConfig = ({ settings, onSave }) => {
  const [localSettings, setLocalSettings] = useState({
    mac_cooldown_failure: 5,
    mac_cooldown_block: 30,
    mac_cooldown_rate_limit: 60,
  });
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    if (settings) {
      setLocalSettings({
        mac_cooldown_failure: settings.mac_cooldown_failure ?? 5,
        mac_cooldown_block: settings.mac_cooldown_block ?? 30,
        mac_cooldown_rate_limit: settings.mac_cooldown_rate_limit ?? 60,
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
        mac_cooldown_failure: settings.mac_cooldown_failure ?? 5,
        mac_cooldown_block: settings.mac_cooldown_block ?? 30,
        mac_cooldown_rate_limit: settings.mac_cooldown_rate_limit ?? 60,
      });
      setHasChanges(false);
    }
  };

  return (
    <Stack gap="md">
      <Text size="sm" c="dimmed">
        Configure how long MAC addresses are excluded from rotation after different
        types of failures. This helps prevent repeated failures and gives portals
        time to recover.
      </Text>

      <Alert icon={<IconInfoCircle size={16} />} color="blue">
        Cooldown periods prevent the system from repeatedly trying a MAC address
        that is experiencing issues. After the cooldown expires, the MAC will
        automatically be available for use again.
      </Alert>

      <Paper withBorder p="md">
        <Title order={4} mb="md">Cooldown Durations</Title>
        
        <Stack gap="md">
          <NumberInput
            label="Failure Cooldown (minutes)"
            description="Cooldown after general authentication or connection failures"
            value={localSettings.mac_cooldown_failure}
            onChange={(val) => handleChange('mac_cooldown_failure', val)}
            min={1}
            max={60}
            suffix=" min"
          />

          <NumberInput
            label="Block Cooldown (minutes)"
            description="Cooldown when MAC is blocked or device conflict detected"
            value={localSettings.mac_cooldown_block}
            onChange={(val) => handleChange('mac_cooldown_block', val)}
            min={5}
            max={1440}
            suffix=" min"
          />

          <NumberInput
            label="Rate Limit Cooldown (minutes)"
            description="Cooldown when rate limiting (HTTP 429) is detected"
            value={localSettings.mac_cooldown_rate_limit}
            onChange={(val) => handleChange('mac_cooldown_rate_limit', val)}
            min={1}
            max={120}
            suffix=" min"
          />
        </Stack>
      </Paper>

      <Paper withBorder p="md" bg="gray.0">
        <Title order={5} mb="xs">Cooldown Summary</Title>
        <Stack gap="xs">
          <Group justify="space-between">
            <Text size="sm">Connection/Auth Failure:</Text>
            <Text size="sm" fw={500}>{localSettings.mac_cooldown_failure} minutes</Text>
          </Group>
          <Group justify="space-between">
            <Text size="sm">Block/Device Conflict:</Text>
            <Text size="sm" fw={500}>{localSettings.mac_cooldown_block} minutes</Text>
          </Group>
          <Group justify="space-between">
            <Text size="sm">Rate Limiting:</Text>
            <Text size="sm" fw={500}>{localSettings.mac_cooldown_rate_limit} minutes</Text>
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

export default CooldownConfig;
