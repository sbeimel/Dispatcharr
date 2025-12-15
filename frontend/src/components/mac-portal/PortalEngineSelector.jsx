/**
 * Portal Engine Selector Component
 * 
 * Allows selection of the portal authentication engine.
 * Combines strategies from MacReplay, EStalker, BoxPirate, and OB2_2025.
 * 
 * Requirements: 100.1
 */

import React from 'react';
import {
  Stack,
  Text,
  Select,
  Paper,
  Badge,
  Group,
  Alert,
  ThemeIcon,
} from '@mantine/core';
import {
  IconRocket,
  IconSettings,
  IconBrandPython,
  IconDeviceTv,
  IconFlask,
  IconInfoCircle,
} from '@tabler/icons-react';

const PORTAL_ENGINES = [
  {
    value: 'auto',
    label: 'Auto-Detect (Recommended)',
    description: 'Automatically tries all strategies and caches the best one',
    icon: IconRocket,
    color: 'green',
    badge: 'Recommended',
  },
  {
    value: 'unified',
    label: 'Unified (All Strategies)',
    description: 'Combines all strategies for maximum compatibility',
    icon: IconSettings,
    color: 'blue',
    badge: null,
  },
  {
    value: 'macreplay',
    label: 'MacReplayXC (Standard)',
    description: 'Standard GET/POST fallback strategy from MacReplayXC v2.2.1',
    icon: IconDeviceTv,
    color: 'cyan',
    badge: 'Standard',
  },
  {
    value: 'estalker',
    label: 'EStalker (Enigma2 Style)',
    description: 'Extended metrics with prehash support, MAG254 style',
    icon: IconBrandPython,
    color: 'violet',
    badge: null,
  },
  {
    value: 'boxpirate',
    label: 'BoxPirate (Dreambox Style)',
    description: 'Dreambox-style authentication with signature',
    icon: IconDeviceTv,
    color: 'orange',
    badge: null,
  },
  {
    value: 'ob2_2025',
    label: 'OB2_2025 (Extended Metrics)',
    description: 'Extended checking logic with api_signature 263',
    icon: IconFlask,
    color: 'yellow',
    badge: 'Experimental',
  },
];

const PortalEngineSelector = ({ value, onChange, disabled = false }) => {
  const selectedEngine = PORTAL_ENGINES.find(e => e.value === value) || PORTAL_ENGINES[0];
  const IconComponent = selectedEngine.icon;

  return (
    <Stack gap="md">
      <Paper withBorder p="md">
        <Group gap="sm" mb="sm">
          <ThemeIcon color={selectedEngine.color} variant="light" size="lg">
            <IconComponent size={20} />
          </ThemeIcon>
          <div>
            <Group gap="xs">
              <Text fw={500}>Portal Authentication Engine</Text>
              {selectedEngine.badge && (
                <Badge size="xs" color={selectedEngine.color} variant="light">
                  {selectedEngine.badge}
                </Badge>
              )}
            </Group>
            <Text size="xs" c="dimmed">
              Select the authentication strategy for MAC/STB portals
            </Text>
          </div>
        </Group>

        <Select
          value={value}
          onChange={onChange}
          disabled={disabled}
          data={PORTAL_ENGINES.map(engine => ({
            value: engine.value,
            label: engine.label,
          }))}
          placeholder="Select engine"
        />

        <Text size="sm" c="dimmed" mt="sm">
          {selectedEngine.description}
        </Text>
      </Paper>

      <Alert icon={<IconInfoCircle size={16} />} color="blue" variant="light">
        <Text size="sm">
          <strong>Engine Comparison:</strong>
        </Text>
        <Text size="xs" mt="xs">
          • <strong>Auto-Detect:</strong> Best for most users - automatically finds working strategy
        </Text>
        <Text size="xs">
          • <strong>MacReplayXC:</strong> Standard strategy, works with most portals
        </Text>
        <Text size="xs">
          • <strong>EStalker:</strong> Better for portals requiring extended metrics (MAG254)
        </Text>
        <Text size="xs">
          • <strong>BoxPirate:</strong> Dreambox-style, uses signature authentication
        </Text>
        <Text size="xs">
          • <strong>OB2_2025:</strong> Experimental, uses api_signature 263
        </Text>
      </Alert>
    </Stack>
  );
};

export default PortalEngineSelector;
