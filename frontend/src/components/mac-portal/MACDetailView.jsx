/**
 * MAC Detail View Component
 * 
 * Detailed view of a single MAC address with history.
 * Requirements: 49.4
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Title,
  Paper,
  Table,
  Badge,
  Group,
  Button,
  Text,
  Progress,
  Stack,
  Card,
  SimpleGrid,
  Timeline,
  LoadingOverlay,
  Modal,
  Divider,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { 
  IconRefresh, 
  IconCheck, 
  IconX, 
  IconClock, 
  IconAlertTriangle,
  IconPlayerPlay,
} from '@tabler/icons-react';
import API from '../../api';

const MACDetailView = ({ accountId, macId, macAddress, opened, onClose }) => {
  const [loading, setLoading] = useState(true);
  const [macStatus, setMacStatus] = useState(null);
  const [history, setHistory] = useState([]);

  useEffect(() => {
    if (opened && accountId && macId) {
      fetchMACDetails();
    }
  }, [opened, accountId, macId]);

  const fetchMACDetails = async () => {
    setLoading(true);
    try {
      const [statusData, historyData] = await Promise.all([
        API.getMACStatus(accountId, macId),
        API.getMACHistory(accountId, macId),
      ]);
      setMacStatus(statusData);
      setHistory(historyData);
    } catch (error) {
      console.error('Failed to fetch MAC details:', error);
      notifications.show({
        title: 'Error',
        message: 'Failed to load MAC details',
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleResetCooldown = async () => {
    try {
      await API.resetMACCooldown(accountId, macId);
      notifications.show({
        title: 'Success',
        message: 'Cooldown reset successfully',
        color: 'green',
      });
      fetchMACDetails();
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: 'Failed to reset cooldown',
        color: 'red',
      });
    }
  };

  const getEventIcon = (eventType) => {
    switch (eventType) {
      case 'success':
        return <IconCheck size={16} color="green" />;
      case 'failure':
        return <IconX size={16} color="red" />;
      case 'cooldown':
        return <IconClock size={16} color="yellow" />;
      case 'block':
        return <IconAlertTriangle size={16} color="orange" />;
      default:
        return <IconClock size={16} color="gray" />;
    }
  };

  const getEventColor = (eventType) => {
    switch (eventType) {
      case 'success': return 'green';
      case 'failure': return 'red';
      case 'cooldown': return 'yellow';
      case 'block': return 'orange';
      default: return 'gray';
    }
  };

  const getHealthColor = (score) => {
    if (score >= 80) return 'green';
    if (score >= 50) return 'yellow';
    return 'red';
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleString();
  };

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={<Title order={4}>MAC Details: {macAddress}</Title>}
      size="lg"
    >
      <Box pos="relative" mih={300}>
        <LoadingOverlay visible={loading} />
        
        {macStatus && (
          <Stack gap="md">
            <SimpleGrid cols={2}>
              <Card withBorder p="sm">
                <Text size="xs" c="dimmed" tt="uppercase">Status</Text>
                <Badge 
                  color={macStatus.status === 'valid' ? 'green' : 'red'}
                  size="lg"
                  mt="xs"
                >
                  {macStatus.status}
                </Badge>
              </Card>
              <Card withBorder p="sm">
                <Text size="xs" c="dimmed" tt="uppercase">Health Score</Text>
                <Group gap="xs" mt="xs">
                  <Progress 
                    value={macStatus.health_score} 
                    color={getHealthColor(macStatus.health_score)}
                    size="lg"
                    w={80}
                  />
                  <Text fw={700}>{macStatus.health_score}%</Text>
                </Group>
              </Card>
            </SimpleGrid>

            {macStatus.in_cooldown && (
              <Card withBorder p="sm" bg="yellow.0">
                <Group justify="space-between">
                  <div>
                    <Text size="sm" fw={500} c="yellow.8">In Cooldown</Text>
                    <Text size="xs" c="dimmed">
                      Reason: {macStatus.cooldown_reason} | 
                      Remaining: {macStatus.cooldown_remaining}s
                    </Text>
                  </div>
                  <Button 
                    size="xs" 
                    color="yellow"
                    leftSection={<IconPlayerPlay size={14} />}
                    onClick={handleResetCooldown}
                  >
                    Reset Cooldown
                  </Button>
                </Group>
              </Card>
            )}

            <SimpleGrid cols={2}>
              <Card withBorder p="sm">
                <Text size="xs" c="dimmed" tt="uppercase">Expires At</Text>
                <Text size="sm" mt="xs">
                  {formatDate(macStatus.expires_at)}
                </Text>
              </Card>
              <Card withBorder p="sm">
                <Text size="xs" c="dimmed" tt="uppercase">Last Checked</Text>
                <Text size="sm" mt="xs">
                  {formatDate(macStatus.last_checked)}
                </Text>
              </Card>
            </SimpleGrid>

            <Divider label="Recent Activity" labelPosition="center" />

            <Paper withBorder p="md" mah={300} style={{ overflow: 'auto' }}>
              {history.length > 0 ? (
                <Timeline active={-1} bulletSize={24} lineWidth={2}>
                  {history.slice(0, 20).map((event, index) => (
                    <Timeline.Item
                      key={index}
                      bullet={getEventIcon(event.event_type)}
                      color={getEventColor(event.event_type)}
                      title={
                        <Group gap="xs">
                          <Badge size="xs" color={getEventColor(event.event_type)}>
                            {event.event_type}
                          </Badge>
                          {event.response_time_ms && (
                            <Text size="xs" c="dimmed">{event.response_time_ms}ms</Text>
                          )}
                        </Group>
                      }
                    >
                      <Text size="xs" c="dimmed">
                        {formatDate(event.timestamp)}
                      </Text>
                      {event.error_message && (
                        <Text size="xs" c="red" mt={4}>
                          {event.error_message}
                        </Text>
                      )}
                      {event.endpoint_used && (
                        <Text size="xs" c="dimmed" mt={2}>
                          Endpoint: {event.endpoint_used}
                        </Text>
                      )}
                    </Timeline.Item>
                  ))}
                </Timeline>
              ) : (
                <Text ta="center" c="dimmed" py="md">
                  No activity history available
                </Text>
              )}
            </Paper>

            <Group justify="flex-end">
              <Button variant="outline" onClick={fetchMACDetails}>
                <IconRefresh size={16} style={{ marginRight: 8 }} />
                Refresh
              </Button>
              <Button onClick={onClose}>Close</Button>
            </Group>
          </Stack>
        )}
      </Box>
    </Modal>
  );
};

export default MACDetailView;
