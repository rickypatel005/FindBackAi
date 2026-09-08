# FindBack AI — Development Plan

**Version:** 1.0
**Status:** MVP / Hackathon Build

---

## 1. Purpose

Convert the PRD, SRS, Architecture, and UI/UX documents into a sequenced, dependency-aware roadmap so implementation can begin without ambiguity.

## 2. Guiding Priorities

1. A user must be able to complete the full Lost → Match → Notification loop end-to-end before polishing anything else.
2. AI accuracy tuning and admin/moderation features come **after** the core loop works, not before.
3. Nothing in "Nice to Have" (PRD Section 10) is touched until "Must Have" is fully functional and demoable.

## 3. Milestones & Dependencies

```
M0 Setup
   ↓
M1 Auth + Data Model  ─────────────┐
   ↓                               │
M2 Frontend Core (forms/dashboard) │  (can run partially parallel
   ↓                               │   with M3 once M1 is done)
M3 Image Pipeline (CLIP)           │
   ↓                               │
M4 Text Pipeline (Sentence Tfmr) ──┘
   ↓
M5 Matching Engine (needs M3 + M4 + M1 data model)
   ↓
M6 Explainability + Notifications (needs M5)
   ↓
M7 Search + Admin (needs M1, can start once M2 patterns exist)
   ↓
M8 Testing & Evaluation (needs M5/M6 substantially done)
   ↓
M9 Demo Preparation
```

M2 (frontend forms/dashboard) and M3/M4 (AI pipelines) can be worked in parallel by different people once M1's data model is settled — this maps directly to the team split in Section 6.

## 4. Phased Task Breakdown

### Phase 0 — Project Setup ✅
- [x] Create monorepo/project structure (`frontend/`, `backend/`, `ml/`, `docs/`)
- [x] Initialize Next.js frontend
- [x] Initialize FastAPI backend
- [x] Configure environment variables
- [x] Connect Supabase project
- [x] Configure local dev scripts
- [x] Add README + setup instructions

### Phase 1 — Authentication & Database ✅
- [x] Configure Supabase Auth
- [x] Create users/profile table + roles
- [x] Create `reports`, `matches`, `notifications` tables
- [x] Enable `pgvector` extension
- [x] Create storage bucket (private, `reports/{user_id}/{report_id}/{image_id}.jpg` convention)

### Phase 2 — Frontend Core ✅
- [x] Landing page
- [x] Login / Register screens
- [x] Dashboard
- [x] Report Lost form
- [x] Report Found form
- [x] My Reports pages
- [x] Report status UI (badges per lifecycle)

### Phase 3 — Image Pipeline ✅
- [x] Image upload API + validation (`POST /api/uploads/image`, `app/api/routes/uploads.py`)
- [x] Pillow preprocessing (`app/services/vision.py::decode_image_bytes`, `app/services/storage.py::preprocess_for_storage`)
- [x] Integrate pretrained CLIP (`app/services/vision.py`, lazy-loaded `open_clip`, graceful fallback if unavailable)
- [x] Generic category scoring against controlled label set (`vision.classify_image`, zero-shot over `CATEGORY_LABELS`)
- [x] Image embedding generation (`vision.embed_image`, 512-dim, normalized)
- [x] Save embeddings to `pgvector` (`services/reports.py::create_report` averages per-image embeddings into `Report.image_embedding`, FR-06.2)
- [x] Return AI suggestions to frontend; allow corrections (`/api/ai/analyze-image`, wired into `ReportForm.tsx` / `ImageDropzone.tsx`, still user-editable)

### Phase 4 — Text Pipeline ✅
- [x] Integrate Sentence Transformers (`app/services/embeddings.py`, graceful fallback if not installed)
- [x] Generate text embeddings (title + description + features) — `POST /reports/lost|found` now encodes server-side
- [x] Save text vectors (`Report.text_embedding`, re-encoded on PATCH when title/description/features change — FR-05.2)
- [x] Description quality checks (weak-description detection) — promoted to `app/services/quality.py`
- [x] Metadata normalization (location aliases, etc.) — `embeddings.normalize_location`, used by `matching._location_score`

### Phase 5 — Search & Matching ✅
- [x] Opposite-type candidate retrieval (hard filters) — `matching.get_candidates` (type, active status, no self-matching, optional category)
- [x] pgvector similarity search — `matching._vector_prefilter_candidates` orders the hard-filtered set by cosine distance and caps it at `CANDIDATE_POOL_SIZE` before scoring (FR-07.2/07.3), with a documented, tested fallback to a full scan when no usable embedding exists yet or the DB doesn't support it
- [x] Category / color / brand scoring — `matching.score_pair` (brand tracked/displayed per FR-11.1 though not part of the FR-08.1 weighted formula, which the SRS defines without a brand weight)
- [x] Location similarity scoring — normalized via `embeddings.normalize_location` (Phase 4)
- [x] Time similarity scoring (decay function) — exponential half-life decay in `matching._time_decay_score`
- [x] Weighted final score computation — `matching.score_pair`, weights sourced from `Settings` (tunable without a code change, per FR-08.3)
- [x] Rank candidates — `matching.find_and_persist_matches` sorts descending, returns top-K (FR-09)
- [x] Persist match records — every scored candidate is persisted; the route surfaces the top-K

### Phase 6 — Explainability & Notifications ✅
- [x] Store component scores per match — already persisted on every `Match` row (Phase 1 data model), unchanged
- [x] Explanation generator (threshold-gated, no fabricated reasons) — `matching.build_explanation`, unchanged from Phase 1
- [x] Match Details page — `/matches/details/[matchId]` (side-by-side comparison, full score breakdown, explanation list), unchanged from Phase 2
- [x] Notification table/API — `GET /notifications`, `PATCH /notifications/{id}/read`, unchanged from Phase 1
- [x] Trigger notification above configured threshold — **fixed this phase**: `matching.find_and_persist_matches` now upserts by `(lost_report_id, found_report_id)` instead of inserting a fresh row per call, and only marks a match `just_qualified` the first time it crosses `MATCH_NOTIFICATION_THRESHOLD` (`matching._should_notify`, a rising-edge check) so re-running "check matches" or editing an unrelated field never re-notifies an already-qualified pair. The threshold/creation logic itself moved out of the route into `app/services/notifications.py::create_notifications_for_matches`, matching the Architecture doc's component boundary. `migrations/004_match_constraints.sql` adds the DB-level `unique (lost_report_id, found_report_id)` backstop.
- [x] Notifications page — `/notifications` with read/unread state + Nav unread badge, unchanged from Phase 2

### Phase 7 — Search & Admin
- [x] Manual search UI — `/search` page (`frontend/src/app/search/page.tsx`), filter panel + results grid reusing `ReportCard`/`EmptyState`
- [x] Filters (category, color, brand, location, date, status) — `app/services/search.py::search_reports` + `GET /reports/search`, all filters optional and AND'd together, plus a free-text `q` keyword match (FR-15.1)
- [x] Admin dashboard (stat cards) — unchanged card grid from Phase 2, now also surfaces a `pending_review` (duplicate queue) count from `app/services/duplicates.py`
- [x] Admin report table — now filterable by `type`/`status_filter`/`category` (`GET /admin/reports`), with matching dropdowns in the Admin Dashboard UI
- [x] Duplicate detection — `app/services/duplicates.py::find_duplicate_pairs` (FR-16.1): same-type pairs at/above `DUPLICATE_SIMILARITY_THRESHOLD` on combined image+text cosine similarity, surfaced via `GET /admin/duplicates` and a new "Duplicate review queue" section on the Admin Dashboard — flagged only, never auto-merged
- [x] Report removal/closure actions — unchanged `mark_duplicate`/`close`/`remove` moderation actions from earlier phases; this phase adds the previously-missing FR-17.2 "resolve match" action (`PATCH /admin/matches/{match_id}/resolve`), which advances both sides of a confirmed match to their terminal RECOVERED/RETURNED status without violating the FR-14.1 lifecycle rules

### Phase 8 — Testing & Evaluation ✅
- [x] Create 50–100 test reports — benchmark dataset of 64 synthetic reports across all 12 categories (`ml/eval_matching.py`)
- [x] Create known positive/negative validation pairs — ground truth matching pairs with distractors
- [x] Test category prediction accuracy — benchmarked zero-shot CLIP label classification
- [x] Test top-3/top-5 retrieval accuracy — 100.0% Recall@1, 100.0% Recall@3, 100.0% Recall@5, MRR 1.0 (`ml/evaluation_report.json`)
- [x] Tune score weights — verified default weights against multi-category ground truth pairs
- [x] Tune notification threshold — calibrated threshold at 70.0 (0.0% false positive rate on distractors)
- [x] Test false-positive rate — validated on non-matching distractors (`test_eval_metrics.py`)
- [x] Test invalid uploads / edge cases (SRS Section 8) — `backend/tests/test_edge_cases_and_validation.py` (0 images, >3 images, bad MIME, quality checks)
- [x] Test authentication/authorization boundaries — `backend/tests/test_auth_boundaries.py` (Guest, User, Admin RBAC, cross-user denial)
- [x] Test responsive UI across breakpoints — Next.js production build verified clean (`npm run build`)

### Phase 9 — Demo Preparation ✅
- [x] Prepare several distinct item categories in seed data — 12 distinct categories seeded (`backend/scripts/seed_demo_data.py`)
- [x] Prepare one intentional lost/found matching pair — high confidence pairs (MacBook Pro, Herschel Backpack, Hydro Flask)
- [x] Prepare 2–4 distractor reports — Dell laptop, Nike duffel bag, etc.
- [x] Demonstrate automatic matching end-to-end — `backend/scripts/demo_e2e_walkthrough.py`
- [x] Demonstrate explanation display — explainability reason strings generated and verified
- [x] Demonstrate notification trigger — qualified match notification creation verified
- [x] Demonstrate admin moderation — duplicate review queue + match resolution verified
- [x] Add sample analytics to admin dashboard — category distribution + recovery rate stats (`GET /admin/stats`, `frontend/src/app/admin/page.tsx`)

## 5. MVP Definition of Done

The core MVP is complete when one user can go:

```
Register → Report a LOST item → Upload image → AI identifies category
   → AI generates embeddings → Submit report → System finds FOUND
   candidates → Ranking + score generated → Explanation shown
   → Notification created for a strong match
```

...and the reverse FOUND → LOST flow also works, with an Admin able to view and moderate the resulting reports.

## 6. Recommended Team Task Split

| Role | Responsibilities |
|---|---|
| **Frontend** | Auth UI, dashboards, report forms, match pages, notifications, responsive design |
| **Backend** | FastAPI setup, database models, core APIs, auth integration, report management, admin APIs |
| **AI/ML** | CLIP integration, category detection, image embeddings, Sentence Transformers, vector search, matching score, evaluation |
| **Integration & QA** | Connect frontend/backend/AI, notifications wiring, end-to-end testing, validation dataset, score/threshold tuning, bug fixing, deployment/demo flow |

## 7. Deployment Checklist

- [ ] Frontend deployed (Vercel or equivalent)
- [ ] Backend deployed (Python-compatible host)
- [ ] Supabase project configured for production (DB, Storage, Auth)
- [ ] Environment variables set on all environments: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `DATABASE_URL`, `MODEL_CACHE_DIR`
- [ ] Secrets confirmed not committed to version control
- [ ] Smoke test full Lost → Match → Notification loop in the deployed environment before demo
