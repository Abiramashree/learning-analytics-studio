"""
Offline tests for the AI accelerator's validation guardrail. No network / no LLM.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analytics import narrative as nar  # noqa: E402


def _facts():
    frames = {
        "overall": pd.DataFrame([{
            "enrolments": 32593, "pass_rate": 0.472, "withdrawal_rate": 0.312,
            "fail_rate": 0.216, "distinction_rate": 0.093,
        }]),
        "engagement_dose": pd.DataFrame({
            "decile": [1, 10], "pass_rate": [0.07, 0.75], "avg_score": [69.5, 80.1],
        }),
        "funnel": pd.DataFrame({
            "ord": [1, 5], "stage": ["Registered", "Passed"], "learners": [32593, 15385],
        }),
    }
    model = {"metrics": {"roc_auc": 0.79, "pr_auc": 0.84, "recall": 0.70, "precision": 0.75,
                         "n_test": 19064, "base_rate_test": 0.54}}
    return nar.collect_facts(frames, model)


def test_deterministic_summary_is_self_consistent():
    f = _facts()
    text = nar.deterministic_summary(f)
    ok, bad = nar.validate_narrative(text, f)
    assert ok, f"deterministic summary should validate, got unverified: {bad}"


def test_validator_flags_a_fabricated_number():
    f = _facts()
    ok, bad = nar.validate_narrative("Pass rate was 47.2% but engagement hit 999.9%.", f)
    assert not ok and "999.9" in bad


def test_validator_allows_known_constants():
    f = _facts()
    ok, _ = nar.validate_narrative("Measured over the first 4 weeks of the 2014 cohort.", f)
    assert ok


def test_classify_courses_tiers():
    outcomes = pd.DataFrame({
        "code_module": ["A", "B", "C"], "code_presentation": ["2013J"] * 3,
        "enrolments": [100, 100, 100], "pass_rate": [0.6, 0.5, 0.4],
        "withdrawal_rate": [0.10, 0.35, 0.45],
    })
    out = nar.classify_courses(outcomes)
    assert set(out["risk_tier"]) == {"Healthy", "Watch", "At risk"}
