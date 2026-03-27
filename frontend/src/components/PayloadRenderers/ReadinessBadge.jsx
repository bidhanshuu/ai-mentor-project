import React from 'react';

const clamp = (n) => Math.min(100, Math.max(0, Number(n) || 0));
const getBarClass = (score) => {
  if (score >= 100) return 'w-full';
  if (score >= 92) return 'w-11/12';
  if (score >= 83) return 'w-10/12';
  if (score >= 75) return 'w-9/12';
  if (score >= 67) return 'w-8/12';
  if (score >= 58) return 'w-7/12';
  if (score >= 50) return 'w-6/12';
  if (score >= 42) return 'w-5/12';
  if (score >= 33) return 'w-4/12';
  if (score >= 25) return 'w-3/12';
  if (score >= 17) return 'w-2/12';
  if (score >= 8) return 'w-1/12';
  return 'w-0';
};

const ReadinessBadge = ({ data }) => {
  const score = clamp(data?.score ?? 0);
  const level = data?.level || 'Unknown';
  const label = data?.label || 'Topic Assessment';

  const tone =
    score >= 80
      ? {
          box: 'border-emerald-200 bg-emerald-50 text-emerald-800',
          bar: 'bg-emerald-500',
          pill: 'bg-emerald-200 text-emerald-900',
        }
      : score >= 50
      ? {
          box: 'border-amber-200 bg-amber-50 text-amber-800',
          bar: 'bg-amber-500',
          pill: 'bg-amber-200 text-amber-900',
        }
      : {
          box: 'border-red-200 bg-red-50 text-red-800',
          bar: 'bg-red-500',
          pill: 'bg-red-200 text-red-900',
        };

  return (
    <article className={`w-full max-w-sm rounded-xl border p-4 shadow-sm ${tone.box}`}>
      <header className="mb-3 flex items-start justify-between gap-3">
        <h3 className="text-sm font-semibold tracking-tight">{label}</h3>
        <span className={`rounded-full px-2.5 py-1 text-[10px] font-bold uppercase ${tone.pill}`}>
          {level}
        </span>
      </header>
      <div className="flex items-center gap-3">
        <strong className="text-3xl font-black tabular-nums">{score}%</strong>
        <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-black/10">
          <div
            className={`h-full transition-all duration-700 ease-out ${tone.bar} ${getBarClass(score)}`}
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={score}
            aria-label="Readiness score"
          />
        </div>
      </div>
    </article>
  );
};

export default ReadinessBadge;
