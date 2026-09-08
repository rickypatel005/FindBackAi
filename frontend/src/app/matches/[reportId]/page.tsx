"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Nav } from "@/components/Nav";
import { EmptyState } from "@/components/EmptyState";
import { ScoreChip } from "@/components/ScoreBar";
import { api, MatchOut, ReportOut } from "@/lib/api";
import { useRequireAuth } from "@/lib/useRequireAuth";

/**
 * Potential Matches list (UIUX Sec. 5/6): ranked list, each item shows a
 * thumbnail, score, and top explanation chips. FR-09.2 — top 3-5 shown.
 */
export default function PotentialMatchesPage() {
  const params = useParams<{ reportId: string }>();
  const { user, token, loading } = useRequireAuth();
  const [matches, setMatches] = useState<MatchOut[]>([]);
  const [reports, setReports] = useState<Record<string, ReportOut>>({});
  const [fetching, setFetching] = useState(true);

  useEffect(() => {
    if (!token) return;
    api
      .getMatches(token, params.reportId)
      .then(async (ms) => {
        setMatches(ms.slice(0, 5));
        const ids = Array.from(new Set(ms.flatMap((m) => [m.lost_report_id, m.found_report_id])));
        const loaded = await Promise.all(
          ids.map((id) => api.getReport(token, id).catch(() => null))
        );
        const map: Record<string, ReportOut> = {};
        loaded.forEach((r) => {
          if (r) map[r.id] = r;
        });
        setReports(map);
      })
      .finally(() => setFetching(false));
  }, [token, params.reportId]);

  if (loading || fetching) return <p className="p-8 text-slate-500">Loading…</p>;

  return (
    <>
      <Nav user={user} />
      <main className="mx-auto max-w-2xl px-6 py-10">
        <h1 className="text-2xl font-semibold text-slate-900">Potential matches</h1>
        <p className="mt-1 text-slate-600">Ranked by how closely each candidate matches your report.</p>

        <div className="mt-6 flex flex-col gap-3">
          {matches.length === 0 ? (
            <EmptyState
              title="No matches yet"
              body="We'll keep checking as new reports come in — you'll get a notification if a strong match appears."
              ctaLabel="Back to My Items"
              ctaHref="/items"
            />
          ) : (
            matches.map((m) => {
              const other = reports[m.lost_report_id === params.reportId ? m.found_report_id : m.lost_report_id];
              return (
                <Link
                  key={m.id}
                  href={`/matches/details/${m.id}`}
                  className="flex gap-4 rounded-xl border border-slate-200 bg-white p-4 hover:shadow-sm"
                >
                  <div className="h-16 w-16 shrink-0 overflow-hidden rounded-lg bg-slate-100">
                    {other?.image_urls[0] && (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={other.image_urls[0]} alt={other.title} className="h-full w-full object-cover" />
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-2">
                      <h3 className="truncate font-semibold text-slate-900">{other?.title ?? "Report"}</h3>
                      <ScoreChip score={m.final_score} />
                    </div>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {m.explanation.slice(0, 2).map((reason) => (
                        <span
                          key={reason}
                          className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600"
                        >
                          {reason}
                        </span>
                      ))}
                    </div>
                  </div>
                </Link>
              );
            })
          )}
        </div>
      </main>
    </>
  );
}
