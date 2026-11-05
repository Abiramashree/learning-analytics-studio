"""
analytics/narrative.py
AI accelerator — a *validated* narrative layer.

Design principle: AI is an accelerator, not a source of truth. The language model only
re-expresses figures that were already computed by the governed SQL; it never produces a
number of its own. Every figure in its output is then checked back against the warehouse
facts, and anything unverifiable is surfaced. The whole feature is optional — with no LLM
configured it falls back to a deterministic template that is correct by construction.

The model is Gemini (via its OpenAI-compatible endpoint), configured with GOOGLE_API_KEY —
the same key the rest of the toolkit uses. No heavy client dependency is required.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import pandas as pd


# --------------------------------------------------------------------- facts
@dataclass(frozen=True)
class Fact:
    label: str
    value: float          # canonical numeric value used for validation
    display: str          # how it should read in prose


def collect_facts(frames: Dict[str, pd.DataFrame], model: Optional[dict]) -> Dict[str, Fact]:
    """Pull the governed numbers the narrative is allowed to mention. Deterministic."""
    f: Dict[str, Fact] = {}
    o = frames["overall"].iloc[0]
    f["enrolments"] = Fact("enrolments", float(o["enrolments"]), f"{int(o['enrolments']):,}")
    for key, col in [("pass_rate", "pass_rate"), ("withdrawal_rate", "withdrawal_rate"),
                     ("fail_rate", "fail_rate"), ("distinction_rate", "distinction_rate")]:
        f[key] = Fact(key, float(o[col]) * 100, f"{float(o[col])*100:.1f}%")

    dose = frames["engagement_dose"].sort_values("decile")
    lo, hi = dose.iloc[0], dose.iloc[-1]
    f["dose_pass_low"] = Fact("least-engaged decile pass rate", lo["pass_rate"] * 100,
                              f"{lo['pass_rate']*100:.0f}%")
    f["dose_pass_high"] = Fact("most-engaged decile pass rate", hi["pass_rate"] * 100,
                               f"{hi['pass_rate']*100:.0f}%")
    f["dose_score_low"] = Fact("least-engaged decile avg score", float(lo["avg_score"]),
                               f"{lo['avg_score']:.0f}")
    f["dose_score_high"] = Fact("most-engaged decile avg score", float(hi["avg_score"]),
                                f"{hi['avg_score']:.0f}")

    fn = frames["funnel"].sort_values("ord")
    for _, r in fn.iterrows():
        slug = re.sub(r"[^a-z]+", "_", r["stage"].lower()).strip("_")
        f[f"funnel_{slug}"] = Fact(f"funnel: {r['stage']}", float(r["learners"]),
                                   f"{int(r['learners']):,}")

    if model and "metrics" in model:
        m = model["metrics"]
        f["roc_auc"] = Fact("ROC-AUC", float(m["roc_auc"]), f"{m['roc_auc']}")
        f["pr_auc"] = Fact("PR-AUC", float(m["pr_auc"]), f"{m['pr_auc']}")
        f["recall"] = Fact("recall", float(m["recall"]) * 100, f"{m['recall']*100:.0f}%")
        f["precision"] = Fact("precision", float(m["precision"]) * 100, f"{m['precision']*100:.0f}%")
        f["n_test"] = Fact("test cohort size", float(m["n_test"]), f"{int(m['n_test']):,}")
        f["base_rate_test"] = Fact("test base rate", float(m["base_rate_test"]) * 100,
                                   f"{m['base_rate_test']*100:.0f}%")
    return f


# ----------------------------------------------------------- deterministic fallback
def deterministic_summary(f: Dict[str, Fact]) -> str:
    """A correct-by-construction narrative using only the facts (no LLM)."""
    lines = [
        f"Across {f['enrolments'].display} learner enrolments, {f['pass_rate'].display} pass "
        f"and {f['withdrawal_rate'].display} withdraw, with {f['distinction_rate'].display} "
        "reaching distinction.",
        f"Engagement is the clearest signal: pass rate rises from {f['dose_pass_low'].display} "
        f"in the least-engaged decile to {f['dose_pass_high'].display} in the most-engaged, and "
        f"average assessment score from {f['dose_score_low'].display} to {f['dose_score_high'].display}.",
    ]
    if "recall" in f:
        lines.append(
            f"An early-warning model trained only on first-four-week behaviour flags at-risk "
            f"learners at {f['recall'].display} recall and {f['precision'].display} precision "
            f"(ROC-AUC {f['roc_auc'].display}) on a held-out future cohort of {f['n_test'].display}."
        )
    return " ".join(lines)


# ----------------------------------------------------------------- classify (deterministic)
def classify_courses(outcomes: pd.DataFrame) -> pd.DataFrame:
    """Rule-based risk tiers per course run (deterministic — not model output)."""
    d = outcomes.copy()
    def tier(w):
        if w >= 0.40:
            return "At risk"
        if w >= 0.30:
            return "Watch"
        return "Healthy"
    d["risk_tier"] = d["withdrawal_rate"].apply(tier)
    d["course"] = d["code_module"] + " " + d["code_presentation"]
    return d[["course", "enrolments", "pass_rate", "withdrawal_rate", "risk_tier"]]


# ----------------------------------------------------------------- Gemini (optional)
# Gemini's OpenAI-compatible endpoint — reuses the same GOOGLE_API_KEY as the rest of the
# toolkit, with no extra client dependency (plain HTTPS).
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/openai"


def llm_configured() -> bool:
    return bool(os.getenv("GOOGLE_API_KEY"))


def llm_summary(f: Dict[str, Fact], timeout: int = 30) -> str:
    """Generate a summary with Gemini (via its OpenAI-compatible endpoint). Raises if unset."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("No GOOGLE_API_KEY set.")
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

    facts_block = "\n".join(f"- {k}: {v.display} ({v.label})" for k, v in f.items())
    system = (
        "You are a learning-analytics writer. Write a concise executive summary (3–4 sentences) "
        "of the figures provided. Use ONLY the numbers given, verbatim; never invent, round "
        "differently, or infer any figure. Plain, confident language. No bullet points."
    )
    user = f"Validated figures:\n{facts_block}\n\nWrite the summary."
    payload = json.dumps({
        "model": model, "temperature": 0,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
    }).encode()
    req = urllib.request.Request(f"{GEMINI_BASE}/chat/completions", data=payload, method="POST",
                                 headers={"Authorization": f"Bearer {api_key}",
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"].strip()


# ----------------------------------------------------------------- validation
_NUM_RE = re.compile(r"\d[\d,]*\.?\d*")
# constants the prose may legitimately contain that are not KPI facts
_ALLOWED_CONSTANTS = {4.0, 10.0, 2013.0, 2014.0, 1.5}


def _allowed_values(f: Dict[str, Fact]) -> List[float]:
    vals = list(_ALLOWED_CONSTANTS)
    for fact in f.values():
        vals.append(fact.value)
        vals.append(round(fact.value))            # tolerate 47 vs 47.2
    return vals


def validate_narrative(text: str, f: Dict[str, Fact], tol: float = 0.6
                       ) -> Tuple[bool, List[str]]:
    """Check every number in `text` traces to a governed fact. Returns (ok, unverified)."""
    allowed = _allowed_values(f)
    unverified: List[str] = []
    for tok in _NUM_RE.findall(text):
        try:
            val = float(tok.replace(",", ""))
        except ValueError:
            continue
        if any(abs(val - a) <= max(tol, abs(a) * 0.01) for a in allowed):
            continue
        unverified.append(tok)
    # dedupe, keep order
    seen, out = set(), []
    for u in unverified:
        if u not in seen:
            seen.add(u); out.append(u)
    return (len(out) == 0, out)
