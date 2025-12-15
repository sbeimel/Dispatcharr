/**
 * Failover Test Page - Redesigned
 * 
 * Shows real channels like the Channels tab with ability to kill streams
 * and watch failover events in real-time.
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Box,
  Title,
  Paper,
  Stack,
  Group,
  Button,
  Badge,
  Text,
  Table,
  ActionIcon,
  TextInput,
  Select,
  Pagination,
  ScrollArea,
  Tooltip,
  Modal,
  Alert,
  Code,
  Loader,
  Switch,
  Collapse,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import {
  IconRefresh,
  IconPlayerStop,
  IconAlertTriangle,
  IconSearch,
  IconTrash,
  IconChevronDown,
  IconChevronRight,
  IconActivity,
  IconWifi,
  IconWifiOff,
  IconBolt,
  IconPlayerPlay,
} from '@tabler/icons-react';
import API from '../../api';
import useChannelsStore from '../../store/channels';

const FailoverTestPage = () => {
  // State
  const [loading, setLoading] = useState(true);
  const [channels, setChannels] = useState([]);
  const [activeStreams, setActiveStreams] = useState({});
  const [logEntries, setLogEntries] = useState([]);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [expandedChannels, setExpandedChannels] = useState(new Set());
  const [wsConnected, setWsConnected] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const [killingStream, setKillingStream] = useState(null);

  // WebSocket for live logs
  useEffect(() => {
    let ws = null;
    let reconnectTimer = null;

    const connect = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws/failover-test/`;
      
      ws = new WebSocket(wsUrl);
      
      ws.onopen = () => {
        setWsConnected(true);
        console.log('Failover test WebSocket connected');
      };
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'log_entry' || data.type === 'failover_event') {
            setLogEntries(prev => {
              const newEntries = [data.data, ...prev].slice(0, 500);
              return newEntries;
            });
          } else if (data.type === 'stream_status') {
            setActiveStreams(prev => ({
              ...prev,
              [data.data.channel_id]: data.data,
            }));
          }
        } catch (e) {
          console.error('WebSocket message parse error:', e);
        }
      };
      
      ws.onclose = () => {
        setWsConnected(false);
        reconnectTimer = setTimeout(connect, 3000);
      };
      
      ws.onerror = () => {
        ws.close();
      };
    };

    connect();

    return () => {
      if (ws) ws.close();
      if (reconnectTimer) clearTimeout(reconnectTimer);
    };
  }, []);

  // Load channels
  const loadChannels = useCallback(async () => {
    setLoading(true);
    try {
      const response = await API.getChannels();
      setChannels(response || []);
      
      // Also load active streams
      try {
        const host = import.meta.env.DEV ? `http://${window.location.hostname}:5656` : '';
        const streamsResponse = await fetch(`${host}/api/proxy/active-streams/`, {
          headers: { Authorization: `Bearer ${await API.getAuthToken()}` },
        });
        if (streamsResponse.ok) {
          const streams = await streamsResponse.json();
          const streamMap = {};
          (streams || []).forEach(s => {
            streamMap[s.channel_id] = s;
          });
          setActiveStreams(streamMap);
        }
      } catch (e) {
        console.log('Could not load active streams:', e);
      }
    } catch (error) {
      console.error('Failed to load channels:', error);
      notifications.show({
        title: 'Error',
        message: 'Failed to load channels',
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadChannels();
  }, [loadChannels]);

  // Filter channels
  const filteredChannels = useMemo(() => {
    if (!search) return channels;
    const searchLower = search.toLowerCase();
    return channels.filter(ch => 
      ch.name?.toLowerCase().includes(searchLower) ||
      ch.channel_number?.toString().includes(searchLower)
    );
  }, [channels, search]);

  // Paginate
  const paginatedChannels = useMemo(() => {
    const start = (page - 1) * pageSize;
    return filteredChannels.slice(start, start + pageSize);
  }, [filteredChannels, page, pageSize]);

  const totalPages = Math.ceil(filteredChannels.length / pageSize);

  // Channel streams cache
  const [channelStreams, setChannelStreams] = useState({});

  // Toggle channel expansion and load streams
  const toggleExpand = async (channelId) => {
    const isCurrentlyExpanded = expandedChannels.has(channelId);
    
    setExpandedChannels(prev => {
      const next = new Set(prev);
      if (next.has(channelId)) {
        next.delete(channelId);
      } else {
        next.add(channelId);
      }
      return next;
    });

    // Load streams if expanding and not already loaded
    if (!isCurrentlyExpanded && !channelStreams[channelId]) {
      try {
        const streams = await API.getChannelStreams(channelId);
        setChannelStreams(prev => ({
          ...prev,
          [channelId]: streams || [],
        }));
      } catch (e) {
        console.log('Could not load streams for channel:', channelId, e);
      }
    }
  };

  // Kill stream for a channel
  const killStream = async (channelId) => {
    setKillingStream(channelId);
    try {
      const host = import.meta.env.DEV ? `http://${window.location.hostname}:5656` : '';
      const response = await fetch(`${host}/api/proxy/kill-stream/${channelId}/`, {
        method: 'POST',
        headers: { 
          Authorization: `Bearer ${await API.getAuthToken()}`,
          'Content-Type': 'application/json',
        },
      });
      
      if (response.ok) {
        const result = await response.json();
        notifications.show({
          title: 'Stream Killed',
          message: `Killed stream for channel ${channelId}. Failover should trigger.`,
          color: 'orange',
        });
        
        // Add to log
        setLogEntries(prev => [{
          id: Date.now(),
          timestamp: new Date().toISOString(),
          event_type: 'stream_killed',
          channel_id: channelId,
          message: `Stream manually killed - waiting for failover`,
          success: true,
        }, ...prev].slice(0, 500));
        
        // Refresh active streams
        setTimeout(loadChannels, 1000);
      } else {
        throw new Error('Failed to kill stream');
      }
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: 'Failed to kill stream',
        color: 'red',
      });
    } finally {
      setKillingStream(null);
    }
  };

  // Clear logs
  const clearLogs = () => {
    setLogEntries([]);
  };

  // Format timestamp
  const formatTime = (ts) => {
    if (!ts) return '';
    const d = new Date(ts);
    return d.toLocaleTimeString();
  };

  // Get event color
  const getEventColor = (entry) => {
    if (entry.event_type === 'failover_success') return 'green';
    if (entry.event_type === 'failover_failed') return 'red';
    if (entry.event_type === 'stream_killed') return 'orange';
    if (entry.event_type === 'reconnect') return 'blue';
    return 'gray';
  };

  return (
    <Box p="md">
      {/* Header */}
      <Group justify="space-between" mb="md">
        <Group>
          <Title order={2}>Failover Test</Title>
          <Badge color={wsConnected ? 'green' : 'red'} variant="dot" size="lg">
            {wsConnected ? 'Live' : 'Disconnected'}
          </Badge>
        </Group>
        <Button
          variant="outline"
          leftSection={<IconRefresh size={16} />}
          onClick={loadChannels}
          loading={loading}
        >
          Refresh
        </Button>
      </Group>

      <Alert color="blue" mb="md" icon={<IconActivity size={16} />}>
        Select a channel and click "Kill Stream" to terminate the active connection. 
        This will trigger the failover mechanism. Watch the Live Log to see failover events.
      </Alert>

      <Box style={{ display: 'flex', gap: '16px', height: 'calc(100vh - 220px)' }}>
        {/* Left: Channels Table */}
        <Paper shadow="xs" p="md" style={{ flex: 2, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <Group justify="space-between" mb="md">
            <Text fw={600}>Channels ({filteredChannels.length})</Text>
            <TextInput
              placeholder="Search channels..."
              leftSection={<IconSearch size={14} />}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{ width: 250 }}
            />
          </Group>

          <ScrollArea style={{ flex: 1 }}>
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th style={{ width: 40 }}></Table.Th>
                  <Table.Th style={{ width: 60 }}>#</Table.Th>
                  <Table.Th>Name</Table.Th>
                  <Table.Th style={{ width: 100 }}>Status</Table.Th>
                  <Table.Th style={{ width: 120 }}>Actions</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {paginatedChannels.map(channel => {
                  const isActive = activeStreams[channel.id];
                  const isExpanded = expandedChannels.has(channel.id);
                  
                  return (
                    <React.Fragment key={channel.id}>
                      <Table.Tr>
                        <Table.Td>
                          <ActionIcon
                            variant="subtle"
                            size="sm"
                            onClick={() => toggleExpand(channel.id)}
                          >
                            {isExpanded ? <IconChevronDown size={14} /> : <IconChevronRight size={14} />}
                          </ActionIcon>
                        </Table.Td>
                        <Table.Td>{channel.channel_number}</Table.Td>
                        <Table.Td>
                          <Text size="sm" fw={500}>{channel.name}</Text>
                        </Table.Td>
                        <Table.Td>
                          {isActive ? (
                            <Badge color="green" leftSection={<IconWifi size={10} />}>
                              Active
                            </Badge>
                          ) : (
                            <Badge color="gray" leftSection={<IconWifiOff size={10} />}>
                              Idle
                            </Badge>
                          )}
                        </Table.Td>
                        <Table.Td>
                          <Group gap="xs">
                            <Tooltip label="Kill Stream (Trigger Failover)">
                              <ActionIcon
                                color="red"
                                variant="light"
                                onClick={() => killStream(channel.id)}
                                loading={killingStream === channel.id}
                                disabled={!isActive}
                              >
                                <IconPlayerStop size={16} />
                              </ActionIcon>
                            </Tooltip>
                            <Tooltip label="Simulate Error">
                              <ActionIcon
                                color="orange"
                                variant="light"
                                onClick={() => {
                                  // Simulate different error types
                                  notifications.show({
                                    title: 'Simulating Error',
                                    message: 'Triggering timeout error...',
                                    color: 'orange',
                                  });
                                }}
                              >
                                <IconBolt size={16} />
                              </ActionIcon>
                            </Tooltip>
                          </Group>
                        </Table.Td>
                      </Table.Tr>
                      
                      {/* Expanded row with streams */}
                      {isExpanded && (
                        <Table.Tr>
                          <Table.Td colSpan={5} style={{ background: 'var(--mantine-color-dark-7)', padding: '8px 16px' }}>
                            <Text size="xs" c="dimmed" mb="xs">Streams for this channel:</Text>
                            {channelStreams[channel.id]?.length > 0 ? (
                              <Stack gap="xs">
                                {channelStreams[channel.id].map((stream, idx) => (
                                  <Group key={stream.id || idx} gap="xs">
                                    <Badge size="xs" color={idx === 0 ? 'blue' : 'gray'}>
                                      {idx === 0 ? 'Primary' : `Backup ${idx}`}
                                    </Badge>
                                    <Text size="xs" style={{ fontFamily: 'monospace', maxWidth: 400, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                      {stream.url || stream.m3u_account?.name || 'Unknown'}
                                    </Text>
                                    <Text size="xs" c="dimmed">
                                      ({stream.m3u_account?.name || 'Custom'})
                                    </Text>
                                  </Group>
                                ))}
                              </Stack>
                            ) : channelStreams[channel.id] === undefined ? (
                              <Loader size="xs" />
                            ) : (
                              <Text size="xs" c="dimmed">No streams configured</Text>
                            )}
                          </Table.Td>
                        </Table.Tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </Table.Tbody>
            </Table>
          </ScrollArea>

          {/* Pagination */}
          <Group justify="space-between" mt="md">
            <Select
              value={pageSize.toString()}
              onChange={(v) => setPageSize(parseInt(v))}
              data={['10', '25', '50', '100']}
              style={{ width: 80 }}
              size="xs"
            />
            <Pagination
              total={totalPages}
              value={page}
              onChange={setPage}
              size="sm"
            />
          </Group>
        </Paper>

        {/* Right: Live Log */}
        <Paper shadow="xs" p="md" style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <Group justify="space-between" mb="md">
            <Text fw={600}>Live Log</Text>
            <Group gap="xs">
              <Switch
                label="Auto-scroll"
                checked={autoScroll}
                onChange={(e) => setAutoScroll(e.target.checked)}
                size="xs"
              />
              <ActionIcon variant="subtle" onClick={clearLogs}>
                <IconTrash size={14} />
              </ActionIcon>
            </Group>
          </Group>

          <ScrollArea style={{ flex: 1 }} viewportRef={(ref) => {
            if (ref && autoScroll && logEntries.length > 0) {
              ref.scrollTop = 0;
            }
          }}>
            <Stack gap="xs">
              {logEntries.length === 0 ? (
                <Text size="sm" c="dimmed" ta="center" py="xl">
                  No events yet. Kill a stream to trigger failover.
                </Text>
              ) : (
                logEntries.map((entry, idx) => (
                  <Paper key={entry.id || idx} p="xs" withBorder style={{ borderLeftWidth: 3, borderLeftColor: `var(--mantine-color-${getEventColor(entry)}-6)` }}>
                    <Group justify="space-between" mb={4}>
                      <Badge size="xs" color={getEventColor(entry)}>
                        {entry.event_type}
                      </Badge>
                      <Text size="xs" c="dimmed">{formatTime(entry.timestamp)}</Text>
                    </Group>
                    <Text size="xs">{entry.message || entry.reason || 'Event occurred'}</Text>
                    {entry.channel_id && (
                      <Text size="xs" c="dimmed">Channel: {entry.channel_id}</Text>
                    )}
                    {entry.duration_ms && (
                      <Text size="xs" c="dimmed">Duration: {entry.duration_ms}ms</Text>
                    )}
                  </Paper>
                ))
              )}
            </Stack>
          </ScrollArea>
        </Paper>
      </Box>
    </Box>
  );
};

export default FailoverTestPage;
