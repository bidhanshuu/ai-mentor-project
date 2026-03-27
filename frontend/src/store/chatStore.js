import { create } from 'zustand';
import storageService from '../services/storageService';

const normalizeMessage = (message) => ({
  id: message.id || `msg-${Date.now()}-${Math.random()}`,
  role: message.role || 'assistant',
  content: message.content || '',
  status: message.status || 'final',
  createdAt: message.createdAt || new Date().toISOString(),
  meta: message.meta || {},
});

export const useChatStore = create((set, get) => ({
  messages: [],
  streamingMessage: null,
  agentStatus: null,
  isHydrated: false,
  lastSyncedAt: null,

  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, normalizeMessage(message)],
      lastSyncedAt: Date.now(),
    })),

  updateStream: ({ chunk = '', isFinal = false, sender = 'assistant', messageId, meta = {} }) =>
    set((state) => {
      const existing = state.streamingMessage;
      const id = messageId || existing?.id || `stream-${Date.now()}`;
      const role = sender === 'user' ? 'user' : 'assistant';

      const nextStreaming = {
        id,
        role,
        content: `${existing?.content || ''}${chunk}`,
        status: isFinal ? 'final' : 'streaming',
        createdAt: existing?.createdAt || new Date().toISOString(),
        meta: { ...(existing?.meta || {}), ...meta },
      };

      if (!isFinal) {
        return { streamingMessage: nextStreaming };
      }

      return {
        messages: [...state.messages, nextStreaming],
        streamingMessage: null,
        lastSyncedAt: Date.now(),
      };
    }),

  setAgentStatus: (agentStatus) => set({ agentStatus }),

  clearHistory: () =>
    set(() => {
      storageService.clearChatHistory();
      return {
      messages: [],
      streamingMessage: null,
      agentStatus: null,
      lastSyncedAt: Date.now(),
      };
    }),

  restoreFromStorage: () => {
    try {
      const parsed = storageService.getChatHistory();
      if (!parsed || !Array.isArray(parsed.messages)) {
        set({ isHydrated: true });
        return;
      }

      const messages = parsed.messages.map((message) => normalizeMessage(message));

      set({
        messages,
        streamingMessage: null,
        agentStatus: null,
        isHydrated: true,
        lastSyncedAt: Date.now(),
      });
    } catch (error) {
      console.error('[chatStore] Failed to restore from storage:', error);
      set({ isHydrated: true });
    }
  },

  persistToStorage: () => {
    try {
      const payload = { messages: get().messages };
      storageService.setChatHistory(payload);
    } catch (error) {
      console.error('[chatStore] Failed to persist to storage:', error);
    }
  },
}));
