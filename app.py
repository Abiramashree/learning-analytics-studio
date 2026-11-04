"""
app.py
Learning Analytics Studio — dashboard over OULAD.

Reads small aggregates (from the DuckDB warehouse locally, or committed serving parquet
when deployed) and renders outcomes, engagement, content performance, cohort drilldowns,
and deterministic anomaly flags. Run: streamlit run app.py
"""
import streamlit as st

import viz
from analytics.data_access import get_frames

st.set_page_config(page_title="Learning Analytics Studio", page_icon="🎓", layout="wide")

st.title("🎓 Learning Analytics Studio")
st.caption("Learner engagement & outcomes on the Open University Learning Analytics Dataset (OULAD) — a reproducible, SQL-backed analytics pipeline.")


@st.cache_data(show_spinner="Loading analytics…")
def load():
    return get_frames()


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

tab_o, tab_e, tab_c, tab_s = st.tabs(
    ["🎯 Outcomes", "📈 Engagement", "📚 Content", "👥 Cohorts"]
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
