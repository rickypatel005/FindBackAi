"use client";

import { useEffect, useState } from "react";
import { Nav } from "@/components/Nav";
import { ReportCard } from "@/components/ReportCard";
import { EmptyState } from "@/components/EmptyState";
import { Button } from "@/components/Button";
import { api, ApiError, CATEGORY_LABELS, ReportOut, ReportStatus, ReportType, SearchFilters } from "@/lib/api";
import { useRequireAuth } from "@/lib/useRequireAuth";

/**
 * Search / Browse (SRS FR-15, UIUX Sec. 5 "Search / Browse", Phase 7).
 * Manual filter/search fallback to automatic matching (PRD Sec. 8) —
 * filters by category, color, brand, location, date, and status, plus a
 * free-text keyword search over title/description/features.
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

const EMPTY_FILTERS: SearchFilters = {};

export default function SearchPage() {
  const { user, token, loading } = useRequireAuth();
  const [filters, setFilters] = useState<SearchFilters>(EMPTY_FILTERS);
  const [results, setResults] = useState<ReportOut[]>([]);
  const [searched, setSearched] = useState(false);
  const [fetching, setFetching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function runSearch(nextFilters: SearchFilters = filters) {
    if (!token) return;
    setFetching(true);
    setError(null);
    try {
      const r = await api.searchReports(token, nextFilters);
      setResults(r);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Search failed. Please try again.");
    } finally {
      setFetching(false);
      setSearched(true);
    }
  }

  // Run once on load so the screen isn't empty before the user touches a filter.
  useEffect(() => {
    if (token) runSearch(EMPTY_FILTERS);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  function update<K extends keyof SearchFilters>(key: K, value: SearchFilters[K]) {
    setFilters((prev) => ({ ...prev, [key]: value || undefined }));
  }

  function clearFilters() {
    setFilters(EMPTY_FILTERS);
    runSearch(EMPTY_FILTERS);
  }

  if (loading) return <p className="p-8 text-slate-500">Loading…</p>;

  return (
    <>
      <Nav user={user} />
      <main className="mx-auto max-w-5xl px-6 py-10">
        <h1 className="text-2xl font-semibold text-slate-900">Search / Browse</h1>
        <p className="mt-1 text-slate-600">
          Manually browse active reports as a fallback to automatic matching.
        </p>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            runSearch();
          }}
          className="mt-6 grid grid-cols-1 gap-3 rounded-xl border border-slate-200 bg-white p-5 sm:grid-cols-2 lg:grid-cols-4"
        >
          <input
            type="text"
            placeholder="Keyword (title, description...)"
            value={filters.q ?? ""}
            onChange={(e) => update("q", e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none lg:col-span-2"
          />

          <select
            value={filters.type ?? ""}
            onChange={(e) => update("type", (e.target.value || undefined) as ReportType | undefined)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none"
          >
            <option value="">Any type</option>
            <option value="LOST">Lost</option>
            <option value="FOUND">Found</option>
          </select>

          <select
            value={filters.category ?? ""}
            onChange={(e) => update("category", e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none"
          >
            <option value="">Any category</option>
            {CATEGORY_LABELS.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>

          <input
            type="text"
            placeholder="Color"
            value={filters.color ?? ""}
            onChange={(e) => update("color", e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none"
          />

          <input
            type="text"
            placeholder="Brand"
            value={filters.brand ?? ""}
            onChange={(e) => update("brand", e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none"
          />

          <input
            type="text"
            placeholder="Location"
            value={filters.location ?? ""}
            onChange={(e) => update("location", e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none"
          />

          <select
            value={filters.status ?? ""}
            onChange={(e) => update("status", (e.target.value || undefined) as ReportStatus | undefined)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none"
          >
            <option value="">Any status</option>
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {s.replaceAll("_", " ")}
              </option>
            ))}
          </select>

          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-500">From</label>
            <input
              type="date"
              value={filters.date_from ?? ""}
              onChange={(e) => update("date_from", e.target.value)}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-500">To</label>
            <input
              type="date"
              value={filters.date_to ?? ""}
              onChange={(e) => update("date_to", e.target.value)}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none"
            />
          </div>

          <div className="flex items-end gap-2 lg:col-span-2">
            <Button type="submit" variant="neutral" className="flex-1">
              Search
            </Button>
            <button
              type="button"
              onClick={clearFilters}
              className="rounded-lg px-4 py-2.5 text-sm font-medium text-slate-500 hover:text-slate-700"
            >
              Clear
            </button>
          </div>
        </form>

        <div className="mt-6 flex flex-col gap-3">
          {error ? (
            <p className="text-status-danger">{error}</p>
          ) : fetching ? (
            <p className="text-slate-500">Searching…</p>
          ) : results.length === 0 && searched ? (
            <EmptyState
              title="No results"
              body="Try loosening a filter — the system will also keep checking for automatic matches as new reports come in."
            />
          ) : (
            results.map((r) => <ReportCard key={r.id} report={r} />)
          )}
        </div>
      </main>
    </>
  );
}
