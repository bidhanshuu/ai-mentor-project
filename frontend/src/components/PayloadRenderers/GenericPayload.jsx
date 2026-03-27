import React from 'react';

const GenericPayload = ({ trigger, reason }) => {
  const type = trigger?.type || 'unknown';
  const action = trigger?.action || 'n/a';
  const payload = trigger?.payload ?? null;

  return (
    <article className="w-full max-w-xl rounded-xl border border-slate-200 bg-slate-50 p-3 text-slate-700">
      <header className="mb-2 flex items-center justify-between gap-3">
        <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-600">UI Payload</h4>
        <span className="rounded bg-slate-200 px-2 py-0.5 font-mono text-[10px] text-slate-700">
          {type}
        </span>
      </header>
      <p className="mb-2 text-xs text-slate-600">
        <span className="font-semibold">Action:</span> {action}
      </p>
      {reason ? <p className="mb-2 text-xs text-red-700">Fallback reason: {reason}</p> : null}
      <pre className="max-h-48 overflow-auto rounded-lg bg-white p-2 text-xs text-slate-800">
        {JSON.stringify(payload, null, 2)}
      </pre>
    </article>
  );
};

export default GenericPayload;
