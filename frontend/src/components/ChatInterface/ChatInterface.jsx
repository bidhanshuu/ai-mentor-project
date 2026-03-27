import React, { useEffect } from 'react';
import { useChatWebSocket } from '../../hooks/useChatWebSocket';
import ConnectionStatus from './ConnectionStatus';
import MessageHistory from './MessageHistory';
import InputPanel from './InputPanel';
import ConnectionMetrics from '../DevTools/ConnectionMetrics';

const ChatInterface = () => {
  const {
    connectionStatus,
    messages,
    currentStreamingMessage,
    lastError,
    metrics,
    isAwaitingStream,
    reconnectState,
    connect,
    sendUserMessage,
    clearError,
  } = useChatWebSocket();

  const isStreaming = Boolean(currentStreamingMessage?.content);
  const disabledInput = connectionStatus !== 'connected';
  const showDevTools = import.meta.env.DEV;

  useEffect(() => {
    connect('user_001');
  }, [connect]);

  return (
    <main className="flex h-screen w-full flex-col bg-slate-100 text-slate-900">
      <ConnectionStatus
        connectionStatus={connectionStatus}
        error={lastError}
        reconnectState={reconnectState}
        onRetry={() => connect()}
        onClearError={clearError}
      />
      <MessageHistory messages={messages} streamingMessage={currentStreamingMessage} />
      <InputPanel
        onSendMessage={sendUserMessage}
        disabled={disabledInput}
        isStreaming={isStreaming}
        isAwaitingStream={isAwaitingStream}
      />
      {showDevTools ? (
        <ConnectionMetrics
          status={connectionStatus}
          metrics={metrics}
          reconnectState={reconnectState}
        />
      ) : null}
    </main>
  );
};

export default ChatInterface;
