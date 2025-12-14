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
  CardContent,
  Typography,
  Switch,
  Slider,
  TextField,
  Button,
  Grid,
  Divider,
  Alert,
  Snackbar,
  FormControlLabel,
  Select,
  MenuItem,
  InputLabel,
  FormControl,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Tooltip,
  IconButton,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  Refresh as RefreshIcon,
  Save as SaveIcon,
  Info as InfoIcon,
} from '@mui/icons-material';
import API from '../../api';

const PredictiveFailoverSettings = () => {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);

  // Load configuration
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
      setError('Failed to load configuration');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const saveConfig = async () => {
    try {
      setSaving(true);
      await API.put('/api/settings/predictive-failover/', config);
      setSuccess(true);
      setHasChanges(false);
    } catch (err) {
      setError('Failed to save configuration');
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
      setSuccess(true);
      setHasChanges(false);
    } catch (err) {
      setError('Failed to reset configuration');
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
    return <Typography>Loading...</Typography>;
  }

  return (
    <Box sx={{ p: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
        <Typography variant="h5">Predictive Failover Settings</Typography>
        <Box>
          <Button
            startIcon={<RefreshIcon />}
            onClick={resetConfig}
            sx={{ mr: 1 }}
          >
            Reset to Defaults
          </Button>
          <Button
            variant="contained"
            startIcon={<SaveIcon />}
            onClick={saveConfig}
            disabled={!hasChanges || saving}
          >
            {saving ? 'Saving...' : 'Save'}
          </Button>
        </Box>
      </Box>

      {/* Master Switch */}
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <FormControlLabel
            control={
              <Switch
                checked={config.enabled}
                onChange={(e) => updateConfig('enabled', e.target.checked)}
                color="primary"
              />
            }
            label={
              <Box>
                <Typography variant="h6">Enable Predictive Failover</Typography>
                <Typography variant="body2" color="textSecondary">
                  When disabled, the system uses reactive failover only
                </Typography>
              </Box>
            }
          />
        </CardContent>
      </Card>

      {/* Main Settings */}
      <Accordion defaultExpanded>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="h6">Threshold Settings</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Typography gutterBottom>
                Warmup Threshold: {config.warmup_threshold}
                <Tooltip title="Risk score at which backup stream warming begins">
                  <IconButton size="small"><InfoIcon fontSize="small" /></IconButton>
                </Tooltip>
              </Typography>
              <Slider
                value={config.warmup_threshold}
                onChange={(e, v) => updateConfig('warmup_threshold', v)}
                min={40}
                max={85}
                marks={[
                  { value: 40, label: '40' },
                  { value: 60, label: '60' },
                  { value: 85, label: '85' },
                ]}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <Typography gutterBottom>
                Failover Threshold: {config.failover_threshold}
                <Tooltip title="Risk score at which proactive failover triggers">
                  <IconButton size="small"><InfoIcon fontSize="small" /></IconButton>
                </Tooltip>
              </Typography>
              <Slider
                value={config.failover_threshold}
                onChange={(e, v) => updateConfig('failover_threshold', v)}
                min={55}
                max={95}
                marks={[
                  { value: 55, label: '55' },
                  { value: 85, label: '85' },
                  { value: 95, label: '95' },
                ]}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <Typography gutterBottom>
                Metrics Interval: {config.metrics_interval}s
              </Typography>
              <Slider
                value={config.metrics_interval}
                onChange={(e, v) => updateConfig('metrics_interval', v)}
                min={1}
                max={10}
                marks
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <Typography gutterBottom>
                Cooldown Period: {config.cooldown_period}s
              </Typography>
              <Slider
                value={config.cooldown_period}
                onChange={(e, v) => updateConfig('cooldown_period', v)}
                min={5}
                max={300}
                step={5}
              />
            </Grid>
          </Grid>
        </AccordionDetails>
      </Accordion>

      {/* Learning Settings */}
      <Accordion>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="h6">Learning Settings</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <FormControlLabel
                control={
                  <Switch
                    checked={config.pattern_learning_enabled}
                    onChange={(e) => updateConfig('pattern_learning_enabled', e.target.checked)}
                  />
                }
                label="Pattern Learning"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControlLabel
                control={
                  <Switch
                    checked={config.time_pattern_enabled}
                    onChange={(e) => updateConfig('time_pattern_enabled', e.target.checked)}
                  />
                }
                label="Time Pattern Detection"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControlLabel
                control={
                  <Switch
                    checked={config.correlation_analysis_enabled}
                    onChange={(e) => updateConfig('correlation_analysis_enabled', e.target.checked)}
                  />
                }
                label="Correlation Analysis"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>Learning Rate</InputLabel>
                <Select
                  value={config.learning_rate}
                  onChange={(e) => updateConfig('learning_rate', e.target.value)}
                  label="Learning Rate"
                >
                  <MenuItem value="slow">Slow</MenuItem>
                  <MenuItem value="normal">Normal</MenuItem>
                  <MenuItem value="fast">Fast</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12}>
              <Typography gutterBottom>
                Pattern Confidence Threshold: {config.pattern_confidence_threshold}%
              </Typography>
              <Slider
                value={config.pattern_confidence_threshold}
                onChange={(e, v) => updateConfig('pattern_confidence_threshold', v)}
                min={40}
                max={90}
              />
            </Grid>
          </Grid>
        </AccordionDetails>
      </Accordion>

      {/* Metric Weights */}
      <Accordion>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="h6">Metric Weights</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Typography gutterBottom>
                Response Time Warning: {config.response_time_warning}ms
              </Typography>
              <Slider
                value={config.response_time_warning}
                onChange={(e, v) => updateConfig('response_time_warning', v)}
                min={50}
                max={500}
                step={10}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <Typography gutterBottom>
                Response Time Critical: {config.response_time_critical}ms
              </Typography>
              <Slider
                value={config.response_time_critical}
                onChange={(e, v) => updateConfig('response_time_critical', v)}
                min={150}
                max={1000}
                step={10}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <Typography gutterBottom>
                Buffer Underrun Weight: {config.buffer_underrun_weight}
              </Typography>
              <Slider
                value={config.buffer_underrun_weight}
                onChange={(e, v) => updateConfig('buffer_underrun_weight', v)}
                min={15}
                max={50}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <Typography gutterBottom>
                Bitrate Variance Threshold: {config.bitrate_variance_threshold}%
              </Typography>
              <Slider
                value={config.bitrate_variance_threshold}
                onChange={(e, v) => updateConfig('bitrate_variance_threshold', v)}
                min={10}
                max={50}
              />
            </Grid>
          </Grid>
        </AccordionDetails>
      </Accordion>

      {/* Optional Modules */}
      <Accordion>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="h6">Optional Modules</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <FormControlLabel
                control={
                  <Switch
                    checked={config.quality_monitoring_enabled}
                    onChange={(e) => updateConfig('quality_monitoring_enabled', e.target.checked)}
                  />
                }
                label="Quality Monitoring (QoS)"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControlLabel
                control={
                  <Switch
                    checked={config.peak_time_awareness_enabled}
                    onChange={(e) => updateConfig('peak_time_awareness_enabled', e.target.checked)}
                  />
                }
                label="Peak Time Awareness"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControlLabel
                control={
                  <Switch
                    checked={config.graceful_degradation_enabled}
                    onChange={(e) => updateConfig('graceful_degradation_enabled', e.target.checked)}
                  />
                }
                label="Graceful Degradation"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControlLabel
                control={
                  <Switch
                    checked={config.provider_ranking_enabled}
                    onChange={(e) => updateConfig('provider_ranking_enabled', e.target.checked)}
                  />
                }
                label="Provider Ranking"
              />
            </Grid>
          </Grid>
        </AccordionDetails>
      </Accordion>

      {/* Notifications */}
      <Snackbar
        open={success}
        autoHideDuration={3000}
        onClose={() => setSuccess(false)}
      >
        <Alert severity="success">Settings saved successfully</Alert>
      </Snackbar>
      <Snackbar
        open={!!error}
        autoHideDuration={5000}
        onClose={() => setError(null)}
      >
        <Alert severity="error">{error}</Alert>
      </Snackbar>
    </Box>
  );
};

export default PredictiveFailoverSettings;
