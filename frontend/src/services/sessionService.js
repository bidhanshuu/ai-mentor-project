/**
 * Session Service
 * Handles authentication and credential management
 */

import config from '../config/api.config';

class SessionService {
  constructor() {
    this.session = null;
  }

  async initSession(userId = 'user_001') {
    try {
      const response = await fetch(
        `${config.API_BASE_URL}${config.ENDPOINTS.SESSION_INIT}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_id: userId, device_id: null }),
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();

      if (!data.session_id || !data.websocket_token) {
        throw new Error('Invalid response: missing credentials');
      }

      this.session = {
        sessionId: data.session_id,
        token: data.websocket_token,
        userProfile: data.user_profile,
        createdAt: Date.now(),
      };

      return this.session;
    } catch (error) {
      console.error('[SessionService] Init failed:', error);
      throw error;
    }
  }

  getSession() {
    return this.session;
  }

  clearSession() {
    this.session = null;
  }
}

export default new SessionService();