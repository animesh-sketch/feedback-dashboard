import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import base64
from data import ANALYTICS_BY_PERIOD, EMAIL_ANALYTICS, CSAT_RESPONDENTS, DAILY_DATES, WEEKLY_DATES
from email_builder import build_email_html, TEMPLATE_NAMES
import client_store
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
        "template": 1,
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
.stApp { background: #f0f5ff; }
.block-container { padding-top: 2rem !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #1a3468 !important;
    border-right: none !important;
}
[data-testid="stSidebar"] * { color: #bfdbfe !important; }
[data-testid="stSidebar"] .stRadio > div { gap: 2px !important; }
[data-testid="stSidebar"] .stRadio label {
    font-size: 0.84rem !important;
    font-weight: 500 !important;
    padding: 8px 10px !important;
    border-radius: 8px !important;
    transition: background 0.15s !important;
}
[data-testid="stSidebar"] .stRadio label:has(input:checked) {
    background: rgba(255,255,255,0.12) !important;
    color: #ffffff !important;
    border-left: 3px solid #93c5fd !important;
}

/* ── Inputs & textareas ── */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {
    background: #ffffff !important;
    border: 1px solid #dde8ff !important;
    border-radius: 10px !important;
    color: #0f172a !important;
    font-size: 0.84rem !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
    border-color: #2563eb !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.1) !important;
}
[data-testid="stSelectbox"] > div > div {
    background: #ffffff !important;
    border: 1px solid #dde8ff !important;
    border-radius: 10px !important;
    color: #0f172a !important;
}
[data-testid="stMultiSelect"] > div > div {
    background: #ffffff !important;
    border: 1px solid #dde8ff !important;
    border-radius: 10px !important;
    color: #0f172a !important;
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
    box-shadow: 0 2px 12px rgba(37,99,235,0.25) !important;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-2px) scale(1.02) !important;
    box-shadow: 0 8px 28px rgba(37,99,235,0.4), 0 0 0 1px rgba(59,130,246,0.3) !important;
}
.stButton > button[kind="secondary"] {
    background: #ffffff !important;
    border: 1px solid #dde8ff !important;
    color: #2563eb !important;
}
.stButton > button[kind="secondary"]:hover {
    background: #f0f5ff !important;
    border-color: #93c5fd !important;
    color: #1d4ed8 !important;
}

/* ── Download button ── */
[data-testid="stDownloadButton"] button {
    background: #ffffff !important;
    border: 1px solid #dde8ff !important;
    border-radius: 10px !important;
    color: #2563eb !important;
    font-size: 0.82rem !important;
}

/* ── Tabs ── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid #dde8ff !important;
    gap: 0 !important;
    padding: 0 !important;
}
[data-baseweb="tab"] {
    background: transparent !important;
    font-size: 0.83rem !important;
    font-weight: 500 !important;
    color: #64748b !important;
    padding: 10px 22px !important;
    border-bottom: 2px solid transparent !important;
}
[aria-selected="true"][data-baseweb="tab"] {
    color: #1d4ed8 !important;
    border-bottom: 2px solid #2563eb !important;
}
[data-testid="stTabs"] [data-baseweb="tab-panel"] {
    padding-top: 1.5rem !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    background: #ffffff !important;
    border: 1px solid #dde8ff !important;
    border-radius: 12px !important;
}
[data-testid="stExpander"] summary {
    font-size: 0.84rem !important;
    font-weight: 500 !important;
    color: #475569 !important;
}

/* ── Forms ── */
[data-testid="stForm"] {
    background: #ffffff !important;
    border: 1px solid #dde8ff !important;
    border-radius: 14px !important;
}

/* ── Alerts ── */
[data-testid="stAlert"] { border-radius: 10px !important; font-size: 0.84rem !important; }

/* ── Divider ── */
hr { border-color: #dde8ff !important; margin: 1.5rem 0 !important; }

/* ── Caption / small text ── */
[data-testid="stCaptionContainer"] p { color: #64748b !important; font-size: 0.77rem !important; }
label { color: #475569 !important; font-size: 0.8rem !important; }

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
    background: #ffffff;
    border: 1px solid #dde8ff;
    border-radius: 16px;
    padding: 1.2rem 1.35rem 1rem;
    position: relative;
    overflow: hidden;
    transition: transform 0.18s, box-shadow 0.18s;
    box-shadow: 0 1px 8px rgba(37,99,235,0.06);
}
.metric-card:hover {
    transform: translateY(-4px) scale(1.01);
    box-shadow: 0 14px 40px rgba(37,99,235,0.14), 0 0 0 1px rgba(59,130,246,0.15);
    border-color: rgba(59,130,246,0.3);
    transition: all 0.35s cubic-bezier(0.34,1.56,0.64,1);
}
.metric-card::after {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    border-radius: 16px 16px 0 0;
}
.accent-blue::after   { background: linear-gradient(90deg, #1d4ed8, #60a5fa, #93c5fd); }
.accent-green::after  { background: linear-gradient(90deg, #059669, #34d399, #6ee7b7); }
.accent-amber::after  { background: linear-gradient(90deg, #d97706, #fbbf24, #fde68a); }
.accent-red::after    { background: linear-gradient(90deg, #dc2626, #f87171, #fca5a5); }

.metric-label {
    font-size: 0.62rem;
    font-weight: 700;
    letter-spacing: 0.11em;
    text-transform: uppercase;
    color: #94a3b8;
    margin-bottom: 0.65rem;
}
.metric-value {
    font-size: 1.8rem;
    font-weight: 800;
    color: #0f172a;
    -webkit-text-fill-color: #0f172a;
    letter-spacing: -0.03em;
    line-height: 1;
    margin-bottom: 0.38rem;
}
.metric-max { font-size: 1rem; color: #94a3b8; -webkit-text-fill-color: #94a3b8; font-weight: 500; letter-spacing: 0; }
.metric-sub { font-size: 0.69rem; color: #64748b; }
.ch-up   { color: #059669; font-weight: 600; }
.ch-down { color: #dc2626; font-weight: 600; }

/* CSAT breakdown */
.csat-section {
    background: #ffffff;
    border: 1px solid #dde8ff;
    border-radius: 16px;
    padding: 1.4rem 1.8rem;
    display: grid;
    grid-template-columns: 150px 1fr;
    gap: 2.5rem;
    align-items: center;
    box-shadow: 0 1px 8px rgba(37,99,235,0.05);
}
.csat-score-side { text-align: center; padding-right: 2rem; border-right: 1px solid #dde8ff; }
.csat-number { font-size: 3rem; font-weight: 800; color: #1d4ed8; -webkit-text-fill-color: #1d4ed8; letter-spacing: -0.04em; line-height: 1; }
.csat-stars { color: #f59e0b; font-size: 1.05rem; margin: 8px 0 5px; letter-spacing: 3px; }
.csat-count { font-size: 0.7rem; color: #94a3b8; }
.bar-row { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.bar-row:last-child { margin-bottom: 0; }
.bar-star  { font-size: 0.67rem; color: #94a3b8; width: 18px; text-align: right; flex-shrink: 0; }
.bar-track { flex: 1; height: 5px; background: #e8f0fe; border-radius: 99px; overflow: hidden; }
.bar-fill  { height: 100%; border-radius: 99px; background: linear-gradient(90deg, #1d4ed8, #3b82f6); }
.bar-pct   { font-size: 0.67rem; color: #64748b; width: 28px; text-align: right; flex-shrink: 0; }
.bar-count { font-size: 0.64rem; color: #94a3b8; width: 14px; flex-shrink: 0; }
.resp-row { display: flex; align-items: center; gap: 10px; padding: 8px 0; border-bottom: 1px solid #e8f0fe; }
.resp-row:last-child { border-bottom: none; }
.resp-name  { color: #0f172a; font-size: 0.78rem; font-weight: 600; min-width: 130px; }
.resp-email { color: #64748b; font-size: 0.73rem; flex: 1; }
.resp-date  { color: #94a3b8; font-size: 0.68rem; min-width: 50px; text-align: right; }
.resp-stars { color: #f59e0b; font-size: 0.75rem; letter-spacing: 1px; min-width: 70px; text-align: right; }

/* ──────────────────────────────────────────────────────
   PAGE HERO / HEADER
────────────────────────────────────────────────────── */

.hero-banner {
    background: linear-gradient(135deg, #1e3a8a 0%, #1d4ed8 55%, #2563eb 100%);
    border: none;
    border-radius: 24px;
    padding: 2rem 2.2rem;
    margin-bottom: 1.8rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: relative;
    overflow: hidden;
    box-shadow: 0 8px 40px rgba(29,78,216,0.22);
}
.hero-banner::before {
    content: '';
    position: absolute;
    top: -80px; right: -60px;
    width: 320px; height: 320px;
    background: radial-gradient(circle, rgba(255,255,255,0.12) 0%, transparent 70%);
    pointer-events: none;
}
.hero-banner::after {
    content: '';
    position: absolute;
    bottom: -100px; left: 25%;
    width: 250px; height: 250px;
    background: radial-gradient(circle, rgba(255,255,255,0.07) 0%, transparent 70%);
    pointer-events: none;
}
.hero-title {
    font-size: 1.45rem; font-weight: 800;
    color: #ffffff;
    -webkit-text-fill-color: #ffffff;
    letter-spacing: -0.025em; margin-bottom: 0.3rem;
    position: relative; z-index: 1;
}
.hero-sub   { font-size: 0.83rem; color: rgba(255,255,255,0.7); position: relative; z-index: 1; }
.live-badge {
    background: rgba(255,255,255,0.15);
    border: 1px solid rgba(255,255,255,0.3);
    color: #ffffff;
    font-size: 0.7rem; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase;
    padding: 6px 14px; border-radius: 99px; white-space: nowrap;
    position: relative; z-index: 1;
}
.live-dot { display: inline-block; animation: pulse-dot 2s ease-in-out infinite; }

/* ──────────────────────────────────────────────────────
   CLIENT REPOSITORY
────────────────────────────────────────────────────── */

.client-repo-card {
    background: #ffffff;
    border: 1px solid #dde8ff;
    border-radius: 18px;
    padding: 18px 20px 14px;
    transition: all 0.3s cubic-bezier(0.34,1.56,0.64,1);
    height: 100%;
    box-shadow: 0 1px 6px rgba(37,99,235,0.05);
}
.client-repo-card:hover {
    border-color: rgba(59,130,246,0.4);
    box-shadow: 0 10px 36px rgba(37,99,235,0.12);
    transform: translateY(-2px);
}
.tag-chip {
    display: inline-block;
    background: #eff6ff;
    color: #2563eb;
    font-size: 0.61rem;
    font-weight: 600;
    padding: 2px 9px;
    border-radius: 99px;
    margin: 2px 2px 0 0;
    border: 1px solid #bfdbfe;
}

/* Stats grid */
.stats-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
    margin-bottom: 1.5rem;
}
.stat-card {
    background: #ffffff;
    border: 1px solid #dde8ff;
    border-radius: 14px;
    padding: 1rem 1.2rem;
    box-shadow: 0 1px 4px rgba(37,99,235,0.04);
    transition: all 0.25s ease;
}
.stat-card:hover {
    border-color: rgba(59,130,246,0.25) !important;
    box-shadow: 0 6px 20px rgba(37,99,235,0.09) !important;
}

/* ──────────────────────────────────────────────────────
   EMAIL MAKER
────────────────────────────────────────────────────── */

.em-header {
    background: linear-gradient(135deg, #1e3a8a 0%, #1d4ed8 100%);
    border: none;
    border-radius: 20px;
    padding: 1.6rem 2rem;
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    gap: 1rem;
    box-shadow: 0 6px 30px rgba(29,78,216,0.2);
    position: relative;
    overflow: hidden;
}
.em-header::before {
    content: '';
    position: absolute;
    top: -50px; right: -30px;
    width: 200px; height: 200px;
    background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
    pointer-events: none;
}
.em-icon  { font-size: 1.6rem; line-height: 1; }
.em-title { font-size: 1.2rem; font-weight: 700; color: #ffffff; -webkit-text-fill-color: #ffffff; letter-spacing: -0.02em; }
.em-sub   { font-size: 0.8rem; color: rgba(255,255,255,0.7); -webkit-text-fill-color: rgba(255,255,255,0.7); margin-top: 0.15rem; }

.draft-card {
    background: #ffffff;
    border: 1px solid #dde8ff;
    border-radius: 16px;
    padding: 16px 18px;
    margin-bottom: 12px;
    box-shadow: 0 1px 6px rgba(37,99,235,0.05);
    transition: border-color 0.25s ease, box-shadow 0.25s ease;
}
.draft-card:hover { border-color: rgba(59,130,246,0.3) !important; box-shadow: 0 4px 20px rgba(37,99,235,0.09) !important; }
.client-card {
    background: #ffffff;
    border: 1px solid #dde8ff;
    border-radius: 12px;
    padding: 14px 18px;
    margin-bottom: 8px;
    transition: border-color 0.15s;
}
.client-card:hover { border-color: #93c5fd; }
.client-name { color: #0f172a; font-weight: 600; font-size: 0.88rem; }
.email-pill {
    display: inline-block;
    background: #eff6ff;
    color: #2563eb;
    font-size: 0.7rem;
    padding: 3px 10px;
    border-radius: 99px;
    margin: 3px 3px 0 0;
    border: 1px solid #bfdbfe;
}

/* ── Keyframe animations ── */
@keyframes pulse-dot {
    0%, 100% { opacity: 1; transform: scale(1); }
    50%       { opacity: 0.6; transform: scale(0.82); }
}

/* ── Section chips ── */
.section-chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    color: #1d4ed8;
    font-size: 0.61rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    padding: 4px 12px;
    border-radius: 99px;
    margin-bottom: 14px;
}
.section-chip::before {
    content: '';
    width: 5px; height: 5px;
    background: #2563eb;
    border-radius: 50%;
}

/* ── Client avatar ── */
.client-avatar {
    width: 42px; height: 42px;
    border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.85rem; font-weight: 800;
    flex-shrink: 0;
    letter-spacing: -0.02em;
}

/* ── Template card ── */
.tmpl-card {
    border-radius: 12px;
    padding: 10px 10px 8px;
    margin-bottom: 8px;
    cursor: pointer;
    transition: transform 0.25s cubic-bezier(0.34,1.56,0.64,1), box-shadow 0.25s ease;
}
.tmpl-card:hover {
    transform: translateY(-3px) scale(1.04);
    box-shadow: 0 8px 24px rgba(37,99,235,0.15);
}
</style>
""", unsafe_allow_html=True)

# ─── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style="padding:8px 4px 22px;">
        <div style="display:flex;align-items:center;gap:11px;">
            <div style="
                width:36px;height:36px;border-radius:10px;flex-shrink:0;
                background:linear-gradient(135deg,#1d4ed8,#3b82f6);
                display:flex;align-items:center;justify-content:center;
                font-size:0.72rem;font-weight:800;color:#fff;letter-spacing:-0.01em;
                box-shadow:0 4px 14px rgba(59,130,246,0.5);
            ">CDL</div>
            <div>
                <div style="color:#dbeafe;font-weight:700;font-size:0.93rem;letter-spacing:-0.015em;line-height:1.2;">Convin Data Labs</div>
                <div style="color:#93c5fd;font-size:0.63rem;margin-top:2px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;">Analytics</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    page = st.radio(
        "nav",
        ["📊 Overview", "🏢 Clients", "📧 Email Maker"],
        label_visibility="collapsed",
    )

    st.markdown("---")
    auth.render_login_sidebar()
    st.markdown("---")
    st.markdown('<div style="color:#7aa0d0;font-size:0.68rem;font-weight:500;">Feb 2026 · v1.0</div>', unsafe_allow_html=True)

# ─── Analytics helpers ────────────────────────────────────────────────────────

def _accent(m: dict) -> str:
    if not m["up_good"]:
        return "accent-green" if m["value"] == "0.0%" else "accent-red"
    return "accent-green" if m["value"] == "100%" else "accent-blue"


def _metric_card_html(m: dict) -> str:
    sub_parts = []
    if m["sub"]:
        sub_parts.append(f'<span style="color:#94a3b8;">{m["sub"]}</span>')
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


def _email_table_html(rows: list) -> str:
    if not rows:
        return '<div style="text-align:center;padding:32px;color:#94a3b8;font-size:0.84rem;">No email activity for this period.</div>'

    def dbadge(v):
        return '<span style="color:#22c55e;font-weight:700;">✓</span>' if v else '<span style="color:#f87171;font-weight:700;">✗</span>'
    def sbadge(v):
        return '<span style="color:#3b82f6;font-weight:600;">✓</span>' if v else '<span style="color:#94a3b8;">—</span>'
    def scbadge(s):
        if s is None:
            return '<span style="color:#94a3b8;">—</span>'
        c = {1:"#f87171",2:"#fb923c",3:"#fbbf24",4:"#34d399",5:"#22c55e"}
        return f'<span style="color:{c[s]};font-weight:700;">{s}★</span>'

    th = 'style="color:#64748b;font-size:0.58rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;padding:10px 12px;text-align:left;white-space:nowrap;background:#f8faff;"'
    tc = 'style="font-size:0.73rem;padding:9px 12px;border-bottom:1px solid #e8f0fe;text-align:center;"'
    headers = ["Email", "DL Report Name", "Del", "Open", "Click", "Resp", "Score", "Date"]
    hrow = f'<tr>{"".join(f"<th {th}>{h}</th>" for h in headers)}</tr>'
    brows = "".join(
        f"""<tr>
          <td style="font-size:0.72rem;padding:9px 12px;border-bottom:1px solid #e8f0fe;color:#0f172a;">{r['email']}</td>
          <td style="font-size:0.67rem;padding:9px 12px;border-bottom:1px solid #e8f0fe;color:#64748b;white-space:nowrap;">{r['campaign']}</td>
          <td {tc}>{dbadge(r['delivered'])}</td>
          <td {tc}>{sbadge(r['opened'])}</td>
          <td {tc}>{sbadge(r['clicked'])}</td>
          <td {tc}>{sbadge(r['responded'])}</td>
          <td {tc}>{scbadge(r['score'])}</td>
          <td style="font-size:0.67rem;padding:9px 12px;border-bottom:1px solid #e8f0fe;color:#94a3b8;text-align:right;">{r['date']}</td>
        </tr>"""
        for r in rows
    )
    return f"""<div style="background:#ffffff;border:1px solid #dde8ff;border-radius:16px;overflow:hidden;">
      <div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;">
        <thead>{hrow}</thead><tbody>{brows}</tbody>
      </table></div></div>"""


# ─── Period content renderer ──────────────────────────────────────────────────

def _render_period_content(period: str):
    data  = ANALYTICS_BY_PERIOD[period]
    csat  = data["csat"]
    score = csat["score"]
    stars = "★" * int(score) + "☆" * (5 - int(score))

    st.markdown(f"""
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;">
        <div style="color:#0f172a;font-size:0.92rem;font-weight:600;">{data['label']}</div>
        <div style="color:#94a3b8;font-size:0.7rem;font-weight:500;letter-spacing:0.03em;">Updated {data['updated']}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-chip">Key Metrics</div>', unsafe_allow_html=True)
    csat_card = f"""<div class="metric-card accent-amber">
        <div class="metric-label">CSAT Score</div>
        <div class="metric-value">{score}<span class="metric-max"> / 5</span></div>
        <div class="metric-sub"><span style="color:#f59e0b;letter-spacing:2px;">{stars}</span>&nbsp;·&nbsp;{csat['responses']} ratings</div>
    </div>"""
    row1 = "".join(_metric_card_html(m) for m in data["metrics"][:3]) + csat_card
    row2 = "".join(_metric_card_html(m) for m in data["metrics"][3:])
    st.markdown(f'<div class="analytics-grid">{row1}</div><div class="analytics-grid">{row2}</div>', unsafe_allow_html=True)

    bars = "".join(
        f'<div class="bar-row"><span class="bar-star">{r["star"]}★</span>'
        f'<div class="bar-track"><div class="bar-fill" style="width:{r["pct"]}%"></div></div>'
        f'<span class="bar-pct">{r["pct"]}%</span><span class="bar-count">{r["count"]}</span></div>'
        for r in csat["dist"]
    )
    st.markdown('<div class="section-chip">Customer Satisfaction</div>', unsafe_allow_html=True)
    st.markdown(f"""<div class="csat-section">
        <div class="csat-score-side">
            <div style="color:#64748b;font-size:0.62rem;font-weight:700;letter-spacing:0.11em;text-transform:uppercase;margin-bottom:14px;">CSAT</div>
            <div class="csat-number">{score}<span style="font-size:1.1rem;color:#64748b;font-weight:500;-webkit-text-fill-color:#64748b;">/5</span></div>
            <div class="csat-stars">{stars}</div>
            <div class="csat-count">{csat['responses']} ratings</div>
        </div>
        <div>
            <div style="color:#64748b;font-size:0.62rem;font-weight:700;letter-spacing:0.11em;text-transform:uppercase;margin-bottom:14px;">Rating Distribution</div>
            {bars}
        </div>
    </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    respondents = CSAT_RESPONDENTS[:csat["responses"]]
    with st.expander(f"👥  View Responses  ({csat['responses']})", expanded=False):
        rows_html = "".join(
            f'<div class="resp-row"><div class="resp-name">{r["name"]}</div>'
            f'<div class="resp-email">{r["email"]}</div>'
            f'<div class="resp-stars">{"★"*r["rating"]}{"☆"*(5-r["rating"])}</div>'
            f'<div class="resp-date">{r["date"]}</div></div>'
            for r in respondents
        )
        st.markdown(f'<div style="padding:4px 2px;">{rows_html}</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    if period == "Daily":
        email_rows = [r for r in EMAIL_ANALYTICS if r["date"] in DAILY_DATES]
    elif period == "Weekly":
        email_rows = [r for r in EMAIL_ANALYTICS if r["date"] in WEEKLY_DATES]
    else:
        email_rows = EMAIL_ANALYTICS

    st.markdown('<div class="section-chip">Email Activity</div>', unsafe_allow_html=True)
    st.markdown(f"""<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">
        <div style="color:#0f172a;font-size:0.92rem;font-weight:600;">Email Activity</div>
        <div style="color:#94a3b8;font-size:0.68rem;font-weight:500;">{len(email_rows)} emails</div>
    </div>""", unsafe_allow_html=True)
    st.markdown(_email_table_html(email_rows), unsafe_allow_html=True)


# ─── Overview ─────────────────────────────────────────────────────────────────

def render_overview():
    st.markdown("""<div class="hero-banner">
        <div>
            <div class="hero-title">Good morning, Animesh 👋</div>
            <div class="hero-sub">Convin Data Labs · Campaign Analytics Dashboard</div>
        </div>
        <div class="live-badge"><span class="live-dot">●</span> Live</div>
    </div>""", unsafe_allow_html=True)

    tab_d, tab_w, tab_m = st.tabs(["📅  Daily", "📅  Weekly", "📅  Monthly"])
    with tab_d: _render_period_content("Daily")
    with tab_w: _render_period_content("Weekly")
    with tab_m: _render_period_content("Monthly")


# ─── Clients ──────────────────────────────────────────────────────────────────

_STATUS_CFG = {
    "Active":   ("#dcfce7", "#16a34a", "#059669"),
    "At Risk":  ("#fef9c3", "#d97706", "#f59e0b"),
    "Inactive": ("#f1f5f9", "#64748b", "#94a3b8"),
}

_AVATAR_GRADS = [
    ("linear-gradient(135deg,#1d4ed8,#3b82f6)", "#fff"),
    ("linear-gradient(135deg,#059669,#34d399)", "#fff"),
    ("linear-gradient(135deg,#7c3aed,#a78bfa)", "#fff"),
    ("linear-gradient(135deg,#d97706,#fbbf24)", "#fff"),
    ("linear-gradient(135deg,#0284c7,#38bdf8)", "#fff"),
    ("linear-gradient(135deg,#db2777,#f472b6)", "#fff"),
]


def _avatar(company: str) -> str:
    words = [w for w in company.split() if w]
    if len(words) >= 2:
        initials = (words[0][0] + words[1][0]).upper()
    elif words:
        initials = words[0][:2].upper()
    else:
        initials = "??"
    grad, color = _AVATAR_GRADS[abs(hash(company)) % len(_AVATAR_GRADS)]
    return (f'<div class="client-avatar" style="background:{grad};color:{color};">'
            f'{initials}</div>')


def _render_client_card(c: dict):
    cid    = c["id"]
    status = c.get("status", "Active")
    sbg, sfg, sline = _STATUS_CFG.get(status, _STATUS_CFG["Active"])

    email_pills = " ".join(f'<span class="email-pill">{e}</span>' for e in c.get("emails", []))
    tag_chips   = " ".join(f'<span class="tag-chip">{t}</span>'   for t in c.get("tags",   []))
    notes_raw   = c.get("notes", "")
    notes_html  = f'<div style="color:#94a3b8;font-size:0.7rem;line-height:1.5;margin-bottom:8px;">{notes_raw[:80]}{"…" if len(notes_raw)>80 else ""}</div>' if notes_raw else ""
    contact_html = f'<div style="color:#64748b;font-size:0.75rem;margin-bottom:8px;">👤 {c["contact"]}</div>' if c.get("contact") else ""
    tags_html    = f'<div style="margin-bottom:8px;">{tag_chips}</div>' if tag_chips else ""

    avatar_html = _avatar(c.get("company", ""))
    st.markdown(
        f'<div class="client-repo-card" style="border-top:2px solid {sline};">'
        f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;">'
        f'{avatar_html}'
        f'<div style="flex:1;min-width:0;">'
        f'<div style="display:flex;align-items:flex-start;justify-content:space-between;gap:8px;">'
        f'<div style="color:#0f172a;font-weight:700;font-size:0.95rem;line-height:1.3;">{c.get("company","")}</div>'
        f'<span style="background:{sbg};color:{sfg};font-size:0.58rem;font-weight:700;letter-spacing:0.1em;'
        f'text-transform:uppercase;padding:3px 9px;border-radius:99px;white-space:nowrap;">{status}</span>'
        f'</div></div></div>{contact_html}'
        f'<div style="margin-bottom:8px;">{email_pills}</div>'
        f'{tags_html}{notes_html}'
        f'<div style="color:#94a3b8;font-size:0.61rem;margin-top:4px;">Added {c.get("added_at","—")}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    bc1, bc2 = st.columns(2)
    with bc1:
        lbl = "✕ Close" if st.session_state.get(f"editing_{cid}") else "✏️ Edit"
        if st.button(lbl, key=f"edit_c_{cid}", use_container_width=True):
            st.session_state[f"editing_{cid}"] = not st.session_state.get(f"editing_{cid}", False)
            st.rerun()
    with bc2:
        if st.button("🗑 Remove", key=f"del_c_{cid}", use_container_width=True):
            client_store.delete(cid)
            st.session_state.pop(f"editing_{cid}", None)
            st.toast(f"Removed {c.get('company','client')}", icon="🗑")
            st.rerun()

    if st.session_state.get(f"editing_{cid}"):
        with st.form(f"edit_f_{cid}"):
            ec1, ec2 = st.columns(2)
            with ec1:
                new_company = st.text_input("Company",   value=c.get("company",""))
                new_contact = st.text_input("Contact",   value=c.get("contact",""))
            with ec2:
                new_status  = st.selectbox("Status",     client_store.STATUSES,
                                           index=client_store.STATUSES.index(c.get("status","Active")))
                new_tags    = st.text_input("Tags",       value=", ".join(c.get("tags",[])),
                                           placeholder="Enterprise, Q1, High Priority")
            new_notes = st.text_area("Notes", value=c.get("notes",""), height=68)

            fs1, fs2 = st.columns(2)
            with fs1:
                save_clicked = st.form_submit_button("Save Changes", type="primary", use_container_width=True)
            with fs2:
                cancel_clicked = st.form_submit_button("Cancel", use_container_width=True)

            if save_clicked:
                client_store.update(cid, {
                    "company": new_company.strip(),
                    "contact": new_contact.strip(),
                    "status":  new_status,
                    "tags":    [t.strip() for t in new_tags.split(",") if t.strip()],
                    "notes":   new_notes.strip(),
                })
                st.session_state.pop(f"editing_{cid}", None)
                st.toast("Client updated.", icon="✅")
                st.rerun()
            if cancel_clicked:
                st.session_state.pop(f"editing_{cid}", None)
                st.rerun()

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)


def render_clients():
    all_clients = client_store.load()

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown("""<div class="em-header">
        <div class="em-icon">🏢</div>
        <div>
            <div class="em-title">Client Repository</div>
            <div class="em-sub">Manage clients, contacts, tags, and email addresses.</div>
        </div>
    </div>""", unsafe_allow_html=True)

    # ── Stats bar ─────────────────────────────────────────────────────────────
    active_n   = sum(1 for c in all_clients if c.get("status") == "Active")
    at_risk_n  = sum(1 for c in all_clients if c.get("status") == "At Risk")
    inactive_n = sum(1 for c in all_clients if c.get("status") == "Inactive")
    total_em   = sum(len(c.get("emails", [])) for c in all_clients)

    st.markdown(f"""<div class="stats-grid">
        <div class="stat-card">
            <div style="color:#64748b;font-size:0.6rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">Total Clients</div>
            <div style="color:#0f172a;font-size:1.8rem;font-weight:700;letter-spacing:-0.03em;">{len(all_clients)}</div>
        </div>
        <div class="stat-card" style="border-top:2px solid #059669;">
            <div style="color:#64748b;font-size:0.6rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">Active</div>
            <div style="color:#34d399;font-size:1.8rem;font-weight:700;">{active_n}</div>
        </div>
        <div class="stat-card" style="border-top:2px solid #d97706;">
            <div style="color:#64748b;font-size:0.6rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">At Risk</div>
            <div style="color:#fbbf24;font-size:1.8rem;font-weight:700;">{at_risk_n}</div>
        </div>
        <div class="stat-card">
            <div style="color:#64748b;font-size:0.6rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">Email Addresses</div>
            <div style="color:#0f172a;font-size:1.8rem;font-weight:700;">{total_em}</div>
        </div>
    </div>""", unsafe_allow_html=True)

    # ── Add New Client ────────────────────────────────────────────────────────
    with st.expander("➕  Add New Client", expanded=len(all_clients) == 0):
        with st.form("add_client_repo", clear_on_submit=True):
            fc1, fc2, fc3 = st.columns([2, 2, 1])
            with fc1: company = st.text_input("Company Name *", placeholder="e.g. Acme Corp")
            with fc2: contact = st.text_input("Contact Person",  placeholder="e.g. John Smith")
            with fc3: status  = st.selectbox("Status", client_store.STATUSES)

            tags_raw = st.text_input("Tags", placeholder="Enterprise, Q1, High Priority (comma-separated)")

            st.markdown('<div style="color:#64748b;font-size:0.75rem;font-weight:600;margin:10px 0 6px;">Email Addresses (up to 5)</div>', unsafe_allow_html=True)
            ec1, ec2 = st.columns(2)
            with ec1:
                e1 = st.text_input("Email 1 *", placeholder="primary@company.com")
                e2 = st.text_input("Email 2",   placeholder="manager@company.com")
                e3 = st.text_input("Email 3",   placeholder="cfo@company.com")
            with ec2:
                e4 = st.text_input("Email 4",   placeholder="analyst@company.com")
                e5 = st.text_input("Email 5",   placeholder="optional@company.com")

            notes = st.text_area("Notes", placeholder="Client context, renewal dates, preferences…", height=72)

            if st.form_submit_button("Add to Repository", type="primary", use_container_width=True):
                if not company.strip():
                    st.warning("Company name is required.")
                else:
                    emails = [e for e in [e1, e2, e3, e4, e5] if e.strip()]
                    if not emails:
                        st.warning("At least one email address is required.")
                    else:
                        tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
                        client_store.add(company.strip(), contact.strip(), emails, status, tags, notes.strip())
                        st.toast(f"✓ {company} added to repository.", icon="🏢")
                        st.rerun()

    st.markdown("---")

    # ── Search + Filter ───────────────────────────────────────────────────────
    sc1, sc2 = st.columns([3, 1])
    with sc1:
        search = st.text_input("", placeholder="🔍  Search by company, contact, or email…", label_visibility="collapsed", key="client_search")
    with sc2:
        filter_status = st.selectbox("", ["All Statuses"] + client_store.STATUSES, label_visibility="collapsed", key="client_filter")

    filtered = all_clients
    if search:
        q = search.lower()
        filtered = [c for c in filtered if
                    q in c.get("company","").lower() or
                    q in c.get("contact","").lower() or
                    any(q in e.lower() for e in c.get("emails",[]))]
    if filter_status != "All Statuses":
        filtered = [c for c in filtered if c.get("status") == filter_status]

    # ── Client Cards Grid ─────────────────────────────────────────────────────
    if not filtered:
        st.markdown('<div style="text-align:center;padding:60px 20px;color:#94a3b8;font-size:0.84rem;">No clients found. Add one above.</div>', unsafe_allow_html=True)
        return

    st.markdown(f'<div style="color:#64748b;font-size:0.75rem;font-weight:600;margin-bottom:14px;">{len(filtered)} client{"s" if len(filtered)!=1 else ""}</div>', unsafe_allow_html=True)

    for i in range(0, len(filtered), 3):
        cols = st.columns(3)
        for j, c in enumerate(filtered[i:i+3]):
            with cols[j]:
                _render_client_card(c)

    # ── Export ────────────────────────────────────────────────────────────────
    if all_clients:
        st.markdown("---")
        rows = [{"Company": c.get("company",""), "Contact": c.get("contact",""),
                 "Email": e, "Status": c.get("status",""), "Tags": ", ".join(c.get("tags",[])),
                 "Added": c.get("added_at","")}
                for c in all_clients for e in c.get("emails",[])]
        csv = pd.DataFrame(rows).to_csv(index=False)
        st.download_button("⬇️  Export Client CSV", data=csv,
                           file_name="convin_clients.csv", mime="text/csv",
                           use_container_width=False)


# ─── Draft helpers ────────────────────────────────────────────────────────────

STATUS_META = {
    "empty": ("#f1f5f9", "#94a3b8", "Empty"),
    "draft": ("#dcfce7", "#16a34a", "In Progress"),
    "ready": ("#eff6ff", "#2563eb", "Ready"),
}

_TMPL_TEXT_COLORS = ["#c9a96e", "#2563eb", "#ffffff", "#a78bfa", "#8b5e3c"]
_TMPL_BG_COLORS   = ["#0d1b2a", "#f1f5f9", "#1e3a8a", "#13111f", "#f4ede0"]


def _screenshot_input(d: dict, key_suffix: str):
    st.markdown('<div style="color:#64748b;font-size:0.75rem;font-weight:600;margin:10px 0 6px;">Screenshot</div>', unsafe_allow_html=True)

    # Show preview + remove button if an image is already stored
    if d.get("screenshot_url", "").startswith("data:"):
        st.image(d["screenshot_url"], width=220)
        if st.button("✕ Remove image", key=f"rm_img_{key_suffix}"):
            d["screenshot_url"] = ""
            st.rerun()
    else:
        uploaded = st.file_uploader(
            "Upload image", type=["png", "jpg", "jpeg", "gif", "webp"],
            key=f"upload_{key_suffix}", label_visibility="collapsed",
        )
        if uploaded:
            b64 = base64.b64encode(uploaded.read()).decode()
            d["screenshot_url"] = f"data:{uploaded.type};base64,{b64}"
            st.rerun()

        d["screenshot_url"] = st.text_input(
            "Or paste image URL", value=d.get("screenshot_url", ""),
            key=f"ssu_{key_suffix}", placeholder="https://…",
        )

    d["screenshot_caption"] = st.text_input(
        "Caption", value=d.get("screenshot_caption", ""),
        key=f"ssc_{key_suffix}", placeholder="Optional caption",
    )


def _template_picker(d: dict, key_suffix: str):
    st.markdown('<div style="color:#64748b;font-size:0.75rem;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;margin-bottom:8px;">Email Template</div>', unsafe_allow_html=True)
    cols = st.columns(5)
    for ti, (tname, tdesc, tswatch) in enumerate(TEMPLATE_NAMES):
        tid    = ti + 1
        is_sel = d.get("template", 1) == tid
        tc     = _TMPL_TEXT_COLORS[ti]
        border = "#2563eb" if is_sel else "#dde8ff"
        with cols[ti]:
            st.markdown(
                f'<div class="tmpl-card" style="background:{tswatch};border:2px solid {border};">'
                f'<div style="color:{tc};font-size:0.68rem;font-weight:700;letter-spacing:0.04em;">{tname}</div>'
                f'<div style="color:{tc};font-size:0.57rem;opacity:0.6;margin-top:3px;">{tdesc[:16]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button("✓" if is_sel else "Use", key=f"tmpl_{key_suffix}_{ti}",
                         use_container_width=True, type="primary" if is_sel else "secondary"):
                d["template"] = tid
                st.rerun()


def render_drafts_tab():
    st.markdown('<div style="color:#0f172a;font-size:1rem;font-weight:600;margin-bottom:4px;">Drafts</div>', unsafe_allow_html=True)
    st.caption("Up to 3 email drafts — edit, preview, and send independently.")
    st.markdown("")

    cols = st.columns(3)
    for i, (col, draft) in enumerate(zip(cols, st.session_state.drafts)):
        bg, fg, lbl = STATUS_META[draft["status"]]
        tname = TEMPLATE_NAMES[draft.get("template", 1) - 1][0]
        with col:
            st.markdown(
                f'<div class="draft-card">'
                f'<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:5px;">'
                f'<span style="color:#0f172a;font-weight:600;font-size:0.88rem;">{draft["name"]}</span>'
                f'<span style="background:{bg};color:{fg};font-size:0.6rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;padding:3px 9px;border-radius:99px;">{lbl}</span>'
                f'</div>'
                f'<div style="color:#94a3b8;font-size:0.72rem;">{draft["client"] or "No client set"}</div>'
                f'<div style="color:#94a3b8;font-size:0.65rem;margin-top:3px;">Template: {tname}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            with st.expander("✏️ Edit Draft", expanded=draft["status"] == "empty"):
                d = st.session_state.drafts[i]
                _template_picker(d, f"d{i}")
                st.markdown("")
                d["name"]     = st.text_input("Draft Name", value=d["name"],     key=f"dname_{i}")
                d["client"]   = st.text_input("Client",     value=d["client"],   key=f"dclient_{i}", placeholder="e.g. Acme Corp")
                d["headline"] = st.text_area("Headline",    value=d["headline"], key=f"dhead_{i}",   height=80,  placeholder="e.g. February showed strong growth…")
                d["body"]     = st.text_area("Email Body",  value=d["body"],     key=f"dbody_{i}",   height=120, placeholder="Write the main body of the email…")

                _screenshot_input(d, f"d{i}")

                st.markdown('<div style="color:#64748b;font-size:0.75rem;font-weight:600;margin:10px 0 4px;">Links</div>', unsafe_allow_html=True)
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
                st.session_state.drafts[i]["show_preview"] = not draft.get("show_preview", False)
                st.rerun()
            if draft["status"] != "empty":
                if st.button("Reset", key=f"reset_{i}", use_container_width=True):
                    st.session_state.drafts[i] = _blank_draft(i)
                    st.rerun()

    for i, draft in enumerate(st.session_state.drafts):
        if draft.get("show_preview"):
            st.markdown("---")
            st.markdown(f"#### Preview — {draft['name']}  ·  {TEMPLATE_NAMES[draft.get('template',1)-1][0]}")
            components.html(build_email_html(draft, draft.get("template", 1)), height=1400, scrolling=True)


# ─── Email Maker ──────────────────────────────────────────────────────────────

def render_email_maker():
    st.markdown("""<div class="em-header">
        <div class="em-icon">📧</div>
        <div>
            <div class="em-title">Email Maker</div>
            <div class="em-sub">Build report emails and send to clients via Gmail.</div>
        </div>
    </div>""", unsafe_allow_html=True)

    tab_drafts, tab_editor, tab_recipients = st.tabs(
        ["✏️  Drafts", "📝  Edit Body", "📤  Send"]
    )

    # ── Drafts ────────────────────────────────────────────────────────────────
    with tab_drafts:
        render_drafts_tab()

    # ── Edit Body ─────────────────────────────────────────────────────────────
    with tab_editor:
        st.markdown('<div style="color:#0f172a;font-size:1rem;font-weight:600;margin-bottom:4px;">Edit Email Body</div>', unsafe_allow_html=True)
        st.caption("Select a draft and fill in the fields below.")

        draft_names = [d["name"] for d in st.session_state.drafts]
        chosen = st.radio("Editing:", draft_names, horizontal=True, key="editor_draft_pick")
        ei = draft_names.index(chosen)
        d  = st.session_state.drafts[ei]
        st.markdown("---")

        _template_picker(d, f"e{ei}")
        st.markdown("")

        cc1, cc2 = st.columns(2)
        with cc1: d["name"]   = st.text_input("Draft Name", value=d["name"],   key=f"ed_name_{ei}")
        with cc2: d["client"] = st.text_input("Client",     value=d["client"], key=f"ed_client_{ei}", placeholder="Acme Corp")

        d["headline"] = st.text_area("Headline",   value=d["headline"], key=f"ed_head_{ei}", height=80,  placeholder="e.g. February showed strong growth with one risk area.")
        d["body"]     = st.text_area("Email Body", value=d["body"],     key=f"ed_body_{ei}", height=160, placeholder="Write the main body of the email…")

        st.markdown("---")
        _screenshot_input(d, f"e{ei}")

        st.markdown("---")
        st.markdown('<div style="color:#64748b;font-size:0.78rem;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;margin-bottom:10px;">Links & Survey</div>', unsafe_allow_html=True)
        lc1, lc2 = st.columns(2)
        with lc1: d["report_link"]     = st.text_input("Full Report URL", value=d["report_link"],     key=f"ed_link_{ei}", placeholder="https://docs.google.com/…")
        with lc2: d["survey_question"] = st.text_input("Survey Question", value=d["survey_question"], key=f"ed_sq_{ei}")

        st.markdown("---")
        bc1, bc2 = st.columns(2)
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

    # ── Send ──────────────────────────────────────────────────────────────────
    with tab_recipients:
        st.markdown('<div style="color:#0f172a;font-size:1rem;font-weight:600;margin-bottom:4px;">Send Report</div>', unsafe_allow_html=True)
        st.caption("Select recipients from the Client Repository and send a draft.")

        repo_clients = client_store.load()

        if not repo_clients:
            st.markdown(
                '<div style="background:#ffffff;border:1px solid #dde8ff;border-radius:14px;padding:24px;'
                'text-align:center;color:#64748b;font-size:0.84rem;">'
                '🏢 No clients in repository yet.<br>'
                '<span style="font-size:0.76rem;color:#94a3b8;">Go to <strong style="color:#64748b;">🏢 Clients</strong> in the sidebar to add clients first.</span>'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            # Draft selector
            draft_names = [d["name"] for d in st.session_state.drafts]
            send_draft_name = st.selectbox("Which draft to send?", draft_names, key="send_draft_pick")
            send_draft = st.session_state.drafts[draft_names.index(send_draft_name)]
            tpl_name = TEMPLATE_NAMES[send_draft.get("template",1)-1][0]
            st.markdown(f'<div style="color:#94a3b8;font-size:0.7rem;margin-bottom:16px;">Template: <span style="color:#64748b;">{tpl_name}</span></div>', unsafe_allow_html=True)

            # Recipient multiselect from repository
            options = [f"{c['company']}  ({', '.join(c['emails'][:2])}{'…' if len(c['emails'])>2 else ''})" for c in repo_clients]
            selected_opts = st.multiselect("Select recipients", options, default=options, key="recipients_select",
                                           placeholder="Choose clients to include…")
            selected_clients = [c for c, opt in zip(repo_clients, options) if opt in selected_opts]
            all_emails = [e for c in selected_clients for e in c.get("emails", [])]

            if selected_clients:
                # Preview recipient list
                pills = " ".join(
                    f'<span class="email-pill">{c["company"]}: {len(c["emails"])} addr</span>'
                    for c in selected_clients
                )
                st.markdown(f'<div style="margin:10px 0 16px;">{pills}</div>', unsafe_allow_html=True)
                st.markdown(f'<div style="color:#64748b;font-size:0.73rem;margin-bottom:16px;">{len(selected_clients)} clients · {len(all_emails)} email addresses total</div>', unsafe_allow_html=True)

            if not st.session_state.get("credentials"):
                st.markdown(
                    '<div style="background:#ffffff;border:1px solid #dde8ff;border-radius:14px;'
                    'padding:18px;text-align:center;color:#64748b;font-size:0.82rem;">'
                    '🔒 Sign in with Google (sidebar) to send emails</div>',
                    unsafe_allow_html=True,
                )
            elif all_emails:
                if st.button(f"📤  Send to {len(all_emails)} address(es)", type="primary", use_container_width=True):
                    subject = send_draft.get("headline", "Report from Convin Data Labs")[:80]
                    with st.spinner(f"Sending to {len(all_emails)} recipient(s)…"):
                        result = gmail_sender.send_report_email(
                            st.session_state["credentials"],
                            all_emails,
                            subject,
                            build_email_html(send_draft, send_draft.get("template", 1)),
                            st.session_state.get("user_email", ""),
                        )
                    if result["sent"]:
                        st.success(f"✓ Sent to {len(result['sent'])} address(es): {', '.join(result['sent'])}")
                    if result["failed"]:
                        for fail in result["failed"]:
                            st.error(f"✗ {fail['email']}: {fail['error']}")

        # Export all repo clients as CSV
        if repo_clients:
            st.markdown("---")
            rows = [{"Company": c.get("company",""), "Email": e, "Status": c.get("status","")}
                    for c in repo_clients for e in c.get("emails",[])]
            csv = pd.DataFrame(rows).to_csv(index=False)
            st.download_button("⬇️  Export Recipients CSV", data=csv,
                               file_name="convin_recipients.csv", mime="text/csv",
                               use_container_width=True)


# ─── Route pages ──────────────────────────────────────────────────────────────

if page == "📊 Overview":
    render_overview()
elif page == "🏢 Clients":
    render_clients()
elif page == "📧 Email Maker":
    render_email_maker()
