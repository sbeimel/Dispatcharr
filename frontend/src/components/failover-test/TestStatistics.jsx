/**
 * Test Statistics Component
 * 
 * Displays failover test statistics.
 * Requirements: 6.1, 6.2, 6.3, 6.4
 */

import React from 'react';
import {
  Box,
  Title,
  Stack,
  Group,
  Button,
  Text,
  Paper,
  Progress,
  SimpleGrid,
  ThemeIcon,
} from '@mantine/core';
import {
  IconRefresh,
  IconDownload,
  IconCheck,
  IconX,
  IconClock,
} from '@tabler/icons-react';

const STRATEGY_COLORS = {
  mac: 'blue',
  portal: 'violet',
  endpoint: 'grape',
  useragent: 'pink',
  stream: 'cyan',
};

const STRATEGY_LABELS = {
  mac: 'MAC',
  portal: 'Portal',
  endpoint: 'Endpoint',
  useragent: 'User-Agent',
  stream: 'Stream',
};

const TestStatistics = ({ statistics, onReset, onExport }) => {
  if (!statistics) {
    return (
      <Box>
        <Title order={4} mb="md">Statistics</Title>
        <Text c="dimmed" size="sm">Loading statistics...</Text>
      </Box>
    );
  }

  const successRate = statistics.total_tests > 0
    ? (statistics.successful_failovers / statistics.total_tests * 100).toFixed(1)
    : 0;

  return (
    <Box>
      <Group justify="space-between" mb="md">
        <Title order={4}>Statistics</Title>
        <Group gap="xs">
          <Button
            size="xs"
            variant="outline"
            leftSection={<IconDownload size={14} />}
            onClick={onExport}
          >
            CSV
          </Button>
          <Button
            size="xs"
            variant="outline"
            color="gray"
            leftSection={<IconRefresh size={14} />}
            onClick={onReset}
          >
            Reset
          </Button>
        </Group>
      </Group>

      <Stack gap="md">
        {/* Overview Stats */}
        <SimpleGrid cols={3}>
          <StatCard
            label="Total Tests"
            value={statistics.total_tests}
            icon={<IconClock size={16} />}
            color="blue"
          />
          <StatCard
            label="Successful"
            value={statistics.successful_failovers}
            icon={<IconCheck size={16} />}
            color="green"
          />
          <StatCard
            label="Failed"
            value={statistics.failed_failovers}
            icon={<IconX size={16} />}
            color="red"
          />
        </SimpleGrid>

        {/* Success Rate */}
        <Paper withBorder p="sm">
          <Group justify="space-between" mb="xs">
            <Text size="sm" fw={500}>Success Rate</Text>
            <Text size="sm" fw={700} c={parseFloat(successRate) >= 80 ? 'green' : 'orange'}>
              {successRate}%
            </Text>
          </Group>
          <Progress
            value={parseFloat(successRate)}
            color={parseFloat(successRate) >= 80 ? 'green' : 'orange'}
            size="lg"
          />
        </Paper>

        {/* Average Time */}
        <Paper withBorder p="sm">
          <Group justify="space-between">
            <Text size="sm" fw={500}>Avg. Failover Time</Text>
            <Text size="sm" fw={700}>
              {statistics.average_failover_time_ms?.toFixed(0) || 0} ms
            </Text>
          </Group>
        </Paper>

        {/* Per-Strategy Stats */}
        {Object.keys(statistics.strategy_stats || {}).length > 0 && (
          <>
            <Text size="sm" fw={500}>Per Strategy</Text>
            <Stack gap="xs">
              {Object.entries(statistics.strategy_stats).map(([strategy, stats]) => (
                <StrategyStatRow
                  key={strategy}
                  strategy={strategy}
                  stats={stats}
                />
              ))}
            </Stack>
          </>
        )}
      </Stack>
    </Box>
  );
};

const StatCard = ({ label, value, icon, color }) => (
  <Paper withBorder p="xs" ta="center">
    <ThemeIcon size="sm" variant="light" color={color} mb={4}>
      {icon}
    </ThemeIcon>
    <Text size="xl" fw={700}>{value}</Text>
    <Text size="xs" c="dimmed">{label}</Text>
  </Paper>
);

const StrategyStatRow = ({ strategy, stats }) => {
  const successRate = stats.attempts > 0
    ? (stats.successes / stats.attempts * 100).toFixed(0)
    : 0;

  return (
    <Paper withBorder p="xs">
      <Group justify="space-between" wrap="nowrap">
        <Group gap="xs">
          <Box
            w={8}
            h={8}
            style={{
              borderRadius: '50%',
              backgroundColor: `var(--mantine-color-${STRATEGY_COLORS[strategy] || 'gray'}-6)`,
            }}
          />
          <Text size="sm" fw={500}>
            {STRATEGY_LABELS[strategy] || strategy}
          </Text>
        </Group>
        <Group gap="md">
          <Text size="xs" c="dimmed">
            {stats.successes}/{stats.attempts}
          </Text>
          <Text size="xs" fw={500} c={parseFloat(successRate) >= 80 ? 'green' : 'orange'}>
            {successRate}%
          </Text>
          <Text size="xs" c="dimmed">
            {stats.avg_time_ms?.toFixed(0) || 0}ms
          </Text>
        </Group>
      </Group>
    </Paper>
  );
};

export default TestStatistics;
