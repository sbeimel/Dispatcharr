/**
 * Pattern Management Component
 * 
 * Manages failure patterns for predictive failover.
 * 
 * Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Chip,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Slider,
  Alert,
  Snackbar,
  Tooltip,
  Switch,
  FormControlLabel,
} from '@mui/material';
import {
  Delete as DeleteIcon,
  ThumbDown as ThumbDownIcon,
  CheckCircle as CheckCircleIcon,
  Refresh as RefreshIcon,
  CleaningServices as CleanupIcon,
} from '@mui/icons-material';
import API from '../../api';

const PatternManagement = () => {
  const [patterns, setPatterns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [deleteDialog, setDeleteDialog] = useState({ open: false, pattern: null });
  const [confidenceDialog, setConfidenceDialog] = useState({ open: false, pattern: null, value: 50 });

  useEffect(() => {
    loadPatterns();
  }, []);

  const loadPatterns = async () => {
    try {
      setLoading(true);
      const response = await API.get('/api/predictive-failover/patterns/');
      setPatterns(response.data);
    } catch (err) {
      setError('Failed to load patterns');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const markFalsePositive = async (pattern) => {
    try {
      await API.post(`/api/predictive-failover/patterns/${pattern.id}/mark_false_positive/`);
      setSuccess('Pattern marked as false positive');
      loadPatterns();
    } catch (err) {
      setError('Failed to mark pattern');
      console.error(err);
    }
  };

  const markConfirmed = async (pattern) => {
    try {
      await API.post(`/api/predictive-failover/patterns/${pattern.id}/mark_confirmed/`);
      setSuccess('Pattern marked as confirmed');
      loadPatterns();
    } catch (err) {
      setError('Failed to confirm pattern');
      console.error(err);
    }
  };

  const toggleStatus = async (pattern) => {
    try {
      await API.post(`/api/predictive-failover/patterns/${pattern.id}/toggle_status/`);
      setSuccess('Pattern status toggled');
      loadPatterns();
    } catch (err) {
      setError('Failed to toggle pattern status');
      console.error(err);
    }
  };

  const deletePattern = async () => {
    if (!deleteDialog.pattern) return;
    try {
      await API.delete(`/api/predictive-failover/patterns/${deleteDialog.pattern.id}/`);
      setSuccess('Pattern deleted');
      setDeleteDialog({ open: false, pattern: null });
      loadPatterns();
    } catch (err) {
      setError('Failed to delete pattern');
      console.error(err);
    }
  };

  const updateConfidence = async () => {
    if (!confidenceDialog.pattern) return;
    try {
      await API.patch(`/api/predictive-failover/patterns/${confidenceDialog.pattern.id}/`, {
        confidence: confidenceDialog.value
      });
      setSuccess('Confidence updated');
      setConfidenceDialog({ open: false, pattern: null, value: 50 });
      loadPatterns();
    } catch (err) {
      setError('Failed to update confidence');
      console.error(err);
    }
  };

  const cleanupPatterns = async () => {
    try {
      const response = await API.post('/api/predictive-failover/patterns/cleanup/', { threshold: 30 });
      setSuccess(`Cleaned up ${response.data.deleted} low-confidence patterns`);
      loadPatterns();
    } catch (err) {
      setError('Failed to cleanup patterns');
      console.error(err);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'active': return 'success';
      case 'confirmed': return 'info';
      case 'disabled': return 'default';
      case 'false_positive': return 'error';
      default: return 'default';
    }
  };

  const getTypeLabel = (type) => {
    const labels = {
      response_time: 'Response Time',
      buffer_underrun: 'Buffer Underrun',
      bitrate_drop: 'Bitrate Drop',
      connection_reset: 'Connection Reset',
      time_window: 'Time Window',
      correlation: 'Correlation',
      composite: 'Composite',
    };
    return labels[type] || type;
  };

  return (
    <Box sx={{ p: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
        <Typography variant="h5">Failure Patterns</Typography>
        <Box>
          <Button
            startIcon={<CleanupIcon />}
            onClick={cleanupPatterns}
            sx={{ mr: 1 }}
          >
            Cleanup Low Confidence
          </Button>
          <IconButton onClick={loadPatterns}>
            <RefreshIcon />
          </IconButton>
        </Box>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Type</TableCell>
              <TableCell>Confidence</TableCell>
              <TableCell>Hits</TableCell>
              <TableCell>Success Rate</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {patterns.map((pattern) => (
              <TableRow key={pattern.id}>
                <TableCell>{pattern.name}</TableCell>
                <TableCell>
                  <Chip label={getTypeLabel(pattern.pattern_type)} size="small" variant="outlined" />
                </TableCell>
                <TableCell>
                  <Button
                    size="small"
                    onClick={() => setConfidenceDialog({ open: true, pattern, value: pattern.confidence })}
                  >
                    {pattern.confidence}%
                  </Button>
                </TableCell>
                <TableCell>{pattern.hit_count}</TableCell>
                <TableCell>{pattern.success_rate?.toFixed(1) || 0}%</TableCell>
                <TableCell>
                  <Chip
                    label={pattern.status}
                    color={getStatusColor(pattern.status)}
                    size="small"
                  />
                </TableCell>
                <TableCell>
                  <Tooltip title="Toggle Active/Disabled">
                    <IconButton
                      size="small"
                      onClick={() => toggleStatus(pattern)}
                      disabled={pattern.status === 'false_positive'}
                    >
                      <Switch
                        checked={pattern.status === 'active' || pattern.status === 'confirmed'}
                        size="small"
                      />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Mark as False Positive">
                    <IconButton
                      size="small"
                      onClick={() => markFalsePositive(pattern)}
                      color="warning"
                    >
                      <ThumbDownIcon />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Mark as Confirmed">
                    <IconButton
                      size="small"
                      onClick={() => markConfirmed(pattern)}
                      color="success"
                    >
                      <CheckCircleIcon />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Delete">
                    <IconButton
                      size="small"
                      onClick={() => setDeleteDialog({ open: true, pattern })}
                      color="error"
                    >
                      <DeleteIcon />
                    </IconButton>
                  </Tooltip>
                </TableCell>
              </TableRow>
            ))}
            {patterns.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} align="center">
                  No patterns found
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialog.open} onClose={() => setDeleteDialog({ open: false, pattern: null })}>
        <DialogTitle>Delete Pattern</DialogTitle>
        <DialogContent>
          Are you sure you want to delete pattern "{deleteDialog.pattern?.name}"?
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialog({ open: false, pattern: null })}>Cancel</Button>
          <Button onClick={deletePattern} color="error">Delete</Button>
        </DialogActions>
      </Dialog>

      {/* Confidence Adjustment Dialog */}
      <Dialog open={confidenceDialog.open} onClose={() => setConfidenceDialog({ open: false, pattern: null, value: 50 })}>
        <DialogTitle>Adjust Confidence</DialogTitle>
        <DialogContent sx={{ minWidth: 300, pt: 2 }}>
          <Typography gutterBottom>
            Confidence: {confidenceDialog.value}%
          </Typography>
          <Slider
            value={confidenceDialog.value}
            onChange={(e, v) => setConfidenceDialog(prev => ({ ...prev, value: v }))}
            min={0}
            max={100}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfidenceDialog({ open: false, pattern: null, value: 50 })}>Cancel</Button>
          <Button onClick={updateConfidence} variant="contained">Save</Button>
        </DialogActions>
      </Dialog>

      {/* Notifications */}
      <Snackbar open={!!success} autoHideDuration={3000} onClose={() => setSuccess(null)}>
        <Alert severity="success">{success}</Alert>
      </Snackbar>
      <Snackbar open={!!error} autoHideDuration={5000} onClose={() => setError(null)}>
        <Alert severity="error">{error}</Alert>
      </Snackbar>
    </Box>
  );
};

export default PatternManagement;
