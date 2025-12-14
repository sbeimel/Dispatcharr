/**
 * Provider Health Dashboard Component
 * 
 * Displays health scores for providers and MAC addresses:
 * - Portal overview with health scores
 * - MAC address list per portal
 * - Warnings for low health scores
 * - Recommendations for MAC replacement
 * 
 * Requirements: 16.4, 16.5, 16.6, 16.7
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  LinearProgress,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Alert,
  AlertTitle,
  IconButton,
  Tooltip,
  Collapse,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
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
    if (score >= 80) return 'success';
    if (score >= 50) return 'warning';
    return 'error';
  };

  const getHealthIcon = (score) => {
    if (score >= 80) return <CheckCircleIcon color="success" />;
    if (score >= 50) return <WarningIcon color="warning" />;
    return <ErrorIcon color="error" />;
  };

  const toggleProvider = (accountId) => {
    setExpandedProviders(prev => ({
      ...prev,
      [accountId]: !prev[accountId]
    }));
  };

  const formatResponseTime = (ms) => {
    if (!ms) return '-';
    return `${Math.round(ms)}ms`;
  };

  const formatUptime = (percent) => {
    if (percent === undefined || percent === null) return '-';
    return `${percent.toFixed(1)}%`;
  };

  if (loading && Object.keys(healthData).length === 0) {
    return (
      <Box sx={{ p: 3 }}>
        <LinearProgress />
        <Typography sx={{ mt: 2 }}>Lade Health-Daten...</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 2 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h5">Provider Health Dashboard</Typography>
        <IconButton onClick={fetchHealthData} disabled={loading}>
          <RefreshIcon />
        </IconButton>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>
      )}

      {/* Problem MACs Warning */}
      {problemMacs.length > 0 && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          <AlertTitle>Problematische MAC-Adressen</AlertTitle>
          <Typography variant="body2">
            {problemMacs.length} MAC-Adresse(n) mit niedrigem Health Score gefunden.
            Erwägen Sie einen Austausch dieser MACs.
          </Typography>
          <List dense>
            {problemMacs.slice(0, 3).map((mac, idx) => (
              <ListItem key={idx}>
                <ListItemIcon>
                  <ErrorIcon color="error" fontSize="small" />
                </ListItemIcon>
                <ListItemText
                  primary={`${mac.mac_address?.substring(0, 12)}...`}
                  secondary={`Score: ${mac.health_score}, Fehler: ${mac.failure_count}`}
                />
              </ListItem>
            ))}
          </List>
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Provider Cards */}
        <Grid item xs={12} md={8}>
          <Typography variant="h6" gutterBottom>Provider Übersicht</Typography>
          {Object.entries(healthData).map(([accountId, provider]) => (
            <Card key={accountId} sx={{ mb: 2 }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    {getHealthIcon(provider.health_score?.score || 0)}
                    <Box>
                      <Typography variant="h6">
                        {provider.account_name || `Provider ${accountId}`}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Account ID: {accountId}
                      </Typography>
                    </Box>
                  </Box>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <Chip
                      label={`Score: ${provider.health_score?.score || 0}`}
                      color={getHealthColor(provider.health_score?.score || 0)}
                    />
                    <IconButton onClick={() => toggleProvider(accountId)}>
                      {expandedProviders[accountId] ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                    </IconButton>
                  </Box>
                </Box>

                {/* Provider Stats */}
                <Box sx={{ mt: 2 }}>
                  <Grid container spacing={2}>
                    <Grid item xs={4}>
                      <Typography variant="body2" color="text.secondary">Uptime</Typography>
                      <Typography variant="body1">
                        {formatUptime(provider.health_score?.uptime_percent)}
                      </Typography>
                    </Grid>
                    <Grid item xs={4}>
                      <Typography variant="body2" color="text.secondary">Fehler</Typography>
                      <Typography variant="body1">
                        {provider.health_score?.failure_count || 0}
                      </Typography>
                    </Grid>
                    <Grid item xs={4}>
                      <Typography variant="body2" color="text.secondary">Ø Response</Typography>
                      <Typography variant="body1">
                        {formatResponseTime(provider.health_score?.avg_response_time_ms)}
                      </Typography>
                    </Grid>
                  </Grid>
                </Box>

                {/* MAC Addresses */}
                <Collapse in={expandedProviders[accountId]}>
                  <Divider sx={{ my: 2 }} />
                  <Typography variant="subtitle2" gutterBottom>
                    MAC-Adressen ({Object.keys(provider.mac_health_scores || {}).length})
                  </Typography>
                  <TableContainer component={Paper} variant="outlined">
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>MAC-Adresse</TableCell>
                          <TableCell align="right">Score</TableCell>
                          <TableCell align="right">Uptime</TableCell>
                          <TableCell align="right">Fehler</TableCell>
                          <TableCell align="right">Ø Response</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {Object.entries(provider.mac_health_scores || {}).map(([mac, score]) => (
                          <TableRow key={mac}>
                            <TableCell>
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                {getHealthIcon(score.score)}
                                <Typography variant="body2">
                                  {mac.substring(0, 12)}...
                                </Typography>
                              </Box>
                            </TableCell>
                            <TableCell align="right">
                              <Chip
                                label={score.score}
                                size="small"
                                color={getHealthColor(score.score)}
                              />
                            </TableCell>
                            <TableCell align="right">{formatUptime(score.uptime_percent)}</TableCell>
                            <TableCell align="right">{score.failure_count}</TableCell>
                            <TableCell align="right">
                              {formatResponseTime(score.avg_response_time_ms)}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </Collapse>
              </CardContent>
            </Card>
          ))}

          {Object.keys(healthData).length === 0 && !loading && (
            <Alert severity="info">
              Keine Provider-Daten verfügbar. Health-Daten werden gesammelt sobald Streams aktiv sind.
            </Alert>
          )}
        </Grid>

        {/* Top Performers Sidebar */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <TrendingUpIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                Top Performer
              </Typography>
              {topPerformers.length > 0 ? (
                <List dense>
                  {topPerformers.map((performer, idx) => (
                    <ListItem key={idx}>
                      <ListItemIcon>
                        <Chip
                          label={`#${idx + 1}`}
                          size="small"
                          color={idx === 0 ? 'success' : 'default'}
                        />
                      </ListItemIcon>
                      <ListItemText
                        primary={performer.mac_address?.substring(0, 12) + '...'}
                        secondary={`Score: ${performer.health_score} | Uptime: ${formatUptime(performer.uptime_percent)}`}
                      />
                    </ListItem>
                  ))}
                </List>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  Noch keine Daten verfügbar
                </Typography>
              )}
            </CardContent>
          </Card>

          {/* Problem MACs Card */}
          <Card sx={{ mt: 2 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <TrendingDownIcon sx={{ mr: 1, verticalAlign: 'middle' }} color="error" />
                Problem MACs
              </Typography>
              {problemMacs.length > 0 ? (
                <List dense>
                  {problemMacs.map((mac, idx) => (
                    <ListItem key={idx}>
                      <ListItemIcon>
                        <ErrorIcon color="error" />
                      </ListItemIcon>
                      <ListItemText
                        primary={mac.mac_address?.substring(0, 12) + '...'}
                        secondary={
                          <Box>
                            <Typography variant="caption" display="block">
                              Score: {mac.health_score}
                            </Typography>
                            <Typography variant="caption" color="error">
                              Empfehlung: MAC ersetzen
                            </Typography>
                          </Box>
                        }
                      />
                    </ListItem>
                  ))}
                </List>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  Keine problematischen MACs gefunden
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default ProviderHealthDashboard;
