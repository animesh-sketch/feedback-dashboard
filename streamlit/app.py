import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
from data import CAMPAIGN_ANALYTICS, CSAT_RESPONDENTS
from email_builder import build_email_html
import auth
import gmail_sender

# ─── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Convin Data Labs",
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
        "client": "",
        "headline": "",
        "body": "",
        "screenshot_url": "",
        "screenshot_caption": "",
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
.stApp { background: #050d1a; }
.block-container { padding-top: 2rem !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #070f1e !important;
    border-right: 1px solid #0e2040 !important;
}
[data-testid="stSidebar"] * { color: #4a7aaa !important; }
[data-testid="stSidebar"] .stRadio > div { gap: 2px !important; }
[data-testid="stSidebar"] .stRadio label {
    font-size: 0.84rem !important;
    font-weight: 500 !important;
    padding: 8px 10px !important;
    border-radius: 8px !important;
    transition: background 0.15s !important;
}
[data-testid="stSidebar"] .stRadio label:has(input:checked) {
    background: #0e2040 !important;
    color: #e8f0fe !important;
}

/* ── Inputs & textareas ── */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {
    background: #091525 !important;
    border: 1px solid #0e2040 !important;
    border-radius: 10px !important;
    color: #c8d8f0 !important;
    font-size: 0.84rem !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.15) !important;
}
[data-testid="stSelectbox"] > div > div {
    background: #091525 !important;
    border: 1px solid #0e2040 !important;
    border-radius: 10px !important;
    color: #c8d8f0 !important;
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
    background: linear-gradient(135deg, #1d4ed8 0%, #2563eb 100%) !important;
    color: #fff !important;
    box-shadow: 0 2px 12px rgba(37,99,235,0.3) !important;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 24px rgba(37,99,235,0.5) !important;
}
.stButton > button[kind="secondary"] {
    background: #091525 !important;
    border: 1px solid #0e2040 !important;
    color: #4a7aaa !important;
}
.stButton > button[kind="secondary"]:hover {
    background: #0e2040 !important;
    color: #7aa0d0 !important;
}

/* ── Download button ── */
[data-testid="stDownloadButton"] button {
    background: #091525 !important;
    border: 1px solid #0e2040 !important;
    border-radius: 10px !important;
    color: #4a7aaa !important;
    font-size: 0.82rem !important;
}

/* ── Tabs ── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid #0e2040 !important;
    gap: 0 !important;
    padding: 0 !important;
}
[data-baseweb="tab"] {
    background: transparent !important;
    font-size: 0.83rem !important;
    font-weight: 500 !important;
    color: #4a7aaa !important;
    padding: 10px 22px !important;
    border-bottom: 2px solid transparent !important;
}
[aria-selected="true"][data-baseweb="tab"] {
    color: #e8f0fe !important;
    border-bottom: 2px solid #3b82f6 !important;
}
[data-testid="stTabs"] [data-baseweb="tab-panel"] {
    padding-top: 1.5rem !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    background: #091525 !important;
    border: 1px solid #0e2040 !important;
    border-radius: 12px !important;
}
[data-testid="stExpander"] summary {
    font-size: 0.84rem !important;
    font-weight: 500 !important;
    color: #4a7aaa !important;
}

/* ── Forms ── */
[data-testid="stForm"] {
    background: #091525 !important;
    border: 1px solid #0e2040 !important;
    border-radius: 14px !important;
}

/* ── Alerts ── */
[data-testid="stAlert"] { border-radius: 10px !important; font-size: 0.84rem !important; }

/* ── Divider ── */
hr { border-color: #0e2040 !important; margin: 1.5rem 0 !important; }

/* ── Caption / small text ── */
[data-testid="stCaptionContainer"] p { color: #4a7aaa !important; font-size: 0.77rem !important; }
label { color: #4a7aaa !important; font-size: 0.8rem !important; }

/* ──────────────────────────────────────────────────────
   CAMPAIGN ANALYTICS DASHBOARD
────────────────────────────────────────────────────── */

.analytics-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 12px;
}
.metric-card {
    background: #091525;
    border: 1px solid #0e2040;
    border-radius: 16px;
    padding: 1.2rem 1.35rem 1rem;
    position: relative;
    overflow: hidden;
    transition: transform 0.18s, box-shadow 0.18s;
}
.metric-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 36px rgba(37,99,235,0.18);
    border-color: #1a3560;
}
.metric-card::after {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    border-radius: 16px 16px 0 0;
}
.accent-blue::after   { background: linear-gradient(90deg, #1d4ed8, #3b82f6); }
.accent-green::after  { background: linear-gradient(90deg, #059669, #34d399); }
.accent-amber::after  { background: linear-gradient(90deg, #d97706, #fbbf24); }
.accent-red::after    { background: linear-gradient(90deg, #dc2626, #f87171); }

.metric-label {
    font-size: 0.62rem;
    font-weight: 700;
    letter-spacing: 0.11em;
    text-transform: uppercase;
    color: #4a7aaa;
    margin-bottom: 0.65rem;
}
.metric-value {
    font-size: 1.8rem;
    font-weight: 700;
    color: #e8f0fe;
    letter-spacing: -0.03em;
    line-height: 1;
    margin-bottom: 0.38rem;
}
.metric-max { font-size: 1rem; color: #4a7aaa; font-weight: 500; letter-spacing: 0; }
.metric-sub { font-size: 0.69rem; color: #4a7aaa; }
.ch-up   { color: #34d399; font-weight: 600; }
.ch-down { color: #f87171; font-weight: 600; }

/* CSAT breakdown card */
.csat-section {
    background: #091525;
    border: 1px solid #0e2040;
    border-radius: 16px;
    padding: 1.4rem 1.8rem;
    display: grid;
    grid-template-columns: 150px 1fr;
    gap: 2.5rem;
    align-items: center;
    margin-top: 0;
}
.csat-score-side {
    text-align: center;
    padding-right: 2rem;
    border-right: 1px solid #0e2040;
}
.csat-number {
    font-size: 2.8rem;
    font-weight: 700;
    color: #e8f0fe;
    letter-spacing: -0.04em;
    line-height: 1;
}
.csat-stars { color: #f59e0b; font-size: 1.05rem; margin: 8px 0 5px; letter-spacing: 3px; }
.csat-count { font-size: 0.7rem; color: #4a7aaa; }

.bar-row { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.bar-row:last-child { margin-bottom: 0; }
.bar-star  { font-size: 0.67rem; color: #4a7aaa; width: 18px; text-align: right; flex-shrink: 0; }
.bar-track { flex: 1; height: 5px; background: #0e2040; border-radius: 99px; overflow: hidden; }
.bar-fill  { height: 100%; border-radius: 99px; background: linear-gradient(90deg, #1d4ed8, #3b82f6); }
.bar-pct   { font-size: 0.67rem; color: #4a7aaa; width: 28px; text-align: right; flex-shrink: 0; }
.bar-count { font-size: 0.64rem; color: #1e3a5f; width: 14px; flex-shrink: 0; }

/* Respondent list */
.resp-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 0;
    border-bottom: 1px solid #0e2040;
}
.resp-row:last-child { border-bottom: none; }
.resp-name  { color: #e8f0fe; font-size: 0.78rem; font-weight: 600; min-width: 130px; }
.resp-email { color: #4a7aaa; font-size: 0.73rem; flex: 1; }
.resp-date  { color: #1e3a5f; font-size: 0.68rem; min-width: 50px; text-align: right; }
.resp-stars { color: #f59e0b; font-size: 0.75rem; letter-spacing: 1px; min-width: 70px; text-align: right; }

/* ──────────────────────────────────────────────────────
   OVERVIEW PAGE COMPONENTS
────────────────────────────────────────────────────── */

.hero-banner {
    background: linear-gradient(135deg, #07142a 0%, #091e3a 50%, #060f20 100%);
    border: 1px solid #0e2040;
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
    color: #e8f0fe;
    letter-spacing: -0.025em;
    margin-bottom: 0.3rem;
}
.hero-sub { font-size: 0.83rem; color: #4a7aaa; }
.live-badge {
    background: rgba(16,185,129,0.08);
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
    background: #091525;
    border: 1px solid #0e2040;
    border-radius: 18px;
    padding: 1.3rem 1.4rem 1.1rem;
    position: relative;
    overflow: hidden;
    transition: transform 0.18s ease, box-shadow 0.18s ease;
    cursor: default;
}
.kpi-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 12px 40px rgba(37,99,235,0.2);
    border-color: #1a3560;
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
    color: #4a7aaa;
    margin-bottom: 0.75rem;
}
.kpi-value {
    font-size: 2rem;
    font-weight: 700;
    color: #e8f0fe;
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
.kpi-period { font-size: 0.67rem; color: #1e3a5f; margin-top: 0.1rem; }

/* section divider label */
.sec-label {
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #1e3a5f;
    margin-bottom: 1.2rem;
}

/* ──────────────────────────────────────────────────────
   EMAIL MAKER COMPONENTS
────────────────────────────────────────────────────── */

.em-header {
    background: linear-gradient(135deg, #07142a 0%, #070f20 100%);
    border: 1px solid #0e2040;
    border-radius: 20px;
    padding: 1.6rem 2rem;
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    gap: 1rem;
}
.em-icon { font-size: 1.6rem; line-height: 1; }
.em-title { font-size: 1.2rem; font-weight: 700; color: #e8f0fe; letter-spacing: -0.02em; }
.em-sub   { font-size: 0.8rem; color: #4a7aaa; margin-top: 0.15rem; }

/* Draft status cards */
.draft-card {
    background: #091525;
    border: 1px solid #0e2040;
    border-radius: 16px;
    padding: 16px 18px;
    margin-bottom: 12px;
}

/* Client cards */
.client-card {
    background: #091525;
    border: 1px solid #0e2040;
    border-radius: 12px;
    padding: 14px 18px;
    margin-bottom: 8px;
    transition: border-color 0.15s;
}
.client-card:hover { border-color: #1a3560; }
.client-name { color: #e8f0fe; font-weight: 600; font-size: 0.88rem; }
.email-pill {
    display: inline-block;
    background: #0e2040;
    color: #4a7aaa;
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
        <div style="color:#e8f0fe;font-weight:700;font-size:1rem;letter-spacing:-0.015em;">Convin Data Labs</div>
        <div style="color:#1e3a5f;font-size:0.7rem;margin-top:3px;font-weight:500;letter-spacing:0.04em;text-transform:uppercase;">Analytics</div>
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
    st.markdown('<div style="color:#1e3a5f;font-size:0.68rem;font-weight:500;">Feb 2026 · v1.0</div>', unsafe_allow_html=True)

# ─── Overview ─────────────────────────────────────────────────────────────────

def _accent(m: dict) -> str:
    if not m["up_good"]:
        return "accent-green" if m["value"] == "0.0%" else "accent-red"
    return "accent-green" if m["value"] == "100%" else "accent-blue"


def _metric_card_html(m: dict) -> str:
    sub_parts = []
    if m["sub"]:
        sub_parts.append(f'<span style="color:#1e3a5f;">{m["sub"]}</span>')
    if m["change"] is not None:
        good  = (m["change"] > 0) == m["up_good"]
        cls   = "ch-up" if good else "ch-down"
        arrow = "↑" if m["change"] > 0 else "↓"
        sub_parts.append(f'<span class="{cls}">{arrow} {abs(m["change"]):.1f}%</span>')
    sub_html = (" · ".join(sub_parts)) if sub_parts else "—"
    return f"""
    <div class="metric-card {_accent(m)}">
        <div class="metric-label">{m['label']}</div>
        <div class="metric-value">{m['value']}</div>
        <div class="metric-sub">{sub_html}</div>
    </div>"""


def render_overview():
    data = CAMPAIGN_ANALYTICS
    csat = data["csat"]

    # ── Hero ──────────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="hero-banner">
        <div>
            <div class="hero-title">Good morning, Animesh 👋</div>
            <div class="hero-sub">Convin Data Labs · Campaign Analytics Dashboard</div>
        </div>
        <div class="live-badge">● Live</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Section header ────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;">
        <div style="color:#e8f0fe;font-size:0.92rem;font-weight:600;">{data['label']}</div>
        <div style="color:#1e3a5f;font-size:0.7rem;font-weight:500;letter-spacing:0.03em;">
            Updated {data['updated']}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Row 1: Sent · Open · Click to Open · CSAT ─────────────────────────────
    score      = csat["score"]
    full_stars = int(score)
    stars_html = "★" * full_stars + "☆" * (5 - full_stars)
    csat_card  = f"""
    <div class="metric-card accent-amber">
        <div class="metric-label">CSAT Score</div>
        <div class="metric-value">{score}<span class="metric-max"> / 5</span></div>
        <div class="metric-sub">
            <span style="color:#f59e0b;letter-spacing:2px;">{stars_html}</span>
            &nbsp;·&nbsp;{csat['responses']} ratings
        </div>
    </div>"""

    row1 = "".join(_metric_card_html(m) for m in data["metrics"][:3]) + csat_card

    # ── Row 2: Delivered · Bounce · Unsubscribe · Blocked ─────────────────────
    row2 = "".join(_metric_card_html(m) for m in data["metrics"][3:])

    st.markdown(
        f'<div class="analytics-grid">{row1}</div>'
        f'<div class="analytics-grid">{row2}</div>',
        unsafe_allow_html=True,
    )

    # ── CSAT Breakdown ────────────────────────────────────────────────────────
    bars_html = "".join(
        f"""<div class="bar-row">
            <span class="bar-star">{r['star']}★</span>
            <div class="bar-track"><div class="bar-fill" style="width:{r['pct']}%"></div></div>
            <span class="bar-pct">{r['pct']}%</span>
            <span class="bar-count">{r['count']}</span>
        </div>"""
        for r in csat["dist"]
    )

    st.markdown(f"""
    <div class="csat-section">
        <div class="csat-score-side">
            <div style="color:#4a7aaa;font-size:0.62rem;font-weight:700;letter-spacing:0.11em;
                        text-transform:uppercase;margin-bottom:14px;">CSAT</div>
            <div class="csat-number">{score}<span style="font-size:1.1rem;color:#4a7aaa;
                font-weight:500;">/5</span></div>
            <div class="csat-stars">{stars_html}</div>
            <div class="csat-count">{csat['responses']} ratings</div>
        </div>
        <div>
            <div style="color:#4a7aaa;font-size:0.62rem;font-weight:700;letter-spacing:0.11em;
                        text-transform:uppercase;margin-bottom:14px;">Rating Distribution</div>
            {bars_html}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── CSAT Respondents ──────────────────────────────────────────────────────
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    with st.expander(f"👥  View Responses  ({csat['responses']})", expanded=False):
        rows_html = "".join(
            f"""<div class="resp-row">
                <div class="resp-name">{r['name']}</div>
                <div class="resp-email">{r['email']}</div>
                <div class="resp-stars">{"★" * r['rating']}{"☆" * (5 - r['rating'])}</div>
                <div class="resp-date">{r['date']}</div>
            </div>"""
            for r in CSAT_RESPONDENTS
        )
        st.markdown(
            f'<div style="padding:4px 2px;">{rows_html}</div>',
            unsafe_allow_html=True,
        )

# ─── Draft helpers ────────────────────────────────────────────────────────────

STATUS_META = {
    "empty": ("#0e2040", "#4a7aaa", "Empty"),
    "draft": ("#0d2515", "#6ee7b7", "In Progress"),
    "ready": ("#0a1535", "#60a5fa", "Ready"),
}

def render_drafts_tab():
    st.markdown('<div style="color:#e8f0fe;font-size:1rem;font-weight:600;margin-bottom:4px;">Drafts</div>', unsafe_allow_html=True)
    st.caption("Up to 3 email drafts — edit, preview, and send independently.")
    st.markdown("")

    cols = st.columns(3)
    for i, (col, draft) in enumerate(zip(cols, st.session_state.drafts)):
        bg, fg, lbl = STATUS_META[draft["status"]]
        with col:
            st.markdown(
                f"""<div class="draft-card">
                    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:5px;">
                        <span style="color:#e8f0fe;font-weight:600;font-size:0.88rem;">{draft['name']}</span>
                        <span style="background:{bg};color:{fg};font-size:0.6rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;padding:3px 9px;border-radius:99px;">{lbl}</span>
                    </div>
                    <div style="color:#1e3a5f;font-size:0.72rem;">{draft['client'] or 'No client set'}</div>
                </div>""",
                unsafe_allow_html=True,
            )

            with st.expander("✏️ Edit Draft", expanded=draft["status"] == "empty"):
                d = st.session_state.drafts[i]
                d["name"]     = st.text_input("Draft Name", value=d["name"],     key=f"dname_{i}")
                d["client"]   = st.text_input("Client",     value=d["client"],   key=f"dclient_{i}", placeholder="e.g. Acme Corp")
                d["headline"] = st.text_area("Headline",    value=d["headline"], key=f"dhead_{i}",   height=80,  placeholder="e.g. February showed strong growth…")
                d["body"]     = st.text_area("Email Body",  value=d["body"],     key=f"dbody_{i}",   height=120, placeholder="Write the main body of the email…")

                st.markdown('<div style="color:#4a7aaa;font-size:0.75rem;font-weight:600;margin:10px 0 4px;">Screenshot</div>', unsafe_allow_html=True)
                d["screenshot_url"]     = st.text_input("Image URL",  value=d["screenshot_url"],     key=f"ssu_{i}", placeholder="https://…")
                d["screenshot_caption"] = st.text_input("Caption",    value=d["screenshot_caption"], key=f"ssc_{i}", placeholder="Optional caption")

                st.markdown('<div style="color:#4a7aaa;font-size:0.75rem;font-weight:600;margin:10px 0 4px;">Links</div>', unsafe_allow_html=True)
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
            components.html(build_email_html(draft), height=1400, scrolling=True)


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
        st.markdown('<div style="color:#e8f0fe;font-size:1rem;font-weight:600;margin-bottom:4px;">Edit Email Body</div>', unsafe_allow_html=True)
        st.caption("Select a draft and fill in the fields below.")

        draft_names = [d["name"] for d in st.session_state.drafts]
        chosen = st.radio("Editing:", draft_names, horizontal=True, key="editor_draft_pick")
        ei = draft_names.index(chosen)
        d  = st.session_state.drafts[ei]
        st.markdown("---")

        cc1, cc2 = st.columns(2)
        with cc1: d["name"]   = st.text_input("Draft Name", value=d["name"],   key=f"ed_name_{ei}")
        with cc2: d["client"] = st.text_input("Client",     value=d["client"], key=f"ed_client_{ei}", placeholder="Acme Corp")

        st.markdown("")
        d["headline"] = st.text_area("Headline", value=d["headline"], key=f"ed_head_{ei}", height=80, placeholder="e.g. February showed strong growth with one risk area.")
        d["body"]     = st.text_area("Email Body", value=d["body"],   key=f"ed_body_{ei}", height=160, placeholder="Write the main body of the email…")

        st.markdown("---")
        st.markdown('<div style="color:#4a7aaa;font-size:0.78rem;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;margin-bottom:10px;">Screenshot</div>', unsafe_allow_html=True)
        su1, su2 = st.columns([3, 2])
        with su1: d["screenshot_url"]     = st.text_input("Image URL", value=d["screenshot_url"],     key=f"ed_ssu_{ei}", placeholder="https://…")
        with su2: d["screenshot_caption"] = st.text_input("Caption",   value=d["screenshot_caption"], key=f"ed_ssc_{ei}", placeholder="Optional")

        st.markdown("---")
        st.markdown('<div style="color:#4a7aaa;font-size:0.78rem;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;margin-bottom:10px;">Links & Survey</div>', unsafe_allow_html=True)
        lc1, lc2 = st.columns(2)
        with lc1: d["report_link"]     = st.text_input("Full Report URL",  value=d["report_link"],     key=f"ed_link_{ei}", placeholder="https://docs.google.com/…")
        with lc2: d["survey_question"] = st.text_input("Survey Question",  value=d["survey_question"], key=f"ed_sq_{ei}")

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
            components.html(build_email_html(d), height=1400, scrolling=True)

    # ── Email Preview ─────────────────────────────────────────────────────────
    with tab_preview:
        st.markdown('<div style="color:#e8f0fe;font-size:1rem;font-weight:600;margin-bottom:4px;">Email Preview</div>', unsafe_allow_html=True)
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
        st.markdown('<div style="color:#e8f0fe;font-size:1rem;font-weight:600;margin-bottom:4px;">Recipients</div>', unsafe_allow_html=True)
        st.caption("Add clients and their email addresses. One client can have up to 5 emails.")

        with st.expander("➕  Add New Client", expanded=len(st.session_state.clients) == 0):
            with st.form("add_client_form", clear_on_submit=True):
                client_name = st.text_input("Client / Company", placeholder="e.g. Acme Corp")
                st.markdown('<div style="color:#4a7aaa;font-size:0.78rem;font-weight:600;margin:10px 0 6px;">Email Addresses — up to 5</div>', unsafe_allow_html=True)
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
                '<div style="text-align:center;padding:48px 20px;color:#1e3a5f;font-size:0.84rem;">No clients yet — add one above.</div>',
                unsafe_allow_html=True,
            )
        else:
            total_emails = sum(len(c["emails"]) for c in st.session_state.clients)
            st.markdown(
                f'<div style="color:#4a7aaa;font-size:0.75rem;font-weight:600;margin-bottom:14px;">'
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
                    '<div style="background:#091525;border:1px solid #0e2040;border-radius:14px;'
                    'padding:18px;text-align:center;color:#4a7aaa;font-size:0.82rem;">'
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
                    file_name="convin_recipients.csv",
                    mime="text/csv",
                    use_container_width=True,
                )


# ─── Route pages ──────────────────────────────────────────────────────────────

if page == "📊 Overview":
    render_overview()
elif page == "📧 Email Maker":
    render_email_maker()
