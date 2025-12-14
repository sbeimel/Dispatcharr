/**
 * Predictive Failover Dashboard Component
 * 
 * Displays real-time predictive failover status including:
 * - Active streams with risk scores
 * - Warmup status
 * - Recent events
 * - Statistics
 * 
 * Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Card,
  Text,
  Title,
  Grid,
  Badge,
  Progress,
  Table,
  Paper,
  Alert,
  ActionIcon,
  Tooltip,
  Group,
  Stack,
  SimpleGrid,
  ThemeIcon,
  Loader,
} from '@mantine/core';
import {
  IconCircleCheck,
  IconAlertTriangle,
  IconCircleX,
  IconRefresh,
} from '@tabler/icons-react';
import API from '../../api';

// Risk score color coding
const getRiskColor = (score, warmupThreshold = 60, failoverThreshold = 85) => {
  if (score >= failoverThreshold) return 'red';
  if (score >= warmupThreshold) return 'yellow';
  return 'green';
};

const getRiskIcon = (score, warmupThreshold = 60, failoverThreshold = 85) => {
  if (score >= failoverThreshold) return <IconCircleX size={16} color="red" />;
  if (score >= warmupThreshold) return <IconAlertTriangle size={16} color="orange" />;
  return <IconCircleCheck size={16} color="green" />;
};

const PredictiveFailoverDashboard = () => {
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadDashboard = useCallback(async () => {
    try {
      setLoading(true);
      const response = await API.get('/api/predictive-failover/dashboard/');
      setDashboard(response.data);
      setError(null);
    } catch (err) {
      setError('Failed to load dashboard');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboard();

    // Connect WebSocket
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/predictive-failover/`;
    
    try {
      const websocket = new WebSocket(wsUrl);
      
      websocket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
      };
      
      return () => websocket.close();
    } catch (err) {
      console.error('Failed to connect WebSocket:', err);
    }
  }, [loadDashboard]);

  const handleWebSocketMessage = (data) => {
    switch (data.type) {
      case 'initial_state':
        setDashboard(prev => ({ ...prev, ...data.data }));
        break;
      case 'risk_score_update':
        setDashboard(prev => {
          if (!prev) return prev;
          const streams = [...(prev.active_streams || [])];
          const idx = streams.findIndex(s => s.stream_id === data.stream_id);
          if (idx >= 0) {
            streams[idx] = { ...streams[idx], risk_score: data.risk_score, reasons: data.reasons };
          }
          return { ...prev, active_streams: streams };
        });
        break;
      case 'failover_event':
        setDashboard(prev => {
          if (!prev) return prev;
          const events = [data, ...(prev.recent_events || [])].slice(0, 20);
          return { ...prev, recent_events: events };
        });
        break;
      case 'warmup_status_update':
        setDashboard(prev => {
          if (!prev) return prev;
          const warmup = { ...(prev.warmup_status || {}) };
          warmup[data.channel_id] = data;
          return { ...prev, warmup_status: warmup };
        });
        break;
      default:
        break;
    }
  };

  if (loading && !dashboard) {
    return <Box ta="center" py="xl"><Loader /></Box>;
  }

  if (error) {
    return <Alert color="red">{error}</Alert>;
  }

  const { enabled, active_streams = [], warmup_status = {}, recent_events = [], statistics = {} } = dashboard || {};

  return (
    <Box p="md">
      <Group justify="space-between" mb="md">
        <Group>
          <Title order={4}>Predictive Failover Dashboard</Title>
          <Badge color={enabled ? 'green' : 'gray'} size="sm">
            {enabled ? 'Enabled' : 'Disabled'}
          </Badge>
        </Group>
        <ActionIcon variant="subtle" onClick={loadDashboard}>
          <IconRefresh size={18} />
        </ActionIcon>
      </Group>

      {/* Statistics Cards */}
      <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} mb="md">
        <Card shadow="sm" p="md" withBorder>
          <Text size="sm" c="dimmed">Active Streams</Text>
          <Title order={2}>{active_streams.length}</Title>
        </Card>
        <Card shadow="sm" p="md" withBorder>
          <Text size="sm" c="dimmed">Warmups Active</Text>
          <Title order={2}>{Object.values(warmup_status).filter(w => w.is_ready).length}</Title>
        </Card>
        <Card shadow="sm" p="md" withBorder>
          <Text size="sm" c="dimmed">Success Rate</Text>
          <Title order={2}>{statistics.success_rate?.toFixed(1) || 0}%</Title>
        </Card>
        <Card shadow="sm" p="md" withBorder>
          <Text size="sm" c="dimmed">Total Failovers</Text>
          <Title order={2}>{statistics.total_failovers || 0}</Title>
        </Card>
      </SimpleGrid>

      {/* Active Streams */}
      <Card shadow="sm" p="md" mb="md" withBorder>
        <Title order={5} mb="sm">Active Streams</Title>
        <Paper withBorder>
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Channel</Table.Th>
                <Table.Th>Risk Score</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Warmup</Table.Th>
                <Table.Th>Reasons</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {active_streams.map((stream) => (
                <Table.Tr key={stream.stream_id}>
                  <Table.Td>{stream.channel_name}</Table.Td>
                  <Table.Td>
                    <Group gap="xs">
                      {getRiskIcon(stream.risk_score)}
                      <Text size="sm">{stream.risk_score}</Text>
                    </Group>
                  </Table.Td>
                  <Table.Td>
                    <Badge color={getRiskColor(stream.risk_score)} size="sm">
                      {stream.risk_score >= 85 ? 'Critical' : stream.risk_score >= 60 ? 'Warning' : 'OK'}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    {warmup_status[stream.channel_id]?.is_ready ? (
                      <Badge color="blue" size="sm">Ready</Badge>
                    ) : warmup_status[stream.channel_id]?.status === 'warming' ? (
                      <Badge color="yellow" size="sm">Warming</Badge>
                    ) : (
                      <Text size="sm" c="dimmed">-</Text>
                    )}
                  </Table.Td>
                  <Table.Td>
                    <Text size="sm">{stream.reasons?.slice(0, 2).join(', ') || '-'}</Text>
                  </Table.Td>
                </Table.Tr>
              ))}
              {active_streams.length === 0 && (
                <Table.Tr>
                  <Table.Td colSpan={5}>
                    <Text ta="center" c="dimmed">No active streams</Text>
                  </Table.Td>
                </Table.Tr>
              )}
            </Table.Tbody>
          </Table>
        </Paper>
      </Card>

      {/* Recent Events */}
      <Card shadow="sm" p="md" withBorder>
        <Title order={5} mb="sm">Recent Events</Title>
        <Paper withBorder>
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Time</Table.Th>
                <Table.Th>Event</Table.Th>
                <Table.Th>Channel</Table.Th>
                <Table.Th>Risk Score</Table.Th>
                <Table.Th>Result</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {recent_events.map((event, idx) => (
                <Table.Tr key={idx}>
                  <Table.Td>
                    <Text size="sm">{new Date(event.timestamp).toLocaleTimeString()}</Text>
                  </Table.Td>
                  <Table.Td>
                    <Badge variant="outline" size="sm">
                      {event.event_type_display || event.event_type}
                    </Badge>
                  </Table.Td>
                  <Table.Td><Text size="sm">{event.channel_name || '-'}</Text></Table.Td>
                  <Table.Td><Text size="sm">{event.risk_score || '-'}</Text></Table.Td>
                  <Table.Td>
                    {event.success !== null && (
                      event.success ? (
                        <IconCircleCheck size={16} color="green" />
                      ) : (
                        <IconCircleX size={16} color="red" />
                      )
                    )}
                  </Table.Td>
                </Table.Tr>
              ))}
              {recent_events.length === 0 && (
                <Table.Tr>
                  <Table.Td colSpan={5}>
                    <Text ta="center" c="dimmed">No recent events</Text>
                  </Table.Td>
                </Table.Tr>
              )}
            </Table.Tbody>
          </Table>
        </Paper>
      </Card>
    </Box>
  );
};

export default PredictiveFailoverDashboard;
