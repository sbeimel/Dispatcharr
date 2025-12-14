/**
 * Failover Event Log Component
 * 
 * Displays and filters failover events.
 * Requirements: 61.1, 61.4
 */

import React, { useState, useEffect } from 'react';
import {
  Stack,
  Paper,
  Title,
  Text,
  Group,
  Select,
  LoadingOverlay,
  Box,
  Table,
  Badge,
  ActionIcon,
  TextInput,
  Pagination,
  Button,
  Tooltip,
} from '@mantine/core';
import { DatePickerInput } from '@mantine/dates';
import { notifications } from '@mantine/notifications';
import { 
  IconRefresh, 
  IconSearch,
  IconCheck,
  IconX,
  IconDownload,
  IconTrash,
} from '@tabler/icons-react';
import API from '../../api';

const FailoverEventLog = ({ accountId }) => {
  const [loading, setLoading] = useState(true);
  const [events, setEvents] = useState([]);
  const [totalPages, setTotalPages] = useState(1);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({
    type: '',
    search: '',
    dateFrom: null,
    dateTo: null,
  });

  useEffect(() => {
    if (accountId) {
      fetchEvents();
    }
  }, [accountId, page, filters]);

  const fetchEvents = async () => {
    setLoading(true);
    try {
      const params = {
        page,
        type: filters.type || undefined,
        search: filters.search || undefined,
        from: filters.dateFrom?.toISOString() || undefined,
        to: filters.dateTo?.toISOString() || undefined,
      };
      const data = await API.getFailoverEvents(accountId, params);
      setEvents(data.results || []);
      setTotalPages(Math.ceil((data.count || 0) / 20));
    } catch (error) {
      console.error('Failed to fetch failover events:', error);
      notifications.show({
        title: 'Error',
        message: 'Failed to load failover events',
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (field, value) => {
    setFilters(prev => ({ ...prev, [field]: value }));
    setPage(1);
  };

  const handleExport = async () => {
    try {
      const data = await API.exportFailoverEvents(accountId, filters);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `failover-events-${accountId}-${new Date().toISOString().split('T')[0]}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: 'Failed to export events',
        color: 'red',
      });
    }
  };

  const handleClearLogs = async () => {
    if (!confirm('Are you sure you want to clear all failover logs?')) return;
    
    try {
      await API.clearFailoverEvents(accountId);
      setEvents([]);
      notifications.show({
        title: 'Success',
        message: 'Failover logs cleared',
        color: 'green',
      });
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: 'Failed to clear logs',
        color: 'red',
      });
    }
  };

  const typeColors = {
    mac: 'blue',
    portal: 'green',
    endpoint: 'teal',
    stream: 'orange',
    useragent: 'violet',
  };

  const formatTimestamp = (ts) => {
    return new Date(ts).toLocaleString();
  };

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <Title order={3}>Failover Event Log</Title>
        <Group>
          <Tooltip label="Refresh">
            <ActionIcon variant="light" onClick={fetchEvents}>
              <IconRefresh size={18} />
            </ActionIcon>
          </Tooltip>
          <Button 
            variant="light" 
            leftSection={<IconDownload size={16} />}
            onClick={handleExport}
          >
            Export
          </Button>
          <Button 
            variant="light" 
            color="red"
            leftSection={<IconTrash size={16} />}
            onClick={handleClearLogs}
          >
            Clear Logs
          </Button>
        </Group>
      </Group>

      <Paper withBorder p="md">
        <Group gap="md" mb="md">
          <Select
            placeholder="Filter by type"
            value={filters.type}
            onChange={(val) => handleFilterChange('type', val)}
            data={[
              { value: '', label: 'All Types' },
              { value: 'mac', label: 'MAC' },
              { value: 'portal', label: 'Portal' },
              { value: 'endpoint', label: 'Endpoint' },
              { value: 'stream', label: 'Stream' },
              { value: 'useragent', label: 'User-Agent' },
            ]}
            clearable
            w={150}
          />
          <TextInput
            placeholder="Search..."
            value={filters.search}
            onChange={(e) => handleFilterChange('search', e.currentTarget.value)}
            leftSection={<IconSearch size={16} />}
            w={200}
          />
          <DatePickerInput
            placeholder="From date"
            value={filters.dateFrom}
            onChange={(val) => handleFilterChange('dateFrom', val)}
            clearable
            w={150}
          />
          <DatePickerInput
            placeholder="To date"
            value={filters.dateTo}
            onChange={(val) => handleFilterChange('dateTo', val)}
            clearable
            w={150}
          />
        </Group>

        <Box pos="relative" mih={200}>
          <LoadingOverlay visible={loading} />
          
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Timestamp</Table.Th>
                <Table.Th>Type</Table.Th>
                <Table.Th>Original</Table.Th>
                <Table.Th>New</Table.Th>
                <Table.Th>Reason</Table.Th>
                <Table.Th>Result</Table.Th>
                <Table.Th>Duration</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {events.map((event, index) => (
                <Table.Tr key={event.id || index}>
                  <Table.Td>
                    <Text size="xs">{formatTimestamp(event.timestamp)}</Text>
                  </Table.Td>
                  <Table.Td>
                    <Badge 
                      color={typeColors[event.failover_type] || 'gray'} 
                      variant="light"
                      size="sm"
                    >
                      {event.failover_type}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Text size="xs" ff="monospace" lineClamp={1}>
                      {event.original_value?.substring(0, 20)}
                      {event.original_value?.length > 20 ? '...' : ''}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Text size="xs" ff="monospace" lineClamp={1}>
                      {event.new_value?.substring(0, 20)}
                      {event.new_value?.length > 20 ? '...' : ''}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Tooltip label={event.reason} multiline w={300}>
                      <Text size="xs" lineClamp={1} style={{ maxWidth: 200 }}>
                        {event.reason}
                      </Text>
                    </Tooltip>
                  </Table.Td>
                  <Table.Td>
                    {event.success ? (
                      <Badge color="green" variant="light" size="sm" leftSection={<IconCheck size={12} />}>
                        Success
                      </Badge>
                    ) : (
                      <Badge color="red" variant="light" size="sm" leftSection={<IconX size={12} />}>
                        Failed
                      </Badge>
                    )}
                  </Table.Td>
                  <Table.Td>
                    <Text size="xs">
                      {event.duration_ms ? `${event.duration_ms}ms` : '-'}
                    </Text>
                  </Table.Td>
                </Table.Tr>
              ))}
              {events.length === 0 && !loading && (
                <Table.Tr>
                  <Table.Td colSpan={7}>
                    <Text size="sm" c="dimmed" ta="center" py="xl">
                      No failover events found
                    </Text>
                  </Table.Td>
                </Table.Tr>
              )}
            </Table.Tbody>
          </Table>
        </Box>

        {totalPages > 1 && (
          <Group justify="center" mt="md">
            <Pagination 
              value={page} 
              onChange={setPage} 
              total={totalPages} 
            />
          </Group>
        )}
      </Paper>
    </Stack>
  );
};

export default FailoverEventLog;
