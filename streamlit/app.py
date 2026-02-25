import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import pandas as pd
from data import (
    HEALTH_KPIS, CAMPAIGNS, ACTION_QUEUE,
    format_kpi, format_delta, delta_is_positive, KPIMetric
)

# ─── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="PulseSignal — Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Global CSS ───────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Hide default Streamlit chrome */
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
header    { visibility: hidden; }

/* Page background */
.stApp { background-color: #0f1117; }

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #161b27;
    border-right: 1px solid #1e2535;
}
[data-testid="stSidebar"] * { color: #94a3b8 !important; }
[data-testid="stSidebar"] .sidebar-title {
    color: #f1f5f9 !important;
    font-weight: 700;
    font-size: 1.1rem;
}

/* Metric cards */
[data-testid="stMetric"] {
    background: #161b27;
    border: 1px solid #1e2535;
    border-radius: 16px;
    padding: 1.2rem 1.4rem !important;
}
[data-testid="stMetricLabel"] { color: #64748b !important; font-size: 0.78rem; font-weight: 500; }
[data-testid="stMetricValue"] { color: #f1f5f9 !important; font-size: 1.8rem; font-weight: 700; }
[data-testid="stMetricDelta"] svg { display: none; }

/* Section headers */
.section-header {
    color: #f1f5f9;
    font-size: 1rem;
    font-weight: 600;
    margin: 0 0 0.25rem 0;
}
.section-sub {
    color: #475569;
    font-size: 0.78rem;
    margin-bottom: 1rem;
}

/* Card container */
.card {
    background: #161b27;
    border: 1px solid #1e2535;
    border-radius: 16px;
    padding: 1.25rem 1.4rem;
    margin-bottom: 1rem;
}

/* Action item */
.action-card {
    background: #161b27;
    border-radius: 14px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.6rem;
    border-left: 3px solid #475569;
}
.action-card.critical { border-left-color: #f43f5e; background: #1a1520; }
.action-card.high     { border-left-color: #f59e0b; background: #181610; }
.action-card.medium   { border-left-color: #38bdf8; background: #121720; }

.customer-name  { color: #f1f5f9; font-weight: 600; font-size: 0.9rem; }
.customer-email { color: #64748b; font-size: 0.78rem; }
.comment-text   { color: #94a3b8; font-size: 0.82rem; font-style: italic; margin: 0.5rem 0; line-height: 1.5; }

.tag {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 99px;
    font-size: 0.7rem;
    font-weight: 500;
    margin-right: 4px;
    background: #1e2535;
    color: #94a3b8;
}
.tag-delay       { background: #431407; color: #fb923c; }
.tag-pricing     { background: #422006; color: #fbbf24; }
.tag-agent       { background: #4c0519; color: #fb7185; }
.tag-billing     { background: #450a0a; color: #fca5a5; }
.tag-refund      { background: #4c0519; color: #fda4af; }
.tag-response    { background: #451a03; color: #fcd34d; }
.tag-quality     { background: #2e1065; color: #c084fc; }
.tag-onboarding  { background: #042f2e; color: #5eead4; }
.tag-feature     { background: #082f49; color: #38bdf8; }
.tag-comm        { background: #1e1b4b; color: #818cf8; }

.sla-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 99px;
    font-size: 0.7rem;
    font-weight: 600;
    background: #4c0519;
    color: #fb7185;
}
.sla-warn {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 99px;
    font-size: 0.7rem;
    font-weight: 600;
    background: #451a03;
    color: #fcd34d;
}

.score-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    border-radius: 10px;
    font-weight: 700;
    font-size: 1rem;
}
.score-bad  { background: rgba(244,63,94,0.15);  color: #f43f5e; border: 1px solid rgba(244,63,94,0.3); }
.score-warn { background: rgba(245,158,11,0.15); color: #f59e0b; border: 1px solid rgba(245,158,11,0.3); }
.score-ok   { background: rgba(52,211,153,0.15); color: #34d399; border: 1px solid rgba(52,211,153,0.3); }

/* Dataframe overrides */
[data-testid="stDataFrameResizable"] {
    border-radius: 12px;
    border: 1px solid #1e2535 !important;
    overflow: hidden;
}

/* Dividers */
hr { border-color: #1e2535 !important; margin: 1.5rem 0; }

/* Smart action buttons */
.smart-btn {
    width: 100%;
    padding: 1rem;
    border-radius: 14px;
    border: 1px solid #1e2535;
    background: #161b27;
    color: #f1f5f9;
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    font-size: 0.85rem;
    cursor: pointer;
    text-align: left;
    transition: all 0.2s;
}
.smart-btn:hover { background: #1e2535; }

/* Page title */
.page-title { color: #f1f5f9; font-size: 1.25rem; font-weight: 700; margin: 0; }
.page-sub   { color: #64748b; font-size: 0.85rem; margin-top: 0.2rem; }
.alert-text { color: #fbbf24; font-weight: 500; }
</style>
""", unsafe_allow_html=True)

# ─── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown('<div class="sidebar-title">⚡ PulseSignal</div>', unsafe_allow_html=True)
    st.markdown("---")

    page = st.radio(
        "Navigation",
        ["📊 Overview", "📣 Campaigns", "🎯 Action Queue"],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown('<div style="color:#475569;font-size:0.75rem;">FILTERS</div>', unsafe_allow_html=True)

    priority_filter = st.multiselect(
        "Priority",
        ["🔴 Critical", "🟠 High", "🟡 Medium"],
        default=["🔴 Critical", "🟠 High", "🟡 Medium"],
    )

    sla_only = st.checkbox("SLA Breached only", value=False)

    st.markdown("---")
    st.markdown(
        '<div style="color:#334155;font-size:0.72rem;">vs last 30 days · AMP surveys</div>',
        unsafe_allow_html=True,
    )

# ─── Helpers ──────────────────────────────────────────────────────────────────

TAG_CLASS = {
    "delay":           "tag-delay",
    "pricing":         "tag-pricing",
    "agent behavior":  "tag-agent",
    "billing issue":   "tag-billing",
    "refund":          "tag-refund",
    "response time":   "tag-response",
    "product quality": "tag-quality",
    "onboarding":      "tag-onboarding",
    "feature request": "tag-feature",
    "communication":   "tag-comm",
}

def score_class(score: int, kind: str) -> str:
    if kind == "CSAT":
        return "score-bad" if score <= 2 else "score-warn" if score == 3 else "score-ok"
    return "score-bad" if score <= 4 else "score-warn" if score <= 6 else "score-ok"

def render_action_card(item: dict) -> str:
    p = item["priority"]
    cls = "critical" if "Critical" in p else "high" if "High" in p else "medium"

    tags_html = " ".join(
        f'<span class="tag {TAG_CLASS.get(t, "")}">{t}</span>'
        for t in item["tags"]
    )

    sla_html = ""
    if item["sla_breached"]:
        sla_html = f'<span class="sla-badge">🔥 SLA Breached · {item["hours_open"]}h open</span>'
    elif (item["sla_hours"] - item["hours_open"]) <= 12:
        remaining = item["sla_hours"] - item["hours_open"]
        sla_html = f'<span class="sla-warn">⏱ {remaining}h to SLA</span>'

    sc = score_class(item["score"], item["type"])

    return f"""
    <div class="action-card {cls}">
        <div style="display:flex;align-items:flex-start;gap:12px;">
            <div class="score-badge {sc}">{item["score"]}</div>
            <div style="flex:1;min-width:0;">
                <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                    <span class="customer-name">{item["name"]}</span>
                    <span class="customer-email">{item["email"]}</span>
                    {sla_html}
                </div>
                <div style="color:#475569;font-size:0.75rem;margin-top:2px;">
                    {item["type"]} · {item["campaign"]}
                </div>
                <div class="comment-text">"{item["comment"]}"</div>
                <div>{tags_html}</div>
            </div>
        </div>
    </div>
    """

# ─── Section: Health KPIs ─────────────────────────────────────────────────────

def render_health():
    st.markdown('<p class="section-header">Feedback Health</p>', unsafe_allow_html=True)
    st.markdown('<p class="section-sub">vs last 30 days · 🟢 Live</p>', unsafe_allow_html=True)

    cols = st.columns(5)
    for col, m in zip(cols, HEALTH_KPIS):
        delta_str = format_delta(m)
        good = delta_is_positive(m)
        # Streamlit shows green for positive delta; invert sign for "lower is better" metrics
        display_delta = delta_str if good else f"-{abs(m.value - m.previous):.1f}{'%' if m.unit == 'percent' else ''}"
        with col:
            st.metric(
                label=m.label,
                value=format_kpi(m),
                delta=delta_str,
                delta_color="normal" if good else "inverse",
                help=m.description,
            )

# ─── Section: Campaigns ───────────────────────────────────────────────────────

def render_campaigns():
    st.markdown('<p class="section-header">Recent Campaigns</p>', unsafe_allow_html=True)
    st.markdown(
        f'<p class="section-sub">{len(CAMPAIGNS)} campaigns sent in the last 30 days</p>',
        unsafe_allow_html=True,
    )

    df = pd.DataFrame(CAMPAIGNS)
    df = df.rename(columns={
        "name":      "Campaign",
        "type":      "Type",
        "responses": "Responses",
        "sent":      "Total Sent",
        "score":     "Score",
        "status":    "Status",
        "audience":  "Audience",
        "sent_at":   "Sent Date",
    })
    df["Response Rate"] = (df["Responses"] / df["Total Sent"] * 100).round(1).astype(str) + "%"
    df = df[["Campaign", "Type", "Responses", "Response Rate", "Score", "Status", "Sent Date"]]

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Campaign": st.column_config.TextColumn(width="large"),
            "Type":     st.column_config.TextColumn(width="small"),
            "Score":    st.column_config.NumberColumn(format="%.1f"),
            "Response Rate": st.column_config.TextColumn(width="small"),
            "Status":   st.column_config.TextColumn(width="medium"),
        },
    )

# ─── Section: Action Queue ────────────────────────────────────────────────────

def render_action_queue(priority_filter, sla_only):
    items = [i for i in ACTION_QUEUE if i["priority"] in priority_filter]
    if sla_only:
        items = [i for i in items if i["sla_breached"]]

    breached = sum(1 for i in items if i["sla_breached"])

    st.markdown(
        f'<p class="section-header">Action Queue <span style="background:#4c0519;color:#fb7185;'
        f'padding:2px 8px;border-radius:99px;font-size:0.75rem;margin-left:6px;">{len(items)}</span></p>',
        unsafe_allow_html=True,
    )
    sub = f'<span style="color:#f43f5e;font-weight:500;">{breached} breaching SLA · </span>' if breached else ""
    st.markdown(
        f'<p class="section-sub">{sub}Customers needing immediate follow-up</p>',
        unsafe_allow_html=True,
    )

    if not items:
        st.info("No items match the current filters.")
        return

    # Sort: SLA breached first, then by priority
    order = {"🔴 Critical": 0, "🟠 High": 1, "🟡 Medium": 2}
    items.sort(key=lambda x: (not x["sla_breached"], order.get(x["priority"], 3)))

    html = "".join(render_action_card(i) for i in items)
    st.markdown(html, unsafe_allow_html=True)

# ─── Section: Smart Next Actions ─────────────────────────────────────────────

def render_smart_actions():
    st.markdown('<p class="section-header">Smart Next Actions</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="section-sub">Recommended based on your current feedback state</p>',
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        if st.button("➕  Create New Survey", use_container_width=True, type="primary"):
            st.toast("Opening survey builder…", icon="➕")

    with c2:
        if st.button("📧  Send Recovery Emails  ·  47 ready", use_container_width=True):
            st.toast("Preparing recovery emails…", icon="📧")

    with c3:
        if st.button("📊  Analyze Last Campaign", use_container_width=True):
            st.toast("Loading campaign analysis…", icon="📊")

    with c4:
        if st.button("⬇️  Export Negative Feedback  ·  228 rows", use_container_width=True):
            st.toast("Preparing CSV export…", icon="⬇️")

# ─── Page header ──────────────────────────────────────────────────────────────

st.markdown("""
<div style="margin-bottom:1.5rem;">
    <p class="page-title">Good morning, Animesh 👋</p>
    <p class="page-sub">
        Here's what's happening with your customer feedback today.
        <span class="alert-text">2 items need urgent attention.</span>
    </p>
</div>
""", unsafe_allow_html=True)

# ─── Render by page ───────────────────────────────────────────────────────────

if page == "📊 Overview":
    render_health()
    st.markdown("---")
    render_smart_actions()
    st.markdown("---")
    col_left, col_right = st.columns([2, 1])
    with col_left:
        render_campaigns()
    with col_right:
        render_action_queue(priority_filter, sla_only)

elif page == "📣 Campaigns":
    render_health()
    st.markdown("---")
    render_campaigns()

elif page == "🎯 Action Queue":
    render_action_queue(priority_filter, sla_only)
