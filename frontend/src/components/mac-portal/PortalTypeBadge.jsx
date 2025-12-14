/**
 * Portal Type Badge Component
 * 
 * Displays portal type with appropriate styling.
 * Requirements: 63.1, 63.2
 */

import React from 'react';
import { Badge, Tooltip } from '@mantine/core';
import { 
  IconServer, 
  IconCloud, 
  IconBrandChrome,
  IconQuestionMark,
} from '@tabler/icons-react';

const PORTAL_TYPES = {
  stalker: { label: 'Stalker', color: 'blue', icon: IconServer },
  xtream: { label: 'Xtream', color: 'green', icon: IconCloud },
  xui: { label: 'XUI.ONE', color: 'violet', icon: IconBrandChrome },
  magload: { label: 'MagLoad', color: 'orange', icon: IconServer },
  xuione: { label: 'XUIONE', color: 'teal', icon: IconCloud },
  stalker_userpass: { label: 'Stalker (User/Pass)', color: 'indigo', icon: IconServer },
  unknown: { label: 'Unknown', color: 'gray', icon: IconQuestionMark },
};

const PortalTypeBadge = ({ type, confidence, showConfidence = false, size = 'sm' }) => {
  const typeInfo = PORTAL_TYPES[type] || PORTAL_TYPES.unknown;
  const Icon = typeInfo.icon;
  
  const badge = (
    <Badge 
      color={typeInfo.color} 
      variant="light"
      size={size}
      leftSection={<Icon size={12} />}
    >
      {typeInfo.label}
      {showConfidence && confidence !== undefined && (
        <span style={{ marginLeft: 4, opacity: 0.7 }}>
          ({Math.round(confidence * 100)}%)
        </span>
      )}
    </Badge>
  );
  
  if (confidence !== undefined) {
    return (
      <Tooltip label={`Detection confidence: ${Math.round(confidence * 100)}%`}>
        {badge}
      </Tooltip>
    );
  }
  
  return badge;
};

export default PortalTypeBadge;
