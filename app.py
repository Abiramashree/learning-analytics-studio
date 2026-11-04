"""
app.py
Learning Analytics Studio — dashboard over OULAD.

Reads small aggregates (from the DuckDB warehouse locally, or committed serving parquet
when deployed) and renders outcomes, engagement, content performance, cohort drilldowns,
and deterministic anomaly flags. Run: streamlit run app.py
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
        "Built on OULAD (32,593 enrolments, 10.6M engagement events). Metrics are defined "
        "in SQL (`sql/metrics.sql`) and documented in the metric glossary — a governed "
        "source of truth. All figures are deterministic."
    )
    st.caption("Data: © Open University, OULAD (open dataset). Portfolio project.")

tab_o, tab_e, tab_c, tab_s, tab_m = st.tabs(
    ["🎯 Outcomes", "📈 Engagement", "📚 Content", "👥 Cohorts", "🚨 Early-warning"]
)

# ------------------------------------------------------------------- Outcomes
with tab_o:
    o = F["overall"].iloc[0]
    k = st.columns(4)
    k[0].metric("Enrolments", f"{int(o['enrolments']):,}")
    k[1].metric("Pass rate", f"{o['pass_rate']*100:.1f}%")
    k[2].metric("Withdrawal rate", f"{o['withdrawal_rate']*100:.1f}%")
    k[3].metric("Distinction rate", f"{o['distinction_rate']*100:.1f}%")
    st.markdown("**Pass vs withdrawal by course** (sorted by withdrawal)")
    st.plotly_chart(viz.outcomes_by_course_fig(F["outcomes_by_course"]), use_container_width=True)

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
with tab_e:
    st.markdown("**Early engagement by outcome** — avg clicks in the first 4 weeks")
    st.plotly_chart(viz.engagement_by_outcome_fig(F["engagement_by_outcome"]), use_container_width=True)
    st.info(
        "Early engagement separates outcomes cleanly — the basis for an early-warning model: "
        "learners who disengage in the first weeks are far likelier to withdraw or fail."
    )
    st.markdown("**Engagement over the course** — avg clicks/student per week, by outcome")
    st.plotly_chart(viz.engagement_timeline_fig(F["timeline"]), use_container_width=True)

# -------------------------------------------------------------------- Content
with tab_c:
    st.markdown("**Content performance** — share of engagement by activity type")
    st.plotly_chart(viz.content_fig(F["content"]), use_container_width=True)
    st.caption("Where learners actually spend attention — useful for prioritising content investment.")

# -------------------------------------------------------------------- Cohorts
with tab_s:
    dims = list(F["segment"]["dimension"].unique())
    dim = st.selectbox("Segment by", dims, index=0)
    st.markdown(f"**Pass vs withdrawal by {dim.replace('_', ' ')}**")
    st.plotly_chart(viz.segment_fig(F["segment"], dim), use_container_width=True)
    st.caption("Segment gaps flag where to target support (shown, not imputed; some bands have nulls).")

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
