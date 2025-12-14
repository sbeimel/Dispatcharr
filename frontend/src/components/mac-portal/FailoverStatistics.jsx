/**
 * Failover Statistics Component
 * 
 * Dashboard showing failover statistics and metrics.
 * Requirements: 61.2
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
  SimpleGrid,
  RingProgress,
  Badge,
  Table,
  Progress,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { 
  IconNetwork, 
  IconRouter, 
  IconPlayerPlay,
  IconUser,
  IconCheck,
  IconX,
} from '@tabler/icons-react';
import API from '../../api';

const FailoverStatistics = ({ accountId }) => {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);
  const [timeRange, setTimeRange] = useState('7');

  useEffect(() => {
    if (accountId) {
      fetchStats();
    }
  }, [accountId, timeRange]);

  const fetchStats = async () => {
    setLoading(true);
    try {
      const data = await API.getFailoverStats(accountId, timeRange);
      setStats(data);
    } catch (error) {
      console.error('Failed to fetch failover stats:', error);
      notifications.show({
        title: 'Error',
        message: 'Failed to load failover statistics',
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Box pos="relative" h={400}>
        <LoadingOverlay visible={true} />
      </Box>
    );
  }

  const successRate = stats?.success_rate ?? 0;
  const totalEvents = stats?.total ?? 0;

  const typeIcons = {
    mac: IconNetwork,
    portal: IconRouter,
    endpoint: IconRouter,
    stream: IconPlayerPlay,
    useragent: IconUser,
  };

  const typeColors = {
    mac: 'blue',
    portal: 'green',
    endpoint: 'teal',
    stream: 'orange',
    useragent: 'violet',
  };

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <Title order={3}>Failover Statistics</Title>
        <Select
          value={timeRange}
          onChange={setTimeRange}
          data={[
            { value: '1', label: 'Last 24 hours' },
            { value: '7', label: 'Last 7 days' },
            { value: '30', label: 'Last 30 days' },
          ]}
          w={150}
        />
      </Group>

      <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} spacing="md">
        <Paper withBorder p="md">
          <Group justify="center">
            <RingProgress
              size={100}
              thickness={10}
              roundCaps
              sections={[
                { value: successRate * 100, color: 'green' },
                { value: (1 - successRate) * 100, color: 'red' },
              ]}
              label={
                <Text ta="center" fw={700} size="lg">
                  {Math.round(successRate * 100)}%
                </Text>
              }
            />
          </Group>
          <Text ta="center" mt="sm" fw={500}>Success Rate</Text>
          <Text ta="center" size="xs" c="dimmed">
            {totalEvents} total events
          </Text>
        </Paper>

        <Paper withBorder p="md">
          <Text size="xl" fw={700} ta="center">
            {stats?.by_type?.find(t => t.failover_type === 'mac')?.count ?? 0}
          </Text>
          <Text ta="center" size="sm" c="dimmed">MAC Failovers</Text>
          <Progress 
            value={getTypePercentage(stats, 'mac')} 
            color="blue" 
            mt="sm" 
            size="sm"
          />
        </Paper>

        <Paper withBorder p="md">
          <Text size="xl" fw={700} ta="center">
            {stats?.by_type?.find(t => t.failover_type === 'stream')?.count ?? 0}
          </Text>
          <Text ta="center" size="sm" c="dimmed">Stream Failovers</Text>
          <Progress 
            value={getTypePercentage(stats, 'stream')} 
            color="orange" 
            mt="sm" 
            size="sm"
          />
        </Paper>

        <Paper withBorder p="md">
          <Text size="xl" fw={700} ta="center">
            {stats?.by_type?.find(t => t.failover_type === 'useragent')?.count ?? 0}
          </Text>
          <Text ta="center" size="sm" c="dimmed">User-Agent Failovers</Text>
          <Progress 
            value={getTypePercentage(stats, 'useragent')} 
            color="violet" 
            mt="sm" 
            size="sm"
          />
        </Paper>
      </SimpleGrid>

      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
        <Paper withBorder p="md">
          <Title order={4} mb="md">Failover by Type</Title>
          <Table>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Type</Table.Th>
                <Table.Th>Count</Table.Th>
                <Table.Th>Percentage</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {(stats?.by_type || []).map((item) => {
                const Icon = typeIcons[item.failover_type] || IconNetwork;
                const color = typeColors[item.failover_type] || 'gray';
                const percentage = totalEvents > 0 
                  ? Math.round((item.count / totalEvents) * 100) 
                  : 0;
                
                return (
                  <Table.Tr key={item.failover_type}>
                    <Table.Td>
                      <Group gap="xs">
                        <Icon size={16} color={`var(--mantine-color-${color}-6)`} />
                        <Text size="sm">{item.failover_type}</Text>
                      </Group>
                    </Table.Td>
                    <Table.Td>{item.count}</Table.Td>
                    <Table.Td>
                      <Badge color={color} variant="light">{percentage}%</Badge>
                    </Table.Td>
                  </Table.Tr>
                );
              })}
            </Table.Tbody>
          </Table>
        </Paper>

        <Paper withBorder p="md">
          <Title order={4} mb="md">Common Failure Reasons</Title>
          <Stack gap="xs">
            {(stats?.common_reasons || []).slice(0, 5).map((item, index) => (
              <Group key={index} justify="space-between">
                <Text size="sm" lineClamp={1} style={{ flex: 1 }}>
                  {item.reason || 'Unknown'}
                </Text>
                <Badge variant="outline">{item.count}</Badge>
              </Group>
            ))}
            {(!stats?.common_reasons || stats.common_reasons.length === 0) && (
              <Text size="sm" c="dimmed" ta="center">No failure data available</Text>
            )}
          </Stack>
        </Paper>
      </SimpleGrid>

      <Paper withBorder p="md">
        <Title order={4} mb="md">Problematic MACs</Title>
        <Text size="xs" c="dimmed" mb="md">
          MACs that have triggered the most failover events
        </Text>
        <Table>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>MAC Address</Table.Th>
              <Table.Th>Failover Count</Table.Th>
              <Table.Th>Status</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {(stats?.problematic_macs || []).slice(0, 5).map((item, index) => (
              <Table.Tr key={index}>
                <Table.Td>
                  <Text size="sm" ff="monospace">{item.original_value}</Text>
                </Table.Td>
                <Table.Td>{item.count}</Table.Td>
                <Table.Td>
                  <Badge 
                    color={item.count > 10 ? 'red' : item.count > 5 ? 'yellow' : 'green'}
                    variant="light"
                  >
                    {item.count > 10 ? 'High' : item.count > 5 ? 'Medium' : 'Low'}
                  </Badge>
                </Table.Td>
              </Table.Tr>
            ))}
            {(!stats?.problematic_macs || stats.problematic_macs.length === 0) && (
              <Table.Tr>
                <Table.Td colSpan={3}>
                  <Text size="sm" c="dimmed" ta="center">No problematic MACs detected</Text>
                </Table.Td>
              </Table.Tr>
            )}
          </Table.Tbody>
        </Table>
      </Paper>
    </Stack>
  );
};

const getTypePercentage = (stats, type) => {
  if (!stats?.by_type || !stats.total) return 0;
  const typeData = stats.by_type.find(t => t.failover_type === type);
  return typeData ? Math.round((typeData.count / stats.total) * 100) : 0;
};

export default FailoverStatistics;
