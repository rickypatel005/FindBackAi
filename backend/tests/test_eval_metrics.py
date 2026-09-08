"""Phase 8 — Retrieval, Ranking & Evaluation Metrics Test Suite (PRD Section 11 & FR-08/09)."""

import sys
from pathlib import Path
from app.core.config import Settings

# Ensure ml folder is in python path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "ml"))

from eval_matching import run_benchmark


def test_multimodal_matching_retrieval_metrics():
    """Validates that candidate matching achieves target accuracy and false-positive bounds."""
    settings = Settings()
    results = run_benchmark(settings)
    metrics = results["metrics"]

    # PRD Sec. 11 Success Metrics / Acceptance Criteria:
    # 1. Top-5 Retrieval Recall >= 80%
    assert metrics["recall_at_5"] >= 0.80, f"Recall@5 ({metrics['recall_at_5']}) fell below target 0.80"

    # 2. Top-3 Retrieval Recall >= 70%
    assert metrics["recall_at_3"] >= 0.70, f"Recall@3 ({metrics['recall_at_3']}) fell below target 0.70"

    # 3. Mean Reciprocal Rank (MRR) >= 0.65
    assert metrics["mrr"] >= 0.65, f"MRR ({metrics['mrr']}) fell below target 0.65"

    # 4. False positive rate on distractor items at notification threshold <= 15%
    assert metrics["false_positive_rate"] <= 0.15, (
        f"False positive rate ({metrics['false_positive_rate']}) exceeded target 0.15"
    )
