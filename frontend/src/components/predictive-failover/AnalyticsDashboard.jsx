/**
 * Analytics Dashboard Component
 * 
 * Displays analytics for the Predictive Failover System.
 * 
 * Requirements: 19.1, 19.2, 19.3, 19.4, 19.5, 19.6
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Card,
  Text,
  Title,
  Grid,
  Button,
  Table,
  Paper,
  Alert,
  Badge,
  Select,
  Tooltip,
  ActionIcon,
  Group,
  Stack,
  SimpleGrid,
  Loader,
} from '@mantine/core';
import {
  IconTrendingUp,
  IconTrendingDown,
  IconMinus,
  IconDownload,
  IconRefresh,
  IconChartBar,
} from '@tabler/icons-react';
import API from '../../api';

const AnalyticsDashboard = () => {
  const [summary, setSummary] = useState(null);
  const [comparison, setComparison] = useState([]);
  const [heatmap, setHeatmap] = useState(null);
  const [selectedProvider, setSelectedProvider] = useState('');
  const [trend, setTrend] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [summaryRes, comparisonRes, heatmapRes] = await Promise.all([
        API.get('/api/predictive-failover/analytics/summary/'),
        API.get('/api/predictive-failover/analytics/comparison/'),
        API.get('/api/predictive-failover/analytics/heatmap/'),
      ]);
      
      setSummary(summaryRes.data);
      setComparison(comparisonRes.data || []);
      setHeatmap(heatmapRes.data);
      setError(null);
    } catch (err) {
      setError('Fehler beim Laden der Analytics-Daten');
      console.error('Error fetching analytics:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchTrend = useCallback(async (accountId) => {
    if (!accountId) return;
    try {
      const res = await API.get(`/api/predictive-failover/analytics/trend/?account_id=${accountId}`);
      setTrend(res.data || []);
    } catch (err) {
      console.error('Error fetching trend:', err);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    if (selectedProvider) {
      fetchTrend(selectedProvider);
    }
  }, [selectedProvider, fetchTrend]);

  const handleExport = async (format) => {
    try {
      const res = await API.get(`/api/predictive-failover/analytics/export/?format=${format}`, {
        responseType: format === 'csv' ? 'blob' : 'json',
      });
      
      const blob = new Blob([format === 'csv' ? res.data : JSON.stringify(res.data, null, 2)], {
        type: format === 'csv' ? 'text/csv' : 'application/json',
      });
      
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `predictive-analytics.${format}`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Export error:', err);
    }
  };

  const getTrendIcon = (direction) => {
    switch (direction) {
      case 'up': return <IconTrendingUp size={16} color="green" />;
      case 'down': return <IconTrendingDown size={16} color="red" />;
      default: return <IconMinus size={16} />;
    }
  };

  const getHeatmapColor = (value, maxValue) => {
    if (maxValue === 0) return 'rgba(76, 175, 80, 0.1)';
    const intensity = value / maxValue;
    if (intensity > 0.7) return 'rgba(244, 67, 54, 0.8)';
    if (intensity > 0.4) return 'rgba(255, 152, 0, 0.6)';
    if (intensity > 0.1) return 'rgba(255, 235, 59, 0.4)';
    return 'rgba(76, 175, 80, 0.1)';
  };

  if (loading && !summary) {
    return <Box ta="center" py="xl"><Loader /><Text mt="md">Lade Analytics...</Text></Box>;
  }

  return (
    <Box p="md">
      <Group justify="space-between" mb="md">
        <Group>
          <IconChartBar size={24} />
          <Title order={4}>Analytics Dashboard</Title>
        </Group>
        <Group>
          <Button.Group>
            <Button variant="outline" size="xs" leftSection={<IconDownload size={14} />} onClick={() => handleExport('json')}>
              JSON
            </Button>
            <Button variant="outline" size="xs" leftSection={<IconDownload size={14} />} onClick={() => handleExport('csv')}>
              CSV
            </Button>
          </Button.Group>
          <ActionIcon variant="subtle" onClick={fetchData} disabled={loading}>
            <IconRefresh size={18} />
          </ActionIcon>
        </Group>
      </Group>

      {error && <Alert color="red" mb="md">{error}</Alert>}

      {summary && (
        <SimpleGrid cols={{ base: 2, md: 4 }} mb="md">
          <Card shadow="sm" p="md" withBorder>
            <Text size="sm" c="dimmed">Provider</Text>
            <Title order={2}>{summary.total_providers}</Title>
          </Card>
          <Card shadow="sm" p="md" withBorder>
            <Text size="sm" c="dimmed">Ø Health Score</Text>
            <Title order={2}>{summary.average_health_score}</Title>
          </Card>
          <Card shadow="sm" p="md" withBorder>
            <Text size="sm" c="dimmed">Fehler (24h)</Text>
            <Title order={2} c="red">{summary.failures_last_24h}</Title>
          </Card>
          <Card shadow="sm" p="md" withBorder>
            <Text size="sm" c="dimmed">Problem MACs</Text>
            <Title order={2} c="yellow">{summary.problem_macs_count}</Title>
          </Card>
        </SimpleGrid>
      )}

      <Grid>
        <Grid.Col span={{ base: 12, md: 7 }}>
          <Card shadow="sm" p="md" withBorder>
            <Title order={5} mb="sm">Portal Vergleich</Title>
            <Paper withBorder>
              <Table striped highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Provider</Table.Th>
                    <Table.Th>Score</Table.Th>
                    <Table.Th>Uptime</Table.Th>
                    <Table.Th>Fehler</Table.Th>
                    <Table.Th>Trend</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {comparison.map((provider) => (
                    <Table.Tr key={provider.account_id}>
                      <Table.Td>{provider.account_name || `Provider ${provider.account_id}`}</Table.Td>
                      <Table.Td>
                        <Badge size="sm" color={provider.health_score >= 80 ? 'green' : provider.health_score >= 50 ? 'yellow' : 'red'}>
                          {provider.health_score}
                        </Badge>
                      </Table.Td>
                      <Table.Td><Text size="sm">{provider.uptime_percent?.toFixed(1)}%</Text></Table.Td>
                      <Table.Td><Text size="sm">{provider.failure_count}</Text></Table.Td>
                      <Table.Td>
                        <Tooltip label={`Trend: ${provider.trend_direction}`}>
                          {getTrendIcon(provider.trend_direction)}
                        </Tooltip>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Paper>
          </Card>
        </Grid.Col>

        <Grid.Col span={{ base: 12, md: 5 }}>
          <Card shadow="sm" p="md" withBorder>
            <Title order={5} mb="sm">Fehler Heatmap (7 Tage)</Title>
            {heatmap && (
              <Box style={{ overflowX: 'auto' }}>
                <Table>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th></Table.Th>
                      {[0, 4, 8, 12, 16, 20].map(h => (
                        <Table.Th key={h} style={{ fontSize: '0.7rem', padding: '4px', textAlign: 'center' }}>
                          {h}:00
                        </Table.Th>
                      ))}
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {heatmap.days?.map((day, dayIdx) => (
                      <Table.Tr key={day}>
                        <Table.Td style={{ fontSize: '0.7rem', padding: '4px' }}>{day.substring(0, 3)}</Table.Td>
                        {[0, 4, 8, 12, 16, 20].map(h => (
                          <Table.Td
                            key={h}
                            style={{
                              backgroundColor: getHeatmapColor(heatmap.heatmap?.[dayIdx]?.[h] || 0, heatmap.max_value || 1),
                              padding: '4px',
                              fontSize: '0.7rem',
                              textAlign: 'center',
                            }}
                          >
                            {heatmap.heatmap?.[dayIdx]?.[h] || 0}
                          </Table.Td>
                        ))}
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              </Box>
            )}
          </Card>
        </Grid.Col>

        <Grid.Col span={12}>
          <Card shadow="sm" p="md" withBorder>
            <Group justify="space-between" mb="md">
              <Title order={5}>Health Score Trend</Title>
              <Select
                size="sm"
                placeholder="Provider wählen"
                value={selectedProvider}
                onChange={setSelectedProvider}
                data={comparison.map((p) => ({
                  value: String(p.account_id),
                  label: p.account_name || `Provider ${p.account_id}`,
                }))}
                w={200}
              />
            </Group>
            
            {trend.length > 0 ? (
              <Group gap="xs" wrap="wrap">
                {trend.map((day) => (
                  <Tooltip
                    key={day.date}
                    label={`Min: ${day.min_score}, Max: ${day.max_score}, Samples: ${day.sample_count}`}
                  >
                    <Stack gap={2} align="center" w={30}>
                      <Box
                        style={{
                          width: 20,
                          height: `${day.avg_score * 0.5}px`,
                          backgroundColor: day.avg_score >= 80 ? 'green' : day.avg_score >= 50 ? 'orange' : 'red',
                          borderRadius: 4,
                        }}
                      />
                      <Text size="xs">{day.date.substring(5)}</Text>
                    </Stack>
                  </Tooltip>
                ))}
              </Group>
            ) : (
              <Text c="dimmed">Wählen Sie einen Provider um den Trend anzuzeigen</Text>
            )}
          </Card>
        </Grid.Col>
      </Grid>
    </Box>
  );
};

export default AnalyticsDashboard;
