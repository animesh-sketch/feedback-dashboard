from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timezone

# ─── Report Feedback Respondents ──────────────────────────────────────────────

CSAT_RESPONDENTS = [
    # 5-star (11)
    {"name": "Animesh test",   "email": "animesh@convin.ai",      "rating": 5, "date": "Apr 22"},
    {"name": "Aiden Clarke",   "email": "a.clarke@techwave.io",   "rating": 5, "date": "Feb 24"},
    {"name": "Maya Patel",     "email": "maya.p@growthhub.com",   "rating": 5, "date": "Feb 23"},
    {"name": "Lucas Bennett",  "email": "l.bennett@scalex.co",    "rating": 5, "date": "Feb 23"},
    {"name": "Zara Ali",       "email": "zara.ali@dataflow.org",  "rating": 5, "date": "Feb 22"},
    {"name": "Ethan Moore",    "email": "e.moore@cloudnine.dev",  "rating": 5, "date": "Feb 22"},
    {"name": "Isabelle Roy",   "email": "i.roy@brightmind.co",    "rating": 5, "date": "Feb 21"},
    {"name": "Noah Fischer",   "email": "n.fischer@synapse.io",   "rating": 5, "date": "Feb 21"},
    {"name": "Sophia Nguyen",  "email": "sophia.n@launchpad.com", "rating": 5, "date": "Feb 20"},
    {"name": "Owen Kim",       "email": "o.kim@neostack.dev",     "rating": 5, "date": "Feb 20"},
    {"name": "Layla Hassan",   "email": "l.hassan@finsight.io",   "rating": 5, "date": "Feb 19"},
    {"name": "James Wu",       "email": "j.wu@orbitmedia.co",     "rating": 5, "date": "Feb 19"},
    # 4-star (8)
    {"name": "Chloe Martin",   "email": "c.martin@clearpath.com", "rating": 4, "date": "Feb 24"},
    {"name": "Ryan Torres",    "email": "r.torres@peakdata.io",   "rating": 4, "date": "Feb 23"},
    {"name": "Mia Johnson",    "email": "mia.j@springboard.co",   "rating": 4, "date": "Feb 22"},
    {"name": "Liam Scott",     "email": "liam.s@gridworks.dev",   "rating": 4, "date": "Feb 21"},
    {"name": "Ava Chen",       "email": "ava.chen@skybridge.io",  "rating": 4, "date": "Feb 21"},
    {"name": "Mason Brown",    "email": "m.brown@logicbase.com",  "rating": 4, "date": "Feb 20"},
    {"name": "Emma Davis",     "email": "e.davis@zenflow.co",     "rating": 4, "date": "Feb 19"},
    {"name": "Oliver Taylor",  "email": "o.taylor@nexuspoint.io", "rating": 4, "date": "Feb 18"},
    # 3-star (3)
    {"name": "Harper Wilson",  "email": "h.wilson@coreloop.com",  "rating": 3, "date": "Feb 23"},
    {"name": "Elijah Green",   "email": "e.green@datavault.io",   "rating": 3, "date": "Feb 21"},
    {"name": "Charlotte Lee",  "email": "c.lee@pulsenet.co",      "rating": 3, "date": "Feb 20"},
    # 2-star (2)
    {"name": "Benjamin Hall",  "email": "b.hall@irongate.dev",    "rating": 2, "date": "Feb 22"},
    {"name": "Amelia Young",   "email": "a.young@driftworks.com", "rating": 2, "date": "Feb 19"},
]

# ─── Report Analytics (all reports) ───────────────────────────────────────────

CAMPAIGN_ANALYTICS = {
    "label":   "All Reports",
    "updated": "2 hours ago",
    "metrics": [
        {"label": "Total Sent",       "value": "88",    "sub": None,          "change": +71.7, "up_good": True},
        {"label": "Open Rate",        "value": "36.4%", "sub": "32 opens",    "change": +10.2, "up_good": True},
        {"label": "Click to Open",    "value": "9.4%",  "sub": "3 clicks",    "change": +43.6, "up_good": True},
        {"label": "Delivered Rate",   "value": "100%",  "sub": "88 emails",   "change": +71.7, "up_good": True},
        {"label": "Bounce Rate",      "value": "0.0%",  "sub": None,          "change": None,  "up_good": False},
        {"label": "Unsubscribe Rate", "value": "0.0%",  "sub": None,          "change": None,  "up_good": False},
        {"label": "Blocked Rate",     "value": "28.5%", "sub": "35 emails",   "change": +23.8, "up_good": False},
    ],
    "csat": {
        "score":     4.2,
        "responses": 24,
        "dist": [
            {"star": 5, "pct": 46, "count": 11},
            {"star": 4, "pct": 33, "count": 8},
            {"star": 3, "pct": 12, "count": 3},
            {"star": 2, "pct": 8,  "count": 2},
            {"star": 1, "pct": 0,  "count": 0},
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
    KPIMetric("Response Rate",      34.8, 29.1, "percent", True,  "% of report recipients who submitted feedback"),
    KPIMetric("Avg Report Score",   3.9,  4.2,  "score",   True,  "Mean report quality score (1–5)"),
    KPIMetric("NPS Score",          42,   51,   "nps",     True,  "Net Promoter Score for insights delivery"),
    KPIMetric("Negative Feedback",  18.3, 12.7, "percent", False, "% of responses flagging data quality issues"),
    KPIMetric("Unresolved Issues",  47,   31,   "count",   False, "Open report issues needing follow-up"),
]

# ─── DL Reports ───────────────────────────────────────────────────────────────

CAMPAIGNS = [
    {
        "name":      "Animesh test — Q2 Bot QA Campaign",
        "type":      "CSAT",
        "responses": 312,
        "sent":      390,
        "score":     4.7,
        "status":    "✅ Healthy",
        "audience":  "QA Reviewers",
        "sent_at":   "2026-04-22",
    },
    {
        "name":      "Feb 2026 Monthly Analytics Report",
        "type":      "CSAT",
        "responses": 1247,
        "sent":      3580,
        "score":     3.9,
        "status":    "⚠️ Needs Action",
        "audience":  "All Stakeholders",
        "sent_at":   "2026-02-18",
    },
    {
        "name":      "Q1 Executive Business Review",
        "type":      "NPS",
        "responses": 312,
        "sent":      490,
        "score":     42,
        "status":    "✅ Healthy",
        "audience":  "Leadership Team",
        "sent_at":   "2026-02-15",
    },
    {
        "name":      "Sales Performance Dashboard — Feb",
        "type":      "Yes-No",
        "responses": 891,
        "sent":      1100,
        "score":     67,
        "status":    "⚠️ Needs Action",
        "audience":  "Sales Managers",
        "sent_at":   "2026-02-20",
    },
    {
        "name":      "Product Metrics Deep Dive — Feb",
        "type":      "CSAT",
        "responses": 204,
        "sent":      250,
        "score":     4.6,
        "status":    "✅ Healthy",
        "audience":  "Product Team",
        "sent_at":   "2026-02-22",
    },
    {
        "name":      "Customer Cohort Analysis — Q1",
        "type":      "NPS",
        "responses": 88,
        "sent":      143,
        "score":     -12,
        "status":    "🔴 Critical",
        "audience":  "Growth & Retention",
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
        "campaign":    "Feb 2026 Monthly Analytics Report",
        "tags":        ["data accuracy", "missing segments"],
        "comment":     "The APAC segment breakdown was missing entirely and the revenue figures didn't match our internal numbers.",
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
        "campaign":    "Feb 2026 Monthly Analytics Report",
        "tags":        ["report delay", "wrong data"],
        "comment":     "Report arrived 3 days late and the churn metrics were calculated on stale data from January.",
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
        "campaign":    "Q1 Executive Business Review",
        "tags":        ["dashboard link", "chart clarity"],
        "comment":     "The dashboard link was broken for two days. Also the funnel charts need clearer axis labels.",
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
        "campaign":    "Sales Performance Dashboard — Feb",
        "tags":        ["missing KPIs", "format issue"],
        "comment":     "Key win-rate and pipeline velocity KPIs were absent. The PDF export was also unreadable on mobile.",
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
        "campaign":    "Customer Cohort Analysis — Q1",
        "tags":        ["methodology", "missing cohort"],
        "comment":     "Dec 2025 cohort was excluded without explanation and the retention curve methodology wasn't documented.",
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
        "campaign":    "Product Metrics Deep Dive — Feb",
        "tags":        ["visualisation", "benchmark missing"],
        "comment":     "Would be more useful with industry benchmarks alongside our metrics. Visualisations look great though.",
        "hours_open":  43,
        "sla_hours":   96,
        "sla_breached": False,
    },
]

# ─── Analytics by Period ──────────────────────────────────────────────────────

ANALYTICS_BY_PERIOD = {
    "Daily": {
        "label":   "Today  ·  Feb 25, 2026",
        "updated": "15 min ago",
        "metrics": [
            {"label": "Total Sent",       "value": "12",    "sub": None,         "change": +8.3,  "up_good": True},
            {"label": "Open Rate",        "value": "41.7%", "sub": "5 opens",    "change": +5.3,  "up_good": True},
            {"label": "Click to Open",    "value": "20.0%", "sub": "1 click",    "change": +12.4, "up_good": True},
            {"label": "Delivered Rate",   "value": "100%",  "sub": "12 emails",  "change": +8.3,  "up_good": True},
            {"label": "Bounce Rate",      "value": "0.0%",  "sub": None,         "change": None,  "up_good": False},
            {"label": "Unsubscribe Rate", "value": "0.0%",  "sub": None,         "change": None,  "up_good": False},
            {"label": "Blocked Rate",     "value": "16.7%", "sub": "2 emails",   "change": -5.1,  "up_good": False},
        ],
        "csat": {
            "score":     4.5,
            "responses": 4,
            "dist": [
                {"star": 5, "pct": 75, "count": 3},
                {"star": 4, "pct": 25, "count": 1},
                {"star": 3, "pct": 0,  "count": 0},
                {"star": 2, "pct": 0,  "count": 0},
                {"star": 1, "pct": 0,  "count": 0},
            ],
        },
    },
    "Weekly": {
        "label":   "This Week  ·  Feb 19–25, 2026",
        "updated": "1 hour ago",
        "metrics": [
            {"label": "Total Sent",       "value": "34",    "sub": None,          "change": +25.9, "up_good": True},
            {"label": "Open Rate",        "value": "38.2%", "sub": "13 opens",    "change": +8.1,  "up_good": True},
            {"label": "Click to Open",    "value": "15.4%", "sub": "2 clicks",    "change": +31.0, "up_good": True},
            {"label": "Delivered Rate",   "value": "100%",  "sub": "34 emails",   "change": +25.9, "up_good": True},
            {"label": "Bounce Rate",      "value": "0.0%",  "sub": None,          "change": None,  "up_good": False},
            {"label": "Unsubscribe Rate", "value": "0.0%",  "sub": None,          "change": None,  "up_good": False},
            {"label": "Blocked Rate",     "value": "23.5%", "sub": "8 emails",    "change": +10.2, "up_good": False},
        ],
        "csat": {
            "score":     4.3,
            "responses": 11,
            "dist": [
                {"star": 5, "pct": 55, "count": 6},
                {"star": 4, "pct": 27, "count": 3},
                {"star": 3, "pct": 9,  "count": 1},
                {"star": 2, "pct": 9,  "count": 1},
                {"star": 1, "pct": 0,  "count": 0},
            ],
        },
    },
    "Monthly": {
        "label":   "All Reports  ·  Feb 2026",
        "updated": "2 hours ago",
        "metrics": [
            {"label": "Total Sent",       "value": "88",    "sub": None,          "change": +71.7, "up_good": True},
            {"label": "Open Rate",        "value": "36.4%", "sub": "32 opens",    "change": +10.2, "up_good": True},
            {"label": "Click to Open",    "value": "9.4%",  "sub": "3 clicks",    "change": +43.6, "up_good": True},
            {"label": "Delivered Rate",   "value": "100%",  "sub": "88 emails",   "change": +71.7, "up_good": True},
            {"label": "Bounce Rate",      "value": "0.0%",  "sub": None,          "change": None,  "up_good": False},
            {"label": "Unsubscribe Rate", "value": "0.0%",  "sub": None,          "change": None,  "up_good": False},
            {"label": "Blocked Rate",     "value": "28.5%", "sub": "35 emails",   "change": +23.8, "up_good": False},
        ],
        "csat": {
            "score":     4.2,
            "responses": 24,
            "dist": [
                {"star": 5, "pct": 46, "count": 11},
                {"star": 4, "pct": 33, "count": 8},
                {"star": 3, "pct": 12, "count": 3},
                {"star": 2, "pct": 8,  "count": 2},
                {"star": 1, "pct": 0,  "count": 0},
            ],
        },
    },
}

# ─── Email-wise Analytics ─────────────────────────────────────────────────────

DAILY_DATES  = {"Feb 25"}
WEEKLY_DATES = {"Feb 18", "Feb 19", "Feb 20", "Feb 21", "Feb 22", "Feb 23", "Feb 24", "Feb 25"}

EMAIL_ANALYTICS = [
    {"email": "kai.l@nextlayer.io",     "campaign": "Monthly Analytics Report",   "delivered": True,  "opened": True,  "clicked": True,  "responded": False, "score": None, "date": "Feb 25"},
    {"email": "diana.p@cleardata.co",   "campaign": "Q1 Executive Review",        "delivered": True,  "opened": False, "clicked": False, "responded": False, "score": None, "date": "Feb 25"},
    {"email": "marco.v@edgescale.dev",  "campaign": "Product Metrics Deep Dive",  "delivered": True,  "opened": True,  "clicked": False, "responded": True,  "score": 5,    "date": "Feb 25"},
    {"email": "marcus.w@techcorp.io",   "campaign": "Monthly Analytics Report",   "delivered": True,  "opened": True,  "clicked": False, "responded": True,  "score": 2,    "date": "Feb 24"},
    {"email": "priya.s@finflow.com",    "campaign": "Monthly Analytics Report",   "delivered": True,  "opened": True,  "clicked": False, "responded": True,  "score": 1,    "date": "Feb 24"},
    {"email": "chloe.m@clearpath.com",  "campaign": "Q1 Executive Review",        "delivered": True,  "opened": True,  "clicked": True,  "responded": True,  "score": 4,    "date": "Feb 24"},
    {"email": "j.ellis@buildhq.co",     "campaign": "Q1 Executive Review",        "delivered": True,  "opened": True,  "clicked": True,  "responded": True,  "score": 3,    "date": "Feb 23"},
    {"email": "harper.w@coreloop.com",  "campaign": "Monthly Analytics Report",   "delivered": True,  "opened": False, "clicked": False, "responded": False, "score": None, "date": "Feb 23"},
    {"email": "ryan.t@peakdata.io",     "campaign": "Sales Performance Dashboard","delivered": True,  "opened": True,  "clicked": False, "responded": True,  "score": 3,    "date": "Feb 23"},
    {"email": "sofia@novahq.io",        "campaign": "Sales Performance Dashboard","delivered": True,  "opened": False, "clicked": False, "responded": False, "score": None, "date": "Feb 22"},
    {"email": "b.hall@irongate.dev",    "campaign": "Monthly Analytics Report",   "delivered": True,  "opened": True,  "clicked": False, "responded": True,  "score": 2,    "date": "Feb 22"},
    {"email": "sam.k@growthco.io",      "campaign": "Product Metrics Deep Dive",  "delivered": True,  "opened": True,  "clicked": True,  "responded": True,  "score": 5,    "date": "Feb 22"},
    {"email": "d.park@cloudbyte.dev",   "campaign": "Customer Cohort Analysis",   "delivered": True,  "opened": True,  "clicked": False, "responded": True,  "score": 1,    "date": "Feb 22"},
    {"email": "liam.s@gridworks.dev",   "campaign": "Q1 Executive Review",        "delivered": True,  "opened": True,  "clicked": False, "responded": True,  "score": 4,    "date": "Feb 21"},
    {"email": "elijah.g@datavault.io",  "campaign": "Sales Performance Dashboard","delivered": True,  "opened": True,  "clicked": True,  "responded": True,  "score": 3,    "date": "Feb 21"},
    {"email": "nina.r@clearsky.com",    "campaign": "Q1 Executive Review",        "delivered": True,  "opened": False, "clicked": False, "responded": False, "score": None, "date": "Feb 21"},
    {"email": "ava.c@skybridge.io",     "campaign": "Product Metrics Deep Dive",  "delivered": True,  "opened": True,  "clicked": True,  "responded": True,  "score": 4,    "date": "Feb 21"},
    {"email": "amira.h@medlink.org",    "campaign": "Monthly Analytics Report",   "delivered": True,  "opened": True,  "clicked": False, "responded": True,  "score": 3,    "date": "Feb 20"},
    {"email": "lena.v@insightful.co",   "campaign": "Product Metrics Deep Dive",  "delivered": True,  "opened": True,  "clicked": True,  "responded": True,  "score": 4,    "date": "Feb 20"},
    {"email": "raj.m@digitalpulse.in",  "campaign": "Customer Cohort Analysis",   "delivered": True,  "opened": True,  "clicked": False, "responded": True,  "score": 2,    "date": "Feb 20"},
    {"email": "c.lee@pulsenet.co",      "campaign": "Monthly Analytics Report",   "delivered": True,  "opened": False, "clicked": False, "responded": False, "score": None, "date": "Feb 20"},
    {"email": "tom.b@stackdev.io",      "campaign": "Monthly Analytics Report",   "delivered": False, "opened": False, "clicked": False, "responded": False, "score": None, "date": "Feb 19"},
    {"email": "yui.k@fusionlab.jp",     "campaign": "Q1 Executive Review",        "delivered": True,  "opened": True,  "clicked": True,  "responded": True,  "score": 5,    "date": "Feb 19"},
    {"email": "a.young@driftworks.com", "campaign": "Sales Performance Dashboard","delivered": True,  "opened": True,  "clicked": False, "responded": True,  "score": 2,    "date": "Feb 19"},
    {"email": "o.taylor@nexuspoint.io", "campaign": "Product Metrics Deep Dive",  "delivered": True,  "opened": True,  "clicked": True,  "responded": True,  "score": 4,    "date": "Feb 18"},
    {"email": "ben.o@fortescale.co",    "campaign": "Product Metrics Deep Dive",  "delivered": True,  "opened": True,  "clicked": False, "responded": True,  "score": 3,    "date": "Feb 18"},
]
