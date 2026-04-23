from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timezone

# ─── Report Feedback Respondents ──────────────────────────────────────────────

CSAT_RESPONDENTS = []

# ─── Report Analytics (all reports) ───────────────────────────────────────────

CAMPAIGN_ANALYTICS = {
    "label":   "All Reports",
    "updated": "—",
    "metrics": [
        {"label": "Total Sent",       "value": "0",     "sub": None, "change": None, "up_good": True},
        {"label": "Open Rate",        "value": "0.0%",  "sub": None, "change": None, "up_good": True},
        {"label": "Click to Open",    "value": "0.0%",  "sub": None, "change": None, "up_good": True},
        {"label": "Delivered Rate",   "value": "0.0%",  "sub": None, "change": None, "up_good": True},
        {"label": "Bounce Rate",      "value": "0.0%",  "sub": None, "change": None, "up_good": False},
        {"label": "Unsubscribe Rate", "value": "0.0%",  "sub": None, "change": None, "up_good": False},
        {"label": "Blocked Rate",     "value": "0.0%",  "sub": None, "change": None, "up_good": False},
    ],
    "csat": {
        "score":     0.0,
        "responses": 0,
        "dist": [
            {"star": 5, "pct": 0, "count": 0},
            {"star": 4, "pct": 0, "count": 0},
            {"star": 3, "pct": 0, "count": 0},
            {"star": 2, "pct": 0, "count": 0},
            {"star": 1, "pct": 0, "count": 0},
        ],
    },
}

# ─── KPI Data ─────────────────────────────────────────────────────────────────

@dataclass
class KPIMetric:
    label: str
    value: float
    previous: float
    unit: str            # "percent" | "score" | "nps" | "count"
    higher_is_better: bool
    description: str

def format_kpi(m: KPIMetric) -> str:
    if m.unit == "percent":
        return f"{m.value}%"
    if m.unit == "score":
        return f"{m.value:.1f}"
    if m.unit == "nps":
        return f"+{int(m.value)}" if m.value > 0 else str(int(m.value))
    return str(int(m.value))

def format_delta(m: KPIMetric) -> str:
    delta = m.value - m.previous
    sign = "+" if delta > 0 else ""
    if m.unit == "percent":
        return f"{sign}{delta:.1f}%"
    if m.unit == "score":
        return f"{sign}{delta:.1f}"
    if m.unit == "nps":
        return f"{sign}{int(delta)}"
    return f"{sign}{int(delta)}"

def delta_is_positive(m: KPIMetric) -> bool:
    """True when the change is a *good* thing."""
    delta = m.value - m.previous
    return (delta > 0 and m.higher_is_better) or (delta < 0 and not m.higher_is_better)

HEALTH_KPIS: list[KPIMetric] = [
    KPIMetric("Response Rate",      0.0, 0.0, "percent", True,  "% of report recipients who submitted feedback"),
    KPIMetric("Avg Report Score",   0.0, 0.0, "score",   True,  "Mean report quality score (1–5)"),
    KPIMetric("NPS Score",          0,   0,   "nps",     True,  "Net Promoter Score for insights delivery"),
    KPIMetric("Negative Feedback",  0.0, 0.0, "percent", False, "% of responses flagging data quality issues"),
    KPIMetric("Unresolved Issues",  0,   0,   "count",   False, "Open report issues needing follow-up"),
]

# ─── DL Reports ───────────────────────────────────────────────────────────────

CAMPAIGNS = []

# ─── Action Queue ─────────────────────────────────────────────────────────────

ACTION_QUEUE = []

# ─── Analytics by Period ──────────────────────────────────────────────────────

ANALYTICS_BY_PERIOD = {
    "Daily": {
        "label":   "Today",
        "updated": "—",
        "metrics": [
            {"label": "Total Sent",       "value": "0",    "sub": None, "change": None, "up_good": True},
            {"label": "Open Rate",        "value": "0.0%", "sub": None, "change": None, "up_good": True},
            {"label": "Click to Open",    "value": "0.0%", "sub": None, "change": None, "up_good": True},
            {"label": "Delivered Rate",   "value": "0.0%", "sub": None, "change": None, "up_good": True},
            {"label": "Bounce Rate",      "value": "0.0%", "sub": None, "change": None, "up_good": False},
            {"label": "Unsubscribe Rate", "value": "0.0%", "sub": None, "change": None, "up_good": False},
            {"label": "Blocked Rate",     "value": "0.0%", "sub": None, "change": None, "up_good": False},
        ],
        "csat": {
            "score":     0.0,
            "responses": 0,
            "dist": [
                {"star": 5, "pct": 0, "count": 0},
                {"star": 4, "pct": 0, "count": 0},
                {"star": 3, "pct": 0, "count": 0},
                {"star": 2, "pct": 0, "count": 0},
                {"star": 1, "pct": 0, "count": 0},
            ],
        },
    },
    "Weekly": {
        "label":   "This Week",
        "updated": "—",
        "metrics": [
            {"label": "Total Sent",       "value": "0",    "sub": None, "change": None, "up_good": True},
            {"label": "Open Rate",        "value": "0.0%", "sub": None, "change": None, "up_good": True},
            {"label": "Click to Open",    "value": "0.0%", "sub": None, "change": None, "up_good": True},
            {"label": "Delivered Rate",   "value": "0.0%", "sub": None, "change": None, "up_good": True},
            {"label": "Bounce Rate",      "value": "0.0%", "sub": None, "change": None, "up_good": False},
            {"label": "Unsubscribe Rate", "value": "0.0%", "sub": None, "change": None, "up_good": False},
            {"label": "Blocked Rate",     "value": "0.0%", "sub": None, "change": None, "up_good": False},
        ],
        "csat": {
            "score":     0.0,
            "responses": 0,
            "dist": [
                {"star": 5, "pct": 0, "count": 0},
                {"star": 4, "pct": 0, "count": 0},
                {"star": 3, "pct": 0, "count": 0},
                {"star": 2, "pct": 0, "count": 0},
                {"star": 1, "pct": 0, "count": 0},
            ],
        },
    },
    "Monthly": {
        "label":   "All Reports",
        "updated": "—",
        "metrics": [
            {"label": "Total Sent",       "value": "0",    "sub": None, "change": None, "up_good": True},
            {"label": "Open Rate",        "value": "0.0%", "sub": None, "change": None, "up_good": True},
            {"label": "Click to Open",    "value": "0.0%", "sub": None, "change": None, "up_good": True},
            {"label": "Delivered Rate",   "value": "0.0%", "sub": None, "change": None, "up_good": True},
            {"label": "Bounce Rate",      "value": "0.0%", "sub": None, "change": None, "up_good": False},
            {"label": "Unsubscribe Rate", "value": "0.0%", "sub": None, "change": None, "up_good": False},
            {"label": "Blocked Rate",     "value": "0.0%", "sub": None, "change": None, "up_good": False},
        ],
        "csat": {
            "score":     0.0,
            "responses": 0,
            "dist": [
                {"star": 5, "pct": 0, "count": 0},
                {"star": 4, "pct": 0, "count": 0},
                {"star": 3, "pct": 0, "count": 0},
                {"star": 2, "pct": 0, "count": 0},
                {"star": 1, "pct": 0, "count": 0},
            ],
        },
    },
}

# ─── Email-wise Analytics ─────────────────────────────────────────────────────

DAILY_DATES  = set()
WEEKLY_DATES = set()

EMAIL_ANALYTICS = []
