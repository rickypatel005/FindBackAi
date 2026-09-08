"use client";

import { useEffect, useMemo, useState } from "react";
import { Nav } from "@/components/Nav";
import { StatusBadge } from "@/components/StatusBadge";
import { EmptyState } from "@/components/EmptyState";
import { api, AdminStats, ApiError, DuplicatePair, ReportOut, ReportStatus, ReportType } from "@/lib/api";
import { useRequireAuth } from "@/lib/useRequireAuth";

/**
 * Admin Dashboard + Report Management (UIUX Sec. 5, Phase 7).
 * Phase 7 additions: type/status filters on the report table, and a
 * duplicate-review queue (SRS FR-16.1 — same-type high-similarity pairs,
 * flagged for the admin to decide on, never auto-merged).
 */

const STATUS_OPTIONS: ReportStatus[] = [
  "SEARCHING",
  "MATCH_FOUND",
  "RECOVERED",
  "UNCLAIMED",
  "POTENTIAL_OWNER_FOUND",
  "RETURNED",
  "CLOSED",
];

export default function AdminPage() {
  const { user, token, loading } = useRequireAuth();
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [reports, setReports] = useState<ReportOut[]>([]);
  const [duplicates, setDuplicates] = useState<DuplicatePair[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [fetching, setFetching] = useState(true);
  const [typeFilter, setTypeFilter] = useState<ReportType | "ALL">("ALL");
  const [statusFilter, setStatusFilter] = useState<ReportStatus | "ALL">("ALL");

  useEffect(() => {
    if (!token || loading) return;
    if (user && user.role !== "Admin") {
      setError("Admin role required.");
      setFetching(false);
      return;
    }
    Promise.all([api.adminStats(token), api.adminReports(token), api.adminDuplicates(token)])
      .then(([s, r, d]) => {
        setStats(s);
        setReports(r);
        setDuplicates(d);
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load admin data."))
      .finally(() => setFetching(false));
  }, [token, user, loading]);

  const filteredReports = useMemo(
    () =>
      reports.filter((r) => {
        if (typeFilter !== "ALL" && r.type !== typeFilter) return false;
        if (statusFilter !== "ALL" && r.status !== statusFilter) return false;
        return true;
      }),
    [reports, typeFilter, statusFilter]
  );

  async function moderate(id: string, action: "remove" | "close" | "mark_duplicate") {
    if (!token) return;
    const updated = await api.adminModerate(token, id, action);
    setReports((prev) => prev.map((r) => (r.id === id ? updated : r)));
  }

  function dismissDuplicate(reportAId: string, reportBId: string) {
    setDuplicates((prev) =>
      prev.filter((d) => !(d.report_a.id === reportAId && d.report_b.id === reportBId))
    );
  }

  if (loading || fetching) return <p className="p-8 text-slate-500">Loading…</p>;

  return (
    <>
      <Nav user={user} />
      <main className="mx-auto max-w-5xl px-6 py-10">
        <h1 className="text-2xl font-semibold text-slate-900">Admin Dashboard</h1>

        {error ? (
          <p className="mt-4 text-status-danger">{error}</p>
        ) : (
          <>
            {stats && (
              <>
                <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-6">
                  <div className="rounded-xl border border-slate-200 bg-white p-4">
                    <p className="text-2xl font-semibold text-slate-900">{stats.total}</p>
                    <p className="mt-0.5 text-xs text-slate-500">Total Reports</p>
                  </div>
                  <div className="rounded-xl border border-slate-200 bg-white p-4">
                    <p className="text-2xl font-semibold text-lost-dark">{stats.lost}</p>
                    <p className="mt-0.5 text-xs text-slate-500">Lost Items</p>
                  </div>
                  <div className="rounded-xl border border-slate-200 bg-white p-4">
                    <p className="text-2xl font-semibold text-found-dark">{stats.found}</p>
                    <p className="mt-0.5 text-xs text-slate-500">Found Items</p>
                  </div>
                  <div className="rounded-xl border border-slate-200 bg-white p-4">
                    <p className="text-2xl font-semibold text-amber-600">{stats.potential_matches}</p>
                    <p className="mt-0.5 text-xs text-slate-500">Potential Matches</p>
                  </div>
                  <div className="rounded-xl border border-slate-200 bg-white p-4">
                    <p className="text-2xl font-semibold text-emerald-600">{stats.recovered}</p>
                    <p className="mt-0.5 text-xs text-slate-500">Recovered ({stats.recovery_rate ?? 0}%)</p>
                  </div>
                  <div className="rounded-xl border border-slate-200 bg-white p-4">
                    <p className="text-2xl font-semibold text-slate-900">{stats.pending_review}</p>
                    <p className="mt-0.5 text-xs text-slate-500">Pending Review</p>
                  </div>
                </div>

                {stats.category_counts && Object.keys(stats.category_counts).length > 0 && (
                  <div className="mt-6 rounded-xl border border-slate-200 bg-white p-4">
                    <h3 className="text-sm font-semibold text-slate-900">Category Distribution</h3>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {Object.entries(stats.category_counts).map(([cat, count]) => (
                        <div
                          key={cat}
                          className="flex items-center gap-1.5 rounded-lg bg-slate-100 px-3 py-1 text-xs text-slate-700"
                        >
                          <span className="font-medium text-slate-900">{cat}:</span>
                          <span>{count}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}

            <section className="mt-8">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h2 className="text-lg font-semibold text-slate-900">Reports</h2>
                <div className="flex gap-2">
                  <select
                    value={typeFilter}
                    onChange={(e) => setTypeFilter(e.target.value as ReportType | "ALL")}
                    className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm focus:border-slate-500 focus:outline-none"
                  >
                    <option value="ALL">All types</option>
                    <option value="LOST">Lost</option>
                    <option value="FOUND">Found</option>
                  </select>
                  <select
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value as ReportStatus | "ALL")}
                    className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm focus:border-slate-500 focus:outline-none"
                  >
                    <option value="ALL">All statuses</option>
                    {STATUS_OPTIONS.map((s) => (
                      <option key={s} value={s}>
                        {s.replaceAll("_", " ")}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="mt-4 overflow-x-auto rounded-xl border border-slate-200 bg-white">
                <table className="w-full min-w-[640px] text-left text-sm">
                  <thead className="border-b border-slate-200 text-xs uppercase text-slate-400">
                    <tr>
                      <th className="px-4 py-3">Title</th>
                      <th className="px-4 py-3">Type</th>
                      <th className="px-4 py-3">Status</th>
                      <th className="px-4 py-3">Category</th>
                      <th className="px-4 py-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {filteredReports.map((r) => (
                      <tr key={r.id}>
                        <td className="px-4 py-3 font-medium text-slate-800">{r.title}</td>
                        <td className="px-4 py-3 text-slate-500">{r.type}</td>
                        <td className="px-4 py-3">
                          <StatusBadge status={r.status} />
                        </td>
                        <td className="px-4 py-3 text-slate-500">{r.category}</td>
                        <td className="px-4 py-3">
                          <div className="flex justify-end gap-2 text-xs">
                            <button onClick={() => moderate(r.id, "mark_duplicate")} className="text-slate-500 hover:text-slate-800">
                              Mark duplicate
                            </button>
                            <button onClick={() => moderate(r.id, "close")} className="text-slate-500 hover:text-slate-800">
                              Close
                            </button>
                            <button onClick={() => moderate(r.id, "remove")} className="text-status-danger hover:underline">
                              Remove
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {filteredReports.length === 0 && (
                  <p className="p-6 text-center text-sm text-slate-500">No reports match these filters.</p>
                )}
              </div>
            </section>

            <section className="mt-10">
              <h2 className="text-lg font-semibold text-slate-900">Duplicate review queue</h2>
              <p className="mt-1 text-sm text-slate-600">
                Same-type reports flagged for very high image/text similarity (FR-16.1). Never
                auto-merged — review each pair and decide.
              </p>

              {duplicates.length === 0 ? (
                <div className="mt-4">
                  <EmptyState title="Nothing to review" body="No high-similarity same-type pairs right now." />
                </div>
              ) : (
                <div className="mt-4 flex flex-col gap-3">
                  {duplicates.map((d) => (
                    <div
                      key={`${d.report_a.id}-${d.report_b.id}`}
                      className="rounded-xl border border-amber-300 bg-amber-50 p-4"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="text-sm font-semibold text-slate-900">
                          {d.type} · {Math.round(d.similarity)}% similar
                        </p>
                        <div className="flex gap-2 text-xs">
                          <button
                            onClick={() =>
                              moderate(d.report_b.id, "mark_duplicate").then(() =>
                                dismissDuplicate(d.report_a.id, d.report_b.id)
                              )
                            }
                            className="rounded-md bg-white px-2.5 py-1 font-medium text-slate-700 hover:bg-slate-100"
                          >
                            Mark 2nd report duplicate
                          </button>
                          <button
                            onClick={() => dismissDuplicate(d.report_a.id, d.report_b.id)}
                            className="rounded-md px-2.5 py-1 font-medium text-slate-500 hover:text-slate-700"
                          >
                            Not a duplicate
                          </button>
                        </div>
                      </div>
                      <div className="mt-3 grid gap-3 sm:grid-cols-2">
                        {[d.report_a, d.report_b].map((r) => (
                          <div key={r.id} className="rounded-lg border border-amber-200 bg-white p-3">
                            <p className="font-medium text-slate-900">{r.title}</p>
                            <p className="mt-0.5 text-xs text-slate-500">
                              {r.category} · {r.color} · {r.location}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </>
        )}
      </main>
    </>
  );
}
