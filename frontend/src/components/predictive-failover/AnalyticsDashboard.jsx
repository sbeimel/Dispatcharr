/**
 * Analytics Dashboard Component
 * 
 * Displays analytics for the Predictive Failover System:
 * - Health score trends
 * - Failure heatmap
 * - Portal comparison
 * - Export functions
 * 
 * Requirements: 19.1, 19.2, 19.3, 19.4, 19.5, 19.6
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  LinearProgress,
  Button,
  ButtonGroup,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Alert,
  Chip,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Tooltip,
  IconButton,
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  TrendingFlat as TrendingFlatIcon,
  Download as DownloadIcon,
  Refresh as RefreshIcon,
  Assessment as AssessmentIcon,
} from '@mui/icons-material';
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
      case 'up': return <TrendingUpIcon color="success" />;
      case 'down': return <TrendingDownIcon color="error" />;
      default: return <TrendingFlatIcon color="action" />;
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
    return (
      <Box sx={{ p: 3 }}>
        <LinearProgress />
        <Typography sx={{ mt: 2 }}>Lade Analytics...</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 2 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h5">
          <AssessmentIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
          Analytics Dashboard
        </Typography>
        <Box>
          <ButtonGroup size="small" sx={{ mr: 2 }}>
            <Button onClick={() => handleExport('json')} startIcon={<DownloadIcon />}>
              JSON
            </Button>
            <Button onClick={() => handleExport('csv')} startIcon={<DownloadIcon />}>
              CSV
            </Button>
          </ButtonGroup>
          <IconButton onClick={fetchData} disabled={loading}>
            <RefreshIcon />
          </IconButton>
        </Box>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {/* Summary Cards */}
      {summary && (
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid item xs={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>Provider</Typography>
                <Typography variant="h4">{summary.total_providers}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>Ø Health Score</Typography>
                <Typography variant="h4">{summary.average_health_score}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>Fehler (24h)</Typography>
                <Typography variant="h4" color="error">{summary.failures_last_24h}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>Problem MACs</Typography>
                <Typography variant="h4" color="warning.main">{summary.problem_macs_count}</Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      <Grid container spacing={3}>
        {/* Portal Comparison */}
        <Grid item xs={12} md={7}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Portal Vergleich</Typography>
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Provider</TableCell>
                      <TableCell align="right">Score</TableCell>
                      <TableCell align="right">Uptime</TableCell>
                      <TableCell align="right">Fehler</TableCell>
                      <TableCell align="center">Trend</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {comparison.map((provider) => (
                      <TableRow key={provider.account_id}>
                        <TableCell>
                          {provider.account_name || `Provider ${provider.account_id}`}
                        </TableCell>
                        <TableCell align="right">
                          <Chip
                            label={provider.health_score}
                            size="small"
                            color={provider.health_score >= 80 ? 'success' : provider.health_score >= 50 ? 'warning' : 'error'}
                          />
                        </TableCell>
                        <TableCell align="right">{provider.uptime_percent?.toFixed(1)}%</TableCell>
                        <TableCell align="right">{provider.failure_count}</TableCell>
                        <TableCell align="center">
                          <Tooltip title={`Trend: ${provider.trend_direction}`}>
                            {getTrendIcon(provider.trend_direction)}
                          </Tooltip>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* Failure Heatmap */}
        <Grid item xs={12} md={5}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Fehler Heatmap (7 Tage)</Typography>
              {heatmap && (
                <Box sx={{ overflowX: 'auto' }}>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell></TableCell>
                        {[0, 4, 8, 12, 16, 20].map(h => (
                          <TableCell key={h} align="center" sx={{ fontSize: '0.7rem', p: 0.5 }}>
                            {h}:00
                          </TableCell>
                        ))}
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {heatmap.days?.map((day, dayIdx) => (
                        <TableRow key={day}>
                          <TableCell sx={{ fontSize: '0.7rem', p: 0.5 }}>{day.substring(0, 3)}</TableCell>
                          {[0, 4, 8, 12, 16, 20].map(h => (
                            <TableCell
                              key={h}
                              align="center"
                              sx={{
                                backgroundColor: getHeatmapColor(
                                  heatmap.heatmap?.[dayIdx]?.[h] || 0,
                                  heatmap.max_value || 1
                                ),
                                p: 0.5,
                                fontSize: '0.7rem',
                              }}
                            >
                              {heatmap.heatmap?.[dayIdx]?.[h] || 0}
                            </TableCell>
                          ))}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Health Trend */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                <Typography variant="h6">Health Score Trend</Typography>
                <FormControl size="small" sx={{ minWidth: 200 }}>
                  <InputLabel>Provider</InputLabel>
                  <Select
                    value={selectedProvider}
                    label="Provider"
                    onChange={(e) => setSelectedProvider(e.target.value)}
                  >
                    {comparison.map((p) => (
                      <MenuItem key={p.account_id} value={p.account_id}>
                        {p.account_name || `Provider ${p.account_id}`}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Box>
              
              {trend.length > 0 ? (
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  {trend.map((day) => (
                    <Tooltip
                      key={day.date}
                      title={`Min: ${day.min_score}, Max: ${day.max_score}, Samples: ${day.sample_count}`}
                    >
                      <Box
                        sx={{
                          width: 30,
                          height: 60,
                          display: 'flex',
                          flexDirection: 'column',
                          alignItems: 'center',
                        }}
                      >
                        <Box
                          sx={{
                            width: 20,
                            height: `${day.avg_score * 0.5}px`,
                            backgroundColor: day.avg_score >= 80 ? 'success.main' : day.avg_score >= 50 ? 'warning.main' : 'error.main',
                            borderRadius: 1,
                          }}
                        />
                        <Typography variant="caption" sx={{ fontSize: '0.6rem' }}>
                          {day.date.substring(5)}
                        </Typography>
                      </Box>
                    </Tooltip>
                  ))}
                </Box>
              ) : (
                <Typography color="text.secondary">
                  Wählen Sie einen Provider um den Trend anzuzeigen
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default AnalyticsDashboard;
