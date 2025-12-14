/**
 * Failover Test API Functions
 * 
 * API functions for the Failover Test Page.
 * Requirements: All API-related
 */

// Get host from environment
const host = import.meta.env.DEV
  ? `http://${window.location.hostname}:5656`
  : '';

// Import auth store for token
import useAuthStore from '../store/auth';

const getAuthToken = async () => {
  return await useAuthStore.getState().getToken();
};

const request = async (url, options = {}) => {
  if (
    options.body &&
    !(options.body instanceof FormData) &&
    typeof options.body === 'object'
  ) {
    options.body = JSON.stringify(options.body);
    options.headers = {
      ...options.headers,
      'Content-Type': 'application/json',
    };
  }

  options.headers = {
    ...options.headers,
    Authorization: `Bearer ${await getAuthToken()}`,
  };

  const response = await fetch(url, options);

  if (!response.ok) {
    const error = new Error(`HTTP error! Status: ${response.status}`);
    let errorBody = await response.text();
    try {
      errorBody = JSON.parse(errorBody);
    } catch (e) {}
    error.status = response.status;
    error.body = errorBody;
    throw error;
  }

  // Handle blob responses for exports
  const contentType = response.headers.get('content-type');
  if (contentType && (contentType.includes('application/json') || contentType.includes('text/csv'))) {
    if (options.responseType === 'blob') {
      return await response.blob();
    }
  }

  try {
    return await response.json();
  } catch (e) {
    return '';
  }
};

// =============================================================================
// Test Channel API
// =============================================================================

export const getFailoverTestChannels = async () => {
  return await request(`${host}/api/failover-test/channels/`);
};

export const createFailoverTestChannel = async (channelData) => {
  return await request(`${host}/api/failover-test/channels/`, {
    method: 'POST',
    body: channelData,
  });
};

export const getFailoverTestChannel = async (channelId) => {
  return await request(`${host}/api/failover-test/channels/${channelId}/`);
};

export const deleteFailoverTestChannel = async (channelId) => {
  return await request(`${host}/api/failover-test/channels/${channelId}/`, {
    method: 'DELETE',
  });
};

export const getAvailableChannelsForImport = async () => {
  return await request(`${host}/api/failover-test/channels/available/`);
};

export const importChannelForTest = async (channelId) => {
  return await request(`${host}/api/failover-test/channels/import/`, {
    method: 'POST',
    body: { channel_id: channelId },
  });
};

// =============================================================================
// Simulation API
// =============================================================================

export const simulateFailoverInterrupt = async (channelId, errorType) => {
  return await request(`${host}/api/failover-test/simulate/interrupt/`, {
    method: 'POST',
    body: {
      channel_id: channelId,
      error_type: errorType,
    },
  });
};

export const startFailoverAutoSimulation = async (channelId, config) => {
  return await request(`${host}/api/failover-test/simulate/auto-start/`, {
    method: 'POST',
    body: {
      channel_id: channelId,
      config: config,
    },
  });
};

export const stopFailoverSimulation = async (simulationId) => {
  return await request(`${host}/api/failover-test/simulate/stop/`, {
    method: 'POST',
    body: { simulation_id: simulationId },
  });
};

export const stopAllSimulations = async (channelId = null) => {
  const body = channelId ? { channel_id: channelId } : {};
  return await request(`${host}/api/failover-test/simulate/stop/`, {
    method: 'POST',
    body,
  });
};

export const getSimulationStatus = async () => {
  return await request(`${host}/api/failover-test/simulate/status/`);
};

// =============================================================================
// Statistics API
// =============================================================================

export const getFailoverTestStatistics = async () => {
  return await request(`${host}/api/failover-test/statistics/`);
};

export const resetFailoverTestStatistics = async () => {
  return await request(`${host}/api/failover-test/statistics/reset/`, {
    method: 'POST',
  });
};

// =============================================================================
// Logs API
// =============================================================================

export const getFailoverTestLogs = async (limit = 100) => {
  return await request(`${host}/api/failover-test/logs/?limit=${limit}`);
};

// =============================================================================
// Export API
// =============================================================================

export const exportFailoverTestLogs = async () => {
  const response = await fetch(`${host}/api/failover-test/export/logs/`, {
    headers: {
      Authorization: `Bearer ${await getAuthToken()}`,
    },
  });
  return await response.blob();
};

export const exportFailoverTestStatistics = async () => {
  const response = await fetch(`${host}/api/failover-test/export/statistics/`, {
    headers: {
      Authorization: `Bearer ${await getAuthToken()}`,
    },
  });
  return await response.blob();
};

// =============================================================================
// Settings API
// =============================================================================

export const getFailoverTestSettings = async () => {
  return await request(`${host}/api/failover-test/settings/`);
};

// =============================================================================
// Default export with all functions
// =============================================================================

export default {
  getFailoverTestChannels,
  createFailoverTestChannel,
  getFailoverTestChannel,
  deleteFailoverTestChannel,
  getAvailableChannelsForImport,
  importChannelForTest,
  simulateFailoverInterrupt,
  startFailoverAutoSimulation,
  stopFailoverSimulation,
  stopAllSimulations,
  getSimulationStatus,
  getFailoverTestStatistics,
  resetFailoverTestStatistics,
  getFailoverTestLogs,
  exportFailoverTestLogs,
  exportFailoverTestStatistics,
  getFailoverTestSettings,
};
