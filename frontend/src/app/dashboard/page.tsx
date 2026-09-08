"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Nav } from "@/components/Nav";
import { ReportCard } from "@/components/ReportCard";
import { EmptyState } from "@/components/EmptyState";
import { api, NotificationOut, ReportOut } from "@/lib/api";
import { useRequireAuth } from "@/lib/useRequireAuth";

const RECOVERED_STATUSES = new Set(["RECOVERED", "RETURNED"]);
const POTENTIAL_STATUSES = new Set(["MATCH_FOUND", "POTENTIAL_OWNER_FOUND"]);

export default function DashboardPage() {
  const { user, token, loading } = useRequireAuth();
  const [reports, setReports] = useState<ReportOut[]>([]);
  const [notifications, setNotifications] = useState<NotificationOut[]>([]);
  const [fetching, setFetching] = useState(true);

  useEffect(() => {
    if (!token) return;
    Promise.all([api.myReports(token), api.listNotifications(token)])
      .then(([r, n]) => {
        setReports(r);
        setNotifications(n);
      })
      .finally(() => setFetching(false));
  }, [token]);

  if (loading) return <p className="p-8 text-slate-500">Loading…</p>;

  const lostCount = reports.filter((r) => r.type === "LOST").length;
  const foundCount = reports.filter((r) => r.type === "FOUND").length;
  const potentialCount = reports.filter((r) => POTENTIAL_STATUSES.has(r.status)).length;
  const recoveredCount = reports.filter((r) => RECOVERED_STATUSES.has(r.status)).length;
  const unread = notifications.filter((n) => !n.is_read);
  const recent = [...reports]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 4);

  return (
    <>
      <Nav user={user} unreadCount={unread.length} />
      <main className="mx-auto max-w-4xl px-6 py-10">
        <h1 className="text-2xl font-semibold text-slate-900">
          Welcome{user?.name ? `, ${user.name}` : ""}
        </h1>
        <p className="mt-1 text-slate-600">Here&apos;s what&apos;s happening with your reports.</p>

        <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatCard label="Lost items" value={lostCount} />
          <StatCard label="Found items" value={foundCount} />
          <StatCard label="Potential matches" value={potentialCount} />
          <StatCard label="Recovered" value={recoveredCount} />
        </div>

        <div className="mt-8 grid gap-4 sm:grid-cols-2">
          <Link href="/report/lost" className="rounded-xl border border-lost-light bg-white p-6 hover:shadow-sm">
            <h2 className="font-semibold text-lost-dark">Report Lost Item</h2>
            <p className="mt-1 text-sm text-slate-600">Lost something? Start a report and let AI find matches.</p>
          </Link>
          <Link href="/report/found" className="rounded-xl border border-found-light bg-white p-6 hover:shadow-sm">
            <h2 className="font-semibold text-found-dark">Report Found Item</h2>
            <p className="mt-1 text-sm text-slate-600">Found something? Report it to help reunite it with its owner.</p>
          </Link>
        </div>

        <section className="mt-10">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-slate-900">Recent reports</h2>
            <Link href="/items" className="text-sm font-medium text-slate-500 hover:text-slate-700">
              View all
            </Link>
          </div>
          <div className="mt-4 flex flex-col gap-3">
            {fetching ? (
              <p className="text-slate-500">Loading…</p>
            ) : recent.length === 0 ? (
              <EmptyState
                title="No reports yet"
                body="Report a lost or found item to get started."
                ctaLabel="Report an item"
                ctaHref="/report/lost"
              />
            ) : (
              recent.map((r) => <ReportCard key={r.id} report={r} />)
            )}
          </div>
        </section>

        <section className="mt-10">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-slate-900">Notifications</h2>
            <Link href="/notifications" className="text-sm font-medium text-slate-500 hover:text-slate-700">
              View all
            </Link>
          </div>
          <div className="mt-4 rounded-xl border border-slate-200 bg-white">
            {unread.length === 0 ? (
              <p className="p-6 text-sm text-slate-500">No unread notifications.</p>
            ) : (
              unread.slice(0, 3).map((n) => (
                <div key={n.id} className="border-b border-slate-100 px-5 py-3 last:border-b-0">
                  <p className="text-sm font-semibold text-slate-900">{n.title}</p>
                  <p className="text-sm text-slate-500">{n.message}</p>
                </div>
              ))
            )}
          </div>
        </section>
      </main>
    </>
  );
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <p className="text-2xl font-semibold text-slate-900">{value}</p>
      <p className="mt-0.5 text-xs text-slate-500">{label}</p>
    </div>
  );
}
