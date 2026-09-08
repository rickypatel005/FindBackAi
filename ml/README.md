# ml/

Reserved for standalone CLIP / Sentence-Transformers experimentation and
evaluation scripts (Development Plan Phases 3, 4, and 8).

In the running application, the actual model wrappers live in the backend
service layer so they're callable from API routes:
- `backend/app/services/vision.py` (Phase 3 — CLIP category scoring + image embeddings)
- `backend/app/services/embeddings.py` (Phase 4 — Sentence Transformers text embeddings)

This folder is for offline work that doesn't belong in the request path:
notebooks, category-label-set tuning, embedding-dimension experiments, and
the validation-pair evaluation harness described in PRD Section 11 (Success
Metrics) and Development Plan Phase 8.
