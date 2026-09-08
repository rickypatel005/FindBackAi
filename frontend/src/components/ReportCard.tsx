import Link from "next/link";
import { ReportOut } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";
import { clsx } from "clsx";

export function ReportCard({ report }: { report: ReportOut }) {
  const thumb = report.image_urls[0];
  return (
    <Link
      href={`/items/${report.id}`}
      className="flex gap-4 rounded-xl border border-slate-200 bg-white p-4 transition-shadow hover:shadow-sm"
    >
      <div className="h-20 w-20 shrink-0 overflow-hidden rounded-lg bg-slate-100">
        {thumb ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={thumb} alt={report.title} className="h-full w-full object-cover" />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-xs text-slate-400">No photo</div>
        )}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span
            className={clsx(
              "text-xs font-semibold uppercase tracking-wide",
              report.type === "LOST" ? "text-lost" : "text-found"
            )}
          >
            {report.type}
          </span>
          <StatusBadge status={report.status} />
        </div>
        <h3 className="mt-1 truncate font-semibold text-slate-900">{report.title}</h3>
        <p className="mt-0.5 truncate text-sm text-slate-500">
          {report.category} · {report.color} · {report.location}
        </p>
        <p className="mt-0.5 text-xs text-slate-400">{report.report_date}</p>
      </div>
    </Link>
  );
}
