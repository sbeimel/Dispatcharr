/**
 * Isolated Test Controls Component
 * 
 * Controls for running isolated failover strategy tests.
 * Requirements: 7.1, 7.2, 7.3, 7.4
 */

import React, { useState } from 'react';
import {
  Box,
  Title,
  Stack,
  Group,
  Button,
  Text,
  Paper,
  Badge,
  SegmentedControl,
} from '@mantine/core';
import {
  IconPlayerPlay,
  IconNetwork,
  IconServer,
  IconUser,
  IconVideo,
} from '@tabler/icons-react';

const STRATEGIES = [
  {
    key: 'mac',
    label: 'MAC Only',
    icon: IconNetwork,
    color: 'blue',
    description: 'Test only MAC address rotation',
  },
  {
    key: 'portal',
    label: 'Portal Only',
    icon: IconServer,
    color: 'violet',
    description: 'Test only portal/endpoint failover',
  },
  {
    key: 'useragent',
    label: 'User-Agent Only',
    icon: IconUser,
    color: 'pink',
    description: 'Test only User-Agent rotation',
  },
  {
    key: 'stream',
    label: 'Stream Only',
    icon: IconVideo,
    color: 'cyan',
    description: 'Test only backup stream failover',
  },
];

const IsolatedTestControls = ({ channel, onRunTest, isRunning }) => {
  const [selectedStrategy, setSelectedStrategy] = useState('mac');

  const handleRunTest = () => {
    if (channel && selectedStrategy) {
      onRunTest(channel.id, selectedStrategy);
    }
  };

  const currentStrategy = STRATEGIES.find(s => s.key === selectedStrategy);

  if (!channel) {
    return (
      <Box>
        <Title order={5} mb="md">Isolated Strategy Tests</Title>
        <Text c="dimmed" size="sm">
          Select a test channel to run isolated strategy tests.
        </Text>
      </Box>
    );
  }

  return (
    <Box>
      <Title order={5} mb="md">Isolated Strategy Tests</Title>
      
      <Text size="sm" c="dimmed" mb="md">
        Test individual failover strategies in isolation to identify issues.
      </Text>

      <Stack gap="md">
        <SegmentedControl
          value={selectedStrategy}
          onChange={setSelectedStrategy}
          data={STRATEGIES.map(s => ({
            value: s.key,
            label: s.label,
          }))}
          fullWidth
          disabled={isRunning}
        />

        {currentStrategy && (
          <Paper withBorder p="sm">
            <Group gap="xs" mb="xs">
              <currentStrategy.icon size={16} color={`var(--mantine-color-${currentStrategy.color}-6)`} />
              <Text fw={500}>{currentStrategy.label}</Text>
            </Group>
            <Text size="xs" c="dimmed">
              {currentStrategy.description}
            </Text>
          </Paper>
        )}

        <Button
          leftSection={<IconPlayerPlay size={16} />}
          onClick={handleRunTest}
          loading={isRunning}
          color={currentStrategy?.color}
        >
          Run {currentStrategy?.label} Test
        </Button>
      </Stack>
    </Box>
  );
};

export default IsolatedTestControls;
