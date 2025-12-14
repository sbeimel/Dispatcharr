/**
 * Debug Log Viewer Component
 * 
 * Filterable log viewer for MAC Portal debug logs.
 * Requirements: 53.1, 53.2, 53.3, 53.4
 */

import React, { useState, useEffect, useRef } from 'react';
import {
  Stack,
  Paper,
  Title,
  Text,
  Group,
  Select,
  TextInput,
  Button,
  ActionIcon,
  Box,
  Badge,
  ScrollArea,
  Code,
  Switch,
  Tooltip,
  Divider,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { 
  IconRefresh, 
  IconSearch,
  IconDownload,
  IconTrash,
  IconPlayerPlay,
  IconPlayerPause,
  IconFilter,
  IconCopy,
} from '@tabler/icons-react';
import API from '../../api';

const LOG_LEVELS = {
  DEBUG: { color: 'gray', priority: 0 },
  INFO: { color: 'blue', priority: 1 },
  WARNING: { color: 'yellow', priority: 2 },
  ERROR: { color: 'red', priority: 3 },
};

const DebugLogViewer = ({ accountId }) => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [filters, setFilters] = useState({
    level: '',
    search: '',
    mac: '',
  });
  const scrollRef = useRef(null);
  const intervalRef = useRef(null);

  useEffect(() => {
    fetchLogs();
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [accountId]);

  useEffect(() => {
    if (autoRefresh) {
      intervalRef.current = setInterval(fetchLogs, 3000);
    } else if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [autoRefresh]);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const params = {
        portal: accountId,
        level: filters.level || undefined,
        search: filters.search || undefined,
        mac: filters.mac || undefined,
      };
      const data = await API.getMACPortalLogs(params);
      setLogs(data.results || data || []);
      
      // Auto-scroll to bottom if auto-refresh is on
      if (autoRefresh && scrollRef.current) {
        setTimeout(() => {
          scrollRef.current.scrollTo({ top: scrollRef.current.scrollHeight });
        }, 100);
      }
    } catch (error) {
      console.error('Failed to fetch logs:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (field, value) => {
    setFilters(prev => ({ ...prev, [field]: value }));
  };

  const applyFilters = () => {
    fetchLogs();
  };

  const handleExport = () => {
    const content = logs.map(log => 
      `[${log.timestamp}] [${log.level}] ${log.mac ? `[${log.mac}] ` : ''}${log.message}`
    ).join('\n');
    
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `mac-portal-logs-${new Date().toISOString().split('T')[0]}.log`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleClear = async () => {
    if (!confirm('Are you sure you want to clear all logs?')) return;
    
    try {
      await API.clearMACPortalLogs(accountId);
      setLogs([]);
      notifications.show({
        title: 'Success',
        message: 'Logs cleared',
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

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    notifications.show({
      title: 'Copied',
      message: 'Log entry copied to clipboard',
      color: 'blue',
    });
  };

  const formatTimestamp = (ts) => {
    return new Date(ts).toLocaleString();
  };

  const filteredLogs = logs.filter(log => {
    if (filters.level && log.level !== filters.level) return false;
    if (filters.search && !log.message.toLowerCase().includes(filters.search.toLowerCase())) return false;
    if (filters.mac && log.mac !== filters.mac) return false;
    return true;
  });

  const uniqueMacs = [...new Set(logs.filter(l => l.mac).map(l => l.mac))];

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <Title order={3}>Debug Logs</Title>
        <Group>
          <Switch
            label="Auto-refresh"
            checked={autoRefresh}
            onChange={(e) => setAutoRefresh(e.currentTarget.checked)}
            onLabel={<IconPlayerPlay size={14} />}
            offLabel={<IconPlayerPause size={14} />}
          />
          <Tooltip label="Refresh">
            <ActionIcon variant="light" onClick={fetchLogs} loading={loading}>
              <IconRefresh size={18} />
            </ActionIcon>
          </Tooltip>
          <Button 
            variant="light" 
            leftSection={<IconDownload size={16} />}
            onClick={handleExport}
            disabled={logs.length === 0}
          >
            Export
          </Button>
          <Button 
            variant="light" 
            color="red"
            leftSection={<IconTrash size={16} />}
            onClick={handleClear}
          >
            Clear
          </Button>
        </Group>
      </Group>

      <Paper withBorder p="sm">
        <Group gap="md">
          <Select
            placeholder="Log level"
            value={filters.level}
            onChange={(val) => handleFilterChange('level', val)}
            data={[
              { value: '', label: 'All Levels' },
              { value: 'DEBUG', label: 'Debug' },
              { value: 'INFO', label: 'Info' },
              { value: 'WARNING', label: 'Warning' },
              { value: 'ERROR', label: 'Error' },
            ]}
            clearable
            w={130}
          />
          {uniqueMacs.length > 0 && (
            <Select
              placeholder="MAC address"
              value={filters.mac}
              onChange={(val) => handleFilterChange('mac', val)}
              data={[
                { value: '', label: 'All MACs' },
                ...uniqueMacs.map(mac => ({ value: mac, label: mac })),
              ]}
              clearable
              w={180}
            />
          )}
          <TextInput
            placeholder="Search logs..."
            value={filters.search}
            onChange={(e) => handleFilterChange('search', e.currentTarget.value)}
            leftSection={<IconSearch size={16} />}
            style={{ flex: 1 }}
          />
          <Button 
            leftSection={<IconFilter size={16} />}
            onClick={applyFilters}
          >
            Apply
          </Button>
        </Group>
      </Paper>

      <Paper withBorder p={0} style={{ overflow: 'hidden' }}>
        <Box 
          p="xs" 
          bg="dark.8" 
          style={{ borderBottom: '1px solid var(--mantine-color-dark-4)' }}
        >
          <Group justify="space-between">
            <Text size="xs" c="dimmed">
              {filteredLogs.length} log entries
              {filters.level || filters.search || filters.mac ? ' (filtered)' : ''}
            </Text>
            {autoRefresh && (
              <Badge size="xs" color="green" variant="dot">
                Live
              </Badge>
            )}
          </Group>
        </Box>
        
        <ScrollArea h={500} viewportRef={scrollRef} bg="dark.9">
          <Box p="xs" style={{ fontFamily: 'monospace', fontSize: '12px' }}>
            {filteredLogs.length === 0 ? (
              <Text c="dimmed" ta="center" py="xl">
                No log entries found
              </Text>
            ) : (
              filteredLogs.map((log, index) => (
                <Group 
                  key={index} 
                  gap="xs" 
                  wrap="nowrap" 
                  py={2}
                  style={{ 
                    borderBottom: '1px solid var(--mantine-color-dark-6)',
                    '&:hover': { backgroundColor: 'var(--mantine-color-dark-7)' },
                  }}
                >
                  <Text size="xs" c="dimmed" style={{ minWidth: 150 }}>
                    {formatTimestamp(log.timestamp)}
                  </Text>
                  <Badge 
                    size="xs" 
                    color={LOG_LEVELS[log.level]?.color || 'gray'}
                    variant="filled"
                    style={{ minWidth: 60 }}
                  >
                    {log.level}
                  </Badge>
                  {log.mac && (
                    <Code size="xs" style={{ minWidth: 140 }}>
                      {log.mac}
                    </Code>
                  )}
                  <Text 
                    size="xs" 
                    c={log.level === 'ERROR' ? 'red' : log.level === 'WARNING' ? 'yellow' : 'gray.3'}
                    style={{ flex: 1, wordBreak: 'break-word' }}
                  >
                    {log.message}
                  </Text>
                  <Tooltip label="Copy">
                    <ActionIcon 
                      size="xs" 
                      variant="subtle"
                      onClick={() => copyToClipboard(`[${log.timestamp}] [${log.level}] ${log.message}`)}
                    >
                      <IconCopy size={12} />
                    </ActionIcon>
                  </Tooltip>
                </Group>
              ))
            )}
          </Box>
        </ScrollArea>
      </Paper>
    </Stack>
  );
};

export default DebugLogViewer;
