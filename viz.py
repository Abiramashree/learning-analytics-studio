"""
viz.py
Plotly figures for the Learning Analytics Studio dashboard. Palette is the validated,
CVD-aware default; outcome colors are semantic and consistent across every chart.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

INK, MUTED, SURFACE = "#0b0b0b", "#52514e", "#fcfcfb"
BLUE = "#2a78d6"
# Sequential single-hue ramp for magnitude encodings (heatmaps): light -> dark blue.
BLUE_SCALE = [[0.0, "#eef4fb"], [0.35, "#9dc0ec"], [0.7, "#3f7fd1"], [1.0, "#17407d"]]
# Semantic, consistent outcome colors (good -> bad)
OUTCOME_COLORS = {
    "Distinction": "#2a78d6",
    "Pass": "#1baf7a",
    "Fail": "#eb6834",
    "Withdrawn": "#e34948",
}
OUTCOME_ORDER = ["Distinction", "Pass", "Fail", "Withdrawn"]

FONT = "-apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
GRID = "#eceef1"

_LAYOUT = dict(
    paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
    font=dict(family=FONT, color=INK, size=13),
    margin=dict(l=8, r=8, t=16, b=8),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0,
                font=dict(color=MUTED, size=12)),
    hoverlabel=dict(font=dict(family=FONT, size=12), bgcolor="#ffffff",
                    bordercolor=GRID),
)


def outcomes_by_course_fig(df: pd.DataFrame) -> go.Figure:
    """Pass vs withdrawal rate per course, sorted by withdrawal (anomaly-spotting)."""
    d = df.copy()
    d["course"] = d["code_module"] + " " + d["code_presentation"]
    d = d.sort_values("withdrawal_rate", ascending=False)
    fig = go.Figure()
    fig.add_bar(name="Pass", x=d["course"], y=(d["pass_rate"] * 100).round(1),
                marker_color=OUTCOME_COLORS["Pass"], marker_line=dict(color=SURFACE, width=2))
    fig.add_bar(name="Withdrawal", x=d["course"], y=(d["withdrawal_rate"] * 100).round(1),
                marker_color=OUTCOME_COLORS["Withdrawn"], marker_line=dict(color=SURFACE, width=2))
    fig.update_layout(barmode="group", yaxis_title="rate (%)", **_LAYOUT)
    fig.update_yaxes(showgrid=True, gridcolor=GRID, ticksuffix="%")
    fig.update_xaxes(showgrid=False, tickangle=-45)
    return fig


def engagement_by_outcome_fig(df: pd.DataFrame) -> go.Figure:
    """Avg first-4-week clicks by outcome (the early-warning signal)."""
    d = df.set_index("final_result").reindex(OUTCOME_ORDER).reset_index()
    fig = go.Figure(go.Bar(
        x=d["final_result"], y=d["avg_clicks_first_4w"],
        marker_color=[OUTCOME_COLORS[o] for o in d["final_result"]],
        marker_line=dict(color=SURFACE, width=2),
        text=d["avg_clicks_first_4w"].round(0).astype(int), textposition="outside",
        textfont=dict(color=MUTED, size=12),
    ))
    fig.update_layout(showlegend=False, yaxis_title="avg clicks, first 4 weeks", **_LAYOUT)
    fig.update_yaxes(showgrid=True, gridcolor=GRID)
    fig.update_xaxes(showgrid=False)
    return fig


def engagement_timeline_fig(df: pd.DataFrame) -> go.Figure:
    """Avg clicks per enrolled student per week, by outcome — divergence over time."""
    fig = go.Figure()
    for outcome in OUTCOME_ORDER:
        d = df[df["final_result"] == outcome]
        if not d.empty:
            fig.add_scatter(x=d["rel_week"], y=d["avg_clicks"], name=outcome, mode="lines",
                            line=dict(color=OUTCOME_COLORS[outcome], width=2))
    fig.update_layout(yaxis_title="avg clicks / student", xaxis_title="week from course start", **_LAYOUT)
    fig.update_yaxes(showgrid=True, gridcolor=GRID)
    fig.update_xaxes(showgrid=False)
    return fig


def content_fig(df: pd.DataFrame) -> go.Figure:
    """Share of engagement by content/activity type (horizontal bar, single hue)."""
    d = df.sort_values("pct_of_clicks").tail(10)
    fig = go.Figure(go.Bar(
        orientation="h", x=d["pct_of_clicks"], y=d["activity_type"],
        marker_color=BLUE, marker_line=dict(color=SURFACE, width=2),
        text=d["pct_of_clicks"].map(lambda v: f"{v}%"), textposition="outside",
        textfont=dict(color=MUTED, size=11),
    ))
    fig.update_layout(showlegend=False, xaxis_title="% of total clicks", **_LAYOUT)
    fig.update_xaxes(showgrid=True, gridcolor=GRID)
    fig.update_yaxes(showgrid=False)
    return fig


def model_importance_fig(df: pd.DataFrame) -> go.Figure:
    """Feature importances for the early-warning model (horizontal bar)."""
    d = df.sort_values("importance").tail(10)
    fig = go.Figure(go.Bar(
        orientation="h", x=d["importance"], y=d["feature"],
        marker_color=BLUE, marker_line=dict(color=SURFACE, width=2),
    ))
    fig.update_layout(showlegend=False, xaxis_title="importance", **_LAYOUT)
    fig.update_xaxes(showgrid=True, gridcolor=GRID)
    fig.update_yaxes(showgrid=False)
    return fig


def model_calibration_fig(df: pd.DataFrame) -> go.Figure:
    """Reliability curve: predicted probability vs actual at-risk rate, by decile."""
    fig = go.Figure()
    fig.add_scatter(x=[0, 1], y=[0, 1], mode="lines", name="perfect",
                    line=dict(color=MUTED, width=1, dash="dot"))
    fig.add_scatter(x=df["mean_pred"], y=df["actual_rate"], mode="lines+markers",
                    name="model", line=dict(color=BLUE, width=2), marker=dict(size=7))
    fig.update_layout(xaxis_title="predicted risk", yaxis_title="actual at-risk rate", **_LAYOUT)
    fig.update_xaxes(range=[0, 1], showgrid=True, gridcolor=GRID)
    fig.update_yaxes(range=[0, 1], showgrid=True, gridcolor=GRID)
    return fig


def outcome_mix_fig(overall_row) -> go.Figure:
    """Donut of the four mutually-exclusive outcomes (distinction/pass/fail/withdrawn)."""
    dist = float(overall_row["distinction_rate"])
    pass_only = float(overall_row["pass_rate"]) - dist          # pass_rate includes distinction
    fail = float(overall_row["fail_rate"])
    wd = float(overall_row["withdrawal_rate"])
    labels = ["Distinction", "Pass", "Fail", "Withdrawn"]
    vals = [dist, pass_only, fail, wd]
    fig = go.Figure(go.Pie(
        labels=labels, values=vals, hole=0.58, sort=False, direction="clockwise",
        marker=dict(colors=[OUTCOME_COLORS[o] for o in labels],
                    line=dict(color=SURFACE, width=2)),
        texttemplate="%{label}<br>%{percent}", textposition="outside",
        textfont=dict(color=INK, size=12),
    ))
    fig.update_layout(showlegend=False, **_LAYOUT)
    return fig


def funnel_fig(df: pd.DataFrame) -> go.Figure:
    """Learner progression funnel: registered -> started -> engaged -> assessed -> passed."""
    d = df.sort_values("ord")
    fig = go.Figure(go.Funnel(
        y=d["stage"], x=d["learners"],
        marker=dict(color=BLUE, line=dict(color=SURFACE, width=2)),
        textinfo="value+percent initial", textfont=dict(color=SURFACE, size=12),
        connector=dict(line=dict(color="#d7d7d7", width=1)),
    ))
    fig.update_layout(**{**_LAYOUT, "margin": dict(l=10, r=10, t=10, b=10)})
    return fig


def demographics_bar_fig(df: pd.DataFrame, dimension: str) -> go.Figure:
    """Cohort composition: enrolment counts by a demographic dimension."""
    d = df[df["dimension"] == dimension].copy().sort_values("enrolments", ascending=True)
    total = d["enrolments"].sum()
    fig = go.Figure(go.Bar(
        orientation="h", x=d["enrolments"], y=d["value"].astype(str),
        marker_color=BLUE, marker_line=dict(color=SURFACE, width=2),
        text=[f"{v:,} ({v/total*100:.0f}%)" for v in d["enrolments"]],
        textposition="outside", textfont=dict(color=MUTED, size=11),
    ))
    fig.update_layout(showlegend=False, xaxis_title="enrolments", **_LAYOUT)
    fig.update_xaxes(showgrid=True, gridcolor=GRID)
    fig.update_yaxes(showgrid=False)
    return fig


def registration_timing_fig(df: pd.DataFrame) -> go.Figure:
    """How early learners register (bars) with pass rate annotated on each bucket."""
    d = df[df["bucket"] != "Unknown"].sort_values("ord")
    fig = go.Figure(go.Bar(
        x=d["bucket"], y=d["enrolments"],
        marker_color=BLUE, marker_line=dict(color=SURFACE, width=2),
        text=[f"{p*100:.0f}% pass" for p in d["pass_rate"]],
        textposition="outside", textfont=dict(color=MUTED, size=11),
    ))
    fig.update_layout(showlegend=False, yaxis_title="enrolments", **_LAYOUT)
    fig.update_yaxes(showgrid=True, gridcolor=GRID)
    fig.update_xaxes(showgrid=False)
    return fig


def engagement_dose_fig(df: pd.DataFrame) -> go.Figure:
    """Dose-response: pass vs withdrawal rate across first-4-week engagement deciles."""
    d = df.sort_values("decile")
    fig = go.Figure()
    fig.add_scatter(x=d["decile"], y=(d["pass_rate"] * 100).round(1), name="Pass rate",
                    mode="lines+markers", line=dict(color=OUTCOME_COLORS["Pass"], width=2),
                    marker=dict(size=7))
    fig.add_scatter(x=d["decile"], y=(d["withdrawal_rate"] * 100).round(1), name="Withdrawal rate",
                    mode="lines+markers", line=dict(color=OUTCOME_COLORS["Withdrawn"], width=2),
                    marker=dict(size=7))
    fig.update_layout(yaxis_title="rate (%)",
                      xaxis_title="first-4-week engagement decile (1 = least active)", **_LAYOUT)
    fig.update_yaxes(showgrid=True, gridcolor=GRID, ticksuffix="%")
    fig.update_xaxes(showgrid=False, dtick=1)
    return fig


def engagement_score_dose_fig(df: pd.DataFrame) -> go.Figure:
    """Avg assessment score across first-4-week engagement deciles (effectiveness)."""
    d = df.sort_values("decile")
    fig = go.Figure(go.Scatter(
        x=d["decile"], y=d["avg_score"], mode="lines+markers",
        line=dict(color=BLUE, width=2), marker=dict(size=7),
        fill="tozeroy", fillcolor="rgba(42,120,214,0.08)",
    ))
    fig.update_layout(showlegend=False, yaxis_title="avg assessment score",
                      xaxis_title="first-4-week engagement decile (1 = least active)", **_LAYOUT)
    fig.update_yaxes(showgrid=True, gridcolor=GRID, range=[60, 85])
    fig.update_xaxes(showgrid=False, dtick=1)
    return fig


def assessment_box_fig(df: pd.DataFrame) -> go.Figure:
    """Score distribution by assessment type, from precomputed quantiles (box plot)."""
    fig = go.Figure()
    for _, r in df.iterrows():
        fig.add_box(
            name=r["assessment_type"], x=[r["assessment_type"]],
            lowerfence=[r["p05"]], q1=[r["p25"]], median=[r["p50"]],
            q3=[r["p75"]], upperfence=[r["p95"]], mean=[r["mean_score"]],
            marker_color=BLUE, line=dict(color=BLUE), fillcolor="#dfeafb",
        )
    fig.update_layout(showlegend=False, yaxis_title="score", **_LAYOUT)
    fig.update_yaxes(showgrid=True, gridcolor=GRID, range=[0, 100])
    fig.update_xaxes(showgrid=False)
    return fig


def assessment_by_course_fig(df: pd.DataFrame) -> go.Figure:
    """Average assessment score per course (horizontal, sorted)."""
    d = df.copy()
    d["course"] = d["code_module"] + " " + d["code_presentation"]
    d = d.sort_values("avg_score", ascending=True)
    fig = go.Figure(go.Bar(
        orientation="h", x=d["avg_score"], y=d["course"],
        marker_color=BLUE, marker_line=dict(color=SURFACE, width=2),
        text=d["avg_score"].round(0).astype(int), textposition="outside",
        textfont=dict(color=MUTED, size=10),
    ))
    fig.update_layout(showlegend=False, xaxis_title="avg assessment score", **_LAYOUT)
    fig.update_xaxes(showgrid=True, gridcolor=GRID, range=[0, 100])
    fig.update_yaxes(showgrid=False)
    return fig


def submission_timing_fig(df: pd.DataFrame) -> go.Figure:
    """Submission timing vs the due date (bars), with average score annotated."""
    d = df.sort_values("ord")
    fig = go.Figure(go.Bar(
        x=d["timing"], y=d["n_submissions"],
        marker_color=BLUE, marker_line=dict(color=SURFACE, width=2),
        text=[f"avg {s:.0f}" for s in d["avg_score"]],
        textposition="outside", textfont=dict(color=MUTED, size=11),
    ))
    fig.update_layout(showlegend=False, yaxis_title="submissions", **_LAYOUT)
    fig.update_yaxes(showgrid=True, gridcolor=GRID)
    fig.update_xaxes(showgrid=False)
    return fig


def pass_rate_heatmap_fig(df: pd.DataFrame) -> go.Figure:
    """Pass rate across module (rows) x presentation (cols) — sequential blue heatmap."""
    d = df.copy()
    d["pass_pct"] = (d["pass_rate"] * 100).round(0)
    pivot = d.pivot(index="code_module", columns="code_presentation", values="pass_pct")
    pivot = pivot.sort_index(ascending=False)
    fig = go.Figure(go.Heatmap(
        z=pivot.values, x=list(pivot.columns), y=list(pivot.index),
        colorscale=BLUE_SCALE, zmin=0, zmax=100,
        xgap=2, ygap=2, colorbar=dict(title="pass %", ticksuffix="%"),
        text=pivot.values, texttemplate="%{text:.0f}", textfont=dict(size=11),
        hovertemplate="module %{y}, %{x}: %{z:.0f}% pass<extra></extra>",
    ))
    fig.update_layout(xaxis_title="presentation", yaxis_title="module", **_LAYOUT)
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=False)
    return fig


def segment_fig(df: pd.DataFrame, dimension: str) -> go.Figure:
    """Pass vs withdrawal rate by a chosen demographic dimension."""
    d = df[df["dimension"] == dimension].copy().sort_values("pass_rate", ascending=False)
    fig = go.Figure()
    fig.add_bar(name="Pass", x=d["value"].astype(str), y=(d["pass_rate"] * 100).round(1),
                marker_color=OUTCOME_COLORS["Pass"], marker_line=dict(color=SURFACE, width=2))
    fig.add_bar(name="Withdrawal", x=d["value"].astype(str), y=(d["withdrawal_rate"] * 100).round(1),
                marker_color=OUTCOME_COLORS["Withdrawn"], marker_line=dict(color=SURFACE, width=2))
    fig.update_layout(barmode="group", yaxis_title="rate (%)", **_LAYOUT)
    fig.update_yaxes(showgrid=True, gridcolor=GRID, ticksuffix="%")
    fig.update_xaxes(showgrid=False, tickangle=-30)
    return fig
