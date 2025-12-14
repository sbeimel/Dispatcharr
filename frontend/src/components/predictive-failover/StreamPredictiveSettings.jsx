/**
 * Stream Predictive Settings Component
 * 
 * Per-stream predictive failover settings.
 * 
 * Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6
 */

import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Typography,
  Box,
  Alert,
  Slider,
  FormControlLabel,
  Switch,
} from '@mui/material';
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

  if (!open) return null;

  return (
    <Dialog open={open} onClose={() => onClose(false)} maxWidth="sm" fullWidth>
      <DialogTitle>
        Predictive Settings: {channelName}
      </DialogTitle>
      <DialogContent>
        {loading ? (
          <Typography>Loading...</Typography>
        ) : error ? (
          <Alert severity="error">{error}</Alert>
        ) : settings && (
          <Box sx={{ pt: 2 }}>
            {/* False Positive Warning */}
            {settings.should_suggest_lower_sensitivity && (
              <Alert severity="warning" sx={{ mb: 2 }}>
                High false positive rate detected ({settings.false_positive_rate?.toFixed(1)}%).
                Consider lowering sensitivity.
              </Alert>
            )}

            {/* Sensitivity Selection */}
            <FormControl fullWidth sx={{ mb: 3 }}>
              <InputLabel>Sensitivity</InputLabel>
              <Select
                value={settings.sensitivity}
                onChange={(e) => updateSetting('sensitivity', e.target.value)}
                label="Sensitivity"
              >
                <MenuItem value="disabled">Disabled</MenuItem>
                <MenuItem value="low">Low (Less sensitive)</MenuItem>
                <MenuItem value="normal">Normal</MenuItem>
                <MenuItem value="high">High (More sensitive)</MenuItem>
              </Select>
              <Typography variant="caption" color="textSecondary" sx={{ mt: 1 }}>
                {settings.sensitivity === 'disabled' && 'Predictive failover disabled for this stream'}
                {settings.sensitivity === 'low' && 'Higher thresholds, fewer false positives'}
                {settings.sensitivity === 'normal' && 'Uses global threshold settings'}
                {settings.sensitivity === 'high' && 'Lower thresholds, faster response'}
              </Typography>
            </FormControl>

            {/* Custom Thresholds Toggle */}
            <FormControlLabel
              control={
                <Switch
                  checked={useCustomThresholds}
                  onChange={(e) => setUseCustomThresholds(e.target.checked)}
                />
              }
              label="Use Custom Thresholds"
              sx={{ mb: 2 }}
            />

            {/* Custom Threshold Sliders */}
            {useCustomThresholds && (
              <Box sx={{ px: 2 }}>
                <Typography gutterBottom>
                  Custom Warmup Threshold: {settings.custom_warmup_threshold || 60}
                </Typography>
                <Slider
                  value={settings.custom_warmup_threshold || 60}
                  onChange={(e, v) => updateSetting('custom_warmup_threshold', v)}
                  min={40}
                  max={85}
                  marks={[
                    { value: 40, label: '40' },
                    { value: 60, label: '60' },
                    { value: 85, label: '85' },
                  ]}
                  sx={{ mb: 3 }}
                />

                <Typography gutterBottom>
                  Custom Failover Threshold: {settings.custom_failover_threshold || 85}
                </Typography>
                <Slider
                  value={settings.custom_failover_threshold || 85}
                  onChange={(e, v) => updateSetting('custom_failover_threshold', v)}
                  min={55}
                  max={95}
                  marks={[
                    { value: 55, label: '55' },
                    { value: 85, label: '85' },
                    { value: 95, label: '95' },
                  ]}
                />
              </Box>
            )}

            {/* Statistics */}
            {settings.total_predictions > 0 && (
              <Box sx={{ mt: 3, p: 2, bgcolor: 'grey.100', borderRadius: 1 }}>
                <Typography variant="subtitle2" gutterBottom>Statistics</Typography>
                <Typography variant="body2">
                  Total Predictions: {settings.total_predictions}
                </Typography>
                <Typography variant="body2">
                  False Positives: {settings.false_positive_count}
                </Typography>
                <Typography variant="body2">
                  False Positive Rate: {settings.false_positive_rate?.toFixed(1)}%
                </Typography>
              </Box>
            )}
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={() => onClose(false)}>Cancel</Button>
        <Button
          onClick={saveSettings}
          variant="contained"
          disabled={saving || loading}
        >
          {saving ? 'Saving...' : 'Save'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default StreamPredictiveSettings;
