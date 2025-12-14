/**
 * Live Log Viewer Component
 * 
 * Real-time display of failover events.
 * Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
 */

import React, { useRef, useEffect, useState } from 'react';
import {
  Box,
  Title,
  Stack,
  Group,
  Button,
  Text,
  Badge,
  Paper,
  ScrollArea,
  Select,
  ActionIcon,
  Tooltip,
} from '@mantine/core';
import {
  IconDownload,
  IconTrash,
  IconCheck,
  IconX,
  IconArrowDown,
} from '@tabler/icons-react';

const EVENT_TYPE_COLORS = {
  mac_failover: 'blue',
  portal_failover: 'violet',
  endpoint_failover: 'grape',
  useragent_failover: 'pink',
  stream_failover: 'cyan',
  simulated_timeout: 'orange',
  simulated_connection_reset: 'orange',
  simulated_403: 'red',
  simulated_404: 'red',
  simulated_500: 'red',
  simulated_stream_error: 'orange',
  test_started: 'green',
  test_completed: 'green',
};

const STRATEGY_LABELS = {
  mac: 'MAC',
  portal: 'Portal',
  endpoint: 'Endpoint',
  useragent: 'User-Agent',
  stream: 'Stream',
  none: 'None',
  unknown: 'Unknown',
};

const LiveLogViewer = ({ entries = [], onExport, onClear }) => {
  const scrollRef = useRef(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const [filter, setFilter] = useState('all');

  // Auto-scroll to bottom when new entries arrive
  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }, [entries, autoScroll]);

  const filteredEntries = entries.filter(entry => {
    if (filter === 'all') return true;
    if (filter === 'success') return entry.success;
    if (filter === 'failure') return !entry.success;
    return entry.strategy === filter;
  });

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('de-DE', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      fractionalSecondDigits: 3,
    });
  };

  const getEventColor = (entry) => {
    if (!entry.success) return 'red';
    return EVENT_TYPE_COLORS[entry.event_type] || 'gray';
  };

  return (
    <Box h="100%">
      <Group justify="space-between" mb="md">
        <Title order={4}>Live Log</Title>
        <Group gap="xs">
          <Select
            size="xs"
            w={120}
            value={filter}
            onChange={setFilter}
            data={[
              { value: 'all', label: 'Alle' },
              { value: 'success', label: 'Erfolg' },
              { value: 'failure', label: 'Fehler' },
              { value: 'mac', label: 'MAC' },
              { value: 'portal', label: 'Portal' },
              { value: 'stream', label: 'Stream' },
            ]}
          />
          <Tooltip label={autoScroll ? 'Auto-Scroll an' : 'Auto-Scroll aus'}>
            <ActionIcon
              variant={autoScroll ? 'filled' : 'outline'}
              color="blue"
              onClick={() => setAutoScroll(!autoScroll)}
            >
              <IconArrowDown size={16} />
            </ActionIcon>
          </Tooltip>
          <Button
            size="xs"
            variant="outline"
            leftSection={<IconDownload size={14} />}
            onClick={onExport}
          >
            Export
          </Button>
        </Group>
      </Group>

      <Text size="xs" c="dimmed" mb="sm">
        {filteredEntries.length} Einträge
      </Text>

      <ScrollArea h={500} viewportRef={scrollRef}>
        <Stack gap="xs">
          {filteredEntries.length === 0 ? (
            <Paper withBorder p="md" ta="center">
              <Text c="dimmed" size="sm">
                Keine Log-Einträge. Starte eine Simulation um Failover-Events zu sehen.
              </Text>
            </Paper>
          ) : (
            filteredEntries.map((entry, index) => (
              <LogEntry key={entry.id || index} entry={entry} />
            ))
          )}
        </Stack>
      </ScrollArea>
    </Box>
  );
};

const LogEntry = ({ entry }) => {
  const isSuccess = entry.success;
  const color = isSuccess ? 'green' : 'red';

  return (
    <Paper
      withBorder
      p="xs"
      style={{
        borderLeftWidth: 3,
        borderLeftColor: `var(--mantine-color-${color}-6)`,
      }}
    >
      <Group justify="space-between" wrap="nowrap">
        <Group gap="xs" wrap="nowrap">
          {isSuccess ? (
            <IconCheck size={16} color="green" />
          ) : (
            <IconX size={16} color="red" />
          )}
          <Badge size="xs" color={EVENT_TYPE_COLORS[entry.event_type] || 'gray'}>
            {STRATEGY_LABELS[entry.strategy] || entry.strategy}
          </Badge>
          <Text size="xs" c="dimmed">
            {formatTimestamp(entry.timestamp)}
          </Text>
        </Group>
        <Badge size="xs" variant="outline">
          {entry.duration_ms}ms
        </Badge>
      </Group>

      <Box mt="xs">
        <Text size="sm" fw={500}>
          {entry.event_type.replace(/_/g, ' ').replace('simulated ', '⚡ ')}
        </Text>
        
        {entry.original_value && entry.new_value && (
          <Text size="xs" c="dimmed">
            {entry.original_value} → {entry.new_value}
          </Text>
        )}
        
        {entry.reason && (
          <Text size="xs" c="dimmed" mt={2}>
            {entry.reason}
          </Text>
        )}

        {entry.details?.channel_name && (
          <Text size="xs" c="dimmed">
            Channel: {entry.details.channel_name}
          </Text>
        )}
      </Box>
    </Paper>
  );
};

const formatTimestamp = (timestamp) => {
  const date = new Date(timestamp);
  return date.toLocaleTimeString('de-DE', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
};

export default LiveLogViewer;
