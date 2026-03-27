import { useState, useRef, useCallback, useEffect } from 'react';
import config from '../config/api.config';
import sessionService from '../services/sessionService';
import { useChatStore } from '../store/chatStore';
import { useConnectionStore } from '../store/connectionStore';
import {
  EVENT_TYPES,
  MESSAGE_ROLES,
  createPayloadTrigger,
  getEventDisplayTag,
  getEventColor,
} from '../types/messages';
import { createReconnectPolicy, getReconnectDelay, canRetryReconnect } from '../utils/reconnect';
import {
  safeJsonParse,
  validateWsEnvelope,
  validateAgentUpdateData,
  validateMessageChunkData,
  validatePayloadTriggerData,
} from '../utils/validators';

const INFO_COLOR = '#6b7280';
const RECONNECT_POLICY = createReconnectPolicy({ maxRetries: 5, baseDelayMs: 1000, maxDelayMs: 20000 });

export const useAutoMentorSocket = () => {
  const [events, setEvents] = useState([]);
  const [isAwaitingStream, setIsAwaitingStream] = useState(false);
  const [reconnectState, setReconnectState] = useState({
    attempts: 0,
    maxAttempts: RECONNECT_POLICY.maxRetries,
    nextDelay: 0,
    countdown: 0,
  });

  const wsRef = useRef(null);
  const streamIdRef = useRef(null);
  const streamSenderRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectTickRef = useRef(null);
  const reconnectAttemptRef = useRef(0);
  const connectRef = useRef(null);
  const userIdRef = useRef('user_001');
  const manualCloseRef = useRef(false);

  const connectionStatus = useConnectionStore((state) => state.status);
  const session = useConnectionStore((state) => state.session);
  const lastError = useConnectionStore((state) => state.error);
  const metrics = useConnectionStore((state) => state.metrics);

  const messages = useChatStore((state) => state.messages);
  const currentStreamingMessage = useChatStore((state) => state.streamingMessage);
  const agentStatus = useChatStore((state) => state.agentStatus);
  const addMessage = useChatStore((state) => state.addMessage);
  const updateStream = useChatStore((state) => state.updateStream);
  const setAgentStatus = useChatStore((state) => state.setAgentStatus);
  const clearHistory = useChatStore((state) => state.clearHistory);
  const restoreFromStorage = useChatStore((state) => state.restoreFromStorage);
  const persistToStorage = useChatStore((state) => state.persistToStorage);

  const setConnecting = useConnectionStore((state) => state.setConnecting);
  const setConnected = useConnectionStore((state) => state.setConnected);
  const setDisconnected = useConnectionStore((state) => state.setDisconnected);
  const setReconnecting = useConnectionStore((state) => state.setReconnecting);
  const setSession = useConnectionStore((state) => state.setSession);
  const setError = useConnectionStore((state) => state.setError);
  const clearError = useConnectionStore((state) => state.clearError);
  const updateMetrics = useConnectionStore((state) => state.updateMetrics);

  const getTimestamp = () => {
    const now = new Date();
    return now.toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      fractionalSecondDigits: 3,
    });
  };

  const addEvent = useCallback((tag, message, data = null, color = INFO_COLOR) => {
    const evt = {
      id: `${Date.now()}-${Math.random()}`,
      timestamp: getTimestamp(),
      tag,
      message,
      data,
      color,
    };
    setEvents((prev) => [...prev, evt]);
    return evt;
  }, []);

  const addTypedEvent = useCallback(
    (eventType, message, data = null) =>
      addEvent(getEventDisplayTag(eventType), message, data, getEventColor(eventType)),
    [addEvent]
  );

  const clearReconnectTimers = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (reconnectTickRef.current) {
      clearInterval(reconnectTickRef.current);
      reconnectTickRef.current = null;
    }
  }, []);

  const resetReconnectState = useCallback(() => {
    reconnectAttemptRef.current = 0;
    setReconnectState({
      attempts: 0,
      maxAttempts: RECONNECT_POLICY.maxRetries,
      nextDelay: 0,
      countdown: 0,
    });
  }, []);

  const handleMessage = useCallback(
    (rawEvent) => {
      const parsed = safeJsonParse(rawEvent.data);
      if (!parsed.ok) {
        setError(`Invalid message format: ${parsed.error}`);
        addTypedEvent(EVENT_TYPES.ERROR, `Failed to parse message: ${parsed.error}`);
        return;
      }

      const envelope = validateWsEnvelope(parsed.value);
      if (!envelope.ok) {
        setError(envelope.error);
        addTypedEvent(EVENT_TYPES.ERROR, envelope.error);
        return;
      }

      const { eventType, data } = envelope;
      try {
        updateMetrics((s) => ({ receivedEvents: s.receivedEvents + 1 }));

        switch (eventType) {
          case EVENT_TYPES.CONNECTION_ESTABLISHED:
            setConnected();
            clearReconnectTimers();
            resetReconnectState();
            addTypedEvent(EVENT_TYPES.CONNECTION_ESTABLISHED, 'WebSocket connection established', data);
            break;
          
          // NEW SIMPLIFIED HANDLING: Mentor always streams, diagnostic/planning optional
          case EVENT_TYPES.MESSAGE_CHUNK:
            // Primary event: mentor response (always streamed)
            setIsAwaitingStream(false);
            if (!validateMessageChunkData(data).ok) {
              addTypedEvent(EVENT_TYPES.ERROR, 'Invalid message chunk payload');
              return;
            }
            
            const sender = data.sender || 'assistant';
            
            // Handle sender switch (if response changes source)
            if (
              streamIdRef.current &&
              streamSenderRef.current &&
              streamSenderRef.current !== sender
            ) {
              updateStream({
                chunk: '',
                isFinal: true,
                sender: streamSenderRef.current,
                messageId: streamIdRef.current,
                meta: {
                  eventType: EVENT_TYPES.MESSAGE_CHUNK,
                  sender: streamSenderRef.current,
                },
              });
              streamIdRef.current = null;
              streamSenderRef.current = null;
            }

            // Initialize stream if first chunk
            if (!streamIdRef.current) {
              streamIdRef.current = `stream-${Date.now()}`;
              streamSenderRef.current = sender;
              addTypedEvent(EVENT_TYPES.MESSAGE_CHUNK, `${sender} responding...`, { sender });
            }

            // Update stream with latest chunk
            updateStream({
              chunk: data.chunk || '',
              isFinal: Boolean(data.is_final),
              sender,
              messageId: streamIdRef.current,
              meta: {
                eventType: EVENT_TYPES.MESSAGE_CHUNK,
                sender,
              },
            });

            // Clean up refs when stream ends
            if (data.is_final) {
              streamIdRef.current = null;
              streamSenderRef.current = null;
            }
            break;
          
          // NEW EVENT: Optional diagnostic insight (appended after mentor response)
          case EVENT_TYPES.DIAGNOSTIC_INSIGHT:
            console.log('[useAutoMentorSocket] Diagnostic insight received');
            addMessage({
              role: 'assistant',
              content: data.text || '',
              status: 'final',
              meta: {
                eventType: EVENT_TYPES.DIAGNOSTIC_INSIGHT,
                type: 'diagnostic',
              },
            });
            addTypedEvent(EVENT_TYPES.DIAGNOSTIC_INSIGHT, 'Analysis: ' + (data.text?.substring(0, 50) || ''), data);
            break;
          
          // NEW EVENT: Optional planning widget (study plan suggestion)
          case EVENT_TYPES.PLANNING_WIDGET:
            console.log('[useAutoMentorSocket] Planning widget received');
            const sessions = data.proposed_sessions || [];
            const readiness = data.estimated_readiness || '';
            addMessage({
              role: 'assistant',
              content: '[Study Plan Generated]',
              status: 'final',
              meta: {
                eventType: EVENT_TYPES.PLANNING_WIDGET,
                type: EVENT_TYPES.PLANNING_WIDGET,
                sessions,
                readiness,
                trigger: createPayloadTrigger({
                  type: 'calendar_widget',
                  action: 'show_plan',
                  payload: {
                    title: readiness || 'Personalized study plan',
                    items: sessions.map((session, index) => ({
                      id: `plan-${index}`,
                      title: session.subject || 'Study Session',
                      time: session.proposed_time || 'TBD',
                    })),
                  },
                }),
              },
            });
            addTypedEvent(
              EVENT_TYPES.PLANNING_WIDGET,
              'Study plan with ' + sessions.length + ' sessions',
              data
            );
            break;
          
          // LEGACY: Agent state updates (less frequent now, optional)
          case EVENT_TYPES.AGENT_STATE_UPDATE: {
            const check = validateAgentUpdateData(data);
            if (!check.ok) {
              addTypedEvent(EVENT_TYPES.ERROR, check.error);
              return;
            }
            // Optional: only log in dev, don't clutter UI
            console.debug('[useAutoMentorSocket] Agent state:', data);
            break;
          }
          
          // LEGACY: UI component triggers (kept for compatibility)
          case EVENT_TYPES.UI_COMPONENT_TRIGGER: {
            const check = validatePayloadTriggerData(data);
            if (!check.ok) {
              addTypedEvent(EVENT_TYPES.ERROR, check.error);
              return;
            }
            const componentType = data.component_type || 'unknown';
            const action = data.action || 'trigger';
            const trigger = createPayloadTrigger({
              type: componentType,
              action,
              payload: data.payload,
            });
            addMessage({
              role: MESSAGE_ROLES.PAYLOAD,
              content: `[Payload] ${componentType} (${action})`,
              status: 'final',
              meta: { eventType: EVENT_TYPES.UI_COMPONENT_TRIGGER, trigger },
            });
            addTypedEvent(
              EVENT_TYPES.UI_COMPONENT_TRIGGER,
              `UI Component: ${componentType} (${action})`,
              trigger
            );
            break;
          }
          
          // LEGACY: Request complete (less needed with simpler flow)
          case EVENT_TYPES.REQUEST_COMPLETE: {
            setIsAwaitingStream(false);
            console.debug('[useAutoMentorSocket] Request complete:', data);
            setAgentStatus(null);
            break;
          }
          case EVENT_TYPES.ERROR: {
            setIsAwaitingStream(false);
            const errorMsg = data.message || 'Unknown error';
            setError(errorMsg);
            addTypedEvent(EVENT_TYPES.ERROR, errorMsg, data);
            break;
          }
          default:
            addEvent('UNKNOWN', `Unknown event type: ${eventType}`, data);
        }
      } catch (error) {
        console.error('[WS] Parse error:', error);
        setError(`Failed to parse message: ${error.message}`);
        addTypedEvent(EVENT_TYPES.ERROR, `Failed to parse message: ${error.message}`);
      }
    },
    [
      addEvent,
      addMessage,
      addTypedEvent,
      clearReconnectTimers,
      resetReconnectState,
      setAgentStatus,
      setConnected,
      setError,
      updateMetrics,
      updateStream,
    ]
  );

  const scheduleReconnect = useCallback(() => {
    if (manualCloseRef.current) return;

    const attemptIndex = reconnectAttemptRef.current;
    if (!canRetryReconnect(attemptIndex, RECONNECT_POLICY)) {
      setError('Reconnection failed after maximum retries');
      setDisconnected();
      return;
    }

    const nextAttempt = attemptIndex + 1;
    const delay = getReconnectDelay(attemptIndex, RECONNECT_POLICY);
    setReconnecting();
    setReconnectState({
      attempts: nextAttempt,
      maxAttempts: RECONNECT_POLICY.maxRetries,
      nextDelay: delay,
      countdown: Math.ceil(delay / 1000),
    });

    clearReconnectTimers();
    reconnectTickRef.current = setInterval(() => {
      setReconnectState((prev) => ({
        ...prev,
        countdown: prev.countdown > 0 ? prev.countdown - 1 : 0,
      }));
    }, 1000);

    reconnectTimeoutRef.current = setTimeout(() => {
      reconnectAttemptRef.current = nextAttempt;
      clearReconnectTimers();
      if (connectRef.current) {
        connectRef.current(userIdRef.current, true);
      }
    }, delay);
  }, [clearReconnectTimers, setDisconnected, setError, setReconnecting]);

  const connect = useCallback(
    async (userId = 'user_001', isRetry = false) => {
      try {
        manualCloseRef.current = false;
        userIdRef.current = userId;
        if (!isRetry) {
          clearReconnectTimers();
          resetReconnectState();
        }
        setConnecting();

        const sessionData = await sessionService.initSession(userId);
        setSession(sessionData);
        const wsUrl = `${config.WS_BASE_URL}${config.ENDPOINTS.WS_CHAT}?token=${sessionData.token}`;
        wsRef.current = new WebSocket(wsUrl);

        wsRef.current.onopen = () => {
          setConnecting();
        };

        wsRef.current.onmessage = handleMessage;

        wsRef.current.onerror = (event) => {
          console.error('[WS] Error:', event);
          setError('WebSocket connection error');
          addTypedEvent(EVENT_TYPES.ERROR, 'WebSocket connection error');
        };

        wsRef.current.onclose = (event) => {
          setIsAwaitingStream(false);
          const reason = event.reason || 'Normal closure';
          setDisconnected();
          setSession(null);
          wsRef.current = null;
          sessionService.clearSession();
          if (!manualCloseRef.current) {
            addEvent('INFO', `Socket closed (${event.code}): ${reason}`);
            scheduleReconnect();
          }
        };
      } catch (error) {
        setIsAwaitingStream(false);
        console.error('[Session] Init failed:', error);
        setError(`Session init failed: ${error.message}`);
        setDisconnected();
        scheduleReconnect();
      }
    },
    [
      addEvent,
      addTypedEvent,
      clearReconnectTimers,
      handleMessage,
      resetReconnectState,
      scheduleReconnect,
      setConnecting,
      setDisconnected,
      setError,
      setSession,
    ]
  );

  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  const disconnect = useCallback(() => {
    manualCloseRef.current = true;
    clearReconnectTimers();
    resetReconnectState();
    if (wsRef.current) {
      wsRef.current.close(1000, 'Client disconnect');
      wsRef.current = null;
    }
    setDisconnected();
    setSession(null);
    sessionService.clearSession();
  }, [clearReconnectTimers, resetReconnectState, setDisconnected, setSession]);

  const sendUserMessage = useCallback(
    (content) => {
      if (!content?.trim()) {
        setError('Cannot send empty message');
        return false;
      }
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        setError('WebSocket not connected');
        return false;
      }
      const currentSession = useConnectionStore.getState().session;
      if (!currentSession?.sessionId) {
        setError('No session ID available');
        return false;
      }
      const payload = {
        event: 'user_message',
        data: { content: content.trim(), session_id: currentSession.sessionId },
      };
      try {
        addMessage({
          role: 'user',
          content: content.trim(),
          status: 'final',
          meta: { eventType: 'user_message' },
        });
        wsRef.current.send(JSON.stringify(payload));
        updateMetrics((s) => ({ sentMessages: s.sentMessages + 1 }));
        setIsAwaitingStream(true);
        return true;
      } catch (error) {
        setIsAwaitingStream(false);
        setError(`Send failed: ${error.message}`);
        return false;
      }
    },
    [addMessage, setError, updateMetrics]
  );

  const clearEvents = useCallback(() => {
    setEvents([]);
  }, []);

  useEffect(() => {
    restoreFromStorage();
  }, [restoreFromStorage]);

  useEffect(() => {
    persistToStorage();
  }, [messages, persistToStorage]);

  useEffect(
    () => () => {
      manualCloseRef.current = true;
      clearReconnectTimers();
      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmount');
      }
      streamIdRef.current = null;
      streamSenderRef.current = null;
    },
    [clearReconnectTimers]
  );

  return {
    connectionStatus,
    session,
    messages,
    currentStreamContent: currentStreamingMessage?.content || '',
    currentStreamingMessage,
    events,
    agentStatus,
    lastError,
    metrics,
    isAwaitingStream,
    reconnectState,
    connect,
    disconnect,
    sendUserMessage,
    clearEvents,
    clearError,
    clearHistory,
  };
};
