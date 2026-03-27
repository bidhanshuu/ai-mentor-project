export const MESSAGE_ROLES = {
  USER: 'user',
  ASSISTANT: 'assistant',
  SYSTEM: 'system',
  PAYLOAD: 'payload',
};

// alias so both names work in components/hooks
export const MESSAGE_TYPES = MESSAGE_ROLES;

export const EVENT_TYPES = {
  CONNECTION_ESTABLISHED: 'connection_established',
  AGENT_STATE_UPDATE: 'agent_state_update',
  MESSAGE_CHUNK: 'message_chunk',
  UI_COMPONENT_TRIGGER: 'ui_component_trigger',
  PLANNING_WIDGET: 'planning_widget',
  REQUEST_COMPLETE: 'request_complete',
  DIAGNOSTIC_INSIGHT: 'diagnostic_insight',
  ERROR: 'error',
};

// kept for backward compatibility
export const WS_EVENTS = {
  CONNECTED: EVENT_TYPES.CONNECTION_ESTABLISHED,
  AGENT_UPDATE: EVENT_TYPES.AGENT_STATE_UPDATE,
  CHUNK: EVENT_TYPES.MESSAGE_CHUNK,
  UI_TRIGGER: EVENT_TYPES.UI_COMPONENT_TRIGGER,
  PLANNING: EVENT_TYPES.PLANNING_WIDGET,
  COMPLETE: EVENT_TYPES.REQUEST_COMPLETE,
  DIAGNOSTIC: EVENT_TYPES.DIAGNOSTIC_INSIGHT,
  ERROR: EVENT_TYPES.ERROR,
};

export const PAYLOAD_TYPES = {
  CALENDAR: 'calendar_widget',
  READINESS: 'readiness_badge',
  QUIZ: 'quiz_widget',
  PROGRESS: 'progress_tracker',
  RESOURCE: 'resource_card',
  GENERIC: 'generic',
};

export const CONNECTION_STATUS = {
  DISCONNECTED: 'disconnected',
  INITIALIZING: 'initializing',
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  RECONNECTING: 'reconnecting',
  ERROR: 'error',
};

export const AGENT_TYPES = {
  MENTOR: 'Mentor Agent',
  DIAGNOSTIC: 'Diagnostic Agent',
  PLANNING: 'Planning Agent',
};

export const SYSTEM_MESSAGE_TYPES = {
  TIMEOUT: 'timeout',
  INTERRUPT: 'interrupt',
  COMPLETE: 'complete',
  ERROR: 'error',
  INFO: 'info',
};

const EVENT_UI = {
  [EVENT_TYPES.CONNECTION_ESTABLISHED]: {
    tag: 'CONNECTED',
    color: '#10b981',
    colorClass: 'text-emerald-600 bg-emerald-50',
  },
  [EVENT_TYPES.AGENT_STATE_UPDATE]: {
    tag: 'AGENT',
    color: '#f97316',
    colorClass: 'text-orange-600 bg-orange-50',
  },
  [EVENT_TYPES.MESSAGE_CHUNK]: {
    tag: 'STREAM',
    color: '#3b82f6',
    colorClass: 'text-blue-600 bg-blue-50',
  },
  [EVENT_TYPES.UI_COMPONENT_TRIGGER]: {
    tag: 'PAYLOAD',
    color: '#22c55e',
    colorClass: 'text-green-600 bg-green-50',
  },
  [EVENT_TYPES.REQUEST_COMPLETE]: {
    tag: 'DONE',
    color: '#8b5cf6',
    colorClass: 'text-violet-600 bg-violet-50',
  },
  [EVENT_TYPES.PLANNING_WIDGET]: {
    tag: 'PLAN',
    color: '#14b8a6',
    colorClass: 'text-teal-600 bg-teal-50',
  },
  [EVENT_TYPES.DIAGNOSTIC_INSIGHT]: {
    tag: 'ANALYSIS',
    color: '#ec4899',
    colorClass: 'text-pink-600 bg-pink-50',
  },
  [EVENT_TYPES.ERROR]: {
    tag: 'ERROR',
    color: '#ef4444',
    colorClass: 'text-red-600 bg-red-50',
  },
};

const id = (prefix) => `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;

export const isValidMessageType = (type) => Object.values(MESSAGE_TYPES).includes(type);
export const isValidEventType = (type) => Object.values(EVENT_TYPES).includes(type);
export const isValidPayloadType = (type) => Object.values(PAYLOAD_TYPES).includes(type);

export function getAgentDisplayName(agentType) {
  const map = {
    mentor: AGENT_TYPES.MENTOR,
    diagnostic: AGENT_TYPES.DIAGNOSTIC,
    planning: AGENT_TYPES.PLANNING,
  };
  return map[String(agentType || '').toLowerCase()] || agentType || 'Unknown Agent';
}

export const getEventConfig = (eventType) =>
  EVENT_UI[eventType] || { tag: 'UNKNOWN', color: '#6b7280', colorClass: 'text-slate-600 bg-slate-50' };

export const getEventDisplayTag = (eventType) => getEventConfig(eventType).tag;
export const getEventColor = (eventType) => getEventConfig(eventType).color;

// returns your current app shape (role/meta/createdAt/status)
export const createMessage = ({
  role,
  type,
  sender,
  content,
  metadata = {},
  meta = {},
  hidden = false,
  status = 'final',
}) => {
  const msgRole = role || type || MESSAGE_ROLES.SYSTEM;
  if (!isValidMessageType(msgRole)) {
    console.warn('[messages] invalid message role/type:', msgRole);
  }

  return {
    id: id('msg'),
    role: isValidMessageType(msgRole) ? msgRole : MESSAGE_ROLES.SYSTEM,
    content: content ?? '',
    status,
    createdAt: new Date().toISOString(),
    meta: { sender, hidden, ...metadata, ...meta },
  };
};

export const createPayloadTrigger = ({ type, action, payload, data }) => {
  const nextType = isValidPayloadType(type) ? type : PAYLOAD_TYPES.GENERIC;
  if (nextType !== type) {
    console.warn('[messages] invalid payload type, falling back to generic:', type);
  }

  return {
    id: id('trigger'),
    type: nextType,
    action,
    payload: payload ?? data ?? null,
    timestamp: new Date().toISOString(),
  };
};

export const isMessage = (obj) => {
  if (!obj || typeof obj !== 'object') return false;
  const role = obj.role || obj.type;
  return Boolean(obj.id && isValidMessageType(role) && typeof obj.content === 'string');
};

export const isPayloadTrigger = (obj) =>
  Boolean(obj && typeof obj === 'object' && obj.id && obj.type && 'payload' in obj);

export const isConnected = (status) => status === CONNECTION_STATUS.CONNECTED;
export const isConnecting = (status) =>
  [CONNECTION_STATUS.INITIALIZING, CONNECTION_STATUS.CONNECTING, CONNECTION_STATUS.RECONNECTING].includes(
    status
  );
