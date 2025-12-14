/**
 * Predictive Failover Settings Component
 * 
 * Provides UI for configuring predictive failover parameters.
 * 
 * Requirements: 6.1, 6.4, 6.5, 6.6, 6.7
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  Text,
  Title,
  Switch,
  Slider,
  Button,
  Grid,
  Accordion,
  Tooltip,
  ActionIcon,
  Group,
  Stack,
  Select,
  Loader,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import {
  IconRefresh,
  IconDeviceFloppy,
  IconInfoCircle,
} from '@tabler/icons-react';
import API from '../../api';

const PredictiveFailoverSettings = () => {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      setLoading(true);
      const response = await API.get('/api/settings/predictive-failover/');
      setConfig(response.data);
      setHasChanges(false);
    } catch (err) {
      notifications.show({ title: 'Error', message: 'Failed to load configuration', color: 'red' });
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const saveConfig = async () => {
    try {
      setSaving(true);
      await API.put('/api/settings/predictive-failover/', config);
      notifications.show({ title: 'Success', message: 'Settings saved successfully', color: 'green' });
      setHasChanges(false);
    } catch (err) {
      notifications.show({ title: 'Error', message: 'Failed to save configuration', color: 'red' });
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  const resetConfig = async () => {
    try {
      setLoading(true);
      const response = await API.post('/api/settings/predictive-failover/reset/');
      setConfig(response.data);
      notifications.show({ title: 'Success', message: 'Settings reset to defaults', color: 'green' });
      setHasChanges(false);
    } catch (err) {
      notifications.show({ title: 'Error', message: 'Failed to reset configuration', color: 'red' });
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const updateConfig = (key, value) => {
    setConfig(prev => ({ ...prev, [key]: value }));
    setHasChanges(true);
  };

  if (loading || !config) {
    return <Box ta="center" py="xl"><Loader /></Box>;
  }

  return (
    <Box p="md">
      <Group justify="space-between" mb="md">
        <Title order={4}>Predictive Failover Settings</Title>
        <Group>
          <Button variant="outline" leftSection={<IconRefresh size={16} />} onClick={resetConfig}>
            Reset to Defaults
          </Button>
          <Button leftSection={<IconDeviceFloppy size={16} />} onClick={saveConfig} disabled={!hasChanges} loading={saving}>
            Save
          </Button>
        </Group>
      </Group>

      {/* Master Switch */}
      <Card shadow="sm" p="md" mb="md" withBorder>
        <Group>
          <Switch
            checked={config.enabled}
            onChange={(e) => updateConfig('enabled', e.currentTarget.checked)}
            size="lg"
          />
          <Box>
            <Text fw={500}>Enable Predictive Failover</Text>
            <Text size="sm" c="dimmed">When disabled, the system uses reactive failover only</Text>
          </Box>
        </Group>
      </Card>

      {/* Threshold Settings */}
      <Accordion defaultValue="thresholds" mb="md">
        <Accordion.Item value="thresholds">
          <Accordion.Control><Text fw={500}>Threshold Settings</Text></Accordion.Control>
          <Accordion.Panel>
            <Grid>
              <Grid.Col span={{ base: 12, md: 6 }}>
                <Group gap="xs" mb="xs">
                  <Text size="sm">Warmup Threshold: {config.warmup_threshold}</Text>
                  <Tooltip label="Risk score at which backup stream warming begins">
                    <ActionIcon size="xs" variant="subtle"><IconInfoCircle size={14} /></ActionIcon>
                  </Tooltip>
                </Group>
                <Slider
                  value={config.warmup_threshold}
                  onChange={(v) => updateConfig('warmup_threshold', v)}
                  min={40} max={85}
                  marks={[{ value: 40, label: '40' }, { value: 60, label: '60' }, { value: 85, label: '85' }]}
                  mb="lg"
                />
              </Grid.Col>
              <Grid.Col span={{ base: 12, md: 6 }}>
                <Group gap="xs" mb="xs">
                  <Text size="sm">Failover Threshold: {config.failover_threshold}</Text>
                  <Tooltip label="Risk score at which proactive failover triggers">
                    <ActionIcon size="xs" variant="subtle"><IconInfoCircle size={14} /></ActionIcon>
                  </Tooltip>
                </Group>
                <Slider
                  value={config.failover_threshold}
                  onChange={(v) => updateConfig('failover_threshold', v)}
                  min={55} max={95}
                  marks={[{ value: 55, label: '55' }, { value: 85, label: '85' }, { value: 95, label: '95' }]}
                  mb="lg"
                />
              </Grid.Col>
              <Grid.Col span={{ base: 12, md: 6 }}>
                <Text size="sm" mb="xs">Metrics Interval: {config.metrics_interval}s</Text>
                <Slider value={config.metrics_interval} onChange={(v) => updateConfig('metrics_interval', v)} min={1} max={10} mb="lg" />
              </Grid.Col>
              <Grid.Col span={{ base: 12, md: 6 }}>
                <Text size="sm" mb="xs">Cooldown Period: {config.cooldown_period}s</Text>
                <Slider value={config.cooldown_period} onChange={(v) => updateConfig('cooldown_period', v)} min={5} max={300} step={5} mb="lg" />
              </Grid.Col>
            </Grid>
          </Accordion.Panel>
        </Accordion.Item>

        {/* Learning Settings */}
        <Accordion.Item value="learning">
          <Accordion.Control><Text fw={500}>Learning Settings</Text></Accordion.Control>
          <Accordion.Panel>
            <Grid>
              <Grid.Col span={{ base: 12, md: 6 }}>
                <Switch label="Pattern Learning" checked={config.pattern_learning_enabled} onChange={(e) => updateConfig('pattern_learning_enabled', e.currentTarget.checked)} mb="md" />
              </Grid.Col>
              <Grid.Col span={{ base: 12, md: 6 }}>
                <Switch label="Time Pattern Detection" checked={config.time_pattern_enabled} onChange={(e) => updateConfig('time_pattern_enabled', e.currentTarget.checked)} mb="md" />
              </Grid.Col>
              <Grid.Col span={{ base: 12, md: 6 }}>
                <Switch label="Correlation Analysis" checked={config.correlation_analysis_enabled} onChange={(e) => updateConfig('correlation_analysis_enabled', e.currentTarget.checked)} mb="md" />
              </Grid.Col>
              <Grid.Col span={{ base: 12, md: 6 }}>
                <Select
                  label="Learning Rate"
                  value={config.learning_rate}
                  onChange={(v) => updateConfig('learning_rate', v)}
                  data={[{ value: 'slow', label: 'Slow' }, { value: 'normal', label: 'Normal' }, { value: 'fast', label: 'Fast' }]}
                  mb="md"
                />
              </Grid.Col>
              <Grid.Col span={12}>
                <Text size="sm" mb="xs">Pattern Confidence Threshold: {config.pattern_confidence_threshold}%</Text>
                <Slider value={config.pattern_confidence_threshold} onChange={(v) => updateConfig('pattern_confidence_threshold', v)} min={40} max={90} />
              </Grid.Col>
            </Grid>
          </Accordion.Panel>
        </Accordion.Item>

        {/* Metric Weights */}
        <Accordion.Item value="weights">
          <Accordion.Control><Text fw={500}>Metric Weights</Text></Accordion.Control>
          <Accordion.Panel>
            <Grid>
              <Grid.Col span={{ base: 12, md: 6 }}>
                <Text size="sm" mb="xs">Response Time Warning: {config.response_time_warning}ms</Text>
                <Slider value={config.response_time_warning} onChange={(v) => updateConfig('response_time_warning', v)} min={50} max={500} step={10} mb="lg" />
              </Grid.Col>
              <Grid.Col span={{ base: 12, md: 6 }}>
                <Text size="sm" mb="xs">Response Time Critical: {config.response_time_critical}ms</Text>
                <Slider value={config.response_time_critical} onChange={(v) => updateConfig('response_time_critical', v)} min={150} max={1000} step={10} mb="lg" />
              </Grid.Col>
              <Grid.Col span={{ base: 12, md: 6 }}>
                <Text size="sm" mb="xs">Buffer Underrun Weight: {config.buffer_underrun_weight}</Text>
                <Slider value={config.buffer_underrun_weight} onChange={(v) => updateConfig('buffer_underrun_weight', v)} min={15} max={50} mb="lg" />
              </Grid.Col>
              <Grid.Col span={{ base: 12, md: 6 }}>
                <Text size="sm" mb="xs">Bitrate Variance Threshold: {config.bitrate_variance_threshold}%</Text>
                <Slider value={config.bitrate_variance_threshold} onChange={(v) => updateConfig('bitrate_variance_threshold', v)} min={10} max={50} mb="lg" />
              </Grid.Col>
            </Grid>
          </Accordion.Panel>
        </Accordion.Item>

        {/* Optional Modules */}
        <Accordion.Item value="modules">
          <Accordion.Control><Text fw={500}>Optional Modules</Text></Accordion.Control>
          <Accordion.Panel>
            <Grid>
              <Grid.Col span={{ base: 12, md: 6 }}>
                <Switch label="Quality Monitoring (QoS)" checked={config.quality_monitoring_enabled} onChange={(e) => updateConfig('quality_monitoring_enabled', e.currentTarget.checked)} mb="md" />
              </Grid.Col>
              <Grid.Col span={{ base: 12, md: 6 }}>
                <Switch label="Peak Time Awareness" checked={config.peak_time_awareness_enabled} onChange={(e) => updateConfig('peak_time_awareness_enabled', e.currentTarget.checked)} mb="md" />
              </Grid.Col>
              <Grid.Col span={{ base: 12, md: 6 }}>
                <Switch label="Graceful Degradation" checked={config.graceful_degradation_enabled} onChange={(e) => updateConfig('graceful_degradation_enabled', e.currentTarget.checked)} mb="md" />
              </Grid.Col>
              <Grid.Col span={{ base: 12, md: 6 }}>
                <Switch label="Provider Ranking" checked={config.provider_ranking_enabled} onChange={(e) => updateConfig('provider_ranking_enabled', e.currentTarget.checked)} mb="md" />
              </Grid.Col>
            </Grid>
          </Accordion.Panel>
        </Accordion.Item>
      </Accordion>
    </Box>
  );
};

export default PredictiveFailoverSettings;
