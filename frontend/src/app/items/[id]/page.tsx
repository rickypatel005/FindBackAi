"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { clsx } from "clsx";
import { Nav } from "@/components/Nav";
import { Button } from "@/components/Button";
import { StatusBadge } from "@/components/StatusBadge";
import { api, ApiError, NEXT_STATUS, ReportOut } from "@/lib/api";
import { useRequireAuth } from "@/lib/useRequireAuth";

export default function ReportDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { user, token, loading } = useRequireAuth();
  const [report, setReport] = useState<ReportOut | null>(null);
  const [fetching, setFetching] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!token) return;
    api
      .getReport(token, params.id)
      .then(setReport)
      .catch(() => setError("Report not found."))
      .finally(() => setFetching(false));
  }, [token, params.id]);

  async function handleFindMatches() {
    if (!token || !report) return;
    setBusy(true);
    try {
      await api.findMatches(token, report.id);
      router.push(`/matches/${report.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't check for matches right now.");
      setBusy(false);
    }
  }

  async function handleStatus(next: ReportOut["status"]) {
    if (!token || !report) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await api.updateReportStatus(token, report.id, next);
      setReport(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't update the status.");
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete() {
    if (!token || !report) return;
    if (!confirm("Delete this report? This can't be undone.")) return;
    setBusy(true);
    try {
      await api.deleteReport(token, report.id);
      router.push("/items");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't delete the report.");
      setBusy(false);
    }
  }

  if (loading || fetching) return <p className="p-8 text-slate-500">Loading…</p>;

  return (
    <>
      <Nav user={user} />
      <main className="mx-auto max-w-2xl px-6 py-10">
        {error && !report ? (
          <p className="text-status-danger">{error}</p>
        ) : report ? (
          <>
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
            <h1 className="mt-2 text-2xl font-semibold text-slate-900">{report.title}</h1>

            {report.image_urls.length > 0 && (
              <div className="mt-4 flex gap-3">
                {report.image_urls.map((src, i) => (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    key={i}
                    src={src}
                    alt={`${report.title} photo ${i + 1}`}
                    className="h-32 w-32 rounded-lg object-cover"
                  />
                ))}
              </div>
            )}

            <dl className="mt-6 grid grid-cols-2 gap-4 text-sm">
              <div>
                <dt className="text-slate-400">Category</dt>
                <dd className="text-slate-800">{report.category}</dd>
              </div>
              <div>
                <dt className="text-slate-400">Color</dt>
                <dd className="text-slate-800">{report.color}</dd>
              </div>
              {report.brand && (
                <div>
                  <dt className="text-slate-400">Brand</dt>
                  <dd className="text-slate-800">{report.brand}</dd>
                </div>
              )}
              <div>
                <dt className="text-slate-400">Location</dt>
                <dd className="text-slate-800">{report.location}</dd>
              </div>
              <div>
                <dt className="text-slate-400">Date</dt>
                <dd className="text-slate-800">
                  {report.report_date} {report.report_time ?? ""}
                </dd>
              </div>
            </dl>

            <div className="mt-4">
              <dt className="text-sm text-slate-400">Description</dt>
              <dd className="mt-1 text-slate-700">{report.description}</dd>
            </div>
            {report.features && (
              <div className="mt-4">
                <dt className="text-sm text-slate-400">Distinguishing features</dt>
                <dd className="mt-1 text-slate-700">{report.features}</dd>
              </div>
            )}

            {error && (
              <p role="alert" className="mt-4 text-sm text-status-danger">
                {error}
              </p>
            )}

            <div className="mt-8 flex flex-wrap gap-3">
              <Button variant={report.type === "LOST" ? "lost" : "found"} onClick={handleFindMatches} disabled={busy}>
                Check for matches
              </Button>
              {(NEXT_STATUS[report.status] ?? []).map((t) => (
                <Button key={t.next} variant="neutral" disabled={busy} onClick={() => handleStatus(t.next)}>
                  {t.label}
                </Button>
              ))}
              <button
                onClick={handleDelete}
                disabled={busy}
                className="ml-auto rounded-lg px-4 py-2.5 font-medium text-status-danger hover:bg-red-50 disabled:opacity-50"
              >
                Delete report
              </button>
            </div>
          </>
        ) : null}
      </main>
    </>
  );
}
