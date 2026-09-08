# FindBack AI — Demo & Evaluation Guide

**Version:** 1.0  
**Phase:** 8 & 9 (Testing, Evaluation & Demo Preparation)

---

## 1. Overview

FindBack AI is a multimodal AI lost-and-found platform. This guide explains how to:
1. Run the test suite and evaluation benchmarks (Phase 8).
2. Seed the demo environment with realistic multi-category reports (Phase 9).
3. Run the automated end-to-end demo walkthrough.
4. Run the frontend and backend web applications locally.

---

## 2. Running Evaluation & Benchmarks (Phase 8)

### 2.1 Multimodal Retrieval & Ranking Benchmark
The ML evaluation harness (`ml/eval_matching.py`) evaluates retrieval performance across a 64-item dataset spanning all 12 supported item categories (Electronics, Bags, Wallets, Documents, Clothing, Keys, Books, Accessories, Bottles, Watches, Earbuds/Headphones, Other).

```bash
# Run standalone benchmark
python3 ml/eval_matching.py
```

**Target Success Metrics:**
- **Recall @ 1 (Top-1 Accuracy):** ≥ 80% (Achieved: **100%**)
- **Recall @ 3 (Top-3 Accuracy):** ≥ 90% (Achieved: **100%**)
- **Recall @ 5 (Top-5 Accuracy):** ≥ 95% (Achieved: **100%**)
- **Mean Reciprocal Rank (MRR):** ≥ 0.70 (Achieved: **1.0**)
- **False Positive Rate @ Threshold:** ≤ 15% (Achieved: **0.0%**)

Output results are saved to `ml/evaluation_report.json`.

### 2.2 Pytest Test Suite (100+ Tests)
Run unit, integration, RBAC, edge-case, and validation tests:

```bash
cd backend
pytest -v
```

---

## 3. Demo Preparation & Seeding (Phase 9)

### 3.1 Demo User Accounts

| Account | Email | Password | Role | Purpose |
|---|---|---|---|---|
| **Admin** | `admin@findback.ai` | `DemoPassword123!` | `Admin` | Moderation, duplicate queue review, resolve matches, platform stats |
| **Lost User** | `lost_user@findback.ai` | `DemoPassword123!` | `User` | Submitting lost reports, viewing matches, receiving notifications |
| **Found User** | `found_user@findback.ai` | `DemoPassword123!` | `User` | Submitting found items to help reunite belongings |

### 3.2 Seed Database
Seed the database with intentional matching pairs, distractors, and duplicate review candidates:

```bash
python3 backend/scripts/seed_demo_data.py
```

### 3.3 Automated End-to-End Demo Walkthrough
Run the complete automated walkthrough script demonstrating every step of the user journey:

```bash
python3 backend/scripts/demo_e2e_walkthrough.py
```

**Journey Steps Verified:**
1. **User Authentication:** Registers/authenticates users and issues JWTs.
2. **AI Assistance:** Runs zero-shot category prediction, color extraction, and description quality checks.
3. **Report Submission:** Submits Lost and Found reports with images and metadata.
4. **Multimodal Matching:** Searches opposite-type candidates, computes image + text + metadata score, and ranks results.
5. **Explainable AI:** Generates and verifies readable match explanation reasons.
6. **Notifications:** Verifies in-app notification creation for qualifying matches above the 70% threshold.
7. **Manual Search & Filters:** Tests filter parameters (category, color, location, keywords).
8. **Admin Moderation:** Inspects duplicate review queue (FR-16.1) and executes match resolution advancing items to terminal `RECOVERED` / `RETURNED` status.
9. **Admin Analytics:** Inspects total reports, recovery rate %, and category distribution breakdown.

---

## 4. Running the Web Application Locally

### 4.1 Backend (FastAPI)
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```
Interactive API docs: `http://localhost:8000/docs`

### 4.2 Frontend (Next.js)
```bash
cd frontend
npm run dev
```
Web app UI: `http://localhost:3000`

### 4.3 Key URLs
- **Landing Page:** `/`
- **Login / Register:** `/login`, `/register`
- **User Dashboard:** `/dashboard`
- **Report Lost Item:** `/report/lost`
- **Report Found Item:** `/report/found`
- **My Reports:** `/items`
- **Matches View:** `/matches/[reportId]`
- **Match Details & Explanation:** `/matches/details/[matchId]`
- **Notifications:** `/notifications`
- **Manual Search & Filters:** `/search`
- **Admin Dashboard & Duplicate Review:** `/admin`
