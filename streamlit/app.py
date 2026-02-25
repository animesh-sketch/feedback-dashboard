import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
from data import HEALTH_KPIS, format_kpi, format_delta, delta_is_positive
from email_builder import build_email_html
import auth
import gmail_sender

# ─── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="LivePure",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Session state defaults ───────────────────────────────────────────────────

if "clients" not in st.session_state:
    st.session_state.clients = []

def _blank_draft(idx: int) -> dict:
    return {
        "name": f"Draft {idx + 1}",
        "status": "empty",
        "report_type": "Monthly Analytics Report",
        "date": "February 2026",
        "client": "",
        "analyst": "Animesh Koner",
        "headline": "",
        "intro": "",
        "kpis": [
            {"label": "Metric 1", "value": "—", "delta": "", "trend": "up",   "period": ""},
            {"label": "Metric 2", "value": "—", "delta": "", "trend": "up",   "period": ""},
            {"label": "Metric 3", "value": "—", "delta": "", "trend": "down", "period": ""},
            {"label": "Metric 4", "value": "—", "delta": "", "trend": "down", "period": ""},
        ],
        "chart1_url": "", "chart1_caption": "Fig. 1",
        "chart2_url": "", "chart2_caption": "Fig. 2",
        "chart3_url": "", "chart3_caption": "Fig. 3",
        "insight": "",
        "findings": ["", "", "", ""],
        "report_link": "",
        "survey_question": "Was this report useful to you?",
        "show_preview": False,
    }

if "drafts" not in st.session_state:
    st.session_state.drafts = [_blank_draft(i) for i in range(3)]

# ─── OAuth callback handler ───────────────────────────────────────────────────

_params = st.query_params
if "code" in _params and not st.session_state.get("credentials"):
    try:
        _redirect_uri = st.secrets.get("REDIRECT_URI", "http://localhost:8501")
        _creds = auth.exchange_code_for_token(_params["code"], _redirect_uri)
        _email = auth.get_user_email(_creds)
        st.session_state["credentials"] = _creds
        st.session_state["user_email"] = _email
        for _k in ["oauth_state", "pending_auth_url"]:
            st.session_state.pop(_k, None)
        st.query_params.clear()
        st.rerun()
    except Exception as _e:
        st.error(f"Google sign-in failed: {_e}")
        st.query_params.clear()

# ─── Global CSS ───────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
header    { visibility: hidden; }

/* ── App shell ── */
.stApp { background: #07090f; }
.block-container { padding-top: 2rem !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #0a0d16 !important;
    border-right: 1px solid #111827 !important;
}
[data-testid="stSidebar"] * { color: #4b5563 !important; }
[data-testid="stSidebar"] .stRadio > div { gap: 2px !important; }
[data-testid="stSidebar"] .stRadio label {
    font-size: 0.84rem !important;
    font-weight: 500 !important;
    padding: 8px 10px !important;
    border-radius: 8px !important;
    transition: background 0.15s !important;
}
[data-testid="stSidebar"] .stRadio label:has(input:checked) {
    background: #131c2e !important;
    color: #e2e8f0 !important;
}

/* ── Inputs & textareas ── */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {
    background: #0d1220 !important;
    border: 1px solid #1a2540 !important;
    border-radius: 10px !important;
    color: #cbd5e1 !important;
    font-size: 0.84rem !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.1) !important;
}
[data-testid="stSelectbox"] > div > div {
    background: #0d1220 !important;
    border: 1px solid #1a2540 !important;
    border-radius: 10px !important;
    color: #cbd5e1 !important;
}

/* ── Buttons ── */
.stButton > button {
    border-radius: 10px !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.01em !important;
    transition: all 0.15s !important;
    border: none !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #2563eb 0%, #4f46e5 100%) !important;
    color: #fff !important;
    box-shadow: 0 2px 12px rgba(59,130,246,0.25) !important;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 24px rgba(59,130,246,0.4) !important;
}
.stButton > button[kind="secondary"] {
    background: #0d1220 !important;
    border: 1px solid #1a2540 !important;
    color: #64748b !important;
}
.stButton > button[kind="secondary"]:hover {
    background: #111827 !important;
    color: #94a3b8 !important;
}

/* ── Download button ── */
[data-testid="stDownloadButton"] button {
    background: #0d1220 !important;
    border: 1px solid #1a2540 !important;
    border-radius: 10px !important;
    color: #64748b !important;
    font-size: 0.82rem !important;
}

/* ── Tabs ── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid #111827 !important;
    gap: 0 !important;
    padding: 0 !important;
}
[data-baseweb="tab"] {
    background: transparent !important;
    font-size: 0.83rem !important;
    font-weight: 500 !important;
    color: #4b5563 !important;
    padding: 10px 22px !important;
    border-bottom: 2px solid transparent !important;
}
[aria-selected="true"][data-baseweb="tab"] {
    color: #e2e8f0 !important;
    border-bottom: 2px solid #3b82f6 !important;
}
[data-testid="stTabs"] [data-baseweb="tab-panel"] {
    padding-top: 1.5rem !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    background: #0d1220 !important;
    border: 1px solid #1a2540 !important;
    border-radius: 12px !important;
}
[data-testid="stExpander"] summary {
    font-size: 0.84rem !important;
    font-weight: 500 !important;
    color: #64748b !important;
}

/* ── Forms ── */
[data-testid="stForm"] {
    background: #0d1220 !important;
    border: 1px solid #1a2540 !important;
    border-radius: 14px !important;
}

/* ── Alerts ── */
[data-testid="stAlert"] { border-radius: 10px !important; font-size: 0.84rem !important; }

/* ── Divider ── */
hr { border-color: #0f172a !important; margin: 1.5rem 0 !important; }

/* ── Caption / small text ── */
[data-testid="stCaptionContainer"] p { color: #374151 !important; font-size: 0.77rem !important; }
label { color: #4b5563 !important; font-size: 0.8rem !important; }

/* ──────────────────────────────────────────────────────
   OVERVIEW PAGE COMPONENTS
────────────────────────────────────────────────────── */

.hero-banner {
    background: linear-gradient(135deg, #0d1425 0%, #0f1a35 50%, #120d28 100%);
    border: 1px solid #1a2540;
    border-radius: 22px;
    padding: 2rem 2.2rem;
    margin-bottom: 1.8rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.hero-title {
    font-size: 1.4rem;
    font-weight: 700;
    color: #f1f5f9;
    letter-spacing: -0.025em;
    margin-bottom: 0.3rem;
}
.hero-sub { font-size: 0.83rem; color: #475569; }
.live-badge {
    background: rgba(16,185,129,0.1);
    border: 1px solid rgba(16,185,129,0.22);
    color: #10b981;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    padding: 6px 14px;
    border-radius: 99px;
    white-space: nowrap;
}

/* KPI grid */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 14px;
    margin-bottom: 2.5rem;
}
.kpi-card {
    background: #0d1220;
    border: 1px solid #111827;
    border-radius: 18px;
    padding: 1.3rem 1.4rem 1.1rem;
    position: relative;
    overflow: hidden;
    transition: transform 0.18s ease, box-shadow 0.18s ease;
    cursor: default;
}
.kpi-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 12px 40px rgba(0,0,0,0.45);
    border-color: #1a2540;
}
.kpi-card::after {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    border-radius: 18px 18px 0 0;
}
.kpi-card.trend-good::after { background: linear-gradient(90deg, #059669, #34d399); }
.kpi-card.trend-bad::after  { background: linear-gradient(90deg, #dc2626, #f87171); }
.kpi-label {
    font-size: 0.67rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #374151;
    margin-bottom: 0.75rem;
}
.kpi-value {
    font-size: 2rem;
    font-weight: 700;
    color: #f1f5f9;
    letter-spacing: -0.03em;
    line-height: 1;
    margin-bottom: 0.4rem;
}
.kpi-delta {
    font-size: 0.75rem;
    font-weight: 600;
    margin-bottom: 0.15rem;
}
.kpi-delta.good { color: #34d399; }
.kpi-delta.bad  { color: #f87171; }
.kpi-period { font-size: 0.67rem; color: #1f2937; margin-top: 0.1rem; }

/* section divider label */
.sec-label {
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #1e293b;
    margin-bottom: 1.2rem;
}

/* ──────────────────────────────────────────────────────
   EMAIL MAKER COMPONENTS
────────────────────────────────────────────────────── */

.em-header {
    background: linear-gradient(135deg, #0d1425 0%, #0f1030 100%);
    border: 1px solid #1a2540;
    border-radius: 20px;
    padding: 1.6rem 2rem;
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    gap: 1rem;
}
.em-icon { font-size: 1.6rem; line-height: 1; }
.em-title { font-size: 1.2rem; font-weight: 700; color: #f1f5f9; letter-spacing: -0.02em; }
.em-sub   { font-size: 0.8rem; color: #4b5563; margin-top: 0.15rem; }

/* Draft status cards */
.draft-card {
    background: #0a0e1a;
    border: 1px solid #111827;
    border-radius: 16px;
    padding: 16px 18px;
    margin-bottom: 12px;
}

/* Client cards */
.client-card {
    background: #0a0e1a;
    border: 1px solid #111827;
    border-radius: 12px;
    padding: 14px 18px;
    margin-bottom: 8px;
    transition: border-color 0.15s;
}
.client-card:hover { border-color: #1a2540; }
.client-name { color: #e2e8f0; font-weight: 600; font-size: 0.88rem; }
.email-pill {
    display: inline-block;
    background: #111827;
    color: #4b5563;
    font-size: 0.7rem;
    padding: 3px 10px;
    border-radius: 99px;
    margin: 3px 3px 0 0;
}
</style>
""", unsafe_allow_html=True)

# ─── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style="padding:8px 4px 20px;">
        <div style="color:#e2e8f0;font-weight:700;font-size:1rem;letter-spacing:-0.015em;">⚡ LivePure</div>
        <div style="color:#1e2d45;font-size:0.7rem;margin-top:3px;font-weight:500;letter-spacing:0.04em;text-transform:uppercase;">Analytics</div>
    </div>
    """, unsafe_allow_html=True)

    page = st.radio(
        "nav",
        ["📊 Overview", "📧 Email Maker"],
        label_visibility="collapsed",
    )

    st.markdown("---")
    auth.render_login_sidebar()
    st.markdown("---")
    st.markdown('<div style="color:#111827;font-size:0.68rem;font-weight:500;">Feb 2026 · v1.0</div>', unsafe_allow_html=True)

# ─── Overview ─────────────────────────────────────────────────────────────────

def render_overview():
    st.markdown("""
    <div class="hero-banner">
        <div>
            <div class="hero-title">Good morning, Animesh 👋</div>
            <div class="hero-sub">Feedback health snapshot · February 2026</div>
        </div>
        <div class="live-badge">● Live</div>
    </div>
    """, unsafe_allow_html=True)

    cards_html = ""
    for m in HEALTH_KPIS:
        value   = format_kpi(m)
        delta   = format_delta(m)
        good    = delta_is_positive(m)
        arrow   = "▲" if (m.value - m.previous) > 0 else "▼"
        t_class = "good" if good else "bad"
        cards_html += f"""
        <div class="kpi-card trend-{t_class}">
            <div class="kpi-label">{m.label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-delta {t_class}">{arrow}&nbsp;{delta}</div>
            <div class="kpi-period">vs last 30 days</div>
        </div>"""

    st.markdown(f'<div class="kpi-grid">{cards_html}</div>', unsafe_allow_html=True)

# ─── Draft helpers ────────────────────────────────────────────────────────────

STATUS_META = {
    "empty": ("#111827", "#374151", "Empty"),
    "draft": ("#0d2515", "#6ee7b7", "In Progress"),
    "ready": ("#13103a", "#a5b4fc", "Ready"),
}

def render_drafts_tab():
    st.markdown('<div style="color:#e2e8f0;font-size:1rem;font-weight:600;margin-bottom:4px;">Drafts</div>', unsafe_allow_html=True)
    st.caption("Up to 3 email drafts — edit, preview, and send independently.")
    st.markdown("")

    cols = st.columns(3)
    for i, (col, draft) in enumerate(zip(cols, st.session_state.drafts)):
        bg, fg, lbl = STATUS_META[draft["status"]]
        with col:
            st.markdown(
                f"""<div class="draft-card">
                    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:5px;">
                        <span style="color:#e2e8f0;font-weight:600;font-size:0.88rem;">{draft['name']}</span>
                        <span style="background:{bg};color:{fg};font-size:0.6rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;padding:3px 9px;border-radius:99px;">{lbl}</span>
                    </div>
                    <div style="color:#1f2937;font-size:0.72rem;">{draft['client'] or 'No client'} · {draft['report_type']}</div>
                </div>""",
                unsafe_allow_html=True,
            )

            with st.expander("✏️ Edit Draft", expanded=draft["status"] == "empty"):
                d = st.session_state.drafts[i]
                d["name"]        = st.text_input("Draft Name",    value=d["name"],        key=f"dname_{i}")
                d["client"]      = st.text_input("Client",        value=d["client"],      key=f"dclient_{i}",  placeholder="Acme Corp")
                d["report_type"] = st.text_input("Report Type",   value=d["report_type"], key=f"drtype_{i}")
                d["date"]        = st.text_input("Date",          value=d["date"],        key=f"ddate_{i}")
                d["headline"]    = st.text_area("Headline",       value=d["headline"],    key=f"dhead_{i}",    height=80)
                d["intro"]       = st.text_area("Intro",          value=d["intro"],       key=f"dintro_{i}",   height=90)

                st.markdown('<div style="color:#374151;font-size:0.75rem;font-weight:600;margin:8px 0 4px;">KPIs</div>', unsafe_allow_html=True)
                for k in range(4):
                    kc1, kc2, kc3 = st.columns([2, 2, 1])
                    with kc1:
                        d["kpis"][k]["label"] = st.text_input(f"Label {k+1}", value=d["kpis"][k]["label"], key=f"klbl_{i}_{k}")
                        d["kpis"][k]["value"] = st.text_input(f"Value {k+1}", value=d["kpis"][k]["value"], key=f"kval_{i}_{k}")
                    with kc2:
                        d["kpis"][k]["delta"]  = st.text_input(f"Delta {k+1}",  value=d["kpis"][k]["delta"],  key=f"kdlt_{i}_{k}", placeholder="↑ 12%")
                        d["kpis"][k]["period"] = st.text_input(f"Period {k+1}", value=d["kpis"][k]["period"], key=f"kper_{i}_{k}")
                    with kc3:
                        d["kpis"][k]["trend"] = st.selectbox(f"↑↓", ["up", "down"], index=0 if d["kpis"][k]["trend"] == "up" else 1, key=f"ktrnd_{i}_{k}")

                st.markdown('<div style="color:#374151;font-size:0.75rem;font-weight:600;margin:8px 0 4px;">Charts — paste URLs</div>', unsafe_allow_html=True)
                d["chart1_url"]     = st.text_input("Chart 1 URL",     value=d["chart1_url"],     key=f"c1u_{i}", placeholder="https://…")
                d["chart1_caption"] = st.text_input("Chart 1 Caption", value=d["chart1_caption"], key=f"c1c_{i}")
                d["chart2_url"]     = st.text_input("Chart 2 URL",     value=d["chart2_url"],     key=f"c2u_{i}", placeholder="https://…")
                d["chart2_caption"] = st.text_input("Chart 2 Caption", value=d["chart2_caption"], key=f"c2c_{i}")
                d["chart3_url"]     = st.text_input("Chart 3 URL",     value=d["chart3_url"],     key=f"c3u_{i}", placeholder="https://…")
                d["chart3_caption"] = st.text_input("Chart 3 Caption", value=d["chart3_caption"], key=f"c3c_{i}")

                d["insight"] = st.text_area("Key Insight", value=d["insight"], key=f"dins_{i}", height=80)

                st.markdown('<div style="color:#374151;font-size:0.75rem;font-weight:600;margin:8px 0 4px;">Findings (up to 4)</div>', unsafe_allow_html=True)
                for f in range(4):
                    d["findings"][f] = st.text_input(f"Finding {f+1}", value=d["findings"][f], key=f"dfnd_{i}_{f}", placeholder=f"Finding {f+1}…")

                d["report_link"]     = st.text_input("Full Report URL",  value=d["report_link"],     key=f"dlink_{i}", placeholder="https://docs.google.com/…")
                d["survey_question"] = st.text_input("Survey Question",  value=d["survey_question"], key=f"dsq_{i}")

                sc1, sc2 = st.columns(2)
                with sc1:
                    if st.button("Save Draft", key=f"save_{i}", use_container_width=True):
                        st.session_state.drafts[i]["status"] = "draft"
                        st.toast(f"{d['name']} saved.", icon="💾")
                        st.rerun()
                with sc2:
                    if st.button("Mark Ready", key=f"ready_{i}", use_container_width=True, type="primary"):
                        st.session_state.drafts[i]["status"] = "ready"
                        st.toast(f"{d['name']} ready to send.", icon="✅")
                        st.rerun()

            if st.button("👁 Preview", key=f"prev_{i}", use_container_width=True):
                st.session_state.drafts[i]["show_preview"] = not draft["show_preview"]
                st.rerun()
            if draft["status"] != "empty":
                if st.button("Reset", key=f"reset_{i}", use_container_width=True):
                    st.session_state.drafts[i] = _blank_draft(i)
                    st.rerun()

    for i, draft in enumerate(st.session_state.drafts):
        if draft.get("show_preview"):
            st.markdown("---")
            st.markdown(f"#### Preview — {draft['name']}")
            components.html(build_email_html(draft), height=1600, scrolling=True)


# ─── Email Maker ──────────────────────────────────────────────────────────────

def render_email_maker():
    st.markdown("""
    <div class="em-header">
        <div class="em-icon">📧</div>
        <div>
            <div class="em-title">Email Maker</div>
            <div class="em-sub">Build report emails and send to clients via Gmail.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    tab_drafts, tab_editor, tab_preview, tab_recipients = st.tabs(
        ["✏️  Drafts", "📝  Edit Body", "📄  Preview", "👥  Recipients"]
    )

    # ── Drafts ────────────────────────────────────────────────────────────────
    with tab_drafts:
        render_drafts_tab()

    # ── Edit Body ─────────────────────────────────────────────────────────────
    with tab_editor:
        st.markdown('<div style="color:#e2e8f0;font-size:1rem;font-weight:600;margin-bottom:4px;">Edit Email Body</div>', unsafe_allow_html=True)
        st.caption("Fill in every section. Hit Preview at the bottom to see it rendered.")

        draft_names = [d["name"] for d in st.session_state.drafts]
        chosen = st.radio("Editing:", draft_names, horizontal=True, key="editor_draft_pick")
        ei = draft_names.index(chosen)
        d  = st.session_state.drafts[ei]
        st.markdown("---")

        st.markdown('<div style="color:#374151;font-size:0.78rem;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;margin-bottom:10px;">Header & Meta</div>', unsafe_allow_html=True)
        hc1, hc2, hc3 = st.columns(3)
        with hc1: d["client"]      = st.text_input("Client / Company", value=d["client"],      key=f"ed_client_{ei}", placeholder="Acme Corp")
        with hc2: d["report_type"] = st.text_input("Report Type",      value=d["report_type"], key=f"ed_rtype_{ei}")
        with hc3: d["date"]        = st.text_input("Date",             value=d["date"],        key=f"ed_date_{ei}")
        st.markdown("---")

        st.markdown('<div style="color:#374151;font-size:0.78rem;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;margin-bottom:10px;">Hero Section</div>', unsafe_allow_html=True)
        d["headline"] = st.text_area("Headline",      value=d["headline"], key=f"ed_head_{ei}",  height=80,  placeholder="e.g. February showed strong growth with one risk area.")
        d["intro"]    = st.text_area("Intro Paragraph", value=d["intro"],  key=f"ed_intro_{ei}", height=100, placeholder="2–3 sentence overview of the report…")
        st.markdown("---")

        st.markdown('<div style="color:#374151;font-size:0.78rem;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;margin-bottom:10px;">KPI Strip — 4 metrics</div>', unsafe_allow_html=True)
        for k in range(4):
            kc1, kc2, kc3, kc4, kc5 = st.columns([2, 2, 2, 2, 1])
            with kc1: d["kpis"][k]["label"]  = st.text_input(f"Metric {k+1}",  value=d["kpis"][k]["label"],  key=f"ed_klbl_{ei}_{k}", placeholder="Conversion Rate")
            with kc2: d["kpis"][k]["value"]  = st.text_input("Value",          value=d["kpis"][k]["value"],  key=f"ed_kval_{ei}_{k}", placeholder="4.7%")
            with kc3: d["kpis"][k]["delta"]  = st.text_input("Delta",          value=d["kpis"][k]["delta"],  key=f"ed_kdlt_{ei}_{k}", placeholder="↑ 0.6pp")
            with kc4: d["kpis"][k]["period"] = st.text_input("Period",         value=d["kpis"][k]["period"], key=f"ed_kper_{ei}_{k}", placeholder="vs last month")
            with kc5: d["kpis"][k]["trend"]  = st.selectbox("↑↓", ["up", "down"], index=0 if d["kpis"][k]["trend"] == "up" else 1, key=f"ed_ktrnd_{ei}_{k}")
        st.markdown("---")

        st.markdown('<div style="color:#374151;font-size:0.78rem;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;margin-bottom:10px;">Charts — paste hosted image URLs</div>', unsafe_allow_html=True)
        for ci, label in enumerate(["Chart 1 (full width)", "Chart 2 (left half)", "Chart 3 (right half)"]):
            cc1, cc2 = st.columns([3, 2])
            key = f"chart{ci+1}"
            with cc1: d[f"{key}_url"]     = st.text_input(f"{label} — URL",     value=d[f"{key}_url"],     key=f"ed_{key}u_{ei}", placeholder="https://…")
            with cc2: d[f"{key}_caption"] = st.text_input(f"{label} — Caption", value=d[f"{key}_caption"], key=f"ed_{key}c_{ei}")
        st.markdown("---")

        st.markdown('<div style="color:#374151;font-size:0.78rem;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;margin-bottom:10px;">Key Insight</div>', unsafe_allow_html=True)
        d["insight"] = st.text_area("", value=d["insight"], key=f"ed_ins_{ei}", height=90, label_visibility="collapsed", placeholder="The single most important takeaway…")
        st.markdown("---")

        st.markdown('<div style="color:#374151;font-size:0.78rem;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;margin-bottom:10px;">Findings (up to 4)</div>', unsafe_allow_html=True)
        for fi in range(4):
            d["findings"][fi] = st.text_input(f"Finding {fi+1}", value=d["findings"][fi], key=f"ed_fnd_{ei}_{fi}", placeholder=f"Finding {fi+1} — leave blank to hide")
        st.markdown("---")

        st.markdown('<div style="color:#374151;font-size:0.78rem;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;margin-bottom:10px;">Report Link & Survey</div>', unsafe_allow_html=True)
        lc1, lc2 = st.columns(2)
        with lc1: d["report_link"]     = st.text_input("Full Report URL", value=d["report_link"],     key=f"ed_link_{ei}", placeholder="https://docs.google.com/…")
        with lc2: d["survey_question"] = st.text_input("Survey Question", value=d["survey_question"], key=f"ed_sq_{ei}")
        st.markdown("---")

        bc1, bc2, bc3 = st.columns(3)
        with bc1:
            if st.button("Save Draft", key=f"ed_save_{ei}", use_container_width=True):
                st.session_state.drafts[ei]["status"] = "draft"
                st.toast(f"{d['name']} saved.", icon="💾")
                st.rerun()
        with bc2:
            if st.button("Mark Ready", key=f"ed_ready_{ei}", use_container_width=True, type="primary"):
                st.session_state.drafts[ei]["status"] = "ready"
                st.toast(f"{d['name']} is ready.", icon="✅")
                st.rerun()
        with bc3:
            if st.button("👁 Preview Email", key=f"ed_prev_{ei}", use_container_width=True):
                st.session_state.drafts[ei]["show_preview"] = True
                st.rerun()

        if d.get("show_preview"):
            st.markdown("---")
            st.markdown(f"#### Preview — {d['name']}")
            components.html(build_email_html(d), height=1600, scrolling=True)

    # ── Email Preview ─────────────────────────────────────────────────────────
    with tab_preview:
        st.markdown('<div style="color:#e2e8f0;font-size:1rem;font-weight:600;margin-bottom:4px;">Email Preview</div>', unsafe_allow_html=True)
        st.caption("Exactly how the email looks in a client's inbox.")
        preview_path = os.path.join(os.path.dirname(__file__), "..", "email-templates", "preview.html")
        try:
            with open(os.path.abspath(preview_path), "r", encoding="utf-8") as f:
                html_content = f.read()
            html_content = html_content.replace(
                '<div class="preview-bar">',
                '<div class="preview-bar" style="display:none">',
            )
            components.html(html_content, height=1500, scrolling=True)
        except FileNotFoundError:
            st.error("preview.html not found. Make sure email-templates/preview.html exists.")

    # ── Recipients ────────────────────────────────────────────────────────────
    with tab_recipients:
        st.markdown('<div style="color:#e2e8f0;font-size:1rem;font-weight:600;margin-bottom:4px;">Recipients</div>', unsafe_allow_html=True)
        st.caption("Add clients and their email addresses. One client can have up to 5 emails.")

        with st.expander("➕  Add New Client", expanded=len(st.session_state.clients) == 0):
            with st.form("add_client_form", clear_on_submit=True):
                client_name = st.text_input("Client / Company", placeholder="e.g. Acme Corp")
                st.markdown('<div style="color:#374151;font-size:0.78rem;font-weight:600;margin:10px 0 6px;">Email Addresses — up to 5</div>', unsafe_allow_html=True)
                col1, col2 = st.columns(2)
                with col1:
                    e1 = st.text_input("Email 1", placeholder="primary@acme.com")
                    e2 = st.text_input("Email 2", placeholder="manager@acme.com")
                    e3 = st.text_input("Email 3", placeholder="cfo@acme.com")
                with col2:
                    e4 = st.text_input("Email 4", placeholder="analyst@acme.com")
                    e5 = st.text_input("Email 5", placeholder="optional@acme.com")
                submitted = st.form_submit_button("Save Client", type="primary", use_container_width=True)
                if submitted:
                    if not client_name.strip():
                        st.warning("Please enter a client name.")
                    else:
                        emails = [e for e in [e1, e2, e3, e4, e5] if e.strip()]
                        if not emails:
                            st.warning("Please add at least one email address.")
                        else:
                            st.session_state.clients.append({"name": client_name.strip(), "emails": emails})
                            st.success(f"✓ {client_name} added with {len(emails)} email(s).")
                            st.rerun()

        st.markdown("---")

        if not st.session_state.clients:
            st.markdown(
                '<div style="text-align:center;padding:48px 20px;color:#1f2937;font-size:0.84rem;">No clients yet — add one above.</div>',
                unsafe_allow_html=True,
            )
        else:
            total_emails = sum(len(c["emails"]) for c in st.session_state.clients)
            st.markdown(
                f'<div style="color:#374151;font-size:0.75rem;font-weight:600;margin-bottom:14px;">'
                f'{len(st.session_state.clients)} clients · {total_emails} addresses</div>',
                unsafe_allow_html=True,
            )

            for idx, client in enumerate(st.session_state.clients):
                pills = " ".join(f'<span class="email-pill">{e}</span>' for e in client["emails"])
                col_card, col_del = st.columns([9, 1])
                with col_card:
                    st.markdown(
                        f'<div class="client-card"><div class="client-name">{client["name"]}</div>'
                        f'<div style="margin-top:6px;">{pills}</div></div>',
                        unsafe_allow_html=True,
                    )
                with col_del:
                    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
                    if st.button("🗑", key=f"del_{idx}", help=f"Remove {client['name']}"):
                        st.session_state.clients.pop(idx)
                        st.rerun()

            st.markdown("---")

            all_emails = [e for c in st.session_state.clients for e in c["emails"]]

            if not st.session_state.get("credentials"):
                st.markdown(
                    '<div style="background:#0a0e1a;border:1px solid #111827;border-radius:14px;'
                    'padding:18px;text-align:center;color:#374151;font-size:0.82rem;">'
                    '🔒 Sign in with Google (sidebar) to send emails</div>',
                    unsafe_allow_html=True,
                )
            else:
                draft_names = [d["name"] for d in st.session_state.drafts]
                send_draft_name = st.selectbox("Send which draft?", draft_names, key="send_draft_pick")
                send_draft = st.session_state.drafts[draft_names.index(send_draft_name)]

                if st.button(
                    f"📤  Send to All  ·  {len(all_emails)} address(es)",
                    type="primary",
                    use_container_width=True,
                ):
                    subject = f"{send_draft.get('report_type', 'Report')} — {send_draft.get('date', '')}"
                    with st.spinner(f"Sending to {len(all_emails)} recipient(s)…"):
                        result = gmail_sender.send_report_email(
                            st.session_state["credentials"],
                            all_emails,
                            subject,
                            build_email_html(send_draft),
                            st.session_state.get("user_email", ""),
                        )
                    if result["sent"]:
                        st.success(f"✓ Sent to {len(result['sent'])} address(es): {', '.join(result['sent'])}")
                    if result["failed"]:
                        for fail in result["failed"]:
                            st.error(f"✗ {fail['email']}: {fail['error']}")

            if st.session_state.clients:
                rows = [{"Client": c["name"], "Email": e} for c in st.session_state.clients for e in c["emails"]]
                csv = pd.DataFrame(rows).to_csv(index=False)
                st.download_button(
                    "⬇️  Export Recipients CSV",
                    data=csv,
                    file_name="livepure_recipients.csv",
                    mime="text/csv",
                    use_container_width=True,
                )


# ─── Route pages ──────────────────────────────────────────────────────────────

if page == "📊 Overview":
    render_overview()
elif page == "📧 Email Maker":
    render_email_maker()
