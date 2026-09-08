"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { clsx } from "clsx";
import { Nav } from "@/components/Nav";
import { ScoreBar, ScoreChip } from "@/components/ScoreBar";
import { StatusBadge } from "@/components/StatusBadge";
import { api, MatchOut, ReportOut } from "@/lib/api";
import { useRequireAuth } from "@/lib/useRequireAuth";

/**
 * Match Details (UIUX Sec. 5/6): lost/found reports side-by-side, final
 * score, all component scores, and the full explanation list (FR-11.1).
 * Stacks vertically below the tablet breakpoint (UIUX Sec. 9).
 */
export default function MatchDetailsPage() {
  const params = useParams<{ matchId: string }>();
  const { user, token, loading } = useRequireAuth();
  const [match, setMatch] = useState<MatchOut | null>(null);
  const [lost, setLost] = useState<ReportOut | null>(null);
  const [found, setFound] = useState<ReportOut | null>(null);
  const [fetching, setFetching] = useState(true);

  useEffect(() => {
    if (!token) return;
    api
      .getMatchDetails(token, params.matchId)
      .then(async (m) => {
        setMatch(m);
        const [l, f] = await Promise.all([
          api.getReport(token, m.lost_report_id),
          api.getReport(token, m.found_report_id),
        ]);
        setLost(l);
        setFound(f);
      })
      .finally(() => setFetching(false));
  }, [token, params.matchId]);

  if (loading || fetching) return <p className="p-8 text-slate-500">Loading…</p>;
  if (!match || !lost || !found) return <p className="p-8 text-slate-500">Match not found.</p>;

  return (
    <>
      <Nav user={user} />
      <main className="mx-auto max-w-4xl px-6 py-10">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold text-slate-900">Match details</h1>
          <ScoreChip score={match.final_score} />
        </div>

        <div className="mt-6 grid gap-6 sm:grid-cols-2">
          <ReportPanel report={lost} accent="lost" />
          <ReportPanel report={found} accent="found" />
        </div>

        <div className="mt-8 rounded-xl border border-slate-200 bg-white p-6">
          <h2 className="font-semibold text-slate-900">Score breakdown</h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <ScoreBar label="Image similarity" score={match.image_score} />
            <ScoreBar label="Text similarity" score={match.text_score} />
            <ScoreBar label="Category" score={match.category_score} />
            <ScoreBar label="Color" score={match.color_score} />
            <ScoreBar label="Brand" score={match.brand_score} />
            <ScoreBar label="Location" score={match.location_score} />
            <ScoreBar label="Time" score={match.time_score} />
            <ScoreBar label="Other attributes" score={match.other_score} />
          </div>
        </div>

        <div className="mt-6 rounded-xl border border-slate-200 bg-white p-6">
          <h2 className="font-semibold text-slate-900">Why this matched</h2>
          {match.explanation.length === 0 ? (
            <p className="mt-2 text-sm text-slate-500">
              No individual signal cleared the explanation threshold yet.
            </p>
          ) : (
            <ul className="mt-2 flex flex-wrap gap-2">
              {match.explanation.map((reason) => (
                <li key={reason} className="rounded-full bg-slate-100 px-3 py-1 text-sm text-slate-700">
                  {reason}
                </li>
              ))}
            </ul>
          )}
        </div>
      </main>
    </>
  );
}

function ReportPanel({ report, accent }: { report: ReportOut; accent: "lost" | "found" }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5">
      <div className="flex items-center gap-2">
        <span
          className={clsx(
            "text-xs font-semibold uppercase tracking-wide",
            accent === "lost" ? "text-lost" : "text-found"
          )}
        >
          {report.type}
        </span>
        <StatusBadge status={report.status} />
      </div>
      {report.image_urls[0] && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={report.image_urls[0]}
          alt={report.title}
          className="mt-3 h-40 w-full rounded-lg object-cover"
        />
      )}
      <h3 className="mt-3 font-semibold text-slate-900">{report.title}</h3>
      <p className="mt-1 text-sm text-slate-500">
        {report.category} · {report.color} · {report.location}
      </p>
      <p className="mt-2 text-sm text-slate-700">{report.description}</p>
    </div>
  );
}
