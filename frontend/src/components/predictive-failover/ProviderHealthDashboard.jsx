/**
 * Provider Health Dashboard Component
 * 
 * Displays health scores for providers and MAC addresses.
 * 
 * Requirements: 16.4, 16.5, 16.6, 16.7
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Card,
  Text,
  Title,
  Grid,
  Progress,
  Badge,
  Table,
  Paper,
  Alert,
  ActionIcon,
  Tooltip,
  Collapse,
  List,
  Divider,
  Group,
  Stack,
  ThemeIcon,
  Loader,
} from '@mantine/core';
import {
  IconChevronDown,
  IconChevronUp,
  IconAlertTriangle,
  IconCircleCheck,
  IconCircleX,
  IconTrendingUp,
  IconTrendingDown,
  IconRefresh,
} from '@tabler/icons-react';
import API from '../../api';

const ProviderHealthDashboard = () => {
  const [healthData, setHealthData] = useState({});
  const [problemMacs, setProblemMacs] = useState([]);
  const [topPerformers, setTopPerformers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedProviders, setExpandedProviders] = useState({});

  const fetchHealthData = useCallback(async () => {
    try {
      setLoading(true);
      const response = await API.get('/api/predictive-failover/provider-health/');
      setHealthData(response.data.providers || {});
      setProblemMacs(response.data.problem_macs || []);
      setTopPerformers(response.data.top_performers || []);
      setError(null);
    } catch (err) {
      setError('Fehler beim Laden der Health-Daten');
      console.error('Error fetching health data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHealthData();
    const interval = setInterval(fetchHealthData, 30000);
    return () => clearInterval(interval);
  }, [fetchHealthData]);

  const getHealthColor = (score) => {
    if (score >= 80) return 'green';
    if (score >= 50) return 'yellow';
    return 'red';
  };

  const getHealthIcon = (score) => {
    if (score >= 80) return <IconCircleCheck size={16} color="green" />;
    if (score >= 50) return <IconAlertTriangle size={16} color="orange" />;
    return <IconCircleX size={16} color="red" />;
  };

  const toggleProvider = (accountId) => {
    setExpandedProviders(prev => ({ ...prev, [accountId]: !prev[accountId] }));
  };

  const formatResponseTime = (ms) => ms ? `${Math.round(ms)}ms` : '-';
  const formatUptime = (percent) => (percent !== undefined && percent !== null) ? `${percent.toFixed(1)}%` : '-';

  if (loading && Object.keys(healthData).length === 0) {
    return <Box ta="center" py="xl"><Loader /><Text mt="md">Lade Health-Daten...</Text></Box>;
  }

  return (
    <Box p="md">
      <Group justify="space-between" mb="md">
        <Title order={4}>Provider Health Dashboard</Title>
        <ActionIcon variant="subtle" onClick={fetchHealthData} disabled={loading}>
          <IconRefresh size={18} />
        </ActionIcon>
      </Group>

      {error && <Alert color="red" mb="md">{error}</Alert>}

      {problemMacs.length > 0 && (
        <Alert color="yellow" title="Problematische MAC-Adressen" mb="md">
          <Text size="sm">{problemMacs.length} MAC-Adresse(n) mit niedrigem Health Score gefunden.</Text>
          <List size="sm" mt="xs">
            {problemMacs.slice(0, 3).map((mac, idx) => (
              <List.Item key={idx} icon={<IconCircleX size={14} color="red" />}>
                {mac.mac_address?.substring(0, 12)}... - Score: {mac.health_score}, Fehler: {mac.failure_count}
              </List.Item>
            ))}
          </List>
        </Alert>
      )}

      <Grid>
        <Grid.Col span={{ base: 12, md: 8 }}>
          <Title order={5} mb="sm">Provider Übersicht</Title>
          {Object.entries(healthData).map(([accountId, provider]) => (
            <Card key={accountId} shadow="sm" p="md" mb="md" withBorder>
              <Group justify="space-between">
                <Group>
                  {getHealthIcon(provider.health_score?.score || 0)}
                  <Box>
                    <Text fw={500}>{provider.account_name || `Provider ${accountId}`}</Text>
                    <Text size="xs" c="dimmed">Account ID: {accountId}</Text>
                  </Box>
                </Group>
                <Group>
                  <Badge color={getHealthColor(provider.health_score?.score || 0)}>
                    Score: {provider.health_score?.score || 0}
                  </Badge>
                  <ActionIcon variant="subtle" onClick={() => toggleProvider(accountId)}>
                    {expandedProviders[accountId] ? <IconChevronUp size={16} /> : <IconChevronDown size={16} />}
                  </ActionIcon>
                </Group>
              </Group>

              <Grid mt="md">
                <Grid.Col span={4}>
                  <Text size="xs" c="dimmed">Uptime</Text>
                  <Text size="sm">{formatUptime(provider.health_score?.uptime_percent)}</Text>
                </Grid.Col>
                <Grid.Col span={4}>
                  <Text size="xs" c="dimmed">Fehler</Text>
                  <Text size="sm">{provider.health_score?.failure_count || 0}</Text>
                </Grid.Col>
                <Grid.Col span={4}>
                  <Text size="xs" c="dimmed">Ø Response</Text>
                  <Text size="sm">{formatResponseTime(provider.health_score?.avg_response_time_ms)}</Text>
                </Grid.Col>
              </Grid>

              <Collapse in={expandedProviders[accountId]}>
                <Divider my="md" />
                <Text size="sm" fw={500} mb="xs">
                  MAC-Adressen ({Object.keys(provider.mac_health_scores || {}).length})
                </Text>
                <Paper withBorder>
                  <Table striped highlightOnHover>
                    <Table.Thead>
                      <Table.Tr>
                        <Table.Th>MAC-Adresse</Table.Th>
                        <Table.Th>Score</Table.Th>
                        <Table.Th>Uptime</Table.Th>
                        <Table.Th>Fehler</Table.Th>
                        <Table.Th>Ø Response</Table.Th>
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {Object.entries(provider.mac_health_scores || {}).map(([mac, score]) => (
                        <Table.Tr key={mac}>
                          <Table.Td>
                            <Group gap="xs">
                              {getHealthIcon(score.score)}
                              <Text size="sm">{mac.substring(0, 12)}...</Text>
                            </Group>
                          </Table.Td>
                          <Table.Td><Badge size="sm" color={getHealthColor(score.score)}>{score.score}</Badge></Table.Td>
                          <Table.Td><Text size="sm">{formatUptime(score.uptime_percent)}</Text></Table.Td>
                          <Table.Td><Text size="sm">{score.failure_count}</Text></Table.Td>
                          <Table.Td><Text size="sm">{formatResponseTime(score.avg_response_time_ms)}</Text></Table.Td>
                        </Table.Tr>
                      ))}
                    </Table.Tbody>
                  </Table>
                </Paper>
              </Collapse>
            </Card>
          ))}

          {Object.keys(healthData).length === 0 && !loading && (
            <Alert color="blue">Keine Provider-Daten verfügbar.</Alert>
          )}
        </Grid.Col>

        <Grid.Col span={{ base: 12, md: 4 }}>
          <Card shadow="sm" p="md" withBorder>
            <Group mb="sm">
              <IconTrendingUp size={18} color="green" />
              <Title order={5}>Top Performer</Title>
            </Group>
            {topPerformers.length > 0 ? (
              <Stack gap="xs">
                {topPerformers.map((performer, idx) => (
                  <Group key={idx} justify="space-between">
                    <Group gap="xs">
                      <Badge size="sm" color={idx === 0 ? 'green' : 'gray'}>#{idx + 1}</Badge>
                      <Text size="sm">{performer.mac_address?.substring(0, 12)}...</Text>
                    </Group>
                    <Text size="xs" c="dimmed">Score: {performer.health_score}</Text>
                  </Group>
                ))}
              </Stack>
            ) : (
              <Text size="sm" c="dimmed">Noch keine Daten verfügbar</Text>
            )}
          </Card>

          <Card shadow="sm" p="md" mt="md" withBorder>
            <Group mb="sm">
              <IconTrendingDown size={18} color="red" />
              <Title order={5}>Problem MACs</Title>
            </Group>
            {problemMacs.length > 0 ? (
              <Stack gap="xs">
                {problemMacs.map((mac, idx) => (
                  <Box key={idx}>
                    <Group gap="xs">
                      <IconCircleX size={14} color="red" />
                      <Text size="sm">{mac.mac_address?.substring(0, 12)}...</Text>
                    </Group>
                    <Text size="xs" c="dimmed">Score: {mac.health_score}</Text>
                    <Text size="xs" c="red">Empfehlung: MAC ersetzen</Text>
                  </Box>
                ))}
              </Stack>
            ) : (
              <Text size="sm" c="dimmed">Keine problematischen MACs gefunden</Text>
            )}
          </Card>
        </Grid.Col>
      </Grid>
    </Box>
  );
};

export default ProviderHealthDashboard;
