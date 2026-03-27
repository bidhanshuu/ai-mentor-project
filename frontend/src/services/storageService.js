const CHAT_STORAGE_KEY = 'automentor.chat.v1';

class StorageService {
  getChatHistory() {
    try {
      const raw = localStorage.getItem(CHAT_STORAGE_KEY);
      if (!raw) return { messages: [] };
      return JSON.parse(raw);
    } catch (error) {
      console.error('[StorageService] Failed to read chat history:', error);
      return { messages: [] };
    }
  }

  setChatHistory(payload) {
    try {
      localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(payload));
      return true;
    } catch (error) {
      console.error('[StorageService] Failed to write chat history:', error);
      return false;
    }
  }

  clearChatHistory() {
    try {
      localStorage.removeItem(CHAT_STORAGE_KEY);
      return true;
    } catch (error) {
      console.error('[StorageService] Failed to clear chat history:', error);
      return false;
    }
  }
}

export default new StorageService();
