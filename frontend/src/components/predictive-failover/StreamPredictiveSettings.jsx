/**
 * Stream Predictive Settings Component
 * 
 * Per-stream predictive failover settings.
 * 
 * Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6
 */

import React, { useState, useEffect } from 'react';
import {
  Modal,
  Button,
  Select,
  Text,
  Box,
  Alert,
  Slider,
  Switch,
  Group,
  Stack,
  Paper,
  Loader,
} from '@mantine/core';
import API from '../../api';

const StreamPredictiveSettings = ({ open, onClose, channelId, channelName }) => {
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [useCustomThresholds, setUseCustomThresholds] = useState(false);

  useEffect(() => {
    if (open && channelId) {
      loadSettings();
    }
  }, [open, channelId]);

  const loadSettings = async () => {
    try {
      setLoading(true);
      const response = await API.get(`/api/streams/${channelId}/predictive-settings/`);
      setSettings(response.data);
      setUseCustomThresholds(
        response.data.custom_warmup_threshold !== null ||
        response.data.custom_failover_threshold !== null
      );
    } catch (err) {
      setError('Failed to load settings');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const saveSettings = async () => {
    try {
      setSaving(true);
      const data = {
        sensitivity: settings.sensitivity,
        custom_warmup_threshold: useCustomThresholds ? settings.custom_warmup_threshold : null,
        custom_failover_threshold: useCustomThresholds ? settings.custom_failover_threshold : null,
      };
      await API.put(`/api/streams/${channelId}/predictive-settings/`, data);
      onClose(true);
    } catch (err) {
      setError('Failed to save settings');
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  const updateSetting = (key, value) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  const getSensitivityDescription = (sensitivity) => {
    switch (sensitivity) {
      case 'disabled': return 'Predictive failover disabled for this stream';
      case 'low': return 'Higher thresholds, fewer false positives';
      case 'normal': return 'Uses global threshold settings';
      case 'high': return 'Lower thresholds, faster response';
      default: return '';
    }
  };

  if (!open) return null;

  return (
    <Modal
      opened={open}
      onClose={() => onClose(false)}
      title={`Predictive Settings: ${channelName}`}
      size="md"
    >
      {loading ? (
        <Box ta="center" py="xl">
          <Loader />
        </Box>
      ) : error ? (
        <Alert color="red">{error}</Alert>
      ) : settings && (
        <Stack gap="md">
          {/* False Positive Warning */}
          {settings.should_suggest_lower_sensitivity && (
            <Alert color="yellow">
              High false positive rate detected ({settings.false_positive_rate?.toFixed(1)}%).
              Consider lowering sensitivity.
            </Alert>
          )}

          {/* Sensitivity Selection */}
          <Select
            label="Sensitivity"
            value={settings.sensitivity}
            onChange={(value) => updateSetting('sensitivity', value)}
            data={[
              { value: 'disabled', label: 'Disabled' },
              { value: 'low', label: 'Low (Less sensitive)' },
              { value: 'normal', label: 'Normal' },
              { value: 'high', label: 'High (More sensitive)' },
            ]}
            description={getSensitivityDescription(settings.sensitivity)}
          />

          {/* Custom Thresholds Toggle */}
          <Switch
            label="Use Custom Thresholds"
            checked={useCustomThresholds}
            onChange={(e) => setUseCustomThresholds(e.currentTarget.checked)}
          />

          {/* Custom Threshold Sliders */}
          {useCustomThresholds && (
            <Paper withBorder p="md">
              <Stack gap="lg">
                <Box>
                  <Text size="sm" mb="xs">
                    Custom Warmup Threshold: {settings.custom_warmup_threshold || 60}
                  </Text>
                  <Slider
                    value={settings.custom_warmup_threshold || 60}
                    onChange={(v) => updateSetting('custom_warmup_threshold', v)}
                    min={40}
                    max={85}
                    marks={[
                      { value: 40, label: '40' },
                      { value: 60, label: '60' },
                      { value: 85, label: '85' },
                    ]}
                  />
                </Box>

                <Box>
                  <Text size="sm" mb="xs">
                    Custom Failover Threshold: {settings.custom_failover_threshold || 85}
                  </Text>
                  <Slider
                    value={settings.custom_failover_threshold || 85}
                    onChange={(v) => updateSetting('custom_failover_threshold', v)}
                    min={55}
                    max={95}
                    marks={[
                      { value: 55, label: '55' },
                      { value: 85, label: '85' },
                      { value: 95, label: '95' },
                    ]}
                  />
                </Box>
              </Stack>
            </Paper>
          )}

          {/* Statistics */}
          {settings.total_predictions > 0 && (
            <Paper withBorder p="md" bg="gray.1">
              <Text fw={500} mb="xs">Statistics</Text>
              <Text size="sm">Total Predictions: {settings.total_predictions}</Text>
              <Text size="sm">False Positives: {settings.false_positive_count}</Text>
              <Text size="sm">False Positive Rate: {settings.false_positive_rate?.toFixed(1)}%</Text>
            </Paper>
          )}

          {/* Actions */}
          <Group justify="flex-end" mt="md">
            <Button variant="outline" onClick={() => onClose(false)}>
              Cancel
            </Button>
            <Button onClick={saveSettings} loading={saving}>
              Save
            </Button>
          </Group>
        </Stack>
      )}
    </Modal>
  );
};

export default StreamPredictiveSettings;
