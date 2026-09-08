# FindBack AI — System Architecture Document

**Version:** 1.0
**Status:** MVP / Hackathon Build

---

## 1. Objective

Define a practical, implementable architecture for a web application that accepts lost/found reports (images + text + metadata), generates multimodal embeddings, retrieves relevant candidates, computes a weighted match score, explains the result, and notifies users — without over-engineering for hackathon/MVP scope.

## 2. Technology Stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | Next.js + TypeScript + Tailwind + shadcn/ui | Fast to build, good defaults, server + client rendering as needed |
| Backend | FastAPI (Python) + Pydantic + Uvicorn | Async-friendly, plays well with the Python ML ecosystem |
| Database | PostgreSQL + pgvector | Relational data + vector similarity in one system, no extra infra |
| Auth/Storage | Supabase | Bundles Postgres, Auth, and file storage — minimal ops for MVP |
| Image AI | Pretrained CLIP / OpenCLIP | Zero-shot category scoring + image embeddings, no training needed |
| Text AI | Sentence Transformers | Strong pretrained sentence embeddings for description matching |
| Utilities | scikit-learn, Pillow | Scoring helpers, image preprocessing |

**Explicitly avoided for MVP:** custom YOLO training, GPS/maps stack, chat infra, payment infra, blockchain, native mobile.

## 3. High-Level Architecture

```
Browser
   |
   v
Next.js Frontend
   |  HTTPS / REST
   v
FastAPI Backend
   |
   +------------------+------------------+
   |                  |                  |
   v                  v                  v
 CLIP            Sentence           Metadata
(image AI)      Transformer        Processing
                 (text AI)
   |                  |                  |
   +------------------+------------------+
                       |
                       v
             PostgreSQL + pgvector
                       |
                       v
                Matching Engine
                       |
              +--------+--------+
              |                 |
              v                 v
       Explainable Match   Notification
          Generator            Service
```

## 4. Component Responsibilities

- **Frontend (Next.js):** auth screens, report forms, dashboards, match views, admin UI. Talks to backend only via REST; never calls AI models directly.
- **Backend (FastAPI):** all business logic — auth verification, report CRUD, AI orchestration, matching, notifications, admin APIs.
- **Vision service (`services/vision.py`):** wraps CLIP for category scoring and image embedding generation.
- **Embeddings service (`services/embeddings.py`):** wraps Sentence Transformers for text embedding generation.
- **Matching service (`services/matching.py`):** candidate retrieval + weighted scoring + ranking.
- **Search service (`services/search.py`):** manual search/filter endpoint logic.
- **Notifications service (`services/notifications.py`):** threshold checks + notification creation.
- **Quality service (`services/quality.py`):** report-quality heuristics (weak description detection).

## 5. Data Model

```
Users
  id, email, name, role, created_at

Reports
  id, user_id, type (LOST/FOUND), title, category, color, brand,
  description, features, location, report_date, report_time,
  status, image_urls, image_embedding (vector), text_embedding (vector),
  created_at, updated_at

Matches
  id, lost_report_id, found_report_id,
  image_score, text_score, category_score, color_score, brand_score,
  location_score, time_score, other_score, final_score,
  explanation, created_at

Notifications
  id, user_id, match_id, title, message, is_read, created_at
```

`image_embedding` / `text_embedding` are `pgvector` columns; an approximate nearest-neighbor index (e.g. IVFFlat or HNSW) should be added once report volume grows beyond a trivial size.

## 6. API Surface

```
Auth        POST /auth/register | /auth/login | /auth/logout   GET /auth/me
Reports     POST /reports/lost | /reports/found
            GET  /reports/{id} | /reports/mine
            PATCH /reports/{id}   DELETE /reports/{id}
AI          POST /ai/analyze-image | /ai/embed-image | /ai/embed-text | /ai/check-report-quality
Matching    POST /matches/find/{report_id}
            GET  /matches/{report_id} | /matches/{match_id}/details
Notify      GET  /notifications   PATCH /notifications/{id}/read
Admin       GET  /admin/stats | /admin/reports   PATCH /admin/reports/{id}
```

## 7. Data Flow — New Report → Match → Notification

```
Create report
   ↓
AI processing (category, image embedding, text embedding) — async / behind loading state
   ↓
Hard filters: opposite type, active status, optional category
   ↓
Vector similarity retrieval (pgvector) narrows candidates
   ↓
Weighted multimodal scoring on narrowed set
   ↓
Rank candidates, persist top matches
   ↓
If final_score >= notification threshold
   ↓
Create in-app notification
```

## 8. Storage

- Images stored in Supabase Storage, private buckets where practical.
- Path convention: `reports/{user_id}/{report_id}/{image_id}.jpg`
- Only storage paths/URLs are persisted in the `Reports` table — never raw binary in Postgres.

## 9. Security Architecture

- Supabase Auth issues sessions/JWTs; FastAPI verifies them on every protected route.
- Role (`User`/`Admin`) checked server-side per request, never trusted from client input.
- File upload validated for MIME type and size before reaching the vision pipeline.
- User-generated text sanitized before storage and before rendering.
- Report ownership verified before edit/delete.
- All secrets (`SUPABASE_SERVICE_ROLE_KEY`, `DATABASE_URL`, etc.) in environment variables only.

## 10. Deployment

| Component | Target |
|---|---|
| Frontend | Vercel (or equivalent Next.js host) |
| Backend | Any Python-compatible host (Render, Railway, Fly.io, etc.) |
| Database / Storage / Auth | Supabase |

Environment variables: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `DATABASE_URL`, `MODEL_CACHE_DIR`.

## 11. Monitoring (MVP-appropriate)

- Basic request logging on the FastAPI backend (latency, status codes).
- Track AI pipeline failures separately (image analysis vs. embedding vs. matching) so failures are diagnosable without full tracing infra.
- Admin `/admin/stats` endpoint doubles as a lightweight health/usage view for the demo.
- Full observability stack (e.g. Prometheus/Grafana) is out of scope for MVP but noted as a future extension.

## 12. Scalability Notes

- Candidate retrieval is already two-staged (hard filters → vector search → full scoring) specifically to avoid O(n²) comparison as reports grow.
- Add a pgvector ANN index once report count materially exceeds what exact search handles comfortably.
- AI inference (CLIP, Sentence Transformers) should run as async background work so report submission stays responsive under load.
- Matching and notification logic is stateless per request, so the FastAPI backend can scale horizontally behind a load balancer if needed later.

## 13. Key Technical Risks

| Risk | Architectural Mitigation |
|---|---|
| Similar-looking but different objects | Multimodal scoring (image + text + metadata), never image-only |
| Incorrect category prediction | User-editable AI suggestions, "Other" fallback |
| False high-confidence matches | Configurable, tunable thresholds validated against test pairs |
| Weak location semantics without GPS | Text similarity + normalized location aliases, no GPS dependency |
| Small dataset for evaluation | Pretrained models only; evaluation focuses on retrieval quality |
