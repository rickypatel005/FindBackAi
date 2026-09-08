"use client";

import { useEffect, useMemo, useState } from "react";
import { Nav } from "@/components/Nav";
import { ReportCard } from "@/components/ReportCard";
import { EmptyState } from "@/components/EmptyState";
import { api, ReportOut, ReportType } from "@/lib/api";
import { useRequireAuth } from "@/lib/useRequireAuth";
import { clsx } from "clsx";

type Tab = "ALL" | ReportType;

export default function MyItemsPage() {
  const { user, token, loading } = useRequireAuth();
  const [reports, setReports] = useState<ReportOut[]>([]);
  const [fetching, setFetching] = useState(true);
  const [tab, setTab] = useState<Tab>("ALL");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");

  useEffect(() => {
    if (!token) return;
    api
      .myReports(token)
      .then(setReports)
      .finally(() => setFetching(false));
  }, [token]);

  const statuses = useMemo(() => Array.from(new Set(reports.map((r) => r.status))), [reports]);

  const filtered = reports.filter((r) => {
    if (tab !== "ALL" && r.type !== tab) return false;
    if (statusFilter !== "ALL" && r.status !== statusFilter) return false;
    return true;
  });

  if (loading) return <p className="p-8 text-slate-500">Loading…</p>;

  return (
    <>
      <Nav user={user} />
      <main className="mx-auto max-w-4xl px-6 py-10">
        <h1 className="text-2xl font-semibold text-slate-900">My Items</h1>
        <p className="mt-1 text-slate-600">Reports you&apos;ve submitted, lost and found.</p>

        <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
          <div className="flex gap-1 rounded-lg bg-slate-100 p-1">
            {(["ALL", "LOST", "FOUND"] as Tab[]).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={clsx(
                  "rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                  tab === t ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700"
                )}
              >
                {t === "ALL" ? "All" : t === "LOST" ? "Lost" : "Found"}
              </button>
            ))}
          </div>

          {statuses.length > 0 && (
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm focus:border-slate-500 focus:outline-none"
            >
              <option value="ALL">All statuses</option>
              {statuses.map((s) => (
                <option key={s} value={s}>
                  {s.replaceAll("_", " ")}
                </option>
              ))}
            </select>
          )}
        </div>

        <div className="mt-6 flex flex-col gap-3">
          {fetching ? (
            <p className="text-slate-500">Loading your reports…</p>
          ) : filtered.length === 0 ? (
            <EmptyState
              title="No reports yet"
              body="Report a lost or found item and it'll show up here."
              ctaLabel="Report an item"
              ctaHref="/report/lost"
            />
          ) : (
            filtered.map((r) => <ReportCard key={r.id} report={r} />)
          )}
        </div>
      </main>
    </>
  );
}
