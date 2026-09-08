import { clsx } from "clsx";

// Visual 0-100 score representation (UIUX Sec. 6 "Score chip/bar"). Color
// band communicates strength; the numeric label always accompanies it
// (Sec. 10 — never rely on color alone).
function band(score: number) {
  if (score >= 70) return "bg-status-success";
  if (score >= 40) return "bg-status-warning";
  return "bg-status-neutral";
}

export function ScoreBar({ label, score }: { label: string; score: number }) {
  const pct = Math.max(0, Math.min(100, score));
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-xs text-slate-600">
        <span>{label}</span>
        <span className="font-medium text-slate-800">{Math.round(pct)}</span>
      </div>
      <div className="h-2 w-full rounded-full bg-slate-100">
        <div className={clsx("h-2 rounded-full", band(pct))} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export function ScoreChip({ score }: { score: number }) {
  const pct = Math.round(Math.max(0, Math.min(100, score)));
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full px-3 py-1 text-sm font-semibold text-white",
        band(pct)
      )}
    >
      {pct}% match
    </span>
  );
}
