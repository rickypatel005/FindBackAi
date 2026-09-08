"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { clsx } from "clsx";
import { Nav } from "@/components/Nav";
import { EmptyState } from "@/components/EmptyState";
import { api, NotificationOut } from "@/lib/api";
import { useRequireAuth } from "@/lib/useRequireAuth";

export default function NotificationsPage() {
  const { user, token, loading } = useRequireAuth();
  const [items, setItems] = useState<NotificationOut[]>([]);
  const [fetching, setFetching] = useState(true);

  useEffect(() => {
    if (!token) return;
    api
      .listNotifications(token)
      .then(setItems)
      .finally(() => setFetching(false));
  }, [token]);

  async function markRead(id: string) {
    if (!token) return;
    const updated = await api.markNotificationRead(token, id);
    setItems((prev) => prev.map((n) => (n.id === id ? updated : n)));
  }

  if (loading || fetching) return <p className="p-8 text-slate-500">Loading…</p>;
  const unread = items.filter((n) => !n.is_read).length;

  return (
    <>
      <Nav user={user} unreadCount={unread} />
      <main className="mx-auto max-w-2xl px-6 py-10">
        <h1 className="text-2xl font-semibold text-slate-900">Notifications</h1>

        <div className="mt-6 flex flex-col divide-y divide-slate-200 rounded-xl border border-slate-200 bg-white">
          {items.length === 0 ? (
            <div className="p-6">
              <EmptyState title="No notifications" body="We'll let you know when a strong match appears." />
            </div>
          ) : (
            items.map((n) => (
              <Link
                key={n.id}
                href={`/matches/details/${n.match_id}`}
                onClick={() => !n.is_read && markRead(n.id)}
                className={clsx("flex items-start gap-3 px-5 py-4 hover:bg-slate-50", !n.is_read && "bg-slate-50/70")}
              >
                <span
                  className={clsx(
                    "mt-1.5 h-2 w-2 shrink-0 rounded-full",
                    n.is_read ? "bg-transparent" : "bg-lost"
                  )}
                />
                <div className="min-w-0 flex-1">
                  <p className={clsx("text-sm", n.is_read ? "text-slate-600" : "font-semibold text-slate-900")}>
                    {n.title}
                  </p>
                  <p className="mt-0.5 text-sm text-slate-500">{n.message}</p>
                  <p className="mt-1 text-xs text-slate-400">{new Date(n.created_at).toLocaleString()}</p>
                </div>
              </Link>
            ))
          )}
        </div>
      </main>
    </>
  );
}
