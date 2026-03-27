import React from 'react';

const ConnectionMetrics = ({ status, metrics, reconnectState }) => {
  if (import.meta.env.PROD) return null;

  const rows = [
    ['Status', status],
    ['Connect attempts', metrics?.connectAttempts ?? 0],
    ['Reconnect count', metrics?.reconnectCount ?? 0],
    ['Sent', metrics?.sentMessages ?? 0],
    ['Received', metrics?.receivedEvents ?? 0],
    ['Retry attempt', reconnectState?.attempts ?? 0],
    ['Retry countdown', reconnectState?.countdown ?? 0],
  ];

  return (
    <aside className="border-t border-slate-200 bg-slate-900 px-3 py-2 text-xs text-slate-100 sm:px-4">
      <div className="mx-auto grid max-w-4xl grid-cols-2 gap-2 sm:grid-cols-4">
        {rows.map(([label, value]) => (
          <div key={label} className="rounded bg-slate-800 px-2 py-1">
            <div className="text-[10px] uppercase tracking-wide text-slate-400">{label}</div>
            <div className="font-mono text-slate-100">{String(value ?? '-')}</div>
          </div>
        ))}
      </div>
    </aside>
  );
};

export default ConnectionMetrics;
