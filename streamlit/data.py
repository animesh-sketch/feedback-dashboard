from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timezone

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
    KPIMetric("Response Rate",      34.8, 29.1, "percent", True,  "% of recipients who completed the survey"),
    KPIMetric("Avg CSAT",           3.9,  4.2,  "score",   True,  "Mean satisfaction score (1–5)"),
    KPIMetric("NPS Score",          42,   51,   "nps",     True,  "Net Promoter Score (-100 to 100)"),
    KPIMetric("Negative Feedback",  18.3, 12.7, "percent", False, "% of responses scored as negative"),
    KPIMetric("Unresolved Issues",  47,   31,   "count",   False, "Open items needing follow-up"),
]

# ─── Campaigns ────────────────────────────────────────────────────────────────

CAMPAIGNS = [
    {
        "name":      "Post-Purchase CSAT — Feb 2026",
        "type":      "CSAT",
        "responses": 1247,
        "sent":      3580,
        "score":     3.9,
        "status":    "⚠️ Needs Action",
        "audience":  "New Purchasers",
        "sent_at":   "2026-02-18",
    },
    {
        "name":      "Q1 NPS Pulse — Enterprise",
        "type":      "NPS",
        "responses": 312,
        "sent":      490,
        "score":     42,
        "status":    "✅ Healthy",
        "audience":  "Enterprise Tier",
        "sent_at":   "2026-02-15",
    },
    {
        "name":      "Support Resolution Check",
        "type":      "Yes-No",
        "responses": 891,
        "sent":      1100,
        "score":     67,          # % Yes
        "status":    "⚠️ Needs Action",
        "audience":  "Closed Tickets",
        "sent_at":   "2026-02-20",
    },
    {
        "name":      "Onboarding Feedback — Cohort 14",
        "type":      "CSAT",
        "responses": 204,
        "sent":      250,
        "score":     4.6,
        "status":    "✅ Healthy",
        "audience":  "Cohort 14 Sign-ups",
        "sent_at":   "2026-02-22",
    },
    {
        "name":      "Churn-Risk Satisfaction Survey",
        "type":      "NPS",
        "responses": 88,
        "sent":      143,
        "score":     -12,
        "status":    "🔴 Critical",
        "audience":  "Churn Risk Segment",
        "sent_at":   "2026-02-24",
    },
]

# ─── Action Queue ─────────────────────────────────────────────────────────────

ACTION_QUEUE = [
    {
        "priority":    "🔴 Critical",
        "name":        "Marcus Webb",
        "email":       "m.webb@techcorp.io",
        "score":       2,
        "type":        "CSAT",
        "campaign":    "Post-Purchase CSAT — Feb 2026",
        "tags":        ["delay", "agent behavior"],
        "comment":     "Package arrived 6 days late and the support agent was dismissive when I reached out.",
        "hours_open":  116,
        "sla_hours":   72,
        "sla_breached": True,
    },
    {
        "priority":    "🔴 Critical",
        "name":        "Priya Sharma",
        "email":       "priya.s@finflow.com",
        "score":       1,
        "type":        "CSAT",
        "campaign":    "Post-Purchase CSAT — Feb 2026",
        "tags":        ["billing issue", "refund"],
        "comment":     "Was charged twice and still haven't received my refund after 10 days.",
        "hours_open":  96,
        "sla_hours":   72,
        "sla_breached": True,
    },
    {
        "priority":    "🟠 High",
        "name":        "Jordan Ellis",
        "email":       "j.ellis@buildhq.co",
        "score":       3,
        "type":        "NPS",
        "campaign":    "Q1 NPS Pulse — Enterprise",
        "tags":        ["pricing", "feature request"],
        "comment":     "Pricing jumped 40% without notice. Missing integrations our team relies on.",
        "hours_open":  65,
        "sla_hours":   96,
        "sla_breached": False,
    },
    {
        "priority":    "🟠 High",
        "name":        "Sofia Reyes",
        "email":       "sofia@novahq.io",
        "score":       2,
        "type":        "CSAT",
        "campaign":    "Support Resolution Check",
        "tags":        ["response time", "communication"],
        "comment":     "Waited 3 days for a reply. Ticket marked resolved without fixing the problem.",
        "hours_open":  52,
        "sla_hours":   96,
        "sla_breached": False,
    },
    {
        "priority":    "🟠 High",
        "name":        "Daniel Park",
        "email":       "d.park@cloudbyte.dev",
        "score":       1,
        "type":        "NPS",
        "campaign":    "Churn-Risk Satisfaction Survey",
        "tags":        ["onboarding", "feature request"],
        "comment":     "Onboarding was confusing and key features from the sales demo aren't available.",
        "hours_open":  34,
        "sla_hours":   96,
        "sla_breached": False,
    },
    {
        "priority":    "🟡 Medium",
        "name":        "Amira Hassan",
        "email":       "amira.h@medlink.org",
        "score":       3,
        "type":        "CSAT",
        "campaign":    "Post-Purchase CSAT — Feb 2026",
        "tags":        ["product quality"],
        "comment":     "Quality was below what was shown in product photos.",
        "hours_open":  43,
        "sla_hours":   96,
        "sla_breached": False,
    },
]
