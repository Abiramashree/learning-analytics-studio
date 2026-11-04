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
# Semantic, consistent outcome colors (good -> bad)
OUTCOME_COLORS = {
    "Distinction": "#2a78d6",
    "Pass": "#1baf7a",
    "Fail": "#eb6834",
    "Withdrawn": "#e34948",
}
OUTCOME_ORDER = ["Distinction", "Pass", "Fail", "Withdrawn"]

_LAYOUT = dict(
    paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
    font=dict(color=INK, size=13),
    margin=dict(l=10, r=10, t=10, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
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
    fig.update_yaxes(showgrid=True, gridcolor="#ececec", ticksuffix="%")
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
    fig.update_yaxes(showgrid=True, gridcolor="#ececec")
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
    fig.update_yaxes(showgrid=True, gridcolor="#ececec")
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
    fig.update_xaxes(showgrid=True, gridcolor="#ececec")
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
    fig.update_yaxes(showgrid=True, gridcolor="#ececec", ticksuffix="%")
    fig.update_xaxes(showgrid=False, tickangle=-30)
    return fig
