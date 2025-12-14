/**
 * MAC Portal WebSocket Hook
 * 
 * Provides real-time updates for MAC Portal dashboard.
 * Requirements: 54.1, 54.2, 54.3, 54.4
 */

import { useState, useEffect, useCallback, useRef } from 'react';

const WS_RECONNECT_DELAY = 3000;
const WS_MAX_RECONNECT_ATTEMPTS = 5;

/**
 * Hook for MAC Portal WebSocket connection
 * @param {number} accountId - The M3U account ID to subscribe to
 * @param {Object} options - Configuration options
 * @returns {Object} WebSocket state and handlers
 */
const useMACPortalWebSocket = (accountId, options = {}) => {
  const {
    onMACStatusUpdate,
    onFailoverEvent,
    onLogMessage,
    onConnectionChange,
    autoConnect = true,
  } = options;

  const [connected, setConnected] = useState(false);
  const [reconnecting, setReconnecting] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  
  const wsRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef(null);

  const getWebSocketUrl = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    return `${protocol}//${host}/ws/mac-portal/${accountId}/`;
  }, [accountId]);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      const url = getWebSocketUrl();
      wsRef.current = new WebSocket(url);

      wsRef.current.onopen = () => {
        console.log('MAC Portal WebSocket connected');
        setConnected(true);
        setReconnecting(false);
        reconnectAttemptsRef.current = 0;
        onConnectionChange?.(true);
      };

      wsRef.current.onclose = (event) => {
        console.log('MAC Portal WebSocket closed:', event.code, event.reason);
        setConnected(false);
        onConnectionChange?.(false);

        // Attempt reconnection if not intentionally closed
        if (event.code !== 1000 && reconnectAttemptsRef.current < WS_MAX_RECONNECT_ATTEMPTS) {
          setReconnecting(true);
          reconnectAttemptsRef.current += 1;
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log(`Reconnecting... (attempt ${reconnectAttemptsRef.current})`);
            connect();
          }, WS_RECONNECT_DELAY);
        }
      };

      wsRef.current.onerror = (error) => {
        console.error('MAC Portal WebSocket error:', error);
      };

      wsRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setLastMessage(data);
          handleMessage(data);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
    }
  }, [getWebSocketUrl, onConnectionChange]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close(1000, 'Client disconnect');
      wsRef.current = null;
    }
    setConnected(false);
    setReconnecting(false);
  }, []);

  const handleMessage = useCallback((data) => {
    switch (data.type) {
      case 'mac_status_update':
        onMACStatusUpdate?.(data.payload);
        break;
      case 'failover_event':
        onFailoverEvent?.(data.payload);
        break;
      case 'log_message':
        onLogMessage?.(data.payload);
        break;
      case 'health_update':
        onMACStatusUpdate?.(data.payload);
        break;
      default:
        console.log('Unknown WebSocket message type:', data.type);
    }
  }, [onMACStatusUpdate, onFailoverEvent, onLogMessage]);

  const sendMessage = useCallback((type, payload) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type, payload }));
    } else {
      console.warn('WebSocket not connected, cannot send message');
    }
  }, []);

  const subscribe = useCallback((channel) => {
    sendMessage('subscribe', { channel });
  }, [sendMessage]);

  const unsubscribe = useCallback((channel) => {
    sendMessage('unsubscribe', { channel });
  }, [sendMessage]);

  // Auto-connect on mount
  useEffect(() => {
    if (autoConnect && accountId) {
      connect();
    }
    return () => {
      disconnect();
    };
  }, [accountId, autoConnect, connect, disconnect]);

  return {
    connected,
    reconnecting,
    lastMessage,
    connect,
    disconnect,
    sendMessage,
    subscribe,
    unsubscribe,
  };
};

export default useMACPortalWebSocket;
