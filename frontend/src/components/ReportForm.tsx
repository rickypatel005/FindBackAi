"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { clsx } from "clsx";
import { Button } from "@/components/Button";
import { ImageDropzone, UploadedImage } from "@/components/ImageDropzone";
import { api, ApiError, CATEGORY_LABELS, ReportType, AnalyzeAndEmbedResult } from "@/lib/api";
import { getToken } from "@/lib/auth";

const inputClass =
  "w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-slate-500 focus:outline-none";
const labelClass = "mb-1 block text-sm font-medium text-slate-700";

/**
 * Shared Report Lost / Report Found form (UIUX Sec. 5, Flow 4.1). Identical
 * layout for both, differentiated only by a persistent color-coded header
 * so users never confuse which flow they're in.
 */
export function ReportForm({ type }: { type: ReportType }) {
  const router = useRouter();
  const accent = type === "LOST" ? "lost" : "found";

  const [images, setImages] = useState<UploadedImage[]>([]);
  const [imageError, setImageError] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState("");
  const [aiSuggestedCategory, setAiSuggestedCategory] = useState(false);
  const [color, setColor] = useState("");
  const [aiSuggestedColor, setAiSuggestedColor] = useState(false);
  const [brand, setBrand] = useState("");
  const [description, setDescription] = useState("");
  const [features, setFeatures] = useState("");
  const [location, setLocation] = useState("");
  const [reportDate, setReportDate] = useState("");
  const [reportTime, setReportTime] = useState("");
  const [qualityTips, setQualityTips] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [loadingCopy, setLoadingCopy] = useState<string | null>(null);

  // FR-04.1/04.3 — as of Phase 3, ImageDropzone calls the real
  // /ai/analyze-image endpoint (CLIP zero-shot) on the first uploaded
  // photo and reports the result here. Suggestions are clearly labeled
  // and stay user-editable; editing a field clears its "AI suggested" tag.
  function handleAnalyzed(result: AnalyzeAndEmbedResult) {
    if (!category) {
      setCategory(result.category);
      setAiSuggestedCategory(true);
    }
    if (!color && result.color) {
      setColor(result.color);
      setAiSuggestedColor(true);
    }
  }

  // FR-18.1 — flag weak/short descriptions, debounced on the client.
  useEffect(() => {
    const token = getToken();
    if (!token || description.trim().length === 0) {
      setQualityTips([]);
      return;
    }
    const handle = setTimeout(() => {
      api
        .checkReportQuality(token, description)
        .then((res) => setQualityTips(res.suggestions))
        .catch(() => setQualityTips([]));
    }, 500);
    return () => clearTimeout(handle);
  }, [description]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    // FOUND reports must have a photo — it's the item itself and essential
    // for visual matching. LOST reports allow submission without a photo
    // since the owner may not have a picture of what they lost.
    if (type === "FOUND" && images.length === 0) {
      setError("Add at least one photo of the found item before submitting.");
      return;
    }

    const token = getToken();
    if (!token) {
      router.push("/login");
      return;
    }

    setSubmitting(true);
    setLoadingCopy("Submitting…");
    try {
      const report = await api.createReport(token, type, {
        title,
        category,
        color,
        brand: brand || undefined,
        description,
        features: features || undefined,
        location,
        report_date: reportDate,
        report_time: reportTime || undefined,
        image_urls: images.map((img) => img.url),
        image_embeddings: images.map((img) => img.embedding),
      });

      setLoadingCopy("Finding potential matches…");
      try {
        const matches = await api.findMatches(token, report.id);
        router.push(matches.length > 0 ? `/matches/${report.id}` : "/items");
      } catch {
        // Matching is best-effort here — SRS Section 8: no candidates
        // found is not an error, and a matching hiccup shouldn't block
        // the report from having been saved.
        router.push("/items");
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
      setSubmitting(false);
      setLoadingCopy(null);
    }
  }

  if (submitting) {
    return (
      <div className="mx-auto flex min-h-[50vh] max-w-md flex-col items-center justify-center text-center">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-slate-200 border-t-slate-900" />
        <p className="mt-4 text-slate-600">{loadingCopy ?? "Submitting…"}</p>
      </div>
    );
  }

  return (
    <main className="mx-auto max-w-2xl px-6 py-10">
      <div className={clsx("rounded-xl px-5 py-4 text-white", accent === "lost" ? "bg-lost" : "bg-found")}>
        <h1 className="text-xl font-semibold">
          {type === "LOST" ? "Report a lost item" : "Report a found item"}
        </h1>
        <p className="mt-1 text-sm text-white/90">
          {type === "LOST"
            ? "Tell us what you lost — we'll check it against active found reports."
            : "Tell us what you found — we'll check it against active lost reports."}
        </p>
      </div>

      <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-5" noValidate>
        <div>
          <label className={labelClass}>
            Photos{type === "LOST" && (
              <span className="ml-1 font-normal text-slate-400">(optional)</span>
            )}
          </label>
          {type === "LOST" && (
            <p className="mb-2 text-xs text-slate-500">
              Don&apos;t have a photo? No problem — describe the item well and we&apos;ll still search for matches.
            </p>
          )}
          <ImageDropzone
            token={getToken() ?? ""}
            images={images}
            onChange={setImages}
            onError={setImageError}
            onAnalyzed={handleAnalyzed}
          />
          {imageError && (
            <p role="alert" className="mt-2 text-sm text-status-danger">
              {imageError}
            </p>
          )}
        </div>

        <div>
          <label htmlFor="title" className={labelClass}>
            Title
          </label>
          <input
            id="title"
            required
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Black leather wallet"
            className={inputClass}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="category" className={labelClass}>
              Category {aiSuggestedCategory && category && (
                <span className="ml-1 rounded-full bg-slate-900/5 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
                  AI suggested
                </span>
              )}
            </label>
            <select
              id="category"
              required
              value={category}
              onChange={(e) => {
                setCategory(e.target.value);
                setAiSuggestedCategory(false);
              }}
              className={inputClass}
            >
              <option value="" disabled>
                Select a category
              </option>
              {CATEGORY_LABELS.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="color" className={labelClass}>
              Color {aiSuggestedColor && color && (
                <span className="ml-1 rounded-full bg-slate-900/5 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
                  AI suggested
                </span>
              )}
            </label>
            <input
              id="color"
              required
              value={color}
              onChange={(e) => {
                setColor(e.target.value);
                setAiSuggestedColor(false);
              }}
              className={inputClass}
            />
          </div>
        </div>

        <div>
          <label htmlFor="brand" className={labelClass}>
            Brand <span className="font-normal text-slate-400">(optional)</span>
          </label>
          <input id="brand" value={brand} onChange={(e) => setBrand(e.target.value)} className={inputClass} />
        </div>

        <div>
          <label htmlFor="description" className={labelClass}>
            Description
          </label>
          <textarea
            id="description"
            required
            rows={4}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Distinguishing details — scratches, stickers, serial numbers…"
            className={inputClass}
          />
          {qualityTips.length > 0 && (
            <ul className="mt-2 space-y-1 rounded-lg bg-amber-50 px-3 py-2 text-xs text-status-warning">
              {qualityTips.map((tip) => (
                <li key={tip}>• {tip}</li>
              ))}
            </ul>
          )}
        </div>

        <div>
          <label htmlFor="features" className={labelClass}>
            Distinguishing features <span className="font-normal text-slate-400">(optional)</span>
          </label>
          <input
            id="features"
            value={features}
            onChange={(e) => setFeatures(e.target.value)}
            className={inputClass}
          />
        </div>

        <div>
          <label htmlFor="location" className={labelClass}>
            Location
          </label>
          <input
            id="location"
            required
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="e.g. Central Library, 2nd floor"
            className={inputClass}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="date" className={labelClass}>
              Date
            </label>
            <input
              id="date"
              type="date"
              required
              value={reportDate}
              onChange={(e) => setReportDate(e.target.value)}
              className={inputClass}
            />
          </div>
          <div>
            <label htmlFor="time" className={labelClass}>
              Approx. time <span className="font-normal text-slate-400">(optional)</span>
            </label>
            <input
              id="time"
              type="time"
              value={reportTime}
              onChange={(e) => setReportTime(e.target.value)}
              className={inputClass}
            />
          </div>
        </div>

        {error && (
          <p role="alert" className="text-sm text-status-danger">
            {error}
          </p>
        )}

        <Button type="submit" variant={accent} className="mt-2">
          Submit {type === "LOST" ? "lost" : "found"} report
        </Button>
      </form>
    </main>
  );
}
