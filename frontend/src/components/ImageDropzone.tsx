"use client";

import { ChangeEvent, useRef, useState } from "react";
import { api, ApiError, AnalyzeImageResult, AnalyzeAndEmbedResult } from "@/lib/api";

const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp"];
const MAX_SIZE_MB = 10;
const MAX_IMAGES = 3;

export interface UploadedImage {
  url: string;
  embedding: number[];
  previewSrc: string;
}

/**
 * Image dropzone/uploader (UIUX Sec. 6): 1-3 images, preview thumbnails,
 * remove action. Validates type/size client-side before submission (SRS
 * FR-02.3, UIUX Sec. 7) — the backend re-validates everything server-side
 * regardless (SRS Sec. 9).
 *
 * Phase 3: each selected file is uploaded to `/uploads/image` for durable
 * storage and sent to `/ai/embed-image` for its CLIP embedding, in
 * parallel. The first photo is also sent to `/ai/analyze-image` so the
 * parent form can pre-fill an "AI suggested" category/color (FR-04.1-04.3).
 */
export function ImageDropzone({
  token,
  images,
  onChange,
  onError,
  onAnalyzed,
}: {
  token: string;
  images: UploadedImage[];
  onChange: (images: UploadedImage[]) => void;
  onError: (message: string | null) => void;
  onAnalyzed?: (result: AnalyzeAndEmbedResult) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);

  async function handleFiles(e: ChangeEvent<HTMLInputElement>) {
    onError(null);
    const files = Array.from(e.target.files ?? []);
    e.target.value = "";
    if (files.length === 0) return;

    if (images.length + files.length > MAX_IMAGES) {
      onError(`You can upload up to ${MAX_IMAGES} images.`);
      return;
    }
    for (const file of files) {
      if (!ALLOWED_TYPES.includes(file.type)) {
        onError("Only JPG, PNG, or WEBP images are allowed.");
        return;
      }
      if (file.size > MAX_SIZE_MB * 1024 * 1024) {
        onError(`Each image must be ${MAX_SIZE_MB}MB or smaller.`);
        return;
      }
    }

    setUploading(true);
    try {
      const wasEmpty = images.length === 0;
      const uploaded: UploadedImage[] = [];
      for (const file of files) {
        const previewSrc = URL.createObjectURL(file);
        // Single combined CLIP call: returns category + color + embedding
        // in one forward pass instead of the previous two separate requests
        // (embed-image + analyze-image), cutting inference time roughly in half.
        const [uploadResult, aiResult] = await Promise.all([
          api.uploadImage(token, file),
          api.analyzeAndEmbed(file, token),
        ]);
        uploaded.push({ url: uploadResult.url, embedding: aiResult.embedding, previewSrc });
        // Surface AI suggestions from the first photo only (FR-04.1)
        if (wasEmpty && onAnalyzed) {
          onAnalyzed(aiResult);
        }
      }

      onChange([...images, ...uploaded]);
    } catch (err) {
      onError(err instanceof ApiError ? err.message : "Upload failed. Please try again.");
    } finally {
      setUploading(false);
    }
  }

  function remove(index: number) {
    onChange(images.filter((_, i) => i !== index));
  }

  return (
    <div>
      <div className="flex flex-wrap gap-3">
        {images.map((img, i) => (
          <div key={img.url} className="relative h-24 w-24 overflow-hidden rounded-lg border border-slate-200">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={img.previewSrc} alt={`Upload ${i + 1}`} className="h-full w-full object-cover" />
            <button
              type="button"
              onClick={() => remove(i)}
              aria-label={`Remove image ${i + 1}`}
              className="absolute right-1 top-1 flex h-5 w-5 items-center justify-center rounded-full bg-slate-900/80 text-xs text-white"
            >
              ×
            </button>
          </div>
        ))}
        {images.length < MAX_IMAGES && (
          <button
            type="button"
            disabled={uploading}
            onClick={() => inputRef.current?.click()}
            className="flex h-24 w-24 flex-col items-center justify-center gap-1 rounded-lg border-2 border-dashed border-slate-300 text-slate-400 hover:border-slate-400 hover:text-slate-500 disabled:opacity-50"
          >
            <span className="text-2xl leading-none">{uploading ? "…" : "+"}</span>
            <span className="text-xs">{uploading ? "Uploading" : "Add photo"}</span>
          </button>
        )}
      </div>
      <input
        ref={inputRef}
        type="file"
        accept={ALLOWED_TYPES.join(",")}
        multiple
        onChange={handleFiles}
        className="hidden"
      />
      <p className="mt-2 text-xs text-slate-400">
        {images.length}/{MAX_IMAGES} photos · JPG, PNG, or WEBP · up to {MAX_SIZE_MB}MB each
      </p>
    </div>
  );
}
