/**
 * MAC Portal Overview - Zentrale Übersichtsseite für alle MAC Portale.
 * 
 * Zeigt:
 * - Alle Portale mit Status (Online/Offline)
 * - Alle MACs pro Portal mit Details
 * - Activity Level, Watchdog Timeout, Max Streams
 * - Aggregierte Statistiken
 * - Health Scores und Expiry Countdown
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Card,
  Text,
  Title,
  Badge,
  Progress,
  ActionIcon,
  Table,
  Paper,
  Collapse,
  Alert,
  Button,
  Loader,
  Group,
  Stack,
  SimpleGrid,
  ThemeIcon,
  Center,
  Container,
} from '@mantine/core';
import {
  IconRefresh,
  IconChevronDown,
  IconChevronUp,
  IconCircleCheck,
  IconCircleX,
  IconAlertTriangle,
  IconClock,
  IconActivity,
  IconDeviceTv,
  IconHeartbeat,
} from '@tabler/icons-react';
import API from '../../api';

// API Base URL
const API_BASE = '/api/mac-portal';

/**
 * Status Badge Komponente
 */
const StatusBadge = ({ status }) => {
  const statusConfig = {
    active: { color: 'green', label: 'Available' },
    in_use: { color: 'blue', label: 'In Use' },
    cooldown: { color: 'yellow', label: 'Cooldown' },
    expired: { color: 'red', label: 'Expired' },
    blocked: { color: 'red', label: 'Blocked' },
    unknown: { color: 'gray', label: 'Unknown' },
  };

  const config = statusConfig[status] || statusConfig.unknown;

  return (
    <Badge size="sm" color={config.color} variant="outline">
      {config.label}
    </Badge>
  );
};

/**
 * Health Score Anzeige
 */
const HealthScore = ({ score }) => {
  const getColor = (s) => {
    if (s >= 80) return 'green';
    if (s >= 50) return 'yellow';
    return 'red';
  };

  return (
    <Group gap="xs">
      <Progress
        value={score}
        color={getColor(score)}
        size="sm"
        w={60}
        radius="xl"
      />
      <Text size="sm" c="dimmed">
        {score}%
      </Text>
    </Group>
  );
};

/**
 * Expiry Countdown Anzeige
 */
const ExpiryCountdown = ({ days }) => {
  if (days === null || days === undefined) {
    return <Text size="sm" c="dimmed">-</Text>;
  }

  const getColor = () => {
    if (days <= 0) return 'red';
    if (days <= 7) return 'yellow';
    return 'green';
  };

  const getText = () => {
    if (days <= 0) return 'Expired';
    if (days === 1) return '1 day';
    return `${days} days`;
  };

  return (
    <Badge size="sm" color={getColor()} variant="outline" leftSection={<IconClock size={12} />}>
      {getText()}
    </Badge>
  );
};

/**
 * Portal Card Komponente
 */
const PortalCard = ({ portal, onRefresh }) => {
  const [expanded, setExpanded] = useState(false);

  const isOnline = portal.status === 'online';

  return (
    <Card shadow="sm" p="md" mb="md" withBorder>
      {/* Header */}
      <Group justify="space-between" mb="sm">
        <Group gap="sm">
          <ThemeIcon color={isOnline ? 'green' : 'red'} variant="light" size="sm">
            {isOnline ? <IconCircleCheck size={16} /> : <IconCircleX size={16} />}
          </ThemeIcon>
          <Title order={5}>{portal.name}</Title>
          <Badge size="sm" variant="outline">
            {portal.portal_type || portal.type || 'Unknown'}
          </Badge>
          {portal.portal_version && portal.portal_version !== 'unknown' && (
            <Badge size="sm" variant="light" color="blue">
              v{portal.portal_version}
            </Badge>
          )}
        </Group>
        <Group gap="xs">
          <Badge color="green" variant="light">
            {portal.available_count} / {portal.mac_count} MACs
          </Badge>
          {portal.max_connections && (
            <Badge color="cyan" variant="light" leftSection={<IconDeviceTv size={12} />}>
              Max {portal.max_connections} Streams
            </Badge>
          )}
          <ActionIcon variant="subtle" onClick={() => setExpanded(!expanded)}>
            {expanded ? <IconChevronUp size={16} /> : <IconChevronDown size={16} />}
          </ActionIcon>
        </Group>
      </Group>

      {/* URL */}
      <Text size="sm" c="dimmed" mb="sm">
        {portal.url}
      </Text>

      {/* MAC Liste (expandierbar) */}
      <Collapse in={expanded}>
        <Paper withBorder mt="sm">
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>MAC Address</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Health</Table.Th>
                <Table.Th>Expiry</Table.Th>
                <Table.Th>Streams</Table.Th>
                <Table.Th>Activity</Table.Th>
                <Table.Th>Watchdog</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {(portal.macs || []).map((mac) => (
                <Table.Tr key={mac.id}>
                  <Table.Td>
                    <Text size="sm" ff="monospace">
                      {mac.mac_address}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <StatusBadge status={mac.status} />
                  </Table.Td>
                  <Table.Td>
                    <HealthScore score={mac.health_score || 0} />
                  </Table.Td>
                  <Table.Td>
                    <ExpiryCountdown days={mac.days_until_expiry} />
                  </Table.Td>
                  <Table.Td>
                    <Group gap={4}>
                      <IconDeviceTv size={14} />
                      <Text size="sm">
                        {mac.current_streams || 0}/{mac.max_connections || 1}
                      </Text>
                    </Group>
                  </Table.Td>
                  <Table.Td>
                    {mac.activity_level !== null && mac.activity_level !== undefined ? (
                      <Badge size="sm" variant="outline">
                        Level {mac.activity_level}
                      </Badge>
                    ) : (
                      <Text size="sm" c="dimmed">-</Text>
                    )}
                  </Table.Td>
                  <Table.Td>
                    {mac.watchdog_timeout !== null && mac.watchdog_timeout !== undefined ? (
                      <Text size="sm">{mac.watchdog_timeout}s</Text>
                    ) : (
                      <Text size="sm" c="dimmed">-</Text>
                    )}
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Paper>
      </Collapse>
    </Card>
  );
};

/**
 * Statistik Card Komponente
 */
const StatCard = ({ title, value, icon, color = 'blue', subtitle }) => (
  <Card shadow="sm" p="md" withBorder>
    <Group justify="space-between" align="flex-start">
      <Stack gap={4}>
        <Text size="sm" c="dimmed">
          {title}
        </Text>
        <Title order={2} c={color}>
          {value}
        </Title>
        {subtitle && (
          <Text size="xs" c="dimmed">
            {subtitle}
          </Text>
        )}
      </Stack>
      <ThemeIcon color={color} variant="light" size="lg">
        {icon}
      </ThemeIcon>
    </Group>
  </Card>
);

/**
 * Hauptkomponente: MAC Portal Overview
 */
const MACPortalOverview = () => {
  const [data, setData] = useState({ portals: [], statistics: {} });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Get auth token for authenticated request
      const token = await API.getAuthToken();
      const response = await fetch(`${API_BASE}/overview/`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const contentType = response.headers.get('content-type');
      if (!contentType || !contentType.includes('application/json')) {
        throw new Error('Server returned non-JSON response');
      }
      
      const result = await response.json();
      setData(result);
    } catch (err) {
      console.error('Error fetching MAC portal overview:', err);
      setError(err.message || 'Failed to load data');
    } finally {
      setLoading(false);
    }
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      // Get auth token for authenticated request
      const token = await API.getAuthToken();
      await fetch(`${API_BASE}/overview/refresh-status/`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      // Wait a bit for the refresh to complete
      setTimeout(() => {
        fetchData();
        setRefreshing(false);
      }, 2000);
    } catch (err) {
      console.error('Error refreshing status:', err);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  if (loading) {
    return (
      <Container size="lg" py="xl">
        <Center style={{ height: '50vh' }}>
          <Stack align="center">
            <Loader size="xl" />
            <Text size="lg" mt="md">Loading MAC Portal data...</Text>
          </Stack>
        </Center>
      </Container>
    );
  }

  if (error) {
    return (
      <Container size="lg" py="xl">
        <Alert 
          title="Error loading MAC portal overview" 
          color="red" 
          variant="filled"
          icon={<IconAlertTriangle size={24} />}
          mb="md"
        >
          {error}
          <Button 
            onClick={fetchData} 
            leftSection={<IconRefresh size={16} />} 
            mt="md"
            variant="white"
          >
            Retry
          </Button>
        </Alert>
      </Container>
    );
  }

  const stats = data.statistics || {};
  const portals = data.portals || [];
  const healthColor = (stats.avg_health_score || 0) >= 80 ? 'green' : (stats.avg_health_score || 0) >= 50 ? 'yellow' : 'red';

  return (
    <Box p="md">
      {/* Header */}
      <Group justify="space-between" mb="md">
        <Title order={3}>MAC Portal Overview</Title>
        <Button
          variant="outline"
          leftSection={refreshing ? <Loader size={16} /> : <IconRefresh size={16} />}
          onClick={handleRefresh}
          disabled={refreshing}
        >
          {refreshing ? 'Refreshing...' : 'Refresh Status'}
        </Button>
      </Group>

      {/* Statistiken */}
      <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} mb="md">
        <StatCard
          title="Total Portals"
          value={stats.total_portals || 0}
          icon={<IconActivity size={20} />}
          color="blue"
          subtitle={`${stats.online_portals || 0} online`}
        />
        <StatCard
          title="Total MACs"
          value={stats.total_macs || 0}
          icon={<IconDeviceTv size={20} />}
          color="cyan"
          subtitle={`${stats.available_macs || 0} available`}
        />
        <StatCard
          title="Avg Health Score"
          value={`${stats.avg_health_score || 0}%`}
          icon={<IconHeartbeat size={20} />}
          color={healthColor}
        />
        <StatCard
          title="Failovers (24h)"
          value={stats.total_failovers_24h || 0}
          icon={<IconAlertTriangle size={20} />}
          color="yellow"
          subtitle={`${stats.expiring_soon || 0} expiring soon`}
        />
      </SimpleGrid>

      {/* Status Übersicht */}
      <Group gap="xs" mb="md">
        <Badge leftSection={<IconCircleCheck size={12} />} color="green" variant="outline">
          {stats.available_macs || 0} Available
        </Badge>
        <Badge leftSection={<IconDeviceTv size={12} />} color="blue" variant="outline">
          {stats.in_use_macs || 0} In Use
        </Badge>
        <Badge leftSection={<IconClock size={12} />} color="yellow" variant="outline">
          {stats.cooldown_macs || 0} Cooldown
        </Badge>
        <Badge leftSection={<IconCircleX size={12} />} color="red" variant="outline">
          {stats.expired_macs || 0} Expired
        </Badge>
      </Group>

      {/* Portal Liste */}
      {portals.length === 0 ? (
        <Alert color="blue">
          No MAC portals configured. Add a MAC/STB portal account to see the overview.
        </Alert>
      ) : (
        portals.map((portal) => (
          <PortalCard
            key={portal.id}
            portal={portal}
            onRefresh={fetchData}
          />
        ))
      )}
    </Box>
  );
};

export default MACPortalOverview;
