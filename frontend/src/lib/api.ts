/**
 * Thin fetch wrapper around the FastAPI backend. Reads the base URL from
 * NEXT_PUBLIC_API_URL (see .env.example at the project root). Frontend
 * never calls AI models directly — always via backend REST (Architecture
 * doc, Section 4).
 */
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}, token?: string): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(body.detail ?? "Request failed", res.status);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

/** Like `request`, but for multipart file uploads — omits the JSON
 * Content-Type header so the browser can set the correct multipart
 * boundary itself (Phase 3: /uploads/image, /ai/analyze-image, /ai/embed-image). */
async function requestFile<T>(path: string, file: File, token?: string): Promise<T> {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    body: form,
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(body.detail ?? "Request failed", res.status);
  }
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Types (mirror backend/app/schemas/*.py)
// ---------------------------------------------------------------------------

export interface UserOut {
  id: string;
  email: string;
  name: string | null;
  role: "User" | "Admin";
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: UserOut;
}

export type ReportType = "LOST" | "FOUND";

export type ReportStatus =
  | "SEARCHING"
  | "MATCH_FOUND"
  | "RECOVERED"
  | "UNCLAIMED"
  | "POTENTIAL_OWNER_FOUND"
  | "RETURNED"
  | "CLOSED";

export interface ReportOut {
  id: string;
  user_id: string;
  type: ReportType;
  title: string;
  category: string;
  color: string;
  brand: string | null;
  description: string;
  features: string | null;
  location: string;
  report_date: string;
  report_time: string | null;
  status: ReportStatus;
  image_urls: string[];
  created_at: string;
}

export interface ReportCreatePayload {
  title: string;
  category: string;
  color: string;
  brand?: string;
  description: string;
  features?: string;
  location: string;
  report_date: string;
  report_time?: string;
  image_urls: string[];
  image_embeddings?: number[][];
}

export interface MatchOut {
  id: string;
  lost_report_id: string;
  found_report_id: string;
  image_score: number;
  text_score: number;
  category_score: number;
  color_score: number;
  brand_score: number;
  location_score: number;
  time_score: number;
  other_score: number;
  final_score: number;
  explanation: string[];
  created_at: string;
  updated_at?: string;
}

export interface NotificationOut {
  id: string;
  match_id: string;
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
}

export interface AdminStats {
  total: number;
  lost: number;
  found: number;
  potential_matches: number;
  recovered: number;
  pending_review: number;
  recovery_rate?: number;
  category_counts?: Record<string, number>;
}

// --- Phase 7: Search & Admin ---

export interface SearchFilters {
  type?: ReportType;
  category?: string;
  color?: string;
  brand?: string;
  location?: string;
  status?: ReportStatus;
  date_from?: string;
  date_to?: string;
  q?: string;
}

export interface DuplicatePair {
  report_a: ReportOut;
  report_b: ReportOut;
  similarity: number;
  type: ReportType;
}

export interface MatchResolveResult {
  lost_report: ReportOut;
  found_report: ReportOut;
}

export interface QualityCheckResult {
  is_weak: boolean;
  suggestions: string[];
}

// --- Phase 3: Image Pipeline ---

export interface UploadImageResult {
  image_id: string;
  path: string;
  url: string;
}

export interface AnalyzeImageResult {
  category: string;
  confidence: number;
  color: string | null;
  brand: string | null;
}

export interface EmbedImageResult {
  embedding: number[];
  dim: number;
}

/** Combined result from /ai/analyze-and-embed — single CLIP forward pass */
export interface AnalyzeAndEmbedResult {
  category: string;
  confidence: number;
  color: string | null;
  brand: string | null;
  embedding: number[];
  dim: number;
}

// Categories mirrored from backend/app/api/routes/ai.py CATEGORY_LABELS
// (PRD Sec. 6 — platform is category-agnostic; this is the MVP reference list).
export const CATEGORY_LABELS = [
  "Electronics",
  "Bags",
  "Wallets",
  "Documents",
  "Clothing",
  "Keys",
  "Books",
  "Accessories",
  "Bottles",
  "Watches",
  "Earbuds/Headphones",
  "Other",
];

// Status transitions a report OWNER can trigger from the UI (SRS FR-14 —
// server re-validates every transition; this only drives which buttons show).
export const NEXT_STATUS: Partial<Record<ReportStatus, { label: string; next: ReportStatus }[]>> = {
  SEARCHING: [
    { label: "Mark recovered", next: "RECOVERED" },
    { label: "Close report", next: "CLOSED" },
  ],
  MATCH_FOUND: [
    { label: "Mark recovered", next: "RECOVERED" },
    { label: "Close report", next: "CLOSED" },
  ],
  UNCLAIMED: [
    { label: "Mark returned", next: "RETURNED" },
    { label: "Close report", next: "CLOSED" },
  ],
  POTENTIAL_OWNER_FOUND: [
    { label: "Mark returned", next: "RETURNED" },
    { label: "Close report", next: "CLOSED" },
  ],
};

export const api = {
  // --- Auth ---
  register: (email: string, password: string, name?: string) =>
    request<TokenResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, name }),
    }),

  login: (email: string, password: string) =>
    request<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  me: (token: string) => request<UserOut>("/auth/me", {}, token),

  // --- Reports ---
  createReport: (token: string, type: ReportType, payload: ReportCreatePayload) =>
    request<ReportOut>(
      type === "LOST" ? "/reports/lost" : "/reports/found",
      { method: "POST", body: JSON.stringify(payload) },
      token
    ),

  myReports: (token: string) => request<ReportOut[]>("/reports/mine", {}, token),

  getReport: (token: string, id: string) => request<ReportOut>(`/reports/${id}`, {}, token),

  updateReportStatus: (token: string, id: string, status: ReportStatus) =>
    request<ReportOut>(`/reports/${id}`, { method: "PATCH", body: JSON.stringify({ status }) }, token),

  deleteReport: (token: string, id: string) => request<void>(`/reports/${id}`, { method: "DELETE" }, token),

  // --- Search (Phase 7, SRS FR-15) ---
  searchReports: (token: string, filters: SearchFilters) => {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") params.set(key, String(value));
    });
    const qs = params.toString();
    return request<ReportOut[]>(`/reports/search${qs ? `?${qs}` : ""}`, {}, token);
  },

  // --- AI ---
  // /analyze-image and /embed-image are real CLIP calls as of Phase 3
  // (app/services/vision.py). /embed-text is real Sentence Transformers as
  // of Phase 4 (app/services/embeddings.py), but the frontend doesn't call
  // it directly — report creation/editing generates text_embedding
  // server-side from title+description+features (app/services/reports.py).
  checkReportQuality: (token: string, description: string) =>
    request<QualityCheckResult>(
      `/ai/check-report-quality?description=${encodeURIComponent(description)}`,
      { method: "POST" },
      token
    ),

  analyzeImage: (file: File) => requestFile<AnalyzeImageResult>("/ai/analyze-image", file),

  embedImage: (file: File) => requestFile<EmbedImageResult>("/ai/embed-image", file),

  /** Single-pass CLIP: returns category + color + embedding in one request */
  analyzeAndEmbed: (file: File, token: string) =>
    requestFile<AnalyzeAndEmbedResult>("/ai/analyze-and-embed", file, token),

  // --- Uploads (Phase 3) ---
  uploadImage: (token: string, file: File) => requestFile<UploadImageResult>("/uploads/image", file, token),

  // --- Matching ---
  findMatches: (token: string, reportId: string) =>
    request<MatchOut[]>(`/matches/find/${reportId}`, { method: "POST" }, token),

  getMatches: (token: string, reportId: string) => request<MatchOut[]>(`/matches/${reportId}`, {}, token),

  getMatchDetails: (token: string, matchId: string) => request<MatchOut>(`/matches/${matchId}/details`, {}, token),

  // --- Notifications ---
  listNotifications: (token: string) => request<NotificationOut[]>("/notifications", {}, token),

  markNotificationRead: (token: string, id: string) =>
    request<NotificationOut>(`/notifications/${id}/read`, { method: "PATCH" }, token),

  // --- Admin ---
  adminStats: (token: string) => request<AdminStats>("/admin/stats", {}, token),

  adminReports: (token: string) => request<ReportOut[]>("/admin/reports", {}, token),

  adminModerate: (token: string, id: string, action: "remove" | "close" | "mark_duplicate") =>
    request<ReportOut>(`/admin/reports/${id}?action=${action}`, { method: "PATCH" }, token),

  // --- Admin: Phase 7 duplicates + match resolution ---
  adminDuplicates: (token: string, type?: ReportType) =>
    request<DuplicatePair[]>(`/admin/duplicates${type ? `?type=${type}` : ""}`, {}, token),

  adminResolveMatch: (token: string, matchId: string) =>
    request<MatchResolveResult>(`/admin/matches/${matchId}/resolve`, { method: "PATCH" }, token),
};
