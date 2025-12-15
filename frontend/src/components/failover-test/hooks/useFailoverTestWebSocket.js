/**
 * WebSocket Hook for Failover Test Page
 * 
 * Manages WebSocket connection for real-time updates.
 * Requirements: 10.1, 10.2, 10.3, 10.4
 */

import { useState, useEffect, useRef, useCallback } from 'react';

const WS_RECONNECT_DELAY = 1000;
const WS_MAX_RECONNECT_DELAY = 30000;

const useFailoverTestWebSocket = ({ onEvent }) => {
  const [connected, setConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState(null);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectDelayRef = useRef(WS_RECONNECT_DELAY);
  const onEventRef = useRef(onEvent);
  const isConnectingRef = useRef(false);

  // Keep onEvent ref updated without causing reconnects
  useEffect(() => {
    onEventRef.current = onEvent;
  }, [onEvent]);

  const connect = useCallback(() => {
    // Prevent multiple simultaneous connection attempts
    if (isConnectingRef.current || (wsRef.current && wsRef.current.readyState === WebSocket.OPEN)) {
      return;
    }
    isConnectingRef.current = true;

    // Build WebSocket URL
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/ws/failover-test/`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('Failover test WebSocket connected');
        setConnected(true);
        reconnectDelayRef.current = WS_RECONNECT_DELAY;
        isConnectingRef.current = false;

        // Request initial state
        ws.send(JSON.stringify({ type: 'get_status' }));
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setLastEvent(data);
          
          if (onEventRef.current) {
            onEventRef.current(data);
          }
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      ws.onclose = (event) => {
        console.log('Failover test WebSocket disconnected:', event.code);
        setConnected(false);
        wsRef.current = null;
        isConnectingRef.current = false;

        // Attempt reconnection with exponential backoff only for unexpected closes
        if (!event.wasClean && event.code !== 1000) {
          scheduleReconnect();
        }
      };

      ws.onerror = (error) => {
        console.error('Failover test WebSocket error:', error);
        isConnectingRef.current = false;
      };
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      isConnectingRef.current = false;
      scheduleReconnect();
    }
  }, []); // No dependencies - stable function

  const scheduleReconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }

    reconnectTimeoutRef.current = setTimeout(() => {
      console.log(`Reconnecting in ${reconnectDelayRef.current}ms...`);
      connect();
      
      // Exponential backoff
      reconnectDelayRef.current = Math.min(
        reconnectDelayRef.current * 2,
        WS_MAX_RECONNECT_DELAY
      );
    }, reconnectDelayRef.current);
  }, [connect]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close(1000, 'Component unmounted');
      wsRef.current = null;
    }

    setConnected(false);
  }, []);

  const send = useCallback((message) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  }, []);

  const subscribeToChannel = useCallback((channelId) => {
    send({ type: 'subscribe_channel', channel_id: channelId });
  }, [send]);

  const unsubscribeFromChannel = useCallback((channelId) => {
    send({ type: 'unsubscribe_channel', channel_id: channelId });
  }, [send]);

  const requestLogs = useCallback((limit = 50) => {
    send({ type: 'get_logs', limit });
  }, [send]);

  // Connect on mount, disconnect on unmount
  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return {
    connected,
    lastEvent,
    send,
    subscribeToChannel,
    unsubscribeFromChannel,
    requestLogs,
    reconnect: connect,
  };
};

export default useFailoverTestWebSocket;
