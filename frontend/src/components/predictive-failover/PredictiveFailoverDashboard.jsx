/**
 * Predictive Failover Dashboard Component
 * 
 * Displays real-time predictive failover status including:
 * - Active streams with risk scores
 * - Warmup status
 * - Recent events
 * - Statistics
 * 
 * Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Chip,
  LinearProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Alert,
  Badge,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  CheckCircle as CheckCircleIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  Refresh as RefreshIcon,
  PlayArrow as PlayIcon,
  Pause as PauseIcon,
} from '@mui/icons-material';
import API from '../../api';

// Risk score color coding
const getRiskColor = (score, warmupThreshold = 60, failoverThreshold = 85) => {
  if (score >= failoverThreshold) return 'error';
  if (score >= warmupThreshold) return 'warning';
  return 'success';
};

const getRiskIcon = (score, warmupThreshold = 60, failoverThreshold = 85) => {
  if (score >= failoverThreshold) return <ErrorIcon color="error" />;
  if (score >= warmupThreshold) return <WarningIcon color="warning" />;
  return <CheckCircleIcon color="success" />;
};

const PredictiveFailoverDashboard = () => {
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [ws, setWs] = useState(null);

  // Load dashboard data
  const loadDashboard = useCallback(async () => {
    try {
      setLoading(true);
      const response = await API.get('/api/predictive-failover/dashboard/');
      setDashboard(response.data);
      setError(null);
    } catch (err) {
      setError('Failed to load dashboard');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  // WebSocket connection for real-time updates
  useEffect(() => {
    loadDashboard();

    // Connect WebSocket
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/predictive-failover/`;
    
    try {
      const websocket = new WebSocket(wsUrl);
      
      websocket.onopen = () => {
        console.log('Predictive failover WebSocket connected');
      };
      
      websocket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
      };
      
      websocket.onerror = (err) => {
        console.error('WebSocket error:', err);
      };
      
      websocket.onclose = () => {
        console.log('WebSocket disconnected');
      };
      
      setWs(websocket);
      
      return () => {
        websocket.close();
      };
    } catch (err) {
      console.error('Failed to connect WebSocket:', err);
    }
  }, [loadDashboard]);

  const handleWebSocketMessage = (data) => {
    switch (data.type) {
      case 'initial_state':
        setDashboard(prev => ({ ...prev, ...data.data }));
        break;
      case 'risk_score_update':
        updateStreamRiskScore(data);
        break;
      case 'failover_event':
        addFailoverEvent(data);
        break;
      case 'warmup_status_update':
        updateWarmupStatus(data);
        break;
      default:
        break;
    }
  };

  const updateStreamRiskScore = (data) => {
    setDashboard(prev => {
      if (!prev) return prev;
      const streams = [...(prev.active_streams || [])];
      const idx = streams.findIndex(s => s.stream_id === data.stream_id);
      if (idx >= 0) {
        streams[idx] = { ...streams[idx], risk_score: data.risk_score, reasons: data.reasons };
      }
      return { ...prev, active_streams: streams };
    });
  };

  const addFailoverEvent = (data) => {
    setDashboard(prev => {
      if (!prev) return prev;
      const events = [data, ...(prev.recent_events || [])].slice(0, 20);
      return { ...prev, recent_events: events };
    });
  };

  const updateWarmupStatus = (data) => {
    setDashboard(prev => {
      if (!prev) return prev;
      const warmup = { ...(prev.warmup_status || {}) };
      warmup[data.channel_id] = data;
      return { ...prev, warmup_status: warmup };
    });
  };

  if (loading && !dashboard) {
    return <LinearProgress />;
  }

  if (error) {
    return <Alert severity="error">{error}</Alert>;
  }

  const { enabled, active_streams = [], warmup_status = {}, recent_events = [], statistics = {} } = dashboard || {};

  return (
    <Box sx={{ p: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
        <Typography variant="h5">
          Predictive Failover Dashboard
          <Chip
            label={enabled ? 'Enabled' : 'Disabled'}
            color={enabled ? 'success' : 'default'}
            size="small"
            sx={{ ml: 2 }}
          />
        </Typography>
        <IconButton onClick={loadDashboard}>
          <RefreshIcon />
        </IconButton>
      </Box>

      {/* Statistics Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Active Streams
              </Typography>
              <Typography variant="h4">{active_streams.length}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Warmups Active
              </Typography>
              <Typography variant="h4">
                {Object.values(warmup_status).filter(w => w.is_ready).length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Success Rate
              </Typography>
              <Typography variant="h4">
                {statistics.success_rate?.toFixed(1) || 0}%
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total Failovers
              </Typography>
              <Typography variant="h4">{statistics.total_failovers || 0}</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Active Streams */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>Active Streams</Typography>
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Channel</TableCell>
                  <TableCell>Risk Score</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Warmup</TableCell>
                  <TableCell>Reasons</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {active_streams.map((stream) => (
                  <TableRow key={stream.stream_id}>
                    <TableCell>{stream.channel_name}</TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        {getRiskIcon(stream.risk_score)}
                        <Typography>{stream.risk_score}</Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={stream.risk_score >= 85 ? 'Critical' : stream.risk_score >= 60 ? 'Warning' : 'OK'}
                        color={getRiskColor(stream.risk_score)}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      {warmup_status[stream.channel_id]?.is_ready ? (
                        <Chip label="Ready" color="info" size="small" />
                      ) : warmup_status[stream.channel_id]?.status === 'warming' ? (
                        <Chip label="Warming" color="warning" size="small" />
                      ) : (
                        '-'
                      )}
                    </TableCell>
                    <TableCell>
                      {stream.reasons?.slice(0, 2).join(', ') || '-'}
                    </TableCell>
                  </TableRow>
                ))}
                {active_streams.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} align="center">
                      No active streams
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      {/* Recent Events */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>Recent Events</Typography>
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Time</TableCell>
                  <TableCell>Event</TableCell>
                  <TableCell>Channel</TableCell>
                  <TableCell>Risk Score</TableCell>
                  <TableCell>Result</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {recent_events.map((event, idx) => (
                  <TableRow key={idx}>
                    <TableCell>
                      {new Date(event.timestamp).toLocaleTimeString()}
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={event.event_type_display || event.event_type}
                        size="small"
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell>{event.channel_name || '-'}</TableCell>
                    <TableCell>{event.risk_score || '-'}</TableCell>
                    <TableCell>
                      {event.success !== null && (
                        event.success ? (
                          <CheckCircleIcon color="success" fontSize="small" />
                        ) : (
                          <ErrorIcon color="error" fontSize="small" />
                        )
                      )}
                    </TableCell>
                  </TableRow>
                ))}
                {recent_events.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} align="center">
                      No recent events
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>
    </Box>
  );
};

export default PredictiveFailoverDashboard;
