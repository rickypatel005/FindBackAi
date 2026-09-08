"""Phase 9 — Demo Seed Data Generator for FindBack AI.

Populates the database with:
1. Standard demo users:
   - admin@findback.ai (Role: Admin)
   - lost_user@findback.ai (Role: User)
   - found_user@findback.ai (Role: User)
2. Realistic multi-category items spanning diverse categories.
3. Intentional high-confidence Lost/Found match pairs.
4. Distractor reports to showcase ranking discrimination.
5. Duplicate reports to demonstrate the Admin Duplicate Review Queue (FR-16.1).
6. Runs matching engine to create match records and notifications.

Run:
    python3 backend/scripts/seed_demo_data.py
"""

from __future__ import annotations

import datetime
import os
import sys
import uuid
from pathlib import Path

# Ensure backend package is in python path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import Settings
from app.core.security import hash_password
from app.db.session import SessionLocal, engine
from app.models.match import Match
from app.models.notification import Notification
from app.models.report import Report, ReportStatus, ReportType
from app.models.user import RoleEnum, User
from app.services import embeddings, matching, notifications

settings = Settings()


def create_demo_user(db, email: str, name: str, role: RoleEnum) -> User:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            id=uuid.uuid4(),
            email=email,
            name=name,
            role=role,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"  👤 Created user: {email} ({role.value})")
    else:
        print(f"  ℹ️ User exists: {email} ({role.value})")
    return user


from app.db.session import Base, SessionLocal, engine

def seed_demo_environment():
    print("=" * 70)
    print("  FindBack AI — Seeding Demo Environment (Phase 9)")
    print("=" * 70)

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 1. Create Users
        print("\n1. Setting up demo user accounts...")
        admin_user = create_demo_user(db, "admin@findback.ai", "Admin Moderator", RoleEnum.ADMIN)
        lost_user = create_demo_user(db, "lost_user@findback.ai", "Alex Lost", RoleEnum.USER)
        found_user = create_demo_user(db, "found_user@findback.ai", "Jordan Finder", RoleEnum.USER)

        # 2. Seed Reports
        print("\n2. Seeding multi-category lost and found reports...")
        demo_reports_spec = [
            # --- High confidence matching pair 1: Laptop ---
            {
                "user_id": lost_user.id,
                "type": ReportType.LOST,
                "title": "14-inch Space Gray MacBook Pro",
                "category": "Electronics",
                "color": "Space Gray",
                "brand": "Apple",
                "description": "M2 MacBook Pro lost on the second floor study hall near window desk.",
                "features": "React and Python stickers on top lid, small dent on bottom left corner.",
                "location": "Main Library 2nd Floor",
                "report_date": datetime.date(2026, 9, 1),
                "report_time": datetime.time(14, 0),
                "status": ReportStatus.SEARCHING.value,
                "image_urls": ["https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=500"],
            },
            {
                "user_id": found_user.id,
                "type": ReportType.FOUND,
                "title": "Dark Gray Apple Laptop",
                "category": "Electronics",
                "color": "Gray",
                "brand": "Apple",
                "description": "Found a space grey MacBook on desk 14 next to the window.",
                "features": "Multiple tech stickers on cover, slight ding on underside.",
                "location": "Library Floor 2 Study Area",
                "report_date": datetime.date(2026, 9, 1),
                "report_time": datetime.time(15, 30),
                "status": ReportStatus.UNCLAIMED.value,
                "image_urls": ["https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=500"],
            },

            # --- High confidence matching pair 2: Backpack ---
            {
                "user_id": lost_user.id,
                "type": ReportType.LOST,
                "title": "Navy Blue Herschel Backpack",
                "category": "Bags",
                "color": "Navy Blue",
                "brand": "Herschel",
                "description": "Navy blue canvas backpack with tan synthetic leather straps and front pocket.",
                "features": "White cursive logo patch on front, brass key chain on zipper.",
                "location": "Student Center Cafeteria",
                "report_date": datetime.date(2026, 9, 2),
                "report_time": datetime.time(12, 15),
                "status": ReportStatus.SEARCHING.value,
                "image_urls": ["https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=500"],
            },
            {
                "user_id": found_user.id,
                "type": ReportType.FOUND,
                "title": "Blue Canvas Rucksack with Leather Straps",
                "category": "Bags",
                "color": "Blue",
                "brand": "Herschel Supply Co.",
                "description": "Found blue backpack left under cafeteria table near coffee bar.",
                "features": "Tan bottom straps, metal zipper charm.",
                "location": "Campus Dining Hall",
                "report_date": datetime.date(2026, 9, 2),
                "report_time": datetime.time(13, 0),
                "status": ReportStatus.UNCLAIMED.value,
                "image_urls": ["https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=500"],
            },

            # --- High confidence matching pair 3: Water Bottle ---
            {
                "user_id": lost_user.id,
                "type": ReportType.LOST,
                "title": "32oz Hydro Flask Water Bottle",
                "category": "Bottles",
                "color": "Olive Green",
                "brand": "Hydro Flask",
                "description": "Olive green wide mouth insulated water bottle with black flex cap.",
                "features": "Yellow National Park sticker, small dent on metal base.",
                "location": "Chemistry Lab 304",
                "report_date": datetime.date(2026, 9, 3),
                "report_time": datetime.time(16, 0),
                "status": ReportStatus.SEARCHING.value,
                "image_urls": ["https://images.unsplash.com/photo-1602143407151-7111542de6e8?w=500"],
            },
            {
                "user_id": found_user.id,
                "type": ReportType.FOUND,
                "title": "Green Metal Insulated Thermos",
                "category": "Bottles",
                "color": "Green",
                "brand": "Hydro Flask",
                "description": "Found green metal bottle left on lab workbench.",
                "features": "Park decal sticker on side, bottom rim dented.",
                "location": "Science Lab Chemistry 3rd Floor",
                "report_date": datetime.date(2026, 9, 3),
                "report_time": datetime.time(17, 0),
                "status": ReportStatus.UNCLAIMED.value,
                "image_urls": ["https://images.unsplash.com/photo-1602143407151-7111542de6e8?w=500"],
            },

            # --- Distractors ---
            {
                "user_id": found_user.id,
                "type": ReportType.FOUND,
                "title": "Silver Dell XPS 13",
                "category": "Electronics",
                "color": "Silver",
                "brand": "Dell",
                "description": "Found Windows laptop in lecture hall 101.",
                "features": "Clean surface, Intel inside badge.",
                "location": "Science Building 101",
                "report_date": datetime.date(2026, 9, 1),
                "report_time": datetime.time(10, 0),
                "status": ReportStatus.UNCLAIMED.value,
                "image_urls": ["https://images.unsplash.com/photo-1588872657578-7efd1f1555ed?w=500"],
            },
            {
                "user_id": found_user.id,
                "type": ReportType.FOUND,
                "title": "Black Nike Gym Duffel Bag",
                "category": "Bags",
                "color": "Black",
                "brand": "Nike",
                "description": "Black sports duffel left near basketball courts.",
                "features": "White swoosh logo.",
                "location": "Recreation Center Gym",
                "report_date": datetime.date(2026, 9, 2),
                "report_time": datetime.time(18, 0),
                "status": ReportStatus.UNCLAIMED.value,
                "image_urls": ["https://images.unsplash.com/photo-1544816155-12df9643f363?w=500"],
            },

            # --- Duplicate Pair (FR-16.1 demonstration for Admin Duplicate Queue) ---
            {
                "user_id": lost_user.id,
                "type": ReportType.LOST,
                "title": "Lost White AirPods Pro Case",
                "category": "Earbuds/Headphones",
                "color": "White",
                "brand": "Apple",
                "description": "Lost my AirPods Pro white charging case with green rubber cover.",
                "features": "Green silicone case with clip.",
                "location": "North Bus Terminal",
                "report_date": datetime.date(2026, 9, 4),
                "report_time": datetime.time(9, 0),
                "status": ReportStatus.SEARCHING.value,
                "image_urls": ["https://images.unsplash.com/photo-1600294037681-c80b4cb5b434?w=500"],
            },
            {
                "user_id": lost_user.id,
                "type": ReportType.LOST,
                "title": "Lost White AirPods Pro Case (Duplicate)",
                "category": "Earbuds/Headphones",
                "color": "White",
                "brand": "Apple",
                "description": "Lost my AirPods Pro white charging case with green rubber cover.",
                "features": "Green silicone case with clip.",
                "location": "North Bus Terminal",
                "report_date": datetime.date(2026, 9, 4),
                "report_time": datetime.time(9, 0),
                "status": ReportStatus.SEARCHING.value,
                "image_urls": ["https://images.unsplash.com/photo-1600294037681-c80b4cb5b434?w=500"],
            },
        ]

        created_reports = []
        for spec in demo_reports_spec:
            # Check if report with exact title already exists
            existing = db.query(Report).filter(Report.title == spec["title"]).first()
            if existing:
                created_reports.append(existing)
                continue

            full_text = f"{spec['title']} {spec['description']} {spec.get('features', '')}"
            text_vec = embeddings.embed_text(full_text)
            img_vec = [0.0] * 512

            report = Report(
                id=uuid.uuid4(),
                user_id=spec["user_id"],
                type=spec["type"],
                title=spec["title"],
                category=spec["category"],
                color=spec["color"],
                brand=spec.get("brand"),
                description=spec["description"],
                features=spec.get("features"),
                location=spec["location"],
                report_date=spec["report_date"],
                report_time=spec.get("report_time"),
                status=spec["status"],
                image_urls=spec["image_urls"],
                text_embedding=text_vec,
                image_embedding=img_vec,
                is_active="true",
            )
            db.add(report)
            db.commit()
            db.refresh(report)
            created_reports.append(report)
            print(f"  📦 Created report: [{report.type.value}] {report.title} ({report.category})")

        # 3. Compute and Persist Matches + Trigger Notifications
        print("\n3. Running matching engine & generating explainable notifications...")
        lost_reports = [r for r in created_reports if r.type == ReportType.LOST]
        for lost in lost_reports:
            matches = matching.find_and_persist_matches(db, lost)
            for m in matches:
                if m.final_score >= settings.MATCH_NOTIFICATION_THRESHOLD:
                    print(f"  🔔 Strong Match ({m.final_score:.1f}%): Lost '{lost.title}' -> Found ID {m.found_report_id}")
                    print(f"     Reasons: {', '.join(m.explanation)}")

        print("\n" + "=" * 70)
        print("  🎉 Demo data seeding successfully completed!")
        print("=" * 70)
        print("  Credentials for Demo:")
        print("    Admin: admin@findback.ai / DemoPassword123!")
        print("    Lost User: lost_user@findback.ai / DemoPassword123!")
        print("    Found User: found_user@findback.ai / DemoPassword123!")
        print("=" * 70)

    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_environment()
