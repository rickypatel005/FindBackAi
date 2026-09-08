import Link from "next/link";
import { Button } from "@/components/Button";

export function EmptyState({
  title,
  body,
  ctaLabel,
  ctaHref,
}: {
  title: string;
  body: string;
  ctaLabel?: string;
  ctaHref?: string;
}) {
  return (
    <div className="rounded-xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center">
      <h3 className="font-semibold text-slate-900">{title}</h3>
      <p className="mx-auto mt-1 max-w-sm text-sm text-slate-500">{body}</p>
      {ctaLabel && ctaHref && (
        <Link href={ctaHref} className="mt-4 inline-block">
          <Button variant="neutral">{ctaLabel}</Button>
        </Link>
      )}
    </div>
  );
}
