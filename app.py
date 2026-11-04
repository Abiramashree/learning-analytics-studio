"""
app.py
Learning Analytics Studio — dashboard over OULAD.

Reads small aggregates (from the DuckDB warehouse locally, or committed serving parquet
when deployed) and renders a narrative overview, learner demographics, outcomes, engagement
behaviour, a content/assessment effectiveness deep-dive, and a leakage-free early-warning
model. Everything is deterministic SQL + fixed transforms. Run: streamlit run app.py
"""
import streamlit as st

import viz
from analytics.data_access import get_frames, load_model_artifacts

st.set_page_config(page_title="Learning Analytics Studio", page_icon="🎓", layout="wide")

st.title("🎓 Learning Analytics Studio")
st.caption("Learner engagement & outcomes on the Open University Learning Analytics Dataset (OULAD) — a reproducible, SQL-backed analytics pipeline.")


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
    st.header("About")
    st.markdown(
        "Built on **OULAD** (32,593 enrolments, 10.6M engagement events). Metrics are "
        "defined once in SQL (`sql/*.sql`) and documented in the metric glossary — a "
        "governed source of truth. Every figure is deterministic and reproducible."
    )
    st.markdown("**Rigor:** data-quality gate on each build · temporal (leakage-free) model "
                "validation · fairness audited · governed KPIs.")
    st.caption("Data: © Open University, OULAD (open dataset). Portfolio project.")

tab_ov, tab_stu, tab_out, tab_eng, tab_con, tab_m = st.tabs(
    ["📊 Overview", "👥 Students", "🎯 Outcomes", "📈 Engagement",
     "📚 Content & Effectiveness", "🚨 Early-warning"]
)

# ------------------------------------------------------------------- Overview
with tab_ov:
    o = F["overall"].iloc[0]
    st.markdown(
        "**The question:** *who completes an online course, who disengages — and how early "
        "can we tell?* This studio answers it end-to-end on OULAD, used as a proxy for "
        "training-program analytics."
    )
    k = st.columns(4)
    k[0].metric("Enrolments", f"{int(o['enrolments']):,}")
    k[1].metric("Pass rate", f"{o['pass_rate']*100:.1f}%")
    k[2].metric("Withdrawal rate", f"{o['withdrawal_rate']*100:.1f}%")
    k[3].metric("Distinction rate", f"{o['distinction_rate']*100:.1f}%")

    c1, c2 = st.columns(2)
    c1.markdown("**Outcome mix**")
    c1.plotly_chart(viz.outcome_mix_fig(o), use_container_width=True)
    c2.markdown("**Learner progression funnel** — where the cohort falls away")
    c2.plotly_chart(viz.funnel_fig(F["funnel"]), use_container_width=True)

    c3, c4 = st.columns(2)
    c3.markdown("**Early engagement by outcome** — avg clicks, first 4 weeks")
    c3.plotly_chart(viz.engagement_by_outcome_fig(F["engagement_by_outcome"]), use_container_width=True)
    c4.markdown("**Where attention goes** — share of engagement by content type")
    c4.plotly_chart(viz.content_fig(F["content"]), use_container_width=True)

    st.success(
        "**Headline:** engagement in the **first 4 weeks** cleanly separates who passes from "
        "who withdraws — pass rate climbs from **7% to 75%** across engagement deciles. That "
        "makes early disengagement a reliable, *actionable* signal.\n\n"
        "**Recommended action:** flag the least-engaged learners by week 4 for outreach "
        "(the Early-warning tab hits ~70% recall at ~75% precision), and invest support where "
        "the Outcomes heatmap and cohort gaps show it concentrates."
    )

# ------------------------------------------------------------------- Students
with tab_stu:
    o = F["overall"].iloc[0]
    courses = F["outcomes_by_course"]
    n_modules = courses["code_module"].nunique()
    n_presentations = courses[["code_module", "code_presentation"]].drop_duplicates().shape[0]
    k = st.columns(3)
    k[0].metric("Enrolments (registrations)", f"{int(o['enrolments']):,}")
    k[1].metric("Modules", f"{n_modules}")
    k[2].metric("Course presentations", f"{n_presentations}")
    st.caption("An *enrolment* is one learner in one module-presentation; a learner may enrol more than once.")

    st.markdown("**Enrolments by course** (module × presentation)")
    bycourse = courses.assign(course=courses["code_module"] + " " + courses["code_presentation"])
    bycourse = bycourse.sort_values("enrolments", ascending=False)[["course", "enrolments"]]
    st.bar_chart(bycourse.set_index("course"), color=viz.BLUE, height=300)

    st.markdown("**Cohort composition** — how enrolments split across a demographic")
    seg = F["segment"]
    dims = list(seg["dimension"].unique())
    dim = st.selectbox("Break down by", dims, index=dims.index("age_band") if "age_band" in dims else 0,
                       key="stu_dim")
    st.plotly_chart(viz.demographics_bar_fig(seg, dim), use_container_width=True)
    st.caption("Counts shown as-is (some bands carry nulls); used to understand who the learners are.")

    st.markdown("**Registration lead time** — how early learners enrol, and the pass rate of each group")
    st.plotly_chart(viz.registration_timing_fig(F["registration_timing"]), use_container_width=True)
    st.info("Learners who register late (or with no recorded date) withdraw far more — a cheap, "
            "pre-course risk signal available before a single click.")

# ------------------------------------------------------------------- Outcomes
with tab_out:
    st.markdown("**Pass vs withdrawal by course** (sorted by withdrawal)")
    st.plotly_chart(viz.outcomes_by_course_fig(F["outcomes_by_course"]), use_container_width=True)

    st.markdown("**Pass-rate heatmap** — module × presentation (spot weak course runs at a glance)")
    st.plotly_chart(viz.pass_rate_heatmap_fig(F["outcomes_by_course"]), use_container_width=True)

    st.markdown("**Outcome gaps by cohort** — pass vs withdrawal rate by segment")
    seg = F["segment"]
    dims = list(seg["dimension"].unique())
    dim = st.selectbox("Segment by", dims, index=0, key="out_dim")
    st.plotly_chart(viz.segment_fig(seg, dim), use_container_width=True)
    st.caption("Segment gaps flag where to target support (shown, not imputed; some bands have nulls).")

    st.markdown("**Anomaly flags — courses with outlier withdrawal** (|z| ≥ 1.5)")
    an = F["anomalies"]
    flagged = an[an["flag"]]
    if flagged.empty:
        st.success("No courses flagged as withdrawal outliers.")
    else:
        show = flagged.assign(course=flagged["code_module"] + " " + flagged["code_presentation"])
        show = show[["course", "enrolments", "withdrawal_rate", "z", "direction"]]
        show["withdrawal_rate"] = (show["withdrawal_rate"] * 100).round(1)
        st.dataframe(show.rename(columns={"withdrawal_rate": "withdrawal_%"}),
                     use_container_width=True, hide_index=True)

# ----------------------------------------------------------------- Engagement
with tab_eng:
    st.markdown("**Early engagement by outcome** — avg clicks in the first 4 weeks")
    st.plotly_chart(viz.engagement_by_outcome_fig(F["engagement_by_outcome"]), use_container_width=True)
    st.markdown("**Engagement over the course** — avg clicks/student per week, by outcome")
    st.plotly_chart(viz.engagement_timeline_fig(F["timeline"]), use_container_width=True)

    st.markdown("**Dose-response** — outcomes across first-4-week engagement deciles")
    st.plotly_chart(viz.engagement_dose_fig(F["engagement_dose"]), use_container_width=True)
    st.info("A monotonic relationship: each step up in early engagement raises pass rate and "
            "lowers withdrawal — pass rate runs from ~7% (least active decile) to ~75% (most active). "
            "This is the empirical basis for the early-warning model.")

# -------------------------------------------------- Content & Effectiveness
with tab_con:
    st.markdown("**Where learners spend attention** — share of engagement by content type")
    st.plotly_chart(viz.content_fig(F["content"]), use_container_width=True)
    st.caption("Useful for prioritising content investment — most attention is a handful of activity types.")

    c1, c2 = st.columns(2)
    c1.markdown("**Score distribution by assessment type**")
    c1.plotly_chart(viz.assessment_box_fig(F["assessment_by_type"]), use_container_width=True)
    c1.caption("Box = p25–p75, whiskers p05–p95. CMAs score highest; exams are hardest.")
    c2.markdown("**Submission timing vs the due date**")
    c2.plotly_chart(viz.submission_timing_fig(F["submission_timing"]), use_container_width=True)
    c2.caption("Early submitters score higher on average — a behavioural marker of effectiveness.")

    st.markdown("**Training effectiveness — avg assessment score per course**")
    st.plotly_chart(viz.assessment_by_course_fig(F["assessment_by_course"]), use_container_width=True)

    st.markdown("**Engagement → learning** — avg assessment score across engagement deciles")
    st.plotly_chart(viz.engagement_score_dose_fig(F["engagement_dose"]), use_container_width=True)
    st.info("More early engagement doesn't just lift completion — it lifts measured learning: "
            "average score rises from ~69 to ~80 from the least- to most-engaged decile.")

# -------------------------------------------------------------- Early-warning
with tab_m:
    M = load_model()
    if not M:
        st.warning("Model not trained yet. Run `python scripts/train_model.py` to generate it.")
    else:
        m = M["metrics"]
        st.subheader("Early-warning model — flag at-risk learners from the first 4 weeks")
        st.caption(
            f"Target = Withdrawal or Fail. Trained on {m['train_years']} "
            f"({m['n_train']:,}), tested on {m['test_years']} ({m['n_test']:,}) — a temporal "
            "split so the model is judged on future cohorts, not shuffled rows."
        )
        st.markdown("`no leakage` · `temporal split` · `fairness audited` · `calibrated` · `governed features`")
        k = st.columns(5)
        k[0].metric("ROC-AUC", m["roc_auc"])
        k[1].metric("PR-AUC", m["pr_auc"])
        k[2].metric("Recall", f"{m['recall']*100:.0f}%")
        k[3].metric("Precision", f"{m['precision']*100:.0f}%")
        k[4].metric("Test base rate", f"{m['base_rate_test']*100:.0f}%")
        st.caption(f"Operating point: flag when risk ≥ {m['threshold']} (chosen for ~70% recall). "
                   f"Brier {m['brier']} (lower = better calibrated).")

        c1, c2 = st.columns(2)
        if "importance" in M:
            c1.markdown("**What drives the prediction**")
            c1.plotly_chart(viz.model_importance_fig(M["importance"]), use_container_width=True)
        if "calibration" in M:
            c2.markdown("**Calibration** (predicted vs actual risk)")
            c2.plotly_chart(viz.model_calibration_fig(M["calibration"]), use_container_width=True)

        if "fairness" in M:
            st.markdown("**Fairness check** — flag rate & recall by group (watch for disparities)")
            st.dataframe(M["fairness"], use_container_width=True, hide_index=True)

        if "scores" in M:
            st.markdown("**Intervention what-if** — flag the highest-risk learners")
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
            st.caption("Trade-off: a bigger flag list catches more at-risk learners but wastes more "
                       "outreach on learners who would have passed anyway.")
            with st.expander("Highest-risk learners (test cohort)"):
                st.dataframe(flagged.head(50), use_container_width=True, hide_index=True)
