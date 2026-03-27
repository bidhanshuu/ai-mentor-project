import React from 'react';

const getConfig = (status, reconnectState) => {
  switch (status) {
    case 'connected':
      return {
        icon: '●',
        label: 'Connected',
        retry: false,
        cls: 'border-emerald-200 bg-emerald-50 text-emerald-700',
      };
    case 'connecting':
    case 'initializing':
      return {
        icon: '⟳',
        label: 'Connecting...',
        retry: false,
        cls: 'border-amber-200 bg-amber-50 text-amber-700',
      };
    case 'reconnecting': {
      const attempts = reconnectState?.attempts ?? 0;
      const maxAttempts = reconnectState?.maxAttempts ?? 5;
      const countdown = reconnectState?.countdown ?? 0;
      return {
        icon: '⟳',
        label: `Reconnecting (${attempts}/${maxAttempts}) in ${countdown}s`,
        retry: true,
        cls: 'border-orange-200 bg-orange-50 text-orange-700',
      };
    }
    default:
      return {
        icon: '○',
        label: 'Disconnected',
        retry: true,
        cls: 'border-red-200 bg-red-50 text-red-700',
      };
  }
};

const ConnectionStatus = ({ connectionStatus, error, reconnectState, onRetry, onClearError }) => {
  const cfg = getConfig(connectionStatus, reconnectState);
  const isConnecting = ['connecting', 'initializing', 'reconnecting'].includes(connectionStatus);

  return (
    <section className="w-full" aria-live="polite">
      <div className={`flex items-center justify-between border-b px-3 py-2 text-xs font-semibold sm:px-4 ${cfg.cls}`}>
        <div className="flex items-center gap-2">
          <span className={`inline-block text-sm ${isConnecting ? 'animate-spin' : ''}`} aria-hidden="true">
            {cfg.icon}
          </span>
          <span>{cfg.label}</span>
        </div>
        {cfg.retry && typeof onRetry === 'function' ? (
          <button
            type="button"
            onClick={onRetry}
            className="rounded-md border border-current bg-white px-2 py-0.5 text-xs font-semibold transition hover:opacity-80"
          >
            Retry
          </button>
        ) : null}
      </div>

      {error ? (
        <div className="flex items-center justify-between border-b border-red-200 bg-red-100 px-3 py-2 text-sm text-red-800 sm:px-4">
          <div className="flex items-center gap-2">
            <span aria-hidden="true">⚠️</span>
            <span>{error}</span>
          </div>
          {typeof onClearError === 'function' ? (
            <button
              type="button"
              onClick={onClearError}
              aria-label="Clear error"
              className="p-0 text-xl leading-none text-red-700 transition hover:text-red-900"
            >
              ×
            </button>
          ) : null}
        </div>
      ) : null}
    </section>
  );
};

export default ConnectionStatus;
