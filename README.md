# FindBack AI

An AI-assisted lost-and-found platform. Users report lost/found items with
photos and metadata; the backend generates image + text embeddings,
retrieves likely candidates, and produces a ranked, explainable multimodal
match score.

Full specs live in [`docs/`](./docs): PRD, SRS, Architecture, UI/UX, and the
Development Plan this build follows phase-by-phase.

**Status: Phase 0 (Project Setup) + Phase 1 (Auth & Data Model) + Phase 2
(Frontend Core) + Phase 3 (Image Pipeline) + Phase 4 (Text Pipeline) +
Phase 5 (Search & Matching) + Phase 6 (Explainability & Notifications) +
Phase 7 (Search & Admin) — complete.** The full Lost/Found → Match →
Notification loop is click-through-able end-to-end in the browser today.
Uploaded photos get real CLIP category/color suggestions and image
embeddings, report text gets real Sentence-Transformers embeddings,
candidate retrieval narrows via a real pgvector cosine-distance query
(FR-07.2) before the full weighted score (image + text + category + color
+ location + time) is computed and ranked, and a match that crosses the
notification threshold now notifies both owners exactly once — re-checking
or editing a report no longer creates duplicate match rows or repeat
notifications. As of Phase 7, users can also manually search/browse active
reports as a fallback to automatic matching, and admins get a
duplicate-review queue plus a full "resolve match" action alongside the
existing moderation tools.
See [Project Status](#project-status) below for what's implemented vs. what
Phase 8+ still needs to build.

## Stack

| Layer | Choice |
|---|---|
| Frontend | Next.js 14 (App Router) + TypeScript + Tailwind CSS |
| Backend | FastAPI (Python) + SQLAlchemy + Pydantic |
| Database | PostgreSQL + pgvector |
| Auth / Storage | Supabase |
| Image AI (Phase 3 ✅) | Pretrained CLIP / OpenCLIP |
| Text AI (Phase 4 ✅) | Sentence Transformers |

## Project Structure

```
findback-ai/
├── docs/                  Product/spec documents (PRD, SRS, Architecture, UI/UX, Dev Plan)
├── backend/               FastAPI application
│   ├── app/
│   │   ├── core/          Settings, JWT auth, Supabase client factory
│   │   ├── models/        SQLAlchemy models (Users, Reports, Matches, Notifications)
│   │   ├── schemas/       Pydantic request/response schemas
│   │   ├── services/      Business logic: reports lifecycle, matching engine,
│   │   │                  Supabase Auth path, vision (CLIP), storage (upload persistence)
│   │   ├── api/routes/    auth, reports, uploads, ai, matches, notifications, admin
│   │   └── main.py        App entrypoint (also serves local-fallback uploaded images at `/media`)
│   ├── migrations/
│   │   ├── 001_init.sql              Full Postgres/Supabase schema (pgvector, indexes, RLS)
│   │   ├── 002_auth_trigger.sql      Auto-creates a profile row when Supabase Auth signs someone up
│   │   ├── 003_vector_indexes.sql    Optional IVFFlat ANN indexes (Phase 5)
│   │   └── 004_match_constraints.sql Unique (lost, found) constraint + updated_at (Phase 6)
│   ├── scripts/
│   │   ├── dev.sh                     Local bootstrap + run script
│   │   └── create_storage_bucket.py   One-time private Storage bucket setup
│   ├── tests/             Pytest suite: health, full auth flow, role enforcement,
│   │                      image upload validation, vision/embeddings services, AI routes,
│   │                      matching + notification dedup logic (75 tests)
│   └── requirements.txt
├── frontend/              Next.js application
│   ├── src/app/           Landing, Login/Register, Dashboard, Report Lost/Found,
│   │                      My Items (+detail), Potential Matches, Match Details,
│   │                      Notifications, Admin
│   ├── src/components/    Nav, ReportForm, ImageDropzone, ReportCard, StatusBadge,
│   │                      ScoreBar/ScoreChip, EmptyState, Button
│   ├── src/lib/           Typed API client, auth token helper, useRequireAuth guard
│   └── scripts/dev.sh     Local bootstrap + run script
├── ml/                    Reserved for CLIP / Sentence-Transformers wrapper scripts (Phase 3/4)
├── .env.example           Annotated environment variable reference
├── Makefile               `make backend` / `make frontend` / `make backend-test`
└── docker-compose.yml     Optional local Postgres+pgvector for dev without Supabase
```

## Quick Start

### 1. Environment variables

```bash
cp .env.example .env          # fill in real Supabase values when you have them
cp backend/.env.example backend/.env
```

For local development without a live Supabase project yet, `docker-compose.yml`
spins up a local Postgres with pgvector so the backend has somewhere to write to.

### 2. Database & Auth

Two supported paths — pick one:

**A. Local dev, no Supabase account needed (fastest to get running):**
```bash
docker compose up -d db
psql postgresql://postgres:postgres@localhost:5432/findback -f backend/migrations/001_init.sql
```
Leave `AUTH_MODE=local` in `backend/.env`. The backend issues and verifies
its own JWTs; register/login work immediately with no external service.

**B. Real Supabase project (recommended before Phase 2+):**
1. Create a project at [supabase.com](https://supabase.com).
2. SQL Editor → run `backend/migrations/001_init.sql`, then
   `backend/migrations/002_auth_trigger.sql` (this second one auto-creates
   a `public.users` profile row every time someone signs up via Supabase
   Auth — the app never has to do that itself).
3. Copy these into `.env` / `backend/.env`:
   - `SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`,
     `SUPABASE_SERVICE_ROLE_KEY` — from Project Settings → API
   - `SUPABASE_JWT_SECRET` — from Project Settings → API → **JWT Settings**
     (this is a different value from the anon/service keys)
   - `DATABASE_URL` — from Project Settings → Database → Connection string
4. Set `AUTH_MODE=supabase`.
5. Create the private image-storage bucket once:
   ```bash
   cd backend && python -m scripts.create_storage_bucket
   ```
6. To make a user an Admin, run this directly in the Supabase SQL editor
   (there's deliberately no API route for it):
   ```sql
   update public.users set role = 'Admin' where email = 'someone@example.com';
   ```

### 3. Backend

```bash
make backend
# or manually:
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Verify it's running: `curl http://localhost:8000/health` → `{"status":"healthy"}`

Run the test suite:
```bash
make backend-test
```

### 4. Frontend

```bash
make frontend
# or manually:
cd frontend
npm install
npm run dev
```

Visit `http://localhost:3000`. The landing page, register, login, and a
placeholder dashboard (proving the auth loop end-to-end) are wired to the
FastAPI backend at `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000/api`).

## Project Status

### Phase 0 — Project Setup ✅
- [x] Monorepo structure (`frontend/`, `backend/`, `ml/`, `docs/`)
- [x] Next.js frontend initialized (TypeScript + Tailwind, builds cleanly)
- [x] FastAPI backend initialized (runs, tests pass)
- [x] Environment variables documented (`.env.example`)
- [x] Local dev scripts (`Makefile`, `backend/scripts/dev.sh`, `frontend/scripts/dev.sh`)
- [x] `docker-compose.yml` for local Postgres+pgvector
- [x] README + setup instructions (this file)
- [ ] Connect a **real** Supabase project — this requires your own Supabase
      account; everything (schema, auth trigger, storage bucket script,
      `AUTH_MODE=supabase` wiring) is ready to point at one the moment it
      exists — see step 2B under Quick Start.

### Phase 1 — Authentication & Database ✅
- [x] `users`, `reports`, `matches`, `notifications` tables + `pgvector` extension (`migrations/001_init.sql`)
- [x] Role-based access (`User`/`Admin`) enforced server-side — never trusted from the client
- [x] **Two working auth modes, switched by one env var (`AUTH_MODE`):**
  - `local` — backend issues/verifies its own JWTs (`pbkdf2_sha256` password
    hashing). Zero external dependencies; this is what the test suite runs
    against. Good for offline development or if you don't have a Supabase
    project yet.
  - `supabase` — register/login delegate to real Supabase Auth
    (`app/services/auth_supabase.py`); the backend verifies the JWT Supabase
    issues via `SUPABASE_JWT_SECRET`. A database trigger
    (`migrations/002_auth_trigger.sql`) auto-creates the matching
    `public.users` profile row the moment Supabase Auth creates a user, so
    no app code has to bridge the two.
- [x] Storage bucket setup: convention documented
      (`reports/{user_id}/{report_id}/{image_id}.jpg`) **and** a runnable
      script (`backend/scripts/create_storage_bucket.py`) that creates the
      private bucket with the right size/type restrictions.
- [x] Test coverage: 12 passing tests covering register/login/me, duplicate
      email rejection, wrong-password rejection, invalid/missing token
      rejection, and admin-route role enforcement.

### Phase 2 — Frontend Core ✅
- [x] Dashboard — summary cards (lost/found/potential/recovered), recent
      reports, unread notifications preview
- [x] Report Lost / Report Found forms — shared component, color-coded
      header per type, image dropzone (1–3 photos, client-side type/size
      validation), AI-suggested category badge, live description-quality
      tips (FR-18), redirects into matching after submit
- [x] My Items — tabbed Lost/Found list with status filter, report detail
      page with lifecycle-aware status actions (SRS FR-14) and delete
- [x] Potential Matches (ranked, score + reason chips) and Match Details
      (side-by-side comparison, full score breakdown, explanation list) —
      wired against the Phase 1 matching engine, which already runs
      end-to-end on metadata even before Phase 3/4 embeddings exist
- [x] Notifications page with read/unread state
- [x] Minimal Admin Dashboard + Report Management (stat cards, moderate
      actions) — pulled forward from Phase 7 since the backend admin API
      already shipped in Phase 1
- [x] Status badges, score bars/chips, empty states — consistent with the
      UI/UX doc's Lost/Found accent + semantic status palette throughout

**Image storage:** photos are uploaded to `POST /api/uploads/image`
(validated, preprocessed with Pillow, persisted to Supabase Storage or a
local-disk fallback) and their CLIP embeddings are collected via
`POST /api/ai/embed-image` — both wired into `ImageDropzone` as of Phase 3.

### Phase 3 — Image Pipeline ✅
- [x] Image upload API + validation — `POST /api/uploads/image`
      (`app/api/routes/uploads.py`): rejects unsupported MIME types,
      oversized files, empty files, and files that fail to decode as a
      real image even if mislabeled (SRS Sec. 8/9)
- [x] Pillow preprocessing — decode/verify + RGB conversion
      (`vision.decode_image_bytes`), downscale + re-encode to JPEG before
      storage (`storage.preprocess_for_storage`)
- [x] Pretrained CLIP integration (`app/services/vision.py`, lazy-loaded
      `open_clip`) with a documented, deterministic fallback
      (category `"Other"`, 0.0 confidence, zero-vector embedding) when
      `torch`/`open_clip` aren't installed or weights can't be fetched —
      so the app and test suite never hard-fail without a GPU/internet
- [x] Zero-shot category scoring against the controlled `CATEGORY_LABELS`
      set (`POST /api/ai/analyze-image`), confidence-thresholded per
      FR-04.4, plus a CLIP-independent dominant-color estimate (K-means)
- [x] Normalized 512-dim image embedding generation
      (`POST /api/ai/embed-image`)
- [x] Embeddings saved to `pgvector` — `ReportCreate.image_embeddings`
      (one per uploaded photo) are averaged and re-normalized into
      `Report.image_embedding` at creation time (FR-06.2)
- [x] AI suggestions returned to the frontend and stay user-editable —
      `ImageDropzone` calls `/ai/analyze-image` on the first photo and
      `ReportForm` pre-fills category/color with an "AI suggested" badge
      that clears the moment the user edits the field
- [x] Test coverage: `test_vision.py` (fallback-path unit tests),
      `test_uploads.py` (validation + auth), `test_ai_routes.py`
      (endpoint contracts) — 29 tests total in the suite

### Phase 4 — Text Pipeline ✅
- [x] Pretrained Sentence Transformers integration (`app/services/embeddings.py`,
      lazy-loaded `all-MiniLM-L6-v2`) with the same documented, deterministic
      fallback pattern as Phase 3's CLIP wrapper — a 384-dim zero-vector
      when `sentence-transformers` isn't installed or weights can't be
      fetched, so the app and test suite never hard-fail without internet
- [x] Text embeddings generated server-side from Title + Description +
      Features (FR-05.1) on every `POST /reports/lost|found` — no extra
      client round-trip required (mirrors how `image_embedding` is derived
      from the collected per-photo embeddings in Phase 3)
- [x] Re-encoding on edit (FR-05.2) — `PATCH /reports/{id}` re-embeds
      `text_embedding` whenever title/description/features change,
      skipped for unrelated updates (e.g. a bare status change)
- [x] Text vectors saved to `pgvector` (`Report.text_embedding`, 384-dim)
- [x] Description-quality heuristic promoted into its own
      `app/services/quality.py` module per the Architecture doc's
      component list (previously inlined in the route), now also flags
      generic/vague titles in addition to short/keyword-free descriptions
- [x] Metadata normalization — `embeddings.normalize_location` expands
      common abbreviations (`Bldg`→`building`, `St`→`street`, etc.) and
      strips punctuation/case before comparison, so `matching._location_score`
      isn't defeated by superficial phrasing differences (no GPS dependency,
      per PRD/Architecture risk tables)
- [x] `POST /api/ai/embed-text` now returns real embeddings instead of the
      Phase-3-era stub
- [x] Test coverage: `test_embeddings.py`, `test_quality.py`,
      `test_matching_location.py`, plus new `/ai/embed-text` and
      `/ai/check-report-quality?title=` cases in `test_ai_routes.py`

With Phase 4 landed, **every** component in the FR-08.1 weighted score
(image, text, category, color, location, time) now runs against real
signal instead of a stub — only `brand_score`/`other_score` remain
0-weighted placeholders (brand/logo detection and distinguishing-feature
matching are explicitly out of MVP scope per the PRD).

### Phase 5 — Search & Matching ✅
- [x] **Real pgvector candidate narrowing (FR-07.2/07.3)** —
      `matching._vector_prefilter_candidates` orders the FR-07.1
      hard-filtered set (opposite type, active, no self-match, optional
      category) by pgvector cosine distance against the querying report's
      image/text embedding, and caps it at `CANDIDATE_POOL_SIZE` (default
      50) *before* full weighted scoring runs — so scoring never touches
      the whole opposite-type table as report volume grows
- [x] Documented, tested "degrade, never crash" fallback: if a report has
      no usable (non-zero) embedding yet, or the underlying DB rejects the
      cosine-distance comparison for any reason (e.g. a zero-norm vector
      from the ML fallback path, or a non-Postgres DB), it transparently
      falls back to scoring the full hard-filtered set — same pattern as
      `vision.py`/`embeddings.py`
- [x] Optional ANN indexes (`migrations/003_vector_indexes.sql`, IVFFlat
      on both embedding columns) to keep that pgvector query fast once
      report volume is non-trivial (Architecture Sec. 12) — split into its
      own migration since it only pays off with real data volume
- [x] Category / color / brand component scoring, location similarity
      (normalized, Phase 4), time-decay scoring, weighted final score,
      descending ranking, and match persistence were already live from
      Phase 1's matching-engine skeleton and are unchanged here — Phase 5
      closed the one real gap (pgvector search) called out in the
      Development Plan
- [x] Test coverage: `test_matching_candidates.py` (mocked-DB tests
      covering the no-embedding case, the DB-error fallback case, the
      success case, and the `ENABLE_VECTOR_PREFILTER=False` bypass)

### Phase 6 — Explainability & Notifications ✅
- [x] Component scores per match (FR-08/FR-10) — already persisted on
      every `Match` row since Phase 1; unchanged here
- [x] Threshold-gated explanation generator (`matching.build_explanation`,
      FR-10.2) — unchanged, was already live
- [x] Match Details page (`/matches/details/[matchId]`) — side-by-side
      lost/found comparison, full score breakdown, explanation chip list
      (FR-11.1) — already live from Phase 2
- [x] Notifications table/API (`GET /notifications`,
      `PATCH /notifications/{id}/read`) — already live from Phase 1
- [x] **Fixed: duplicate matches / repeat notifications.** Before this
      phase, `POST /matches/find/{report_id}` inserted a brand-new `Match`
      row for the same (lost, found) pair on every call, and the route's
      inline threshold check re-notified both owners every time a
      qualifying pair was re-scored (e.g. a repeated "check matches"
      click, or an unrelated report edit). `matching.find_and_persist_matches`
      now **upserts** by `(lost_report_id, found_report_id)` and only
      flags a match `just_qualified` the first time it crosses
      `MATCH_NOTIFICATION_THRESHOLD` (rising-edge check, `_should_notify`)
      — a pair that drops below threshold and later re-crosses it
      correctly notifies again, but a pair sitting above threshold across
      repeated calls does not. `migrations/004_match_constraints.sql`
      backstops this with a DB-level `unique (lost_report_id, found_report_id)`
      constraint (run it once against Postgres; it also cleans up any
      duplicate rows produced by pre-Phase-6 runs).
- [x] **New `app/services/notifications.py`** — the threshold/dedup logic
      that used to live inline in `app/api/routes/matches.py` is now its
      own service (matches the Architecture doc's component boundary) and
      is unit-tested without a live Postgres connection.
- [x] Notifications page (`/notifications`) with read/unread state and
      Nav unread-count badge — already live from Phase 2
- [x] Test coverage: `test_matching_notifications.py` (rising-edge logic +
      upsert-vs-insert behavior) and `test_notifications_service.py`
      (dedup contract, missing-report edge case, shared-owner case)

### Phase 7 — Search & Admin ✅
- [x] **Manual search/filter service (FR-15.1)** — new
      `app/services/search.py` + `GET /api/reports/search`: filters by
      type, category, color, brand, location, status, and a `date_from`/
      `date_to` range, plus a free-text `q` keyword match across
      title/description/features. Only active reports are browsable.
      Declared ahead of `GET /reports/{report_id}` in the router so
      `"search"` is never swallowed as a UUID path param.
- [x] **Search / Browse page** (`/search`) — filter panel (type, category
      dropdown from the shared `CATEGORY_LABELS`, color, brand, location,
      status, date range, keyword) over the new endpoint, reusing
      `ReportCard`/`EmptyState` for a consistent look with My Items.
- [x] **Duplicate detection (FR-16.1)** — new `app/services/duplicates.py`:
      flags *same-type* (LOST-LOST / FOUND-FOUND) active report pairs
      whose average image+text cosine similarity is at/above
      `DUPLICATE_SIMILARITY_THRESHOLD` (reuses `matching._cosine_similarity`,
      the same yardstick used for real match scoring). Never auto-merges —
      strictly flags for admin review, per FR-16.1. Exposed via
      `GET /api/admin/duplicates` and folded into `/api/admin/stats` as a
      new `pending_review` count.
- [x] **Admin report table filters** — `GET /api/admin/reports` now
      accepts `type`/`status_filter`/`category` query params; the Admin
      Dashboard UI grew matching dropdown filters above the table.
- [x] **Duplicate review queue UI** — new section on the Admin Dashboard
      listing each flagged pair side-by-side with its similarity %, a
      "mark 2nd report duplicate" action (reuses the existing
      `mark_duplicate` moderation action), and a "not a duplicate" dismiss.
- [x] **Admin "resolve match" action (FR-17.2)** — this was the one
      FR-17.2 admin action with no implementation through Phase 6.
      `PATCH /api/admin/matches/{match_id}/resolve` now advances both
      sides of a confirmed match toward their terminal RECOVERED/RETURNED
      status, correctly stepping through the required intermediate status
      first (SEARCHING→MATCH_FOUND→RECOVERED, etc.) so it never violates
      the FR-14.1 lifecycle rules even for an admin caller.
- [x] Test coverage: `test_search.py` (filter composition, limit
      clamping), `test_duplicates.py` (similarity math, same-type-only
      scanning, dissimilar pairs correctly ignored, type filter), and
      `test_admin_resolve.py` (status-advancement walk for both report
      types, no-op when already terminal/closed) — all mocked-`Session`
      style tests, same rationale as `test_matching_candidates.py`
      (Report/Match carry a Postgres-only pgvector column, so these run
      without a live Postgres connection).

### What's stubbed, pending later phases
- **pgvector ANN indexing** now ships as an opt-in migration
  (`migrations/003_vector_indexes.sql`) — run it once you've seeded enough
  demo data that an exact scan is no longer instant.
- **`migrations/004_match_constraints.sql`** (Phase 6) hasn't been applied
  to a live database yet by this build — run it once against your
  Postgres/Supabase instance alongside `001_init.sql`.
- **Duplicate detection (FR-16) is O(n²) per type, on-demand.** Fine at
  MVP/demo scale (it's an admin-only dashboard query, not on the report
  submission path) — see `app/services/duplicates.py`'s module docstring
  for the scaling note if report volume grows materially.
- **Natural-language (semantic) search (FR-15.2)** remains a documented
  post-core strong addition — Phase 7's `/reports/search` is metadata +
  keyword filtering, not semantic query understanding.
- **Phase 8 (Testing & Evaluation)** and **Phase 9 (Demo Preparation)**
  haven't started: no seeded validation dataset, no weight/threshold
  tuning pass, no responsive-breakpoint QA sweep yet.

## Security Notes

- Secrets live only in `.env` files (git-ignored) — never commit real values.
- All admin routes (`/api/admin/*`) require the `Admin` role, checked
  server-side, never trusted from the client.
- Report ownership is verified server-side before any edit/delete.
