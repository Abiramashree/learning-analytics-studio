"""
app.py
Learning Analytics Studio — dashboard over OULAD.

Reads small aggregates (from the DuckDB warehouse locally, or committed serving parquet
when deployed) and renders a narrative overview, learner demographics, outcomes, engagement
behaviour, a content/assessment-effectiveness deep-dive, and a leakage-free early-warning
model. Everything is deterministic SQL + fixed transforms. Run: streamlit run app.py
"""
import streamlit as st

import viz
from analytics import narrative as nar
from analytics.data_access import get_frames, load_model_artifacts

st.set_page_config(page_title="Learning Analytics Studio", page_icon="🎓", layout="wide")

# ----------------------------------------------------------------- styling
st.markdown(
    """
    <style>
      html, body, [class*="css"] { font-family: -apple-system, BlinkMacSystemFont,
        "SF Pro Text", "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
      .block-container { padding-top: 2.2rem; max-width: 1200px; }
      h1 { font-weight: 600; letter-spacing: -0.02em; }
      h2, h3 { font-weight: 600; letter-spacing: -0.01em; }
      /* metric tiles as soft cards */
      [data-testid="stMetric"] { background: #f5f5f7; border-radius: 14px;
        padding: 14px 18px 10px; }
      [data-testid="stMetricLabel"] p { font-size: 0.80rem; color: #6e6e73;
        font-weight: 500; }
      [data-testid="stMetricValue"] { font-weight: 600; letter-spacing: -0.02em; }
      /* tabs: calmer, roomier */
      button[data-baseweb="tab"] { font-size: 0.98rem; font-weight: 500; }
      [data-testid="stTabs"] [role="tablist"] { gap: 10px; }
      /* section lead-ins */
      .lead { font-size: 1.02rem; color: #1d1d1f; margin: 0.2rem 0 1.1rem; }
      .sect { font-size: 0.78rem; font-weight: 600; letter-spacing: 0.04em;
        text-transform: uppercase; color: #86868b; margin: 1.2rem 0 0.1rem; }
      .sub  { font-size: 0.86rem; color: #6e6e73; margin: 0 0 0.6rem; }
      .insight { background: #f5f5f7; border-radius: 12px; padding: 16px 20px;
        color: #1d1d1f; font-size: 0.95rem; line-height: 1.5; margin: 0.4rem 0 0.2rem; }
      .insight.key { background: #eef4fb; border-left: 3px solid #2a78d6; }
      .badge { display:inline-block; background:#f5f5f7; color:#3a3a3c;
        border-radius: 999px; padding: 3px 11px; font-size: 0.78rem; margin-right: 6px; }
    </style>
    """,
    unsafe_allow_html=True,
)


def sect(title: str, sub: str = "") -> None:
    st.markdown(f"<div class='sect'>{title}</div>", unsafe_allow_html=True)
    if sub:
        st.markdown(f"<div class='sub'>{sub}</div>", unsafe_allow_html=True)


def insight(text: str, key: bool = False) -> None:
    cls = "insight key" if key else "insight"
    st.markdown(f"<div class='{cls}'>{text}</div>", unsafe_allow_html=True)


st.title("Learning Analytics Studio")
st.caption(
    "From 32,593 learner enrolments and 10.6M activity events to decisions — who completes a "
    "course, who disengages, and how early you can tell. A reproducible, SQL-backed pipeline on "
    "the Open University dataset (OULAD): governed metrics, validated models, every number "
    "traceable to its source."
)


@st.cache_data(show_spinner="Loading analytics…")
def load():
    return get_frames()


@st.cache_data(show_spinner=False)
def load_model():
    return load_model_artifacts()


try:
    F = load()
except Exception as exc:  # noqa: BLE001
    st.error(f"No data available: {exc}")
    st.stop()

with st.sidebar:
    st.subheader("About")
    st.markdown(
        "Built on **OULAD** — 32,593 learner enrolments and 10.6M engagement events. "
        "Every metric is defined once in SQL and documented in the glossary, so the "
        "numbers are consistent and the whole pipeline is reproducible."
    )
    sect("How it stays honest")
    st.markdown(
        "- Data-quality gate on every build\n"
        "- Leakage-free, temporal model validation\n"
        "- Fairness audited across cohorts\n"
        "- Governed, documented KPIs"
    )
    st.caption("Data © Open University, OULAD (open dataset). Portfolio project.")

tab_ov, tab_stu, tab_out, tab_eng, tab_con, tab_m = st.tabs(
    ["Overview", "Students", "Outcomes", "Engagement", "Content & effectiveness", "Early warning"]
)

# ------------------------------------------------------------------- Overview
with tab_ov:
    o = F["overall"].iloc[0]
    st.markdown("<div class='lead'><b>Who finishes an online course, who disengages — "
                "and how early can you tell?</b> This studio answers that question end to end.</div>",
                unsafe_allow_html=True)
    k = st.columns(4)
    k[0].metric("Enrolments", f"{int(o['enrolments']):,}")
    k[1].metric("Pass rate", f"{o['pass_rate']*100:.1f}%")
    k[2].metric("Withdrawal rate", f"{o['withdrawal_rate']*100:.1f}%")
    k[3].metric("Distinction rate", f"{o['distinction_rate']*100:.1f}%")

    sect("AI summary", "An accelerator — the model only re-expresses the governed figures, "
                       "and every number it writes is checked back against the warehouse.")
    with st.expander("Generate a validated summary", expanded=False):
        facts = nar.collect_facts(F, load_model())
        if st.button("Generate", key="ai_gen"):
            if nar.llm_configured():
                try:
                    text, source = nar.llm_summary(facts), "live model"
                except Exception as exc:  # noqa: BLE001
                    text, source = nar.deterministic_summary(facts), f"deterministic fallback ({exc})"
            else:
                text, source = nar.deterministic_summary(facts), "deterministic template (no model configured)"
            ok, bad = nar.validate_narrative(text, facts)
            st.markdown(text)
            if ok:
                st.success(f"✓ Every figure verified against the warehouse · source: {source}")
            else:
                st.warning(f"⚠ Figures not traceable to a governed metric: {', '.join(bad)} · source: {source}")
        st.caption("Set `GOOGLE_API_KEY` (optionally `GEMINI_MODEL`) to generate with Gemini; "
                   "otherwise the validated deterministic template is shown. The same "
                   "validate-then-trust pattern is how a free-text classifier (e.g. survey "
                   "verbatims) would be governed.")

    c1, c2 = st.columns(2)
    with c1:
        sect("Outcome mix", "Share of enrolments by final result.")
        st.plotly_chart(viz.outcome_mix_fig(o), width="stretch", key="ov_mix")
    with c2:
        sect("Learner progression", "How many remain at each stage, registration to pass.")
        st.plotly_chart(viz.funnel_fig(F["funnel"]), width="stretch", key="ov_funnel")

    c3, c4 = st.columns(2)
    with c3:
        sect("Early engagement, by outcome", "Average clicks in the first four weeks.")
        st.plotly_chart(viz.engagement_by_outcome_fig(F["engagement_by_outcome"]),
                        width="stretch", key="ov_engagement")
    with c4:
        sect("Where attention goes", "Share of engagement by content type.")
        st.plotly_chart(viz.content_fig(F["content"]), width="stretch", key="ov_content")

    insight(
        "<b>Early engagement is the signal.</b> Across the first four weeks, pass rate rises "
        "from 7% to 75% as engagement climbs — so disengagement is something you can see, and "
        "act on, by week four. The Early-warning model turns this into a flag at about "
        "70% recall and 75% precision.",
        key=True,
    )

# ------------------------------------------------------------------- Students
with tab_stu:
    o = F["overall"].iloc[0]
    courses = F["outcomes_by_course"]
    n_modules = courses["code_module"].nunique()
    n_presentations = courses[["code_module", "code_presentation"]].drop_duplicates().shape[0]
    st.markdown("<div class='lead'><b>Who are the learners — and what do they bring before "
                "day one?</b></div>", unsafe_allow_html=True)
    k = st.columns(3)
    k[0].metric("Enrolments", f"{int(o['enrolments']):,}")
    k[1].metric("Modules", f"{n_modules}")
    k[2].metric("Course runs", f"{n_presentations}")
    st.caption("Each enrolment is one learner in one course run; a learner may enrol more than once.")

    sect("Enrolments by course run", "Module × presentation, largest first.")
    bycourse = courses.assign(course=courses["code_module"] + " " + courses["code_presentation"])
    bycourse = bycourse.sort_values("enrolments", ascending=False)[["course", "enrolments"]]
    st.bar_chart(bycourse.set_index("course"), color=viz.BLUE, height=300)

    sect("Cohort composition", "How enrolments split across a demographic.")
    seg = F["segment"]
    dims = list(seg["dimension"].unique())
    dim = st.selectbox("Break down by", dims,
                       index=dims.index("age_band") if "age_band" in dims else 0, key="stu_dim")
    st.plotly_chart(viz.demographics_bar_fig(seg, dim), width="stretch", key="stu_demo")
    st.caption("Counts shown as recorded; some bands contain nulls.")

    sect("Registration lead time", "How early learners enrol, with the pass rate of each group.")
    st.plotly_chart(viz.registration_timing_fig(F["registration_timing"]), width="stretch", key="stu_reg")
    insight("<b>Register late, leave early.</b> Learners who enrol in the final weeks — or with "
            "no recorded date — withdraw far more often. Enrolment timing is a risk signal "
            "available before the first click.")

# ------------------------------------------------------------------- Outcomes
with tab_out:
    st.markdown("<div class='lead'><b>What happened across courses — and where the outliers "
                "are.</b></div>", unsafe_allow_html=True)
    sect("Pass and withdrawal by course run", "Sorted by withdrawal rate.")
    st.plotly_chart(viz.outcomes_by_course_fig(F["outcomes_by_course"]), width="stretch", key="out_course")

    sect("Pass rate by course run", "Darker is stronger — weak runs stand out at a glance.")
    st.plotly_chart(viz.pass_rate_heatmap_fig(F["outcomes_by_course"]), width="stretch", key="out_heat")

    sect("Outcome gaps by cohort", "Pass vs withdrawal rate by demographic segment.")
    seg = F["segment"]
    dims = list(seg["dimension"].unique())
    dim = st.selectbox("Segment by", dims, index=0, key="out_dim")
    st.plotly_chart(viz.segment_fig(seg, dim), width="stretch", key="out_seg")
    st.caption("Gaps flag where to target support (shown as recorded; some bands have nulls).")

    sect("Withdrawal outliers", "Course runs more than 1.5σ from the mean withdrawal rate.")
    an = F["anomalies"]
    flagged = an[an["flag"]]
    if flagged.empty:
        st.success("No course runs flagged as withdrawal outliers.")
    else:
        show = flagged.assign(course=flagged["code_module"] + " " + flagged["code_presentation"])
        show = show[["course", "enrolments", "withdrawal_rate", "z", "direction"]]
        show["withdrawal_rate"] = (show["withdrawal_rate"] * 100).round(1)
        st.dataframe(show.rename(columns={"withdrawal_rate": "withdrawal_%"}),
                     width="stretch", hide_index=True)

    sect("Course risk tiers",
         "Deterministic rule — withdrawal ≥ 40% = At risk, ≥ 30% = Watch, else Healthy.")
    tiers = nar.classify_courses(F["outcomes_by_course"])
    counts = tiers["risk_tier"].value_counts()
    tc = st.columns(3)
    tc[0].metric("At risk", int(counts.get("At risk", 0)))
    tc[1].metric("Watch", int(counts.get("Watch", 0)))
    tc[2].metric("Healthy", int(counts.get("Healthy", 0)))
    disp = tiers.sort_values("withdrawal_rate", ascending=False).copy()
    disp["pass_rate"] = (disp["pass_rate"] * 100).round(1)
    disp["withdrawal_rate"] = (disp["withdrawal_rate"] * 100).round(1)
    st.dataframe(disp.rename(columns={"pass_rate": "pass_%", "withdrawal_rate": "withdrawal_%"}),
                 width="stretch", hide_index=True)

# ----------------------------------------------------------------- Engagement
with tab_eng:
    st.markdown("<div class='lead'><b>How learners interact with a course — from the first "
                "week to the finish.</b></div>", unsafe_allow_html=True)
    sect("Early engagement, by outcome", "Average clicks in the first four weeks.")
    st.plotly_chart(viz.engagement_by_outcome_fig(F["engagement_by_outcome"]),
                    width="stretch", key="eng_engagement")

    sect("Engagement through the course", "Average clicks per learner, per week, by outcome.")
    st.plotly_chart(viz.engagement_timeline_fig(F["timeline"]), width="stretch", key="eng_timeline")

    sect("Engagement predicts outcomes", "Pass vs withdrawal across first-four-week engagement deciles.")
    st.plotly_chart(viz.engagement_dose_fig(F["engagement_dose"]), width="stretch", key="eng_dose")
    insight("<b>A clean, monotonic relationship.</b> Each step up in early engagement raises "
            "pass rate and lowers withdrawal — pass rate runs from ~7% in the least-active "
            "decile to ~75% in the most-active. This is the empirical basis for the early-warning model.")

# -------------------------------------------------- Content & effectiveness
with tab_con:
    st.markdown("<div class='lead'><b>What learners engage with — and what it produces.</b></div>",
                unsafe_allow_html=True)
    sect("Where learners spend attention", "Share of engagement by content type.")
    st.plotly_chart(viz.content_fig(F["content"]), width="stretch", key="con_content")

    c1, c2 = st.columns(2)
    with c1:
        sect("Scores by assessment type", "Box = middle 50%; whiskers 5th–95th percentile.")
        st.plotly_chart(viz.assessment_box_fig(F["assessment_by_type"]), width="stretch", key="con_box")
        st.caption("CMAs score highest; exams are the hardest.")
    with c2:
        sect("Submission timing", "Submissions relative to the due date, with average score.")
        st.plotly_chart(viz.submission_timing_fig(F["submission_timing"]), width="stretch", key="con_time")
        st.caption("Early submitters score higher on average.")

    sect("Training effectiveness by course run", "Average assessment score per module × presentation.")
    st.plotly_chart(viz.assessment_by_course_fig(F["assessment_by_course"]), width="stretch", key="con_course")

    sect("Engagement and learning", "Average assessment score across engagement deciles.")
    st.plotly_chart(viz.engagement_score_dose_fig(F["engagement_dose"]), width="stretch", key="con_dose")
    insight("<b>Engagement lifts learning, not just completion.</b> Average assessment score "
            "climbs from 69 to 80 from the least- to most-engaged learners.")

# -------------------------------------------------------------- Early warning
with tab_m:
    M = load_model()
    if not M:
        st.warning("Model not trained yet. Run `python scripts/train_model.py` to generate it.")
    else:
        m = M["metrics"]
        st.markdown("<div class='lead'><b>Flag at-risk learners from first-four-week behaviour "
                    "— in time to help.</b></div>", unsafe_allow_html=True)
        st.caption(
            f"Target = withdrawal or fail. Trained on {m['train_years']} ({m['n_train']:,}), "
            f"tested on {m['test_years']} ({m['n_test']:,}) — a temporal split, so the model is "
            "judged on future cohorts, not shuffled rows."
        )
        st.markdown(
            "<span class='badge'>no leakage</span><span class='badge'>temporal split</span>"
            "<span class='badge'>fairness audited</span><span class='badge'>calibrated</span>"
            "<span class='badge'>governed features</span>", unsafe_allow_html=True)
        st.write("")
        k = st.columns(5)
        k[0].metric("ROC-AUC", m["roc_auc"])
        k[1].metric("PR-AUC", m["pr_auc"])
        k[2].metric("Recall", f"{m['recall']*100:.0f}%")
        k[3].metric("Precision", f"{m['precision']*100:.0f}%")
        k[4].metric("Test base rate", f"{m['base_rate_test']*100:.0f}%")
        st.caption(f"Operating point: flag when risk ≥ {m['threshold']} (chosen for ~70% recall). "
                   f"Brier {m['brier']} — lower is better calibrated.")

        c1, c2 = st.columns(2)
        if "importance" in M:
            with c1:
                sect("What drives the prediction", "Feature importance.")
                st.plotly_chart(viz.model_importance_fig(M["importance"]), width="stretch", key="m_imp")
        if "calibration" in M:
            with c2:
                sect("Calibration", "Predicted risk vs actual at-risk rate.")
                st.plotly_chart(viz.model_calibration_fig(M["calibration"]), width="stretch", key="m_cal")

        if "fairness" in M:
            sect("Fairness check", "Flag rate and recall by group — watch for disparities.")
            st.dataframe(M["fairness"], width="stretch", hide_index=True)

        if "scores" in M:
            sect("Intervention what-if", "Choose how many learners to flag, and see the trade-off.")
            scores = M["scores"].sort_values("risk_score", ascending=False).reset_index(drop=True)
            pct = st.slider("Flag the top N% by risk", 5, 50, 20, step=5)
            n_flag = max(1, int(len(scores) * pct / 100))
            flagged = scores.head(n_flag)
            caught = int(flagged["at_risk"].sum())
            total_risk = int(scores["at_risk"].sum())
            cc = st.columns(3)
            cc[0].metric("Learners flagged", f"{n_flag:,}")
            cc[1].metric("At-risk caught", f"{caught:,} / {total_risk:,}",
                         f"{caught/total_risk*100:.0f}% recall")
            cc[2].metric("Precision of flag", f"{caught/n_flag*100:.0f}%")
            st.caption("A larger flag list catches more at-risk learners, but spends more outreach "
                       "on learners who would have passed anyway.")
            with st.expander("Highest-risk learners (test cohort)"):
                st.dataframe(flagged.head(50), width="stretch", hide_index=True)
