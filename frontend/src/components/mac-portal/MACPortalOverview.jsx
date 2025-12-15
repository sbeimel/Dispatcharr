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
  Grid,
  Badge,
  Progress,
  ActionIcon,
  Tooltip,
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
import { notifications } from '@mantine/notifications';
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

// API Base URL
const API_BASE = '/api/mac-portal';

// Add a mock data fallback for development
const MOCK_DATA = {
  portals: [
    {
      id: 1,
      name: 'Main Portal',
      status: 'online',
      macs: [
        { id: 1, address: '00:1A:79:XX:XX:XX', status: 'active', streams: 5, maxStreams: 10 },
        { id: 2, address: '00:1A:79:XX:XX:XY', status: 'inactive', streams: 0, maxStreams: 10 },
      ],
      healthScore: 85,
      expiryDays: 30,
    },
  ],
  stats: {
    totalPortals: 1,
    onlinePortals: 1,
    totalMACs: 2,
    activeMACs: 1,
    totalStreams: 5,
    maxStreams: 20,
  },
};

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
            {portal.type || 'Unknown'}
          </Badge>
        </Group>
        <Group gap="xs">
          <Badge color="green" variant="light">
            {portal.available_count} / {portal.mac_count} MACs
          </Badge>
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
              {portal.macs.map((mac) => (
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
                    <HealthScore score={mac.health_score} />
                  </Table.Td>
                  <Table.Td>
                    <ExpiryCountdown days={mac.days_until_expiry} />
                  </Table.Td>
                  <Table.Td>
                    <Group gap={4}>
                      <IconDeviceTv size={14} />
                      <Text size="sm">
                        {mac.current_streams}/{mac.max_connections}
                      </Text>
                    </Group>
                  </Table.Td>
                  <Table.Td>
                    {mac.activity_level !== null ? (
                      <Badge size="sm" variant="outline">
                        Level {mac.activity_level}
                      </Badge>
                    ) : (
                      <Text size="sm" c="dimmed">-</Text>
                    )}
                  </Table.Td>
                  <Table.Td>
                    {mac.watchdog_timeout !== null ? (
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
 * Hauptkomponente: MAC Portal Overview
 */
const MACPortalOverview = () => {
  const [portals, setPortals] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [useMockData, setUseMockData] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Try to fetch real data first
      try {
        // Fetch portals data
        const portalsRes = await fetch(`${API_BASE}/portals`);
        if (!portalsRes.ok) throw new Error('Failed to fetch portals');
        const portalsData = await portalsRes.json();
        
        // Fetch stats
        const statsRes = await fetch(`${API_BASE}/stats`);
        if (!statsRes.ok) throw new Error('Failed to fetch stats');
        const statsData = await statsRes.json();
        
        setPortals(portalsData);
        setStats(statsData);
        setUseMockData(false);
      } catch (err) {
        console.error('Error fetching real data, falling back to mock data:', err);
        throw err; // Will be caught by the outer catch
      }
    } catch (err) {
      console.error('Error in fetchData:', err);
      setError(err.message || 'Failed to load data');
      
      // Fallback to mock data in development
      if (process.env.NODE_ENV === 'development' || process.env.NODE_ENV === 'production') {
        console.warn('Using mock data due to API error');
        setPortals(MOCK_DATA.portals);
        setStats(MOCK_DATA.stats);
        setUseMockData(true);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await fetch(`${API_BASE}/overview/refresh-status/`, {
        method: 'POST',
      });
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

  if (error && !useMockData) {
    return (
      <Container size="lg" py="xl">
        <Alert 
          title="Error loading data" 
          color="red" 
          variant="filled"
          icon={<IconAlertTriangle size={24} />}
          mb="md"
        >
          {error}
          <Text mt="sm">
            {useMockData 
              ? 'Showing mock data for demonstration.' 
              : 'Please check your connection and try again.'}
          </Text>
          <Button 
            onClick={fetchData} 
            leftIcon={<IconRefresh size={16} />} 
            mt="md"
            variant="white"
          >
            Retry
          </Button>
        </Alert>
      </Container>
    );
  }

  if (useMockData) {
    return (
      <Container size="lg" py="xl">
        <Alert 
          title="Demo Mode" 
          color="yellow" 
          mb="md"
          icon={<IconAlertTriangle size={24} />}
        >
          <Text>This is a demo with mock data. The MAC Portal API is not available.</Text>
          <Text mt="xs">To use real data, ensure the backend API is running and accessible.</Text>
        </Alert>
        {renderContent()}
      </Container>
    );
  }

  const stats = stats || {};
  const portals = portals || [];
  const portals = data?.portals || [];

  const healthColor = stats.avg_health_score >= 80 ? 'green' : stats.avg_health_score >= 50 ? 'yellow' : 'red';

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
