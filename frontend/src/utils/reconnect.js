const DEFAULTS = {
  maxRetries: 5,
  baseDelayMs: 1000,
  maxDelayMs: 30000,
  jitterRatio: 0.2,
};

export const createReconnectPolicy = (overrides = {}) => ({
  ...DEFAULTS,
  ...overrides,
});

export const getReconnectDelay = (attempt, policy = DEFAULTS) => {
  const safeAttempt = Math.max(0, Number(attempt) || 0);
  const expo = policy.baseDelayMs * 2 ** safeAttempt;
  const capped = Math.min(expo, policy.maxDelayMs);
  const jitter = capped * policy.jitterRatio * Math.random();
  return Math.round(capped + jitter);
};

export const canRetryReconnect = (attempt, policy = DEFAULTS) => {
  const max = Number(policy.maxRetries) || DEFAULTS.maxRetries;
  return attempt < max;
};
