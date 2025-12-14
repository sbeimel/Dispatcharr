/**
 * MAC Health Dashboard Component
 * 
 * Overview of all MACs with status and health information.
 * Requirements: 49.1, 49.2, 49.3, 49.4
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
  ActionIcon,
  Tooltip,
  LoadingOverlay,
  Stack,
  Card,
  SimpleGrid,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconRefresh, IconEye, IconPlayerPlay, IconPlayerPause } from '@tabler/icons-react';
import API from '../../api';

const MACHealthDashboard = ({ accountId }) => {
  const [loading, setLoading] = useState(true);
  const [macs, setMacs] = useState([]);
  const [stats, setStats] = useState({
    total: 0,
    healthy: 0,
    inCooldown: 0,
    expired: 0,
  });

  useEffect(() => {
    if (accountId) {
      fetchMACHealth();
    }
  }, [accountId]);

  const fetchMACHealth = async () => {
    setLoading(true);
    try {
      const data = await API.getMACHealth(accountId);
      setMacs(data);
      
      // Calculate stats
      const total = data.length;
      const healthy = data.filter(m => m.status === 'valid' && !m.in_cooldown).length;
      const inCooldown = data.filter(m => m.in_cooldown).length;
      const expired = data.filter(m => m.status === 'expired').length;
      
      setStats({ total, healthy, inCooldown, expired });
    } catch (error) {
      console.error('Failed to fetch MAC health:', error);
      notifications.show({
        title: 'Error',
        message: 'Failed to load MAC health data',
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleResetCooldown = async (macId) => {
    try {
      await API.resetMACCooldown(accountId, macId);
      notifications.show({
        title: 'Success',
        message: 'Cooldown reset successfully',
        color: 'green',
      });
      fetchMACHealth();
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: 'Failed to reset cooldown',
        color: 'red',
      });
    }
  };

  const getStatusBadge = (mac) => {
    if (mac.in_cooldown) {
      return <Badge color="yellow">Cooldown ({mac.cooldown_remaining}s)</Badge>;
    }
    switch (mac.status) {
      case 'valid':
        return <Badge color="green">Healthy</Badge>;
      case 'expired':
        return <Badge color="red">Expired</Badge>;
      case 'error':
        return <Badge color="orange">Error</Badge>;
      default:
        return <Badge color="gray">Unknown</Badge>;
    }
  };

  const getHealthColor = (score) => {
    if (score >= 80) return 'green';
    if (score >= 50) return 'yellow';
    return 'red';
  };

  return (
    <Box pos="relative">
      <LoadingOverlay visible={loading} />
      
      <Group justify="space-between" mb="md">
        <Title order={3}>MAC Health Dashboard</Title>
        <Button 
          leftSection={<IconRefresh size={16} />}
          variant="outline"
          onClick={fetchMACHealth}
        >
          Refresh
        </Button>
      </Group>

      <SimpleGrid cols={{ base: 2, md: 4 }} mb="md">
        <Card withBorder p="md">
          <Text size="xs" c="dimmed" tt="uppercase">Total MACs</Text>
          <Text size="xl" fw={700}>{stats.total}</Text>
        </Card>
        <Card withBorder p="md">
          <Text size="xs" c="dimmed" tt="uppercase">Healthy</Text>
          <Text size="xl" fw={700} c="green">{stats.healthy}</Text>
        </Card>
        <Card withBorder p="md">
          <Text size="xs" c="dimmed" tt="uppercase">In Cooldown</Text>
          <Text size="xl" fw={700} c="yellow">{stats.inCooldown}</Text>
        </Card>
        <Card withBorder p="md">
          <Text size="xs" c="dimmed" tt="uppercase">Expired</Text>
          <Text size="xl" fw={700} c="red">{stats.expired}</Text>
        </Card>
      </SimpleGrid>

      <Paper withBorder>
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>MAC Address</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Health Score</Table.Th>
              <Table.Th>Cooldown</Table.Th>
              <Table.Th>Expires</Table.Th>
              <Table.Th>Actions</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {macs.map((mac) => (
              <Table.Tr key={mac.address}>
                <Table.Td>
                  <Text size="sm" ff="monospace">{mac.address}</Text>
                </Table.Td>
                <Table.Td>{getStatusBadge(mac)}</Table.Td>
                <Table.Td>
                  <Group gap="xs">
                    <Progress 
                      value={mac.health_score} 
                      color={getHealthColor(mac.health_score)}
                      size="sm"
                      w={60}
                    />
                    <Text size="xs">{mac.health_score}%</Text>
                  </Group>
                </Table.Td>
                <Table.Td>
                  {mac.in_cooldown ? (
                    <Group gap="xs">
                      <Text size="sm" c="yellow">{mac.cooldown_remaining}s</Text>
                      <Text size="xs" c="dimmed">({mac.cooldown_reason})</Text>
                    </Group>
                  ) : (
                    <Text size="sm" c="dimmed">-</Text>
                  )}
                </Table.Td>
                <Table.Td>
                  <Text size="sm">
                    {mac.expires_at ? new Date(mac.expires_at).toLocaleDateString() : '-'}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Group gap="xs">
                    <Tooltip label="View Details">
                      <ActionIcon variant="subtle" color="blue">
                        <IconEye size={16} />
                      </ActionIcon>
                    </Tooltip>
                    {mac.in_cooldown && (
                      <Tooltip label="Reset Cooldown">
                        <ActionIcon 
                          variant="subtle" 
                          color="yellow"
                          onClick={() => handleResetCooldown(mac.id)}
                        >
                          <IconPlayerPlay size={16} />
                        </ActionIcon>
                      </Tooltip>
                    )}
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
        
        {macs.length === 0 && !loading && (
          <Text ta="center" py="xl" c="dimmed">
            No MAC addresses found for this account
          </Text>
        )}
      </Paper>
    </Box>
  );
};

export default MACHealthDashboard;
