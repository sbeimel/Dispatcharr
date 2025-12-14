/**
 * OB2_2025 Toggle Component
 * 
 * Toggle for OB2_2025 vs MacReplay mode.
 * Requirements: 76.1
 */

import React from 'react';
import {
  Paper,
  Group,
  Text,
  Switch,
  Stack,
  Alert,
  Badge,
} from '@mantine/core';
import { IconAlertCircle, IconFlask } from '@tabler/icons-react';

const OB2_2025Toggle = ({ enabled, onChange, currentMode }) => {
  return (
    <Stack gap="md">
      <Paper withBorder p="md">
        <Group justify="space-between">
          <div>
            <Group gap="xs">
              <Text fw={500}>OB2_2025 Engine</Text>
              <Badge size="xs" color="yellow" variant="light" leftSection={<IconFlask size={10} />}>
                Experimental
              </Badge>
            </Group>
            <Text size="xs" c="dimmed">
              Use OB2_2025 checking logic instead of MacReplay
            </Text>
          </div>
          <Switch
            checked={enabled}
            onChange={(e) => onChange(e.currentTarget.checked)}
            size="md"
          />
        </Group>
      </Paper>

      {enabled && (
        <Alert icon={<IconAlertCircle size={16} />} color="yellow">
          <Text size="sm">
            OB2_2025 mode uses advanced portal detection and handshake strategies.
            This may improve compatibility with some portals but is still experimental.
          </Text>
        </Alert>
      )}

      <Paper withBorder p="md">
        <Text size="sm" fw={500} mb="xs">Current Mode</Text>
        <Group gap="xs">
          <Badge color={enabled ? 'violet' : 'blue'} variant="filled">
            {enabled ? 'OB2_2025' : 'MacReplay'}
          </Badge>
          <Text size="xs" c="dimmed">
            {enabled 
              ? 'Using OB2_2025 portal detection and handshake logic'
              : 'Using standard MacReplay authentication logic'
            }
          </Text>
        </Group>
      </Paper>
    </Stack>
  );
};

export default OB2_2025Toggle;
