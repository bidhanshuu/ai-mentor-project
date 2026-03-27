import React from 'react';

const normalizeItems = (data) => {
  if (!data) return [];
  if (Array.isArray(data.events)) return data.events;
  if (Array.isArray(data.items)) return data.items;
  if (Array.isArray(data)) return data;
  return [];
};

const CalendarWidget = ({ data }) => {
  const title = data?.title || 'Upcoming schedule';
  const events = normalizeItems(data);

  return (
    <article className="w-full max-w-xl rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <header className="mb-3 flex items-center justify-between">
        <h4 className="text-sm font-semibold text-slate-800">{title}</h4>
        <span className="rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700">
          {events.length} items
        </span>
      </header>

      {events.length === 0 ? (
        <p className="text-sm text-slate-500">No calendar items available.</p>
      ) : (
        <ul className="grid gap-2 sm:grid-cols-2">
          {events.map((item, idx) => (
            <li key={`${item?.id || item?.title || 'event'}-${idx}`} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <p className="text-sm font-medium text-slate-800">{item?.title || 'Untitled event'}</p>
              <p className="mt-1 text-xs text-slate-600">{item?.date || item?.time || 'TBD'}</p>
            </li>
          ))}
        </ul>
      )}
    </article>
  );
};

export default CalendarWidget;
