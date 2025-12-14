/**
 * MAC Portal Overview - Zentrale Übersichtsseite für alle MAC Portale.
 * 
 * Zeigt:
 * - Alle Portale mit Status (Online/Offline)
 * - Alle MACs pro Portal mit Details
 * - Activity Level, Watchdog Timeout, Max Streams
 * - Aggregierte Statistiken
 * - Health Scores und Expiry Countdown
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
  IconButton,
  Tooltip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Collapse,
  Alert,
  Button,
  CircularProgress,
  Badge,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  CheckCircle as OnlineIcon,
  Cancel as OfflineIcon,
  Warning as WarningIcon,
  AccessTime as TimeIcon,
  Speed as SpeedIcon,
  Tv as StreamIcon,
  HealthAndSafety as HealthIcon,
} from '@mui/icons-material';

// API Base URL
const API_BASE = '/api/mac-portal';

/**
 * Status Badge Komponente
 */
const StatusBadge = ({ status }) => {
  const statusConfig = {
    active: { color: 'success', label: 'Available' },
    in_use: { color: 'info', label: 'In Use' },
    cooldown: { color: 'warning', label: 'Cooldown' },
    expired: { color: 'error', label: 'Expired' },
    blocked: { color: 'error', label: 'Blocked' },
    unknown: { color: 'default', label: 'Unknown' },
  };

  const config = statusConfig[status] || statusConfig.unknown;

  return (
    <Chip
      size="small"
      label={config.label}
      color={config.color}
      variant="outlined"
    />
  );
};

/**
 * Health Score Anzeige
 */
const HealthScore = ({ score }) => {
  const getColor = (s) => {
    if (s >= 80) return 'success';
    if (s >= 50) return 'warning';
    return 'error';
  };

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
      <LinearProgress
        variant="determinate"
        value={score}
        color={getColor(score)}
        sx={{ width: 60, height: 8, borderRadius: 4 }}
      />
      <Typography variant="body2" color="text.secondary">
        {score}%
      </Typography>
    </Box>
  );
};

/**
 * Expiry Countdown Anzeige
 */
const ExpiryCountdown = ({ days }) => {
  if (days === null || days === undefined) {
    return <Typography variant="body2" color="text.secondary">-</Typography>;
  }

  const getColor = () => {
    if (days <= 0) return 'error';
    if (days <= 7) return 'warning';
    return 'success';
  };

  const getText = () => {
    if (days <= 0) return 'Expired';
    if (days === 1) return '1 day';
    return `${days} days`;
  };

  return (
    <Chip
      size="small"
      label={getText()}
      color={getColor()}
      variant="outlined"
      icon={<TimeIcon />}
    />
  );
};

/**
 * Portal Card Komponente
 */
const PortalCard = ({ portal, onRefresh }) => {
  const [expanded, setExpanded] = useState(false);

  const isOnline = portal.status === 'online';

  return (
    <Card sx={{ mb: 2 }}>
      <CardContent>
        {/* Header */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {isOnline ? (
              <OnlineIcon color="success" />
            ) : (
              <OfflineIcon color="error" />
            )}
            <Typography variant="h6">{portal.name}</Typography>
            <Chip
              size="small"
              label={portal.type || 'Unknown'}
              variant="outlined"
            />
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Badge badgeContent={portal.available_count} color="success">
              <Chip
                label={`${portal.mac_count} MACs`}
                size="small"
              />
            </Badge>
            <IconButton size="small" onClick={() => setExpanded(!expanded)}>
              {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            </IconButton>
          </Box>
        </Box>

        {/* URL */}
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          {portal.url}
        </Typography>

        {/* MAC Liste (expandierbar) */}
        <Collapse in={expanded}>
          <TableContainer component={Paper} variant="outlined" sx={{ mt: 2 }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>MAC Address</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Health</TableCell>
                  <TableCell>Expiry</TableCell>
                  <TableCell>Streams</TableCell>
                  <TableCell>Activity</TableCell>
                  <TableCell>Watchdog</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {portal.macs.map((mac) => (
                  <TableRow key={mac.id}>
                    <TableCell>
                      <Typography variant="body2" fontFamily="monospace">
                        {mac.mac_address}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={mac.status} />
                    </TableCell>
                    <TableCell>
                      <HealthScore score={mac.health_score} />
                    </TableCell>
                    <TableCell>
                      <ExpiryCountdown days={mac.days_until_expiry} />
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        <StreamIcon fontSize="small" color="action" />
                        <Typography variant="body2">
                          {mac.current_streams}/{mac.max_connections}
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      {mac.activity_level !== null ? (
                        <Chip
                          size="small"
                          label={`Level ${mac.activity_level}`}
                          variant="outlined"
                        />
                      ) : (
                        <Typography variant="body2" color="text.secondary">-</Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      {mac.watchdog_timeout !== null ? (
                        <Typography variant="body2">
                          {mac.watchdog_timeout}s
                        </Typography>
                      ) : (
                        <Typography variant="body2" color="text.secondary">-</Typography>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Collapse>
      </CardContent>
    </Card>
  );
};

/**
 * Statistik Card Komponente
 */
const StatCard = ({ title, value, icon, color = 'primary', subtitle }) => (
  <Card>
    <CardContent>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <Box>
          <Typography variant="body2" color="text.secondary">
            {title}
          </Typography>
          <Typography variant="h4" color={`${color}.main`}>
            {value}
          </Typography>
          {subtitle && (
            <Typography variant="caption" color="text.secondary">
              {subtitle}
            </Typography>
          )}
        </Box>
        <Box sx={{ color: `${color}.main` }}>
          {icon}
        </Box>
      </Box>
    </CardContent>
  </Card>
);

/**
 * Hauptkomponente: MAC Portal Overview
 */
const MACPortalOverview = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${API_BASE}/overview/`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      setData(result);
    } catch (err) {
      console.error('Error fetching MAC portal overview:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await fetch(`${API_BASE}/overview/refresh-status/`, {
        method: 'POST',
      });
      // Warte kurz und lade dann neu
      setTimeout(() => {
        fetchData();
        setRefreshing(false);
      }, 2000);
    } catch (err) {
      console.error('Error refreshing status:', err);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
    // Auto-refresh alle 30 Sekunden
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  if (loading && !data) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ m: 2 }}>
        Error loading MAC portal overview: {error}
      </Alert>
    );
  }

  const stats = data?.statistics || {};
  const portals = data?.portals || [];

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h5">MAC Portal Overview</Typography>
        <Button
          variant="outlined"
          startIcon={refreshing ? <CircularProgress size={20} /> : <RefreshIcon />}
          onClick={handleRefresh}
          disabled={refreshing}
        >
          {refreshing ? 'Refreshing...' : 'Refresh Status'}
        </Button>
      </Box>

      {/* Statistiken */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Total Portals"
            value={stats.total_portals || 0}
            icon={<SpeedIcon fontSize="large" />}
            color="primary"
            subtitle={`${stats.online_portals || 0} online`}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Total MACs"
            value={stats.total_macs || 0}
            icon={<StreamIcon fontSize="large" />}
            color="info"
            subtitle={`${stats.available_macs || 0} available`}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Avg Health Score"
            value={`${stats.avg_health_score || 0}%`}
            icon={<HealthIcon fontSize="large" />}
            color={stats.avg_health_score >= 80 ? 'success' : stats.avg_health_score >= 50 ? 'warning' : 'error'}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Failovers (24h)"
            value={stats.total_failovers_24h || 0}
            icon={<WarningIcon fontSize="large" />}
            color="warning"
            subtitle={`${stats.expiring_soon || 0} expiring soon`}
          />
        </Grid>
      </Grid>

      {/* Status Übersicht */}
      <Grid container spacing={1} sx={{ mb: 3 }}>
        <Grid item>
          <Chip
            icon={<OnlineIcon />}
            label={`${stats.available_macs || 0} Available`}
            color="success"
            variant="outlined"
          />
        </Grid>
        <Grid item>
          <Chip
            icon={<StreamIcon />}
            label={`${stats.in_use_macs || 0} In Use`}
            color="info"
            variant="outlined"
          />
        </Grid>
        <Grid item>
          <Chip
            icon={<TimeIcon />}
            label={`${stats.cooldown_macs || 0} Cooldown`}
            color="warning"
            variant="outlined"
          />
        </Grid>
        <Grid item>
          <Chip
            icon={<OfflineIcon />}
            label={`${stats.expired_macs || 0} Expired`}
            color="error"
            variant="outlined"
          />
        </Grid>
      </Grid>

      {/* Portal Liste */}
      {portals.length === 0 ? (
        <Alert severity="info">
          No MAC portals configured. Add a MAC/STB portal account to see the overview.
        </Alert>
      ) : (
        portals.map((portal) => (
          <PortalCard
            key={portal.id}
            portal={portal}
            onRefresh={fetchData}
          />
        ))
      )}
    </Box>
  );
};

export default MACPortalOverview;
