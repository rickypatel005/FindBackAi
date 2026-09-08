"use client";

import { Nav } from "@/components/Nav";
import { ReportForm } from "@/components/ReportForm";
import { useRequireAuth } from "@/lib/useRequireAuth";

export default function ReportFoundPage() {
  const { user, loading } = useRequireAuth();
  if (loading) return <p className="p-8 text-slate-500">Loading…</p>;

  return (
    <>
      <Nav user={user} />
      <ReportForm type="FOUND" />
    </>
  );
}
