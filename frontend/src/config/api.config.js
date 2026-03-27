/**
 * API Configuration
 * Centralized endpoint management
 */

const config = {
  API_BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000',
  WS_BASE_URL: import.meta.env.VITE_WS_BASE_URL || 'ws://127.0.0.1:8000',
  
  ENDPOINTS: {
    SESSION_INIT: '/api/v1/session/init',
    WS_CHAT: '/ws/chat',
  },
  
  VERSION: '1.0.0',
};

if (!config.API_BASE_URL || !config.WS_BASE_URL) {
  throw new Error('[CONFIG] Missing required environment variables');
}

export default config;