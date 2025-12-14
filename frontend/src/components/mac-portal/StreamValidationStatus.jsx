/**
 * Stream Validation Status Component
 * 
 * Displays stream validation status.
 * Requirements: 70.1, 70.2, 70.3, 70.4, 70.5
 */

import React from 'react';
import { Badge, Group, Text, Tooltip, ThemeIcon } from '@mantine/core';
import { 
  IconCheck, 
  IconX, 
  IconLoader,
  IconAlertTriangle,
  IconWorldOff,
  IconServer,
} from '@tabler/icons-react';

const STATUS_CONFIG = {
  broadcasting: {
    label: 'Broadcasting',
    color: 'green',
    icon: IconCheck,
    description: 'Stream is active and accessible',
  },
  not_broadcasting: {
    label: 'Not Broadcasting',
    color: 'red',
    icon: IconX,
    description: 'Stream is not currently available',
  },
  geo_blocked: {
    label: 'GEO Blocked',
    color: 'orange',
    icon: IconWorldOff,
    description: 'Stream is blocked in your region',
  },
  server_error: {
    label: 'Server Error',
    color: 'red',
    icon: IconServer,
    description: 'Portal server returned an error',
  },
  timeout: {
    label: 'Timeout',
    color: 'yellow',
    icon: IconAlertTriangle,
    description: 'Stream validation timed out',
  },
  validating: {
    label: 'Validating...',
    color: 'blue',
    icon: IconLoader,
    description: 'Checking stream status',
  },
  unknown: {
    label: 'Unknown',
    color: 'gray',
    icon: IconAlertTriangle,
    description: 'Stream status could not be determined',
  },
};

const StreamValidationStatus = ({ 
  status, 
  httpStatus, 
  responseTime,
  showDetails = false,
  size = 'sm',
}) => {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.unknown;
  const Icon = config.icon;
  
  const badge = (
    <Badge 
      color={config.color} 
      variant="light"
      size={size}
      leftSection={
        status === 'validating' ? (
          <Icon size={12} className="animate-spin" />
        ) : (
          <Icon size={12} />
        )
      }
    >
      {config.label}
    </Badge>
  );
  
  if (!showDetails) {
    return (
      <Tooltip label={config.description}>
        {badge}
      </Tooltip>
    );
  }
  
  return (
    <Group gap="xs">
      <Tooltip label={config.description}>
        {badge}
      </Tooltip>
      {httpStatus && (
        <Text size="xs" c="dimmed">
          HTTP {httpStatus}
        </Text>
      )}
      {responseTime && (
        <Text size="xs" c="dimmed">
          {responseTime}ms
        </Text>
      )}
    </Group>
  );
};

export const getStatusFromHttpCode = (httpStatus) => {
  if (!httpStatus) return 'unknown';
  
  if (httpStatus >= 200 && httpStatus < 400) {
    return 'broadcasting';
  } else if (httpStatus === 451) {
    return 'geo_blocked';
  } else if (httpStatus >= 500) {
    return 'server_error';
  } else if (httpStatus === 404 || httpStatus === 403) {
    return 'not_broadcasting';
  }
  
  return 'unknown';
};

export default StreamValidationStatus;
