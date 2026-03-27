import { EVENT_TYPES, PAYLOAD_TYPES, isValidPayloadType, isValidEventType } from '../types/messages';

const isObject = (value) => value !== null && typeof value === 'object' && !Array.isArray(value);

export const validateWsEnvelope = (input) => {
  if (!isObject(input)) return { ok: false, error: 'Envelope is not an object' };
  const eventType = input.event;
  if (typeof eventType !== 'string' || !isValidEventType(eventType)) {
    return { ok: false, error: 'Invalid event type' };
  }
  if (!('data' in input) || !isObject(input.data)) {
    return { ok: false, error: 'Missing event data object' };
  }
  return { ok: true, eventType, data: input.data };
};

export const validateMessageChunkData = (data) => {
  if (!isObject(data)) return { ok: false, error: 'Chunk data must be an object' };
  if (typeof data.is_final !== 'boolean') return { ok: false, error: 'Chunk missing is_final flag' };
  if (!data.is_final && typeof data.chunk !== 'string') {
    return { ok: false, error: 'Chunk event missing text content' };
  }
  return { ok: true };
};

export const validateAgentUpdateData = (data) => {
  if (!isObject(data)) return { ok: false, error: 'Agent state must be an object' };
  return { ok: true };
};

export const validatePayloadTriggerData = (data) => {
  if (!isObject(data)) return { ok: false, error: 'Payload trigger data must be an object' };
  if (typeof data.component_type !== 'string') {
    return { ok: false, error: 'component_type must be a string' };
  }
  return { ok: true };
};

export const validatePayloadTrigger = (trigger) => {
  if (!isObject(trigger)) return { ok: false, error: 'Trigger is not an object' };
  if (typeof trigger.type !== 'string') return { ok: false, error: 'Trigger missing type' };
  if (!isValidPayloadType(trigger.type)) return { ok: false, error: 'Unsupported payload type' };
  if (!('payload' in trigger)) return { ok: false, error: 'Trigger missing payload' };
  return { ok: true };
};

export const isSupportedPayloadType = (type) =>
  [PAYLOAD_TYPES.READINESS, PAYLOAD_TYPES.CALENDAR].includes(type);

export const safeJsonParse = (raw) => {
  try {
    return { ok: true, value: JSON.parse(raw) };
  } catch (error) {
    return { ok: false, error: error.message };
  }
};

export const isEventType = (type) => Object.values(EVENT_TYPES).includes(type);
