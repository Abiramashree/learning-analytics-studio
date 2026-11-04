"""
Offline test for the early-warning model — synthetic data with a temporal split.
No warehouse / network needed.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analytics.model import train_and_evaluate  # noqa: E402


def _synthetic(n=1200, seed=0):
    rng = np.random.default_rng(seed)
    clicks = rng.poisson(40, n).astype(float)
    # lower early engagement -> more likely at-risk (signal the model should find)
    risk_p = 1 / (1 + np.exp((clicks - 40) / 15))
    at_risk = rng.binomial(1, risk_p)
    final = np.where(at_risk == 1, rng.choice(["Withdrawn", "Fail"], n), rng.choice(["Pass", "Distinction"], n))
    year = rng.choice(["2013J", "2014J"], n)
    return pd.DataFrame({
        "id_student": np.arange(n),
        "code_module": rng.choice(["AAA", "BBB"], n),
        "code_presentation": year,
        "gender": rng.choice(["M", "F"], n),
        "region": rng.choice(["R1", "R2"], n),
        "highest_education": rng.choice(["HE", "A level"], n),
        "imd_band": rng.choice(["0-10%", "90-100%"], n),
        "age_band": rng.choice(["0-35", "35-55"], n),
        "disability": rng.choice(["Y", "N"], n),
        "num_of_prev_attempts": rng.integers(0, 2, n),
        "studied_credits": rng.integers(30, 240, n),
        "date_registration": -rng.integers(0, 100, n),
        "clicks_first_4w": clicks,
        "active_days_first_4w": (clicks / 4).round(),
        "clicks_pre_start": rng.poisson(5, n).astype(float),
        "module_presentation_length": rng.choice([240, 268], n),
        "final_result": final,
    })


def test_train_and_evaluate_produces_sane_artifacts():
    art = train_and_evaluate(_synthetic(), seed=42, target_recall=0.6)
    m = art["metrics"]
    assert m["n_train"] > 0 and m["n_test"] > 0
    assert 0.5 <= m["roc_auc"] <= 1.0          # beats random on a real signal
    assert 0 <= m["recall"] <= 1 and 0 <= m["precision"] <= 1
    assert not art["importance"].empty
    assert {"attribute", "group", "recall"} <= set(art["fairness"].columns)
    assert "risk_score" in art["scores"].columns


def test_early_engagement_is_a_top_driver():
    art = train_and_evaluate(_synthetic(), seed=42)
    top3 = set(art["importance"]["feature"].head(3))
    assert "clicks_first_4w" in top3 or "active_days_first_4w" in top3
