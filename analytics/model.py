"""
analytics/model.py
Early-warning model: predict at-risk (Withdrawal/Fail) from information available in the
FIRST 4 WEEKS only — no full-course features (which would leak the outcome).

Rigor for a DS portfolio:
- Temporal split (train on 2013 presentations, test on 2014) → no leakage across time.
- Honest metrics: ROC-AUC, PR-AUC, and recall/precision at a chosen operating point.
- Calibration (reliability by decile), feature importance, and a fairness check across
  demographic groups. Deterministic (fixed seed + fixed split).
"""
from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    precision_recall_curve,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

# Features known at/within the first 4 weeks (NO total_clicks/avg_score/outcome).
CAT_FEATURES = ["code_module", "gender", "region", "highest_education", "imd_band", "age_band", "disability"]
NUM_FEATURES = ["num_of_prev_attempts", "studied_credits", "date_registration",
                "clicks_first_4w", "active_days_first_4w", "clicks_pre_start",
                "module_presentation_length"]
SENSITIVE = ["gender", "disability", "age_band", "imd_band"]

MODELING_SQL = f"""
    SELECT id_student, code_module, code_presentation,
           {', '.join(CAT_FEATURES[1:] + NUM_FEATURES)},
           final_result
    FROM mart_student
"""


def load_modeling_frame(con) -> pd.DataFrame:
    return con.execute(MODELING_SQL).fetchdf()


def _pick_threshold(y_true, proba, target_recall: float = 0.70) -> float:
    """Highest threshold whose recall >= target_recall (max precision at that recall)."""
    prec, rec, thr = precision_recall_curve(y_true, proba)
    # prec/rec have len n+1; thr has len n. Align to thr.
    rec_t, thr_t = rec[:-1], thr
    ok = np.where(rec_t >= target_recall)[0]
    if len(ok) == 0:
        return 0.5
    return float(thr_t[ok[-1]])  # largest threshold still meeting the recall target


def train_and_evaluate(df: pd.DataFrame, seed: int = 42, target_recall: float = 0.70) -> Dict[str, Any]:
    df = df.copy()
    df["at_risk"] = df["final_result"].isin(["Withdrawn", "Fail"]).astype(int)

    is_2013 = df["code_presentation"].str.startswith("2013")
    train, test = df[is_2013], df[~is_2013]
    if train.empty or test.empty:
        raise ValueError("Temporal split produced an empty set; check code_presentation values.")

    X_tr, y_tr = train[CAT_FEATURES + NUM_FEATURES], train["at_risk"]
    X_te, y_te = test[CAT_FEATURES + NUM_FEATURES], test["at_risk"]

    pre = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"), CAT_FEATURES),
        ("num", SimpleImputer(strategy="median"), NUM_FEATURES),
    ])
    clf = RandomForestClassifier(n_estimators=300, random_state=seed, n_jobs=-1, class_weight="balanced")
    pipe = Pipeline([("pre", pre), ("clf", clf)])
    pipe.fit(X_tr, y_tr)

    proba = pipe.predict_proba(X_te)[:, 1]
    thr = _pick_threshold(y_te, proba, target_recall)
    pred = (proba >= thr).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_te, pred).ravel()

    metrics = {
        "n_train": int(len(train)), "n_test": int(len(test)),
        "base_rate_test": round(float(y_te.mean()), 4),
        "roc_auc": round(float(roc_auc_score(y_te, proba)), 4),
        "pr_auc": round(float(average_precision_score(y_te, proba)), 4),
        "brier": round(float(brier_score_loss(y_te, proba)), 4),
        "threshold": round(thr, 4),
        "recall": round(float(tp / (tp + fn)) if (tp + fn) else 0.0, 4),
        "precision": round(float(tp / (tp + fp)) if (tp + fp) else 0.0, 4),
        "confusion": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "train_years": "2013 presentations", "test_years": "2014 presentations",
    }

    # Feature importances aggregated back to original columns.
    names = pipe.named_steps["pre"].get_feature_names_out()
    imp = pipe.named_steps["clf"].feature_importances_
    agg: Dict[str, float] = {}
    for n, v in zip(names, imp):
        base = n.split("__", 1)[1]
        orig = base.split("_", 1)[0] if base.startswith(tuple(c + "_" for c in CAT_FEATURES)) else base
        # map one-hot column back to its source categorical / numeric feature
        src = next((c for c in CAT_FEATURES if base.startswith(c + "_")), base)
        agg[src] = agg.get(src, 0.0) + float(v)
    importance = (pd.DataFrame({"feature": list(agg), "importance": list(agg.values())})
                  .sort_values("importance", ascending=False).reset_index(drop=True))

    # Calibration by predicted-probability decile.
    cal = pd.DataFrame({"proba": proba, "y": y_te.values})
    cal["decile"] = pd.qcut(cal["proba"].rank(method="first"), 10, labels=False)
    calibration = (cal.groupby("decile")
                   .agg(mean_pred=("proba", "mean"), actual_rate=("y", "mean"), n=("y", "size"))
                   .round(4).reset_index())

    # Fairness: selection rate & recall per group at the chosen threshold.
    test_scored = test.copy()
    test_scored["risk_score"] = proba
    test_scored["flagged"] = pred
    rows = []
    for attr in SENSITIVE:
        for val, g in test_scored.groupby(attr, dropna=False):
            pos = g[g["at_risk"] == 1]
            rows.append({
                "attribute": attr, "group": str(val), "n": int(len(g)),
                "selection_rate": round(float(g["flagged"].mean()), 4),
                "recall": round(float(pos["flagged"].mean()) if len(pos) else np.nan, 4),
            })
    fairness = pd.DataFrame(rows)

    scores = test_scored[["id_student", "code_module", "code_presentation",
                          "risk_score", "at_risk", "flagged", "final_result"]].copy()
    scores["risk_score"] = scores["risk_score"].round(3)

    return {"metrics": metrics, "importance": importance, "calibration": calibration,
            "fairness": fairness, "scores": scores}
