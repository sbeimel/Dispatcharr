/**
 * VOD Scanning Toggle Component
 * 
 * Toggle for enabling/disabling VOD scanning on MAC/STB Portal accounts.
 * Requirements: 91.1, 91.5
 */

import React from 'react';
import {
  Group,
  Switch,
  Text,
  Box,
  Tooltip,
} from '@mantine/core';
import { IconInfoCircle } from '@tabler/icons-react';

const VODScanningToggle = ({ 
  enabled, 
  onChange, 
  disabled = false,
  showDescription = true 
}) => {
  return (
    <Box>
      <Group justify="space-between" wrap="nowrap">
        <Group gap="xs">
          <Text size="sm" fw={500}>Enable VOD Scanning</Text>
          <Tooltip 
            label="VOD content is scanned using a single MAC address to avoid redundant requests. Content is shared across all MACs in this account."
            multiline
            w={300}
          >
            <IconInfoCircle size={16} style={{ opacity: 0.5, cursor: 'help' }} />
          </Tooltip>
        </Group>
        <Switch
          checked={enabled}
          onChange={(e) => onChange(e.currentTarget.checked)}
          disabled={disabled}
        />
      </Group>
      {showDescription && (
        <Text size="xs" c="dimmed" mt={4}>
          Scan and import VOD content (movies/series) from this MAC Portal account
        </Text>
      )}
    </Box>
  );
};

export default VODScanningToggle;
