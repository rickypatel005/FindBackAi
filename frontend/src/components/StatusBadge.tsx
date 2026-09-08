import { clsx } from "clsx";
import type { ReportStatus } from "@/lib/api";

// Semantic status bands per 04_UIUX.md Sec. 11 — color is always paired
// with a text label (Sec. 10 Accessibility: never rely on color alone).
const BAND: Record<ReportStatus, { label: string; classes: string }> = {
  SEARCHING: { label: "Searching", classes: "bg-slate-100 text-slate-700 border-slate-300" },
  UNCLAIMED: { label: "Unclaimed", classes: "bg-slate-100 text-slate-700 border-slate-300" },
  MATCH_FOUND: { label: "Match found", classes: "bg-amber-50 text-status-warning border-amber-300" },
  POTENTIAL_OWNER_FOUND: {
    label: "Potential owner found",
    classes: "bg-amber-50 text-status-warning border-amber-300",
  },
  RECOVERED: { label: "Recovered", classes: "bg-emerald-50 text-status-success border-emerald-300" },
  RETURNED: { label: "Returned", classes: "bg-emerald-50 text-status-success border-emerald-300" },
  CLOSED: { label: "Closed", classes: "bg-slate-100 text-status-neutral border-slate-300" },
};

export function StatusBadge({ status }: { status: ReportStatus }) {
  const band = BAND[status] ?? BAND.CLOSED;
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium",
        band.classes
      )}
    >
      {band.label}
    </span>
  );
}
