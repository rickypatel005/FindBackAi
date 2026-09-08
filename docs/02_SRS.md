# FindBack AI — Software Requirements Specification (SRS)

**Version:** 1.0
**Status:** MVP / Hackathon Build

---

## 1. Purpose

This document defines the functional and non-functional requirements for FindBack AI in testable, implementation-ready form, expanding on the PRD.

## 2. User Roles and Permissions

| Role | Permissions |
|---|---|
| **Guest** | View landing page, register, log in |
| **User** | Create/edit/delete own reports, view own matches, view notifications, search/browse public report metadata, cannot see other users' contact info |
| **Admin** | All User permissions + view all reports, mark duplicates, remove reports, resolve/close matches, view platform statistics |

Role is stored on the user record (`User` / `Admin`) and enforced server-side on every protected route — never inferred from the frontend alone.

## 3. Functional Requirements

### FR-01 Authentication
- FR-01.1 Users register with email + password (or Supabase Auth provider).
- FR-01.2 Users log in and receive a session/JWT.
- FR-01.3 Users can log out, invalidating the session client-side.
- FR-01.4 `GET /auth/me` returns the current user's profile and role.
- FR-01.5 Passwords must meet a minimum strength policy (delegated to Supabase Auth).

### FR-02 / FR-03 Report Creation (Lost / Found)
- FR-02.1 A report requires: title, category, color, description, location, date, time, 1–3 images. Brand is optional.
- FR-02.2 Report `type` is fixed at creation (`LOST` or `FOUND`) and is immutable afterward.
- FR-02.3 Images must be validated for file type (jpg/png/webp) and size (e.g. ≤10MB each) before upload.
- FR-02.4 A report cannot be submitted with zero images.
- FR-02.5 Reports are associated with the authenticated `user_id`; anonymous reports are not permitted.

### FR-04 AI Image Analysis
- FR-04.1 On upload, the backend runs a pretrained vision-language model (CLIP) against a controlled category label set and returns the top predicted category with a confidence score.
- FR-04.2 The system attempts to estimate main color and, where feasible, brand/logo and distinguishing features.
- FR-04.3 All AI-suggested fields are pre-filled but remain user-editable before submission.
- FR-04.4 If confidence is below a configured threshold, the category defaults to "Other" rather than guessing.

### FR-05 Text Understanding
- FR-05.1 Title + Description + Features are concatenated and encoded via a Sentence Transformers model into a normalized text embedding.
- FR-05.2 Re-encoding occurs whenever the underlying text fields are edited.

### FR-06 Image Embeddings
- FR-06.1 Each uploaded image is encoded into a normalized CLIP embedding and stored in a `pgvector` column.
- FR-06.2 If multiple images are uploaded, embeddings may be averaged or the primary image used (implementation choice documented in the Architecture doc).

### FR-07 Semantic Search / Candidate Retrieval
- FR-07.1 Candidate retrieval first applies hard filters: opposite report type, `active` status, optional category filter.
- FR-07.2 The filtered set is then narrowed using vector similarity search (image and/or text) via pgvector.
- FR-07.3 Full multimodal scoring is computed only on the narrowed candidate set (not the entire table).

### FR-08 Multimodal Matching
- FR-08.1 The system computes a weighted final score from: image similarity (40%), text similarity (20%), category (10%), color (10%), location (10%), time (5%), other attributes (5%).
- FR-08.2 All component scores are normalized to a 0–100 scale before weighting.
- FR-08.3 Weights are stored as configuration values, not hardcoded, and must be tunable without a code change.

### FR-09 Match Ranking
- FR-09.1 Candidate matches are sorted descending by final score.
- FR-09.2 The system displays the top 3–5 ranked matches per report.

### FR-10 Explainable Match
- FR-10.1 Each displayed match includes the contributing signals that passed a configured threshold (e.g. "Same category", "Similar appearance").
- FR-10.2 A reason is never shown unless its underlying component score exceeds its configured threshold — no fabricated explanations.

### FR-11 Match Details
- FR-11.1 The Match Details page shows lost/found reports side-by-side, the final score, all component scores, and the explanation list.

### FR-12 Notifications
- FR-12.1 When a new report produces a match at or above the configured notification threshold, an in-app notification is created for the affected user(s).
- FR-12.2 Notifications can be marked as read (`PATCH /notifications/{id}/read`).

### FR-13 Dashboard
- FR-13.1 Displays: lost item count, found item count, potential matches, recovered items, recent reports, unread notifications.

### FR-14 Report Status Lifecycle
- Lost: `SEARCHING → MATCH_FOUND → RECOVERED / CLOSED`
- Found: `UNCLAIMED → POTENTIAL_OWNER_FOUND → RETURNED / CLOSED`
- FR-14.1 Status transitions must follow the defined lifecycle; arbitrary jumps (e.g. `SEARCHING → RETURNED`) are rejected server-side.

### FR-15 Search and Filters
- FR-15.1 Users can filter by category, color, brand, location, date, and status.
- FR-15.2 Natural-language search is a strong-addition (post-core) feature.

### FR-16 Duplicate Detection (Strong Addition)
- FR-16.1 Reports with very high mutual similarity within the same type (LOST-LOST or FOUND-FOUND) are flagged for admin review, not auto-merged.

### FR-17 Admin Dashboard
- FR-17.1 Shows total/lost/found/potential-match/recovered/pending-review counts.
- FR-17.2 Admin actions: view report, mark duplicate, remove inappropriate report, resolve match, close report — all require `Admin` role, enforced server-side.

### FR-18 Report Quality Suggestions
- FR-18.1 Before submission, the system flags weak/short descriptions and suggests adding distinguishing details (e.g. scratches, stickers, serial numbers).

### FR-19 Privacy Controls
- FR-19.1 Personal contact details are never exposed in public-facing report data.
- FR-19.2 Only internal user IDs are referenced in report/match records visible to other users.
- FR-19.3 Controlled contact actions (if implemented) require authentication.
- FR-19.4 Users can delete their own reports; deletion removes associated images and embeddings.

## 4. Business Rules

- A report always belongs to exactly one user and one type (`LOST`/`FOUND`); type cannot change post-creation.
- Matches are only computed between opposite-type, active-status reports.
- A user cannot be matched against their own reports (self-matching excluded).
- Explanation reasons must be traceable to a stored component score — never generated independently of the scoring engine.
- Threshold and weight values live in configuration, not code, for auditability and tuning.

## 5. Data Requirements

Core entities: **Users**, **Reports** (`type`, category, color, brand, description, features, location, date/time, status, image URLs, image/text embeddings), **Matches** (per-component scores + final score + explanation), **Notifications** (user, match, read state). Full schema is defined in the Architecture document, Section "Data Model".

## 6. Validation Rules

- Email format validated at registration; duplicate emails rejected.
- Image files: type-restricted (jpg/png/webp), size-capped, count-capped at 3.
- Required text fields (title, category, color, description, location, date) cannot be empty.
- Date/time fields must be valid and not set in the future beyond a small tolerance.
- Score/weight configuration values must sum sensibly (weights ≈ 1.0) and are validated at load time.

## 7. Authentication & Authorization

- Session-based or JWT-based authentication (Supabase Auth).
- Every write endpoint verifies the requesting user owns the resource (report, match, notification) unless the caller has `Admin` role.
- Admin routes (`/admin/*`) reject non-admin callers with `403`.

## 8. Error Handling & Edge Cases

| Case | Expected Behavior |
|---|---|
| Upload with 0 or >3 images | Reject with validation error before AI processing |
| Unsupported image format | Reject at upload with clear error message |
| AI category confidence below threshold | Default to "Other", do not block submission |
| No candidates found on matching | Return empty match list, not an error |
| Duplicate report submission (rapid re-submit) | De-duplicate via idempotency check or short-window rate limit |
| Report deleted while a match references it | Cascade-soft-delete the match and any dependent notification |
| Invalid status transition | Reject with `400` and current allowed transitions |
| Non-owner attempts edit/delete | Reject with `403` |
| Expired/invalid session | Reject with `401`, prompt re-login |

## 9. Security Requirements

- All API routes protected by authenticated sessions/JWTs except `/auth/register`, `/auth/login`, and public landing content.
- Role checks enforced on every admin route.
- Uploaded files validated for type/size server-side (not just client-side).
- User-generated text sanitized before storage/rendering to prevent injection/XSS.
- No private contact information exposed via any public API response.
- Ownership validated before any edit/delete operation.
- Secrets (DB URL, service role key) stored only in environment variables, never committed.

## 10. Performance Requirements

- Standard report submission should feel interactive (immediate UI feedback; AI processing runs async or behind a loading state).
- Candidate retrieval uses vector indexing (pgvector) rather than full-table scans as data grows.
- Frontend lazy-loads report images.
- Matching computation is limited to a narrowed candidate set, not the full report table (see FR-07).

## 11. Acceptance Criteria

Requirements are considered met when each FR above has at least one corresponding passing test case (unit, integration, or manual QA script) covering both the happy path and at least one edge case from Section 8.
