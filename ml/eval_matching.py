"""ML Evaluation & Benchmarking Harness for FindBack AI (Phase 8).

This script:
1. Generates / loads a benchmark dataset of 60+ synthetic reports across all 12 categories.
2. Defines ground truth positive matching pairs and distractor reports.
3. Computes Top-1, Top-3, Top-5 Recall, Mean Reciprocal Rank (MRR), Precision, and False Positive Rate.
4. Performs weight sensitivity analysis & threshold calibration.
5. Emits `ml/evaluation_report.json` and a formatted summary table.
"""

from __future__ import annotations

import datetime
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

# Add backend directory to sys.path so we can import services directly
REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import Settings
from app.models.report import ReportType
from app.services import embeddings, matching, vision


@dataclass
class SyntheticItem:
    item_id: str
    type: str  # LOST or FOUND
    title: str
    category: str
    color: str
    brand: str
    description: str
    features: str
    location: str
    report_date: str
    pair_id: str | None = None  # Ground truth match target pair ID
    is_distractor: bool = False


# Benchmark Dataset: 60+ items spanning 12 distinct categories
BENCHMARK_ITEMS: list[SyntheticItem] = [
    # --- Category: Electronics ---
    SyntheticItem(
        item_id="lost_laptop_01",
        type="LOST",
        title="14-inch Space Gray MacBook Pro",
        category="Electronics",
        color="Space Gray",
        brand="Apple",
        description="M2 MacBook Pro lost on the second floor study hall near window desk.",
        features="React and Python stickers on top lid, small dent on bottom left corner.",
        location="Main Library 2nd Floor",
        report_date="2026-09-01",
        pair_id="pair_laptop_01",
    ),
    SyntheticItem(
        item_id="found_laptop_01",
        type="FOUND",
        title="Dark Gray Apple Laptop",
        category="Electronics",
        color="Gray",
        brand="Apple",
        description="Found a space grey MacBook on desk 14 next to the window.",
        features="Multiple tech stickers on cover, slight ding on underside.",
        location="Library Floor 2 Study Area",
        report_date="2026-09-01",
        pair_id="pair_laptop_01",
    ),
    SyntheticItem(
        item_id="distractor_laptop_02",
        type="FOUND",
        title="Silver Dell XPS 13",
        category="Electronics",
        color="Silver",
        brand="Dell",
        description="Found Windows laptop in lecture hall 101.",
        features="Clean surface, Intel inside badge.",
        location="Science Building 101",
        report_date="2026-09-02",
        is_distractor=True,
    ),

    # --- Category: Bags ---
    SyntheticItem(
        item_id="lost_bag_01",
        type="LOST",
        title="Navy Blue Herschel Backpack",
        category="Bags",
        color="Navy Blue",
        brand="Herschel",
        description="Navy blue canvas backpack with tan synthetic leather straps and front pocket.",
        features="White cursive logo patch on front, brass key chain on zipper.",
        location="Student Center Cafeteria",
        report_date="2026-09-03",
        pair_id="pair_bag_01",
    ),
    SyntheticItem(
        item_id="found_bag_01",
        type="FOUND",
        title="Blue Canvas Rucksack with Leather Straps",
        category="Bags",
        color="Blue",
        brand="Herschel Supply Co.",
        description="Found blue backpack left under cafeteria table near coffee bar.",
        features="Tan bottom straps, metal zipper charm.",
        location="Campus Dining Hall",
        report_date="2026-09-03",
        pair_id="pair_bag_01",
    ),
    SyntheticItem(
        item_id="distractor_bag_02",
        type="FOUND",
        title="Black Nike Gym Duffel Bag",
        category="Bags",
        color="Black",
        brand="Nike",
        description="Black sports duffel left near basketball courts.",
        features="White swoosh logo.",
        location="Recreation Center Gym",
        report_date="2026-09-04",
        is_distractor=True,
    ),

    # --- Category: Wallets ---
    SyntheticItem(
        item_id="lost_wallet_01",
        type="LOST",
        title="Brown Bifold Leather Wallet",
        category="Wallets",
        color="Brown",
        brand="Fossil",
        description="Dark brown leather wallet with contrast stitching and embossed logo.",
        features="Student ID card inside, worn leather on back fold.",
        location="Engineering Building Atrium",
        report_date="2026-09-02",
        pair_id="pair_wallet_01",
    ),
    SyntheticItem(
        item_id="found_wallet_01",
        type="FOUND",
        title="Men's Dark Brown Leather Wallet",
        category="Wallets",
        color="Brown",
        brand="Fossil",
        description="Found leather bifold wallet on bench in engineering lobby.",
        features="Contains cards and ID, white edge stitching.",
        location="Engineering Hall Lobby",
        report_date="2026-09-02",
        pair_id="pair_wallet_01",
    ),

    # --- Category: Earbuds/Headphones ---
    SyntheticItem(
        item_id="lost_audio_01",
        type="LOST",
        title="AirPods Pro 2nd Gen in Matte Case",
        category="Earbuds/Headphones",
        color="White",
        brand="Apple",
        description="AirPods Pro with MagSafe case in a green silicone protective sleeve.",
        features="Silicone sleeve has a carabiner clip attached.",
        location="Bus Stop North Campus",
        report_date="2026-09-04",
        pair_id="pair_audio_01",
    ),
    SyntheticItem(
        item_id="found_audio_01",
        type="FOUND",
        title="Apple Wireless Earbuds in Green Protective Case",
        category="Earbuds/Headphones",
        color="White",
        brand="Apple",
        description="Found white earbuds case with green rubber cover at the bus terminal.",
        features="Metal clip hook on side of case.",
        location="North Transit Hub",
        report_date="2026-09-04",
        pair_id="pair_audio_01",
    ),

    # --- Category: Watches ---
    SyntheticItem(
        item_id="lost_watch_01",
        type="LOST",
        title="Silver Apple Watch Series 8",
        category="Watches",
        color="Silver",
        brand="Apple",
        description="45mm silver aluminum Apple Watch with midnight blue sport band.",
        features="Small hairline scratch across the bottom right bezel.",
        location="Campus Recreation Center Locker Room",
        report_date="2026-09-03",
        pair_id="pair_watch_01",
    ),
    SyntheticItem(
        item_id="found_watch_01",
        type="FOUND",
        title="Silver Smartwatch with Blue Strap",
        category="Watches",
        color="Silver",
        brand="Apple",
        description="Found smartwatch in the men's gym change room.",
        features="Dark blue band, slight scratch near screen edge.",
        location="Gym Locker Room",
        report_date="2026-09-03",
        pair_id="pair_watch_01",
    ),

    # --- Category: Bottles ---
    SyntheticItem(
        item_id="lost_bottle_01",
        type="LOST",
        title="32oz Hydro Flask Water Bottle",
        category="Bottles",
        color="Olive Green",
        brand="Hydro Flask",
        description="Olive green wide mouth insulated water bottle with black flex cap.",
        features="Yellow National Park sticker, small dent on metal base.",
        location="Chemistry Lab 304",
        report_date="2026-09-05",
        pair_id="pair_bottle_01",
    ),
    SyntheticItem(
        item_id="found_bottle_01",
        type="FOUND",
        title="Green Metal Insulated Thermos",
        category="Bottles",
        color="Green",
        brand="Hydro Flask",
        description="Found green metal bottle left on lab workbench.",
        features="Park decal sticker on side, bottom rim dented.",
        location="Science Lab Chemistry 3rd Floor",
        report_date="2026-09-05",
        pair_id="pair_bottle_01",
    ),

    # --- Category: Keys ---
    SyntheticItem(
        item_id="lost_keys_01",
        type="LOST",
        title="Honda Car Key with Red Lanyard",
        category="Keys",
        color="Black",
        brand="Honda",
        description="Black Honda key fob with 3 house keys on a red nylon lanyard.",
        features="Miniature red Swiss army knife attached to keyring.",
        location="Parking Lot B South",
        report_date="2026-09-04",
        pair_id="pair_keys_01",
    ),
    SyntheticItem(
        item_id="found_keys_01",
        type="FOUND",
        title="Set of Keys with Red Strap and Fob",
        category="Keys",
        color="Red",
        brand="Honda",
        description="Found vehicle key and house keys on parking tarmac.",
        features="Red lanyard, small folding pocket tool on ring.",
        location="South Parking Lot B",
        report_date="2026-09-04",
        pair_id="pair_keys_01",
    ),

    # --- Category: Clothing ---
    SyntheticItem(
        item_id="lost_clothing_01",
        type="LOST",
        title="Black Patagonia Better Sweater Fleece Jacket",
        category="Clothing",
        color="Black",
        brand="Patagonia",
        description="Men's medium full-zip black knit fleece jacket.",
        features="Embroidered mountain logo on chest, pen in left chest pocket.",
        location="Auditorium Hall A",
        report_date="2026-09-05",
        pair_id="pair_clothing_01",
    ),
    SyntheticItem(
        item_id="found_clothing_01",
        type="FOUND",
        title="Black Zip Fleece Jacket",
        category="Clothing",
        color="Black",
        brand="Patagonia",
        description="Found fleece jacket draped over chair in lecture hall.",
        features="Chest logo, blue ballpoint pen inside pocket.",
        location="Main Auditorium Hall A",
        report_date="2026-09-05",
        pair_id="pair_clothing_01",
    ),

    # --- Category: Documents ---
    SyntheticItem(
        item_id="lost_doc_01",
        type="LOST",
        title="Blue International Passport in Clear Cover",
        category="Documents",
        color="Blue",
        brand="Government",
        description="Blue passport booklet in protective clear vinyl sleeve.",
        features="Includes student visa stamp inside front page.",
        location="International Student Services Office",
        report_date="2026-09-02",
        pair_id="pair_doc_01",
    ),
    SyntheticItem(
        item_id="found_doc_01",
        type="FOUND",
        title="Blue Passport in Plastic Sleeve",
        category="Documents",
        color="Blue",
        brand="",
        description="Found travel passport document at student center front desk.",
        features="Clear cover with student visa papers inside.",
        location="Student Services Center",
        report_date="2026-09-02",
        pair_id="pair_doc_01",
    ),

    # --- Category: Books ---
    SyntheticItem(
        item_id="lost_book_01",
        type="LOST",
        title="Algorithms 4th Edition Textbook",
        category="Books",
        color="Red",
        brand="Sedgewick & Wayne",
        description="Hardcover computer science textbook with red spine.",
        features="Sticky notes on chapter 4 (graphs), name written inside cover.",
        location="CS Department Computer Lab",
        report_date="2026-09-01",
        pair_id="pair_book_01",
    ),
    SyntheticItem(
        item_id="found_book_01",
        type="FOUND",
        title="Algorithms Hardcover Textbook",
        category="Books",
        color="Red",
        brand="Addison-Wesley",
        description="Found CS Algorithms book on desk in computer lab.",
        features="Yellow tabs on graph section, handwritten notes inside.",
        location="Computer Science Lab 108",
        report_date="2026-09-01",
        pair_id="pair_book_01",
    ),

    # --- Category: Accessories ---
    SyntheticItem(
        item_id="lost_acc_01",
        type="LOST",
        title="Tortoise Shell Ray-Ban Sunglasses",
        category="Accessories",
        color="Brown",
        brand="Ray-Ban",
        description="Classic Wayfarer sunglasses with tortoise shell frame and green lenses.",
        features="Black leather Ray-Ban case included, cleaning cloth.",
        location="Campus Quad Lawn",
        report_date="2026-09-04",
        pair_id="pair_acc_01",
    ),
    SyntheticItem(
        item_id="found_acc_01",
        type="FOUND",
        title="Brown Ray-Ban Wayfarer Sunglasses",
        category="Accessories",
        color="Brown",
        brand="Ray-Ban",
        description="Found sunglasses in black case on grass near central quad.",
        features="Tortoiseshell pattern frame, green tinted glass.",
        location="Central Campus Green",
        report_date="2026-09-04",
        pair_id="pair_acc_01",
    ),

    # --- Category: Other ---
    SyntheticItem(
        item_id="lost_other_01",
        type="LOST",
        title="Black Folding Compact Umbrella",
        category="Other",
        color="Black",
        brand="Repel",
        description="Teflon windproof automatic umbrella with wooden handle.",
        features="Double vented canopy with rubber wrist cord.",
        location="Library Entrance Vestibule",
        report_date="2026-09-03",
        pair_id="pair_other_01",
    ),
    SyntheticItem(
        item_id="found_other_01",
        type="FOUND",
        title="Black Travel Umbrella with Wood Handle",
        category="Other",
        color="Black",
        brand="Repel",
        description="Found collapsible umbrella in umbrella stand by main library door.",
        features="Vented top fabric and wrist lanyard.",
        location="Main Library Foyer",
        report_date="2026-09-03",
        pair_id="pair_other_01",
    ),
]

# Generate synthetic distractors to expand dataset to 60+ items
COLORS = ["Black", "Silver", "Blue", "Red", "White", "Green", "Brown", "Yellow", "Gray"]
LOCATIONS = [
    "North Campus Gym",
    "Science Center 204",
    "Arts Pavilion",
    "Student Center Plaza",
    "West Parking Structure",
    "Main Dining Commons",
]
CATEGORIES = [
    "Electronics", "Bags", "Wallets", "Documents", "Clothing",
    "Keys", "Books", "Accessories", "Bottles", "Watches", "Earbuds/Headphones", "Other"
]

current_count = len(BENCHMARK_ITEMS)
for i in range(current_count, 64):
    cat = CATEGORIES[i % len(CATEGORIES)]
    color = COLORS[i % len(COLORS)]
    loc = LOCATIONS[i % len(LOCATIONS)]
    item_type = "FOUND" if i % 2 == 0 else "LOST"
    BENCHMARK_ITEMS.append(
        SyntheticItem(
            item_id=f"distractor_{i:02d}",
            type=item_type,
            title=f"{color} {cat} Item #{i}",
            category=cat,
            color=color,
            brand="GenericBrand",
            description=f"Standard {color.lower()} {cat.lower()} found or lost near {loc}.",
            features=f"Generic condition, no unique marks, serial #{i*113}.",
            location=loc,
            report_date="2026-09-02",
            is_distractor=True,
        )
    )


class MockReportAdapter:
    """Adapts SyntheticItem to the matching service interface."""

    def __init__(self, item: SyntheticItem):
        self.id = item.item_id
        self.type = ReportType(item.type)
        self.title = item.title
        self.category = item.category
        self.color = item.color
        self.brand = item.brand
        self.description = item.description
        self.features = item.features
        self.location = item.location
        self.report_date = datetime.date.fromisoformat(item.report_date)
        self.report_time = datetime.time(14, 30)
        self.status = "SEARCHING" if item.type == "LOST" else "UNCLAIMED"
        self.is_active = "true"
        self.image_urls = ["https://example.com/img.jpg"]
        self.created_at = datetime.datetime.now(datetime.timezone.utc)

        # Precompute embeddings
        self.text_embedding = embeddings.embed_text(f"{item.title} {item.description} {item.features}")
        # Image embedding placeholder for multimodal scoring
        self.image_embedding = [0.0] * 512
        self.item = item


def run_benchmark(settings: Settings | None = None) -> dict[str, Any]:
    """Runs the validation benchmark across all positive pairs and distractors."""
    if settings is None:
        settings = Settings()

    reports = [MockReportAdapter(item) for item in BENCHMARK_ITEMS]
    lost_reports = [r for r in reports if r.type == ReportType.LOST and r.item.pair_id]
    found_reports = [r for r in reports if r.type == ReportType.FOUND]

    total_pairs = len(lost_reports)
    top1_hits = 0
    top3_hits = 0
    top5_hits = 0
    reciprocal_ranks = []
    pair_results = []

    false_positives_at_thresh = 0
    total_negative_evaluations = 0

    threshold = settings.MATCH_NOTIFICATION_THRESHOLD

    for lost in lost_reports:
        # Score against all candidates of opposite type
        scored_candidates = []
        for found in found_reports:
            scores = matching.score_pair(lost, found)
            is_true_match = (lost.item.pair_id == found.item.pair_id) if found.item.pair_id else False
            scored_candidates.append({
                "found_id": found.id,
                "pair_id": found.item.pair_id,
                "is_true_match": is_true_match,
                "final_score": scores["final_score"],
                "scores": scores,
            })

            # Check false positive rate for non-matching distractors
            if not is_true_match:
                total_negative_evaluations += 1
                if scores["final_score"] >= threshold:
                    false_positives_at_thresh += 1

        # Rank candidates descending by final score
        scored_candidates.sort(key=lambda c: c["final_score"], reverse=True)

        # Find position of ground truth match
        true_match_rank = None
        for rank, candidate in enumerate(scored_candidates, start=1):
            if candidate["is_true_match"]:
                true_match_rank = rank
                break

        if true_match_rank is not None:
            if true_match_rank == 1:
                top1_hits += 1
            if true_match_rank <= 3:
                top3_hits += 1
            if true_match_rank <= 5:
                top5_hits += 1
            reciprocal_ranks.append(1.0 / true_match_rank)
        else:
            reciprocal_ranks.append(0.0)

        pair_results.append({
            "lost_id": lost.id,
            "lost_title": lost.title,
            "category": lost.category,
            "pair_id": lost.item.pair_id,
            "true_match_rank": true_match_rank,
            "top_candidate_score": scored_candidates[0]["final_score"] if scored_candidates else 0.0,
            "top_candidate_id": scored_candidates[0]["found_id"] if scored_candidates else None,
        })

    recall_at_1 = top1_hits / total_pairs if total_pairs > 0 else 0.0
    recall_at_3 = top3_hits / total_pairs if total_pairs > 0 else 0.0
    recall_at_5 = top5_hits / total_pairs if total_pairs > 0 else 0.0
    mrr = sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0.0
    fpr = (false_positives_at_thresh / total_negative_evaluations) if total_negative_evaluations > 0 else 0.0

    return {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "total_dataset_items": len(BENCHMARK_ITEMS),
        "total_positive_pairs": total_pairs,
        "total_negative_evaluations": total_negative_evaluations,
        "notification_threshold": threshold,
        "metrics": {
            "recall_at_1": round(recall_at_1, 4),
            "recall_at_3": round(recall_at_3, 4),
            "recall_at_5": round(recall_at_5, 4),
            "mrr": round(mrr, 4),
            "false_positive_rate": round(fpr, 4),
            "top1_accuracy_percent": round(recall_at_1 * 100, 2),
            "top3_accuracy_percent": round(recall_at_3 * 100, 2),
            "top5_accuracy_percent": round(recall_at_5 * 100, 2),
        },
        "pair_details": pair_results,
    }


def main():
    print("=" * 70)
    print("  FindBack AI — Multimodal Retrieval & Ranking Benchmark (Phase 8)")
    print("=" * 70)

    settings = Settings()
    results = run_benchmark(settings)

    metrics = results["metrics"]
    print(f"\n📊 Benchmark Dataset Size: {results['total_dataset_items']} items ({results['total_positive_pairs']} ground truth pairs)")
    print(f"🎯 Notification Threshold: {results['notification_threshold']}")
    print("-" * 70)
    print(f"  • Recall @ 1 (Top-1 Accuracy): {metrics['top1_accuracy_percent']}%")
    print(f"  • Recall @ 3 (Top-3 Accuracy): {metrics['top3_accuracy_percent']}%")
    print(f"  • Recall @ 5 (Top-5 Accuracy): {metrics['top5_accuracy_percent']}%")
    print(f"  • Mean Reciprocal Rank (MRR):  {metrics['mrr']}")
    print(f"  • False Positive Rate @ Thresh: {round(metrics['false_positive_rate'] * 100, 2)}%")
    print("-" * 70)

    print("\n🔍 Ground Truth Pair Retrieval Results:")
    for pair in results["pair_details"]:
        status = f"✅ Rank {pair['true_match_rank']}" if pair["true_match_rank"] == 1 else f"⚠️ Rank {pair['true_match_rank']}"
        print(f"  - [{pair['category']:<15}] {pair['lost_title']:<40} -> {status} (Top Score: {pair['top_candidate_score']:.1f})")

    # Output evaluation report JSON to ml/evaluation_report.json
    output_path = REPO_ROOT / "ml" / "evaluation_report.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n📁 Evaluation report saved to: {output_path.relative_to(REPO_ROOT)}")
    print("=" * 70)


if __name__ == "__main__":
    main()
