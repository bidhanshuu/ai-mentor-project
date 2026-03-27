import { create } from 'zustand';

const baseMetrics = {
  connectAttempts: 0,
  reconnectCount: 0,
  sentMessages: 0,
  receivedEvents: 0,
  lastConnectedAt: null,
  lastDisconnectedAt: null,
  lastErrorAt: null,
};

export const useConnectionStore = create((set) => ({
  status: 'disconnected',
  session: null,
  error: null,
  metrics: { ...baseMetrics },

  setConnected: (session = null) =>
    set((state) => ({
      status: 'connected',
      session: session || state.session,
      error: null,
      metrics: {
        ...state.metrics,
        lastConnectedAt: Date.now(),
      },
    })),

  setConnecting: () =>
    set((state) => ({
      status: 'connecting',
      metrics: {
        ...state.metrics,
        connectAttempts: state.metrics.connectAttempts + 1,
      },
    })),

  setDisconnected: () =>
    set((state) => ({
      status: 'disconnected',
      metrics: {
        ...state.metrics,
        lastDisconnectedAt: Date.now(),
      },
    })),

  setReconnecting: () =>
    set((state) => ({
      status: 'reconnecting',
      metrics: {
        ...state.metrics,
        reconnectCount: state.metrics.reconnectCount + 1,
      },
    })),

  setSession: (session) => set({ session }),

  setError: (error) =>
    set((state) => ({
      error,
      metrics: {
        ...state.metrics,
        lastErrorAt: Date.now(),
      },
    })),

  clearError: () => set({ error: null }),

  updateMetrics: (patch) =>
    set((state) => ({
      metrics: {
        ...state.metrics,
        ...(typeof patch === 'function' ? patch(state.metrics) : patch),
      },
    })),

  resetMetrics: () => set({ metrics: { ...baseMetrics } }),
}));
