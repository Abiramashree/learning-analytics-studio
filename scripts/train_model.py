"""
scripts/train_model.py
Train the early-warning model on the warehouse and export small artifacts to
data/serving/ (metrics, feature importance, calibration, fairness, scored test learners)
so the dashboard can show them without retraining or the raw data.

    python scripts/train_model.py
"""
import json
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402
from analytics.data_access import SERVING_DIR  # noqa: E402
from analytics.model import load_modeling_frame, train_and_evaluate  # noqa: E402


def main() -> None:
    con = duckdb.connect(config.DB_PATH, read_only=True)
    try:
        df = load_modeling_frame(con)
    finally:
        con.close()

    art = train_and_evaluate(df, seed=42, target_recall=0.70)
    SERVING_DIR.mkdir(parents=True, exist_ok=True)
    (SERVING_DIR / "model_metrics.json").write_text(json.dumps(art["metrics"], indent=2))
    art["importance"].to_parquet(SERVING_DIR / "model_importance.parquet", index=False)
    art["calibration"].to_parquet(SERVING_DIR / "model_calibration.parquet", index=False)
    art["fairness"].to_parquet(SERVING_DIR / "model_fairness.parquet", index=False)
    art["scores"].to_parquet(SERVING_DIR / "model_scores.parquet", index=False)

    m = art["metrics"]
    print("Early-warning model (first 4 weeks -> at-risk):")
    print(f"  train/test: {m['n_train']:,} / {m['n_test']:,}  (test base rate {m['base_rate_test']*100:.1f}%)")
    print(f"  ROC-AUC {m['roc_auc']} | PR-AUC {m['pr_auc']} | Brier {m['brier']}")
    print(f"  @threshold {m['threshold']}: recall {m['recall']} precision {m['precision']}")
    print(f"  confusion {m['confusion']}")
    print("  top drivers:", ", ".join(art["importance"]["feature"].head(5)))
    print(f"Artifacts -> {SERVING_DIR}")


if __name__ == "__main__":
    main()
