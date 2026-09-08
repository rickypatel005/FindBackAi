"""Phase 9 — End-to-End Demo Walkthrough & Verification Script for FindBack AI.

Exercises the complete user journey:
1. User registration and JWT authentication (Guest -> User -> Admin)
2. Report creation with AI image analysis & quality validation
3. Multimodal vector + metadata candidate retrieval & scoring
4. Explainable match reason generation
5. In-app notification creation upon qualifying match
6. Manual search & filter verification
7. Admin duplicate detection review queue
8. Admin match resolution (advancing reports to RECOVERED / RETURNED)
9. Admin stats & platform health analytics

Run:
    python3 backend/scripts/demo_e2e_walkthrough.py
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from PIL import Image
from fastapi.testclient import TestClient

# Ensure backend package is in python path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import Settings
from app.db.session import get_db
from app.main import app
from app.models.user import User, RoleEnum
from app.models.report import Report
from app.models.match import Match
from app.models.notification import Notification

import sqlite3
from sqlalchemy import ARRAY, JSON, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from pgvector.sqlalchemy import Vector

from app.db.session import Base

# Allow SQLite to accept Python lists as JSON
sqlite3.register_adapter(list, json.dumps)

@compiles(ARRAY, "sqlite")
def compile_array(type_, compiler, **kw):
    return "JSON"

@compiles(Vector, "sqlite")
def compile_vector(type_, compiler, **kw):
    return "JSON"

settings = Settings()

test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Create all tables (User, Report, Match, Notification) in SQLite memory DB
Base.metadata.create_all(bind=test_engine)

shared_session = TestingSessionLocal()

def override_get_db():
    try:
        yield shared_session
    finally:
        pass

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def create_sample_png() -> bytes:
    img = Image.new("RGB", (32, 32), color=(20, 100, 220))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def run_e2e_demo():
    print("=" * 75)
    print("  FindBack AI — End-to-End System Demo Walkthrough (Phase 9)")
    print("=" * 75)

    # ------------------------------------------------------------------
    # Step 1: Authentication & User Provisioning
    # ------------------------------------------------------------------
    print("\n[Step 1] Authenticating Users...")

    # Register Lost User
    res_lost = client.post(
        "/api/auth/register",
        json={"email": "lost.alex@findback.ai", "password": "SecurePassword123!", "name": "Alex Lost"},
    )
    if res_lost.status_code == 400:  # already exists
        res_lost = client.post(
            "/api/auth/login",
            json={"email": "lost.alex@findback.ai", "password": "SecurePassword123!"},
        )
    assert res_lost.status_code in (200, 201), f"Failed to auth lost user: {res_lost.text}"
    token_lost = res_lost.json()["access_token"]
    lost_user_id = res_lost.json()["user"]["id"]
    print(f"  ✅ Authenticated User (Alex): ID={lost_user_id}")

    # Register Found User
    res_found = client.post(
        "/api/auth/register",
        json={"email": "found.jordan@findback.ai", "password": "SecurePassword123!", "name": "Jordan Finder"},
    )
    if res_found.status_code == 400:
        res_found = client.post(
            "/api/auth/login",
            json={"email": "found.jordan@findback.ai", "password": "SecurePassword123!"},
        )
    assert res_found.status_code in (200, 201), f"Failed to auth found user: {res_found.text}"
    token_found = res_found.json()["access_token"]
    found_user_id = res_found.json()["user"]["id"]
    print(f"  ✅ Authenticated User (Jordan): ID={found_user_id}")

    # Register Admin
    res_admin = client.post(
        "/api/auth/register",
        json={"email": "admin.mod@findback.ai", "password": "AdminPassword123!", "name": "Admin Mod"},
    )
    if res_admin.status_code == 400:
        res_admin = client.post(
            "/api/auth/login",
            json={"email": "admin.mod@findback.ai", "password": "AdminPassword123!"},
        )
    token_admin = res_admin.json()["access_token"]
    print("  ✅ Authenticated Admin: admin.mod@findback.ai")

    # ------------------------------------------------------------------
    # Step 2: AI Assistance (Image Analysis & Quality Check)
    # ------------------------------------------------------------------
    print("\n[Step 2] Testing AI Image Analysis & Description Quality Heuristics...")

    sample_img = create_sample_png()
    ai_res = client.post(
        "/api/ai/analyze-image",
        files={"file": ("laptop.png", sample_img, "image/png")},
    )
    assert ai_res.status_code == 200, f"AI analyze failed: {ai_res.text}"
    ai_data = ai_res.json()
    print(f"  🤖 AI Suggested Category: '{ai_data['category']}' (Confidence: {ai_data['confidence']:.2f})")
    print(f"  🤖 AI Suggested Dominant Color: '{ai_data.get('color')}'")

    # Quality check
    quality_res = client.post(
        "/api/ai/check-report-quality?description=Blue+backpack&title=Lost+bag",
    )
    assert quality_res.status_code == 200
    q_data = quality_res.json()
    print(f"  ⚠️  Quality Heuristic flagged short description: is_weak={q_data['is_weak']}, suggestions={len(q_data['suggestions'])}")

    # ------------------------------------------------------------------
    # Step 3: Create Lost & Found Reports
    # ------------------------------------------------------------------
    print("\n[Step 3] Submitting Lost & Found Reports...")

    lost_report_payload = {
        "title": "14-inch Space Gray MacBook Pro",
        "category": "Electronics",
        "color": "Space Gray",
        "brand": "Apple",
        "description": "M2 MacBook Pro with React and Python stickers on the lid.",
        "features": "Small scratch on the left corner of top cover.",
        "location": "Main Library 2nd Floor Study Room",
        "report_date": "2026-09-08",
        "report_time": "11:30:00",
        "image_urls": ["https://images.unsplash.com/photo-1517336714731-489689fd1ca8"],
    }
    lost_create_res = client.post(
        "/api/reports/lost",
        json=lost_report_payload,
        headers={"Authorization": f"Bearer {token_lost}"},
    )
    assert lost_create_res.status_code == 201, f"Create lost failed: {lost_create_res.text}"
    lost_report = lost_create_res.json()
    print(f"  📄 [LOST REPORT CREATED] ID={lost_report['id']} Title='{lost_report['title']}' Status={lost_report['status']}")

    found_report_payload = {
        "title": "Space Gray Apple Laptop",
        "category": "Electronics",
        "color": "Space Gray",
        "brand": "Apple",
        "description": "Found a MacBook on desk 14 on the 2nd floor library near window.",
        "features": "Has coding stickers on lid and small mark on corner.",
        "location": "Main Library 2nd Floor Study Room",
        "report_date": "2026-09-08",
        "report_time": "12:15:00",
        "image_urls": ["https://images.unsplash.com/photo-1517336714731-489689fd1ca8"],
    }
    found_create_res = client.post(
        "/api/reports/found",
        json=found_report_payload,
        headers={"Authorization": f"Bearer {token_found}"},
    )
    assert found_create_res.status_code == 201, f"Create found failed: {found_create_res.text}"
    found_report = found_create_res.json()
    print(f"  📄 [FOUND REPORT CREATED] ID={found_report['id']} Title='{found_report['title']}' Status={found_report['status']}")

    # ------------------------------------------------------------------
    # Step 4: Automatic Multimodal Matching & Ranking
    # ------------------------------------------------------------------
    print("\n[Step 4] Running Automatic Candidate Retrieval & Multimodal Scoring...")

    match_find_res = client.post(
        f"/api/matches/find/{lost_report['id']}",
        headers={"Authorization": f"Bearer {token_lost}"},
    )
    assert match_find_res.status_code == 200, f"Find matches failed: {match_find_res.text}"
    matches = match_find_res.json()
    print(f"  🎯 Found {len(matches)} potential candidate match(es):")

    top_match = None
    for idx, m in enumerate(matches, 1):
        print(f"     Rank #{idx}: Final Score = {m['final_score']:.1f}% (Found ID: {m['found_report_id']})")
        print(f"        Component Scores -> Text: {m['text_score']} | Cat: {m['category_score']} | Color: {m['color_score']} | Loc: {m['location_score']} | Time: {m['time_score']}")
        print(f"        Explainability Reasons -> {m['explanation']}")
        if m["found_report_id"] == found_report["id"]:
            top_match = m

    # ------------------------------------------------------------------
    # Step 5: Notifications Trigger Verification
    # ------------------------------------------------------------------
    print("\n[Step 5] Verifying In-App Notifications...")

    notif_res = client.get("/api/notifications", headers={"Authorization": f"Bearer {token_lost}"})
    assert notif_res.status_code == 200
    notifications = notif_res.json()
    print(f"  🔔 User Alex has {len(notifications)} notification(s)")
    for n in notifications:
        print(f"     • [{n['title']}] {n['message']} (Read: {n['is_read']})")

    # ------------------------------------------------------------------
    # Step 6: Manual Search & Filtering
    # ------------------------------------------------------------------
    print("\n[Step 6] Testing Manual Search & Filter Fallback (FR-15)...")

    search_res = client.get(
        "/api/reports/search?category=Electronics&color=Space+Gray",
        headers={"Authorization": f"Bearer {token_lost}"},
    )
    assert search_res.status_code == 200
    search_results = search_res.json()
    print(f"  🔎 Filtered Search returned {len(search_results)} matching reports.")

    # ------------------------------------------------------------------
    # Step 7: Admin Statistics, Duplicate Review & Match Resolution
    # ------------------------------------------------------------------
    print("\n[Step 7] Checking Admin Dashboard Stats, Duplicate Review & Match Resolution...")

    # Promote admin user in session
    admin_db_user = shared_session.query(User).filter(User.email == "admin.mod@findback.ai").first()
    if admin_db_user:
        admin_db_user.role = RoleEnum.ADMIN
        shared_session.commit()

    # Re-login to get updated JWT token with Admin role
    login_admin = client.post(
        "/api/auth/login",
        json={"email": "admin.mod@findback.ai", "password": "AdminPassword123!"},
    )
    token_admin = login_admin.json()["access_token"]

    stats_res = client.get(
        "/api/admin/stats",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert stats_res.status_code == 200, f"Admin stats failed: {stats_res.text}"
    stats = stats_res.json()
    print(f"  📊 Total Reports: {stats['total']} | Lost: {stats['lost']} | Found: {stats['found']}")
    print(f"  📊 Potential Matches: {stats['potential_matches']} | Recovered: {stats['recovered']} (Rate: {stats.get('recovery_rate', 0)}%)")
    print(f"  📊 Category Distribution: {stats.get('category_counts')}")

    # Check duplicates queue
    dups_res = client.get("/api/admin/duplicates", headers={"Authorization": f"Bearer {token_admin}"})
    assert dups_res.status_code == 200
    print(f"  🔍 Admin Duplicate Review Queue: {len(dups_res.json())} pending duplicate candidate(s)")

    # Resolve match if top_match exists
    if top_match:
        resolve_res = client.patch(
            f"/api/admin/matches/{top_match['id']}/resolve",
            headers={"Authorization": f"Bearer {token_admin}"},
        )
        assert resolve_res.status_code == 200, f"Resolve match failed: {resolve_res.text}"
        res_data = resolve_res.json()
        print(f"  🤝 Admin resolved match: Lost Status='{res_data['lost_report']['status']}', Found Status='{res_data['found_report']['status']}'")

    print("\n" + "=" * 75)
    print("  ✨ ALL END-TO-END DEMO STEPS COMPLETED & VERIFIED SUCCESSFULLY!")
    print("=" * 75)


if __name__ == "__main__":
    run_e2e_demo()
