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
        "img2_url": "",
        "img2_caption": "",
        "img3_url": "",
        "img3_caption": "",
        "report_link": "",
        "survey_question": "How would you rate this insights report?",
        "show_preview": False,
        "template": 1,
    }

if "drafts" not in st.session_state:
    st.session_state.drafts = [_blank_draft(i) for i in range(2)]

# Auto-load secrets into session state
if not st.session_state.get("resend_api_key"):
    key = st.secrets.get("RESEND_API_KEY", "")
    if key:
        st.session_state["resend_api_key"] = key

# ─── Global CSS ───────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
header    { visibility: hidden; }

/* ── App shell ── */
.stApp { background: #f8fafc; }
.block-container { padding-top: 1.8rem !important; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] { background: #ffffff !important; }
section[data-testid="stSidebar"] > div { background: #ffffff !important; }
section[data-testid="stSidebar"] label { color: #374151 !important; font-size: 0.86rem !important; font-weight: 500 !important; }
section[data-testid="stSidebar"] p { color: #374151 !important; }
section[data-testid="stSidebar"] span { color: #374151 !important; }
section[data-testid="stSidebar"] .stRadio > div { gap: 2px !important; }
section[data-testid="stSidebar"] .stRadio label {
    padding: 8px 10px !important;
    border-radius: 8px !important;
    transition: background 0.15s !important;
}
section[data-testid="stSidebar"] .stRadio label:has(input:checked) {
    background: #eff6ff !important;
    color: #1d4ed8 !important;
    border-left: 3px solid #2563eb !important;
}
section[data-testid="stSidebar"] hr { border-color: #e2e8f0 !important; }

/* ── Inputs & textareas ── */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    color: #0f172a !important;
    font-size: 0.84rem !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
    border-color: #2563eb !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.08) !important;
}
[data-testid="stSelectbox"] > div > div {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    color: #0f172a !important;
}
[data-testid="stMultiSelect"] > div > div {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    color: #0f172a !important;
}

/* ── Buttons ── */
.stButton > button {
    border-radius: 8px !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.01em !important;
    transition: background 0.12s, border-color 0.12s !important;
    border: none !important;
}
.stButton > button[kind="primary"] {
    background: #2563eb !important;
    color: #fff !important;
}
.stButton > button[kind="primary"]:hover {
    background: #1d4ed8 !important;
}
.stButton > button[kind="secondary"] {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    color: #2563eb !important;
}
.stButton > button[kind="secondary"]:hover {
    background: #f1f5f9 !important;
    color: #1d4ed8 !important;
}

/* ── Download button ── */
[data-testid="stDownloadButton"] button {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    color: #2563eb !important;
    font-size: 0.82rem !important;
}

/* ── Tabs ── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid #e2e8f0 !important;
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
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
}
[data-testid="stExpander"] summary {
    font-size: 0.84rem !important;
    font-weight: 500 !important;
    color: #475569 !important;
}

/* ── Forms ── */
[data-testid="stForm"] {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 10px !important;
}

/* ── Alerts ── */
[data-testid="stAlert"] { border-radius: 10px !important; font-size: 0.84rem !important; }

/* ── Divider ── */
hr { border-color: #e2e8f0 !important; margin: 1.5rem 0 !important; }

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
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 1.1rem 1.2rem 0.9rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

.metric-label {
    font-size: 0.62rem;
    font-weight: 700;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    color: #94a3b8;
    margin-bottom: 0.55rem;
}
.metric-value {
    font-size: 1.75rem;
    font-weight: 700;
    color: #0f172a;
    -webkit-text-fill-color: #0f172a;
    letter-spacing: -0.03em;
    line-height: 1;
    margin-bottom: 0.3rem;
}
.metric-max { font-size: 1rem; color: #94a3b8; -webkit-text-fill-color: #94a3b8; font-weight: 500; letter-spacing: 0; }
.metric-sub { font-size: 0.69rem; color: #64748b; }
.ch-up   { color: #059669; font-weight: 600; }
.ch-down { color: #dc2626; font-weight: 600; }

/* CSAT breakdown */
.csat-section {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 1.2rem 1.5rem;
    display: grid;
    grid-template-columns: 140px 1fr;
    gap: 2rem;
    align-items: center;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.csat-score-side { text-align: center; padding-right: 2rem; border-right: 1px solid #e2e8f0; }
.csat-number { font-size: 2.8rem; font-weight: 700; color: #2563eb; -webkit-text-fill-color: #2563eb; letter-spacing: -0.04em; line-height: 1; }
.csat-stars { color: #f59e0b; font-size: 1rem; margin: 8px 0 5px; letter-spacing: 2px; }
.csat-count { font-size: 0.7rem; color: #94a3b8; }
.bar-row { display: flex; align-items: center; gap: 10px; margin-bottom: 7px; }
.bar-row:last-child { margin-bottom: 0; }
.bar-star  { font-size: 0.67rem; color: #94a3b8; width: 18px; text-align: right; flex-shrink: 0; }
.bar-track { flex: 1; height: 4px; background: #f1f5f9; border-radius: 99px; overflow: hidden; }
.bar-fill  { height: 100%; border-radius: 99px; background: #2563eb; }
.bar-pct   { font-size: 0.67rem; color: #64748b; width: 28px; text-align: right; flex-shrink: 0; }
.bar-count { font-size: 0.64rem; color: #94a3b8; width: 14px; flex-shrink: 0; }
.resp-row { display: flex; align-items: center; gap: 10px; padding: 8px 0; border-bottom: 1px solid #f1f5f9; }
.resp-row:last-child { border-bottom: none; }
.resp-name  { color: #0f172a; font-size: 0.78rem; font-weight: 600; min-width: 130px; }
.resp-email { color: #64748b; font-size: 0.73rem; flex: 1; }
.resp-date  { color: #94a3b8; font-size: 0.68rem; min-width: 50px; text-align: right; }
.resp-stars { color: #f59e0b; font-size: 0.75rem; letter-spacing: 1px; min-width: 70px; text-align: right; }

/* ──────────────────────────────────────────────────────
   PAGE HEADER
────────────────────────────────────────────────────── */

.page-header {
    margin-bottom: 1.5rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid #e2e8f0;
}
.page-title {
    font-size: 1.2rem;
    font-weight: 700;
    color: #0f172a;
    letter-spacing: -0.02em;
}
.page-sub { font-size: 0.82rem; color: #64748b; margin-top: 0.2rem; }

/* ──────────────────────────────────────────────────────
   CLIENT REPOSITORY
────────────────────────────────────────────────────── */

.client-repo-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 16px 18px 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.tag-chip {
    display: inline-block;
    background: #f8fafc;
    color: #475569;
    font-size: 0.61rem;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 4px;
    margin: 2px 2px 0 0;
    border: 1px solid #e2e8f0;
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
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 0.9rem 1.1rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

/* ──────────────────────────────────────────────────────
   EMAIL MAKER
────────────────────────────────────────────────────── */


.draft-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 14px 16px;
    margin-bottom: 10px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.client-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 8px;
}
.client-name { color: #0f172a; font-weight: 600; font-size: 0.88rem; }
.email-pill {
    display: inline-block;
    background: #f0f7ff;
    color: #2563eb;
    font-size: 0.7rem;
    padding: 2px 9px;
    border-radius: 4px;
    margin: 3px 3px 0 0;
    border: 1px solid #bfdbfe;
}

/* ── Section labels ── */
.section-chip {
    display: block;
    font-size: 0.62rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #94a3b8;
    margin-bottom: 12px;
}

/* ── Client avatar ── */
.client-avatar {
    width: 38px; height: 38px;
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.8rem; font-weight: 700;
    flex-shrink: 0;
}

/* ── Template card ── */
.tmpl-card {
    border-radius: 8px;
    padding: 10px 10px 8px;
    margin-bottom: 8px;
    cursor: pointer;
    transition: opacity 0.12s;
}
.tmpl-card:hover { opacity: 0.85; }
</style>
""", unsafe_allow_html=True)

# ─── Login gate ───────────────────────────────────────────────────────────────

def _render_login_page():
    st.markdown("""
    <style>
    .login-wrap {
        max-width: 360px;
        margin: 8vh auto 0;
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 2.4rem 2rem 2rem;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        text-align: center;
    }
    .login-logo {
        width: 40px; height: 40px;
        background: #2563eb;
        border-radius: 8px;
        display: inline-flex; align-items: center; justify-content: center;
        font-size: 0.75rem; font-weight: 700; color: #fff;
        margin-bottom: 1rem;
    }
    .login-title { font-size: 1.1rem; font-weight: 700; color: #0f172a; margin-bottom: 0.2rem; }
    .login-sub   { font-size: 0.8rem; color: #94a3b8; margin-bottom: 1.8rem; }
    </style>
    <div class="login-wrap">
        <div class="login-logo">CDL</div>
        <div class="login-title">Convin Data Labs</div>
        <div class="login-sub">Sign in to continue</div>
    </div>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1.4, 1])
    with col:
        email = st.text_input("Your Email", placeholder="you@gmail.com", key="login_email")
        if st.button("Sign in", type="primary", use_container_width=True, key="login_btn"):
            ok, err = auth.check_login(email)
            if ok:
                st.session_state["logged_in"]  = True
                st.session_state["user_email"] = email.strip().lower()
                st.rerun()
            else:
                st.error(err)

if not st.session_state.get("logged_in"):
    _render_login_page()
    st.stop()

# ─── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style="padding:8px 4px 22px;">
        <div style="display:flex;align-items:center;gap:10px;">
            <div style="width:32px;height:32px;border-radius:8px;flex-shrink:0;background:#2563eb;display:flex;align-items:center;justify-content:center;font-size:0.7rem;font-weight:700;color:#fff;">CDL</div>
            <div>
                <div style="color:#0f172a;font-weight:700;font-size:0.9rem;letter-spacing:-0.01em;line-height:1.2;">Convin Data Labs</div>
                <div style="color:#94a3b8;font-size:0.63rem;margin-top:2px;font-weight:500;letter-spacing:0.04em;text-transform:uppercase;">Analytics</div>
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

    # ── Resend settings ────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown('<div style="color:#64748b;font-size:0.7rem;font-weight:700;letter-spacing:0.07em;text-transform:uppercase;margin-bottom:8px;">Email Sender</div>', unsafe_allow_html=True)
    if st.session_state.get("resend_api_key"):
        st.markdown(
            f'<div style="color:#16a34a;font-size:0.75rem;font-weight:600;margin-bottom:6px;">✓ {st.session_state.get("user_email","")}</div>',
            unsafe_allow_html=True,
        )
        if st.button("Change", key="resend_change_btn", use_container_width=True):
            st.session_state.pop("resend_api_key", None)
            st.rerun()
    else:
        sb_email  = st.text_input("From Email", value=st.session_state.get("user_email",""), placeholder="you@yourcompany.com", key="sb_email", label_visibility="collapsed")
        sb_apikey = st.text_input("Resend API Key", type="password", placeholder="re_xxxxxxxxxxxx", key="sb_resend_key", label_visibility="collapsed")
        st.caption("[Get free API key → resend.com](https://resend.com)")
        if st.button("Connect", key="sb_resend_save", type="primary", use_container_width=True):
            if "@" in sb_email and sb_apikey.strip().startswith("re_"):
                st.session_state["user_email"]    = sb_email.strip().lower()
                st.session_state["resend_api_key"] = sb_apikey.strip()
                st.toast("Email sender connected.", icon="✅")
                st.rerun()
            else:
                st.error("Enter a valid email and Resend API key (starts with re_).")

    st.markdown("---")
    st.markdown('<div style="color:#94a3b8;font-size:0.68rem;font-weight:500;">Feb 2026 · v1.0</div>', unsafe_allow_html=True)

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
    return f"""<div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;">
      <div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;">
        <thead>{hrow}</thead><tbody>{brows}</tbody>
      </table></div></div>"""


# ─── Period content renderer ──────────────────────────────────────────────────

def _render_period_content(period: str):
    data  = ANALYTICS_BY_PERIOD[period]
    csat  = data["csat"]
    score = csat["score"]
    stars = "★" * int(score) + "☆" * (5 - int(score))

    # Pre-filter email rows for drill-down panels
    if period == "Daily":
        email_rows = [r for r in EMAIL_ANALYTICS if r["date"] in DAILY_DATES]
    elif period == "Weekly":
        email_rows = [r for r in EMAIL_ANALYTICS if r["date"] in WEEKLY_DATES]
    else:
        email_rows = EMAIL_ANALYTICS

    opened_rows  = [r for r in email_rows if r["opened"]]
    clicked_rows = [r for r in email_rows if r["clicked"]]

    st.markdown(f"""
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;">
        <div style="color:#0f172a;font-size:0.92rem;font-weight:600;">{data['label']}</div>
        <div style="color:#94a3b8;font-size:0.7rem;font-weight:500;letter-spacing:0.03em;">Updated {data['updated']}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-chip">Key Metrics</div>', unsafe_allow_html=True)
    csat_card = f"""<div class="metric-card accent-amber">
        <div class="metric-label">Report Score</div>
        <div class="metric-value">{score}<span class="metric-max"> / 5</span></div>
        <div class="metric-sub"><span style="color:#f59e0b;letter-spacing:2px;">{stars}</span>&nbsp;·&nbsp;{csat['responses']} ratings</div>
    </div>"""
    row1 = "".join(_metric_card_html(m) for m in data["metrics"][:3]) + csat_card
    row2 = "".join(_metric_card_html(m) for m in data["metrics"][3:])
    st.markdown(f'<div class="analytics-grid">{row1}</div><div class="analytics-grid">{row2}</div>', unsafe_allow_html=True)

    # ── Drill-down: who opened / who clicked ──────────────────────────────────
    col_o, col_c = st.columns(2)

    def _people_rows_html(rows, action_key):
        if not rows:
            return '<div style="color:#94a3b8;font-size:0.78rem;padding:8px 0;">No data for this period.</div>'
        items = "".join(
            f'<div style="display:flex;align-items:center;gap:10px;padding:7px 0;'
            f'border-bottom:1px solid #f1f5f9;">'
            f'<div style="width:8px;height:8px;border-radius:50%;background:#2563eb;flex-shrink:0;"></div>'
            f'<div style="flex:1;min-width:0;">'
            f'<div style="font-size:0.79rem;font-weight:600;color:#0f172a;white-space:nowrap;'
            f'overflow:hidden;text-overflow:ellipsis;">{r["email"]}</div>'
            f'<div style="font-size:0.7rem;color:#64748b;">{r["campaign"]} · {r["date"]}</div>'
            f'</div>'
            f'<div style="font-size:0.68rem;color:#94a3b8;flex-shrink:0;">{r["date"]}</div>'
            f'</div>'
            for r in rows
        )
        return f'<div style="max-height:260px;overflow-y:auto;">{items}</div>'

    with col_o:
        with st.expander(f"👁  Who Opened  ({len(opened_rows)})", expanded=False):
            st.markdown(_people_rows_html(opened_rows, "opened"), unsafe_allow_html=True)

    with col_c:
        with st.expander(f"👆  Who Clicked  ({len(clicked_rows)})", expanded=False):
            st.markdown(_people_rows_html(clicked_rows, "clicked"), unsafe_allow_html=True)

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    bars = "".join(
        f'<div class="bar-row"><span class="bar-star">{r["star"]}★</span>'
        f'<div class="bar-track"><div class="bar-fill" style="width:{r["pct"]}%"></div></div>'
        f'<span class="bar-pct">{r["pct"]}%</span><span class="bar-count">{r["count"]}</span></div>'
        for r in csat["dist"]
    )
    st.markdown('<div class="section-chip">Customer Satisfaction</div>', unsafe_allow_html=True)
    st.markdown(f"""<div class="csat-section">
        <div class="csat-score-side">
            <div style="color:#64748b;font-size:0.62rem;font-weight:700;letter-spacing:0.11em;text-transform:uppercase;margin-bottom:14px;">Report Score</div>
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
    with st.expander(f"👥  View Report Ratings  ({csat['responses']})", expanded=False):
        rows_html = "".join(
            f'<div class="resp-row"><div class="resp-name">{r["name"]}</div>'
            f'<div class="resp-email">{r["email"]}</div>'
            f'<div class="resp-stars">{"★"*r["rating"]}{"☆"*(5-r["rating"])}</div>'
            f'<div class="resp-date">{r["date"]}</div></div>'
            for r in respondents
        )
        st.markdown(f'<div style="padding:4px 2px;">{rows_html}</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    st.markdown('<div class="section-chip">Email Activity</div>', unsafe_allow_html=True)
    st.markdown(f"""<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">
        <div style="color:#0f172a;font-size:0.92rem;font-weight:600;">Email Activity</div>
        <div style="color:#94a3b8;font-size:0.68rem;font-weight:500;">{len(email_rows)} emails</div>
    </div>""", unsafe_allow_html=True)
    st.markdown(_email_table_html(email_rows), unsafe_allow_html=True)

    _render_ai_summary(period, csat, respondents)


# ─── Overview ─────────────────────────────────────────────────────────────────

def render_overview():
    st.markdown("""<div class="page-header">
        <div class="page-title">Overview</div>
        <div class="page-sub">Convin Data Labs · Insights Report Feedback Dashboard</div>
    </div>""", unsafe_allow_html=True)

    tab_d, tab_w, tab_m = st.tabs(["📅  Daily", "📅  Weekly", "📅  Monthly"])
    with tab_d: _render_period_content("Daily")
    with tab_w: _render_period_content("Weekly")
    with tab_m: _render_period_content("Monthly")


# ─── AI Feedback Summariser ───────────────────────────────────────────────────

def _render_ai_summary(period: str, csat_data: dict, respondents: list):
    """Renders the AI Feedback Summary section for a given analytics period."""
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    st.markdown('<div class="section-chip">🤖 AI Feedback Summary</div>', unsafe_allow_html=True)

    ss_key = f"ai_summary_{period}"
    err_key = f"ai_summary_err_{period}"

    if st.session_state.get(ss_key):
        s = st.session_state[ss_key]

        def _card(title, items, bg, border, tc, dot):
            bullets = "".join(
                f'<div style="display:flex;gap:8px;margin-bottom:6px;">'
                f'<span style="color:{dot};font-size:0.85rem;flex-shrink:0;">●</span>'
                f'<span style="font-size:0.8rem;color:{tc};line-height:1.5;">{item}</span></div>'
                for item in items
            )
            return (
                f'<div style="background:{bg};border:1px solid {border};border-radius:8px;'
                f'padding:14px 16px;margin-bottom:12px;">'
                f'<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.08em;'
                f'text-transform:uppercase;color:{dot};margin-bottom:10px;">{title}</div>'
                f'{bullets}</div>'
            )

        sentiment_html = (
            f'<div style="background:#f0f7ff;border:1px solid #e2e8f0;border-radius:8px;'
            f'padding:14px 16px;margin-bottom:12px;">'
            f'<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.08em;'
            f'text-transform:uppercase;color:#0284c7;margin-bottom:8px;">Overall Sentiment</div>'
            f'<div style="font-size:0.84rem;color:#0f172a;line-height:1.6;">{s.get("sentiment","—")}</div>'
            f'</div>'
        )
        themes_html  = _card("Key Themes",           s.get("themes", []),  "#f0fdf4", "#bbf7d0", "#166534", "#16a34a")
        issues_html  = _card("Top Issues",           s.get("issues", []),  "#fff7ed", "#fed7aa", "#9a3412", "#ea580c")
        actions_html = _card("Recommended Actions",  s.get("actions", []), "#eff6ff", "#bfdbfe", "#1e3a5f", "#2563eb")

        st.markdown(sentiment_html + themes_html + issues_html + actions_html, unsafe_allow_html=True)

        col_r, col_c = st.columns([1, 4])
        with col_r:
            if st.button("↺ Regenerate", key=f"ai_regen_{period}", use_container_width=True):
                st.session_state.pop(ss_key, None)
                st.session_state.pop(err_key, None)
                st.rerun()
        return

    if st.session_state.get(err_key):
        st.error(st.session_state[err_key])

    if st.button("✨ Generate AI Summary", key=f"ai_gen_{period}", type="primary"):
        api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            st.session_state[err_key] = "ANTHROPIC_API_KEY not found in secrets."
            st.rerun()
        else:
            dist  = csat_data.get("dist", [])
            score = csat_data.get("score", "N/A")
            total = csat_data.get("responses", 0)
            dist_text = "  ".join(f'{r["star"]}★: {r["count"]} ({r["pct"]}%)' for r in dist)

            from data import ACTION_QUEUE
            comments_text = "\n".join(
                f'- [{item["priority"].split()[0]}] {item["name"]}: "{item["comment"]}"'
                for item in ACTION_QUEUE if item.get("comment")
            ) or "No detailed comments available."

            prompt = (
                f"You are an expert data analytics insights analyst. Stakeholders have rated and reviewed data reports sent by the analytics team. Analyze their feedback and return a JSON object.\n\n"
                f"Report Score: {score}/5 ({total} responses)\n"
                f"Rating breakdown: {dist_text}\n\n"
                f"Stakeholder comments on the reports:\n{comments_text}\n\n"
                f"Return ONLY valid JSON (no markdown, no explanation) with exactly these keys:\n"
                f'{{"sentiment": "1-2 sentence overall sentiment about the insights reports", '
                f'"themes": ["theme 1", "theme 2", "theme 3"], '
                f'"issues": ["issue 1 with the reports", "issue 2", "issue 3"], '
                f'"actions": ["action 1 for the data team", "action 2", "action 3"]}}'
            )

            try:
                import anthropic as _anthropic, json as _json
                _client = _anthropic.Anthropic(api_key=api_key)
                with st.spinner("Analysing feedback with AI…"):
                    _msg = _client.messages.create(
                        model="claude-haiku-4-5-20251001",
                        max_tokens=512,
                        messages=[{"role": "user", "content": prompt}],
                    )
                raw = _msg.content[0].text.strip()
                # Strip markdown code fences if present
                if raw.startswith("```"):
                    raw = raw.split("```")[1]
                    if raw.startswith("json"):
                        raw = raw[4:]
                parsed = _json.loads(raw)
                st.session_state[ss_key] = parsed
                st.session_state.pop(err_key, None)
            except Exception as e:
                st.session_state[err_key] = f"AI error: {e}"
            st.rerun()


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
        # ── Email address management (outside form so delete/add buttons work) ──
        st.markdown(
            '<div style="color:#64748b;font-size:0.72rem;font-weight:700;letter-spacing:0.06em;'
            'text-transform:uppercase;margin:6px 0 6px;">Email Addresses</div>',
            unsafe_allow_html=True,
        )
        current_emails = list(c.get("emails", []))
        for idx, em in enumerate(current_emails):
            ec1, ec2 = st.columns([5, 1])
            with ec1:
                st.markdown(
                    f'<div style="background:#f0f7ff;border:1px solid #e2e8f0;border-radius:6px;'
                    f'padding:6px 10px;font-size:0.78rem;color:#2563eb;">{em}</div>',
                    unsafe_allow_html=True,
                )
            with ec2:
                if st.button("✕", key=f"del_em_{cid}_{idx}", use_container_width=True, help="Remove this email"):
                    client_store.update(cid, {"emails": [e for j, e in enumerate(current_emails) if j != idx]})
                    st.toast(f"Removed {em}", icon="🗑")
                    st.rerun()

        ae1, ae2 = st.columns([5, 1])
        with ae1:
            new_em = st.text_input(
                "new_email", key=f"add_em_{cid}",
                placeholder="Add email address…",
                label_visibility="collapsed",
            )
        with ae2:
            if st.button("＋", key=f"add_em_btn_{cid}", use_container_width=True, help="Add email"):
                if new_em.strip():
                    client_store.update(cid, {"emails": current_emails + [new_em.strip()]})
                    st.toast(f"Added {new_em.strip()}", icon="✅")
                    st.rerun()

        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

        # ── Other fields form ─────────────────────────────────────────────────
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
    st.markdown("""<div class="page-header">
        <div class="page-title">Client Repository</div>
        <div class="page-sub">Manage stakeholders, contacts, tags, and email addresses.</div>
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

_TMPL_TEXT_COLORS = ["#c9a96e", "#2563eb", "#ffffff", "#a78bfa", "#8b5e3c",
                     "#06b6d4", "#ea580c", "#10b981", "#f97316"]
_TMPL_BG_COLORS   = ["#0d1b2a", "#f1f5f9", "#1e3a8a", "#13111f", "#f4ede0",
                     "#040d18", "#fff3e8", "#0b1f14", "#1a1a1a"]


def _single_image_slot(d: dict, url_key: str, cap_key: str, label: str, key_suffix: str):
    """Renders one image upload/paste slot inside an expander."""
    has_img = bool(d.get(url_key, ""))
    with st.expander(f"🖼 {label}{'  ✓' if has_img else '  (optional)'}", expanded=has_img):
        current_url = d.get(url_key, "")
        if current_url.startswith("data:") or (current_url.startswith("http") and current_url):
            st.image(current_url, width=220)
            if st.button("✕ Remove", key=f"rm_{url_key}_{key_suffix}", use_container_width=False):
                d[url_key] = ""
                d[cap_key] = ""
                st.rerun()
        else:
            uploaded = st.file_uploader(
                "Upload", type=["png", "jpg", "jpeg", "gif", "webp"],
                key=f"up_{url_key}_{key_suffix}", label_visibility="collapsed",
            )
            if uploaded:
                b64 = base64.b64encode(uploaded.read()).decode()
                d[url_key] = f"data:{uploaded.type};base64,{b64}"
                st.rerun()
            d[url_key] = st.text_input(
                "Or paste URL", value=current_url,
                key=f"url_{url_key}_{key_suffix}", placeholder="https://…",
                label_visibility="visible",
            )
        d[cap_key] = st.text_input(
            "Caption", value=d.get(cap_key, ""),
            key=f"cap_{url_key}_{key_suffix}", placeholder="Optional caption",
        )


def _screenshot_input(d: dict, key_suffix: str):
    st.markdown(
        '<div style="color:#64748b;font-size:0.75rem;font-weight:700;letter-spacing:0.06em;'
        'text-transform:uppercase;margin:10px 0 6px;">Images</div>',
        unsafe_allow_html=True,
    )
    _single_image_slot(d, "screenshot_url", "screenshot_caption", "Image 1 — Main Screenshot", key_suffix)
    _single_image_slot(d, "img2_url",        "img2_caption",        "Image 2",                   key_suffix)
    _single_image_slot(d, "img3_url",        "img3_caption",        "Image 3",                   key_suffix)


def _template_picker(d: dict, key_suffix: str):
    st.markdown('<div style="color:#64748b;font-size:0.75rem;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;margin-bottom:8px;">Email Template</div>', unsafe_allow_html=True)
    for row_start in range(0, len(TEMPLATE_NAMES), 5):
        row_items = TEMPLATE_NAMES[row_start:row_start + 5]
        cols = st.columns(len(row_items))
        for j, (tname, tdesc, tswatch) in enumerate(row_items):
            ti     = row_start + j
            tid    = ti + 1
            is_sel = d.get("template", 1) == tid
            tc     = _TMPL_TEXT_COLORS[ti]
            border = "#2563eb" if is_sel else "#e2e8f0"
            with cols[j]:
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

    cols = st.columns(2)
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
            tpl_name = TEMPLATE_NAMES[draft.get("template", 1) - 1][0]
            st.markdown(f'<div style="color:#0f172a;font-size:0.88rem;font-weight:600;margin:8px 0;">Preview · {draft["name"]} · {tpl_name}</div>', unsafe_allow_html=True)
            try:
                html_content = build_email_html(draft, draft.get("template", 1))
                components.html(html_content, height=2200, scrolling=True)
            except Exception as e:
                st.error(f"Preview error: {e}")


# ─── Email Maker ──────────────────────────────────────────────────────────────

def render_email_maker():
    st.markdown("""<div class="page-header">
        <div class="page-title">Email Maker</div>
        <div class="page-sub">Compose, preview, and send insights report emails.</div>
    </div>""", unsafe_allow_html=True)

    tab_compose, tab_ai = st.tabs(["📤  Compose & Send", "🤖  AI Check"])

    # ── Compose & Send ────────────────────────────────────────────────────────
    with tab_compose:
        repo_clients = client_store.load()

        # ── Step 1: Draft selector ─────────────────────────────────────────
        st.markdown('<div style="color:#64748b;font-size:0.7rem;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:8px;">① Select Draft</div>', unsafe_allow_html=True)
        draft_names = [d["name"] for d in st.session_state.drafts]
        sc1, sc2 = st.columns([3, 1])
        with sc1:
            chosen = st.selectbox("Draft", draft_names, key="compose_draft_pick", label_visibility="collapsed")
        ci = draft_names.index(chosen)
        d  = st.session_state.drafts[ci]
        tpl_name = TEMPLATE_NAMES[d.get("template", 1) - 1][0]
        st.markdown(f'<div style="color:#94a3b8;font-size:0.7rem;margin-bottom:4px;">Template: {tpl_name}</div>', unsafe_allow_html=True)
        with sc2:
            if st.button("Reset Draft", key=f"compose_reset_{ci}", use_container_width=True):
                st.session_state.drafts[ci] = _blank_draft(ci)
                st.rerun()

        # ── Step 2: Compose (collapsible) ─────────────────────────────────
        st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
        st.markdown('<div style="color:#64748b;font-size:0.7rem;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:8px;">② Compose Email</div>', unsafe_allow_html=True)

        _template_picker(d, f"c{ci}")
        st.markdown("")

        cc1, cc2 = st.columns(2)
        with cc1: d["client"]   = st.text_input("Client Name", value=d["client"],   key=f"cc_client_{ci}", placeholder="e.g. Acme Corp")
        with cc2: d["report_link"] = st.text_input("Report URL", value=d["report_link"], key=f"cc_link_{ci}", placeholder="https://docs.google.com/…")

        d["headline"] = st.text_area("Subject / Headline", value=d["headline"], key=f"cc_head_{ci}", height=70, placeholder="e.g. February showed strong growth…")
        d["body"]     = st.text_area("Email Body",         value=d["body"],     key=f"cc_body_{ci}", height=130, placeholder="Write the main body of the email…")

        with st.expander("🖼  Images & Survey (optional)"):
            _screenshot_input(d, f"c{ci}")
            st.markdown("")
            d["survey_question"] = st.text_input("Survey Question", value=d["survey_question"], key=f"cc_sq_{ci}")

        pc1, pc2, pc3 = st.columns(3)
        with pc1:
            if st.button("💾 Save Draft", key=f"cc_save_{ci}", use_container_width=True):
                st.session_state.drafts[ci]["status"] = "draft"
                st.toast("Draft saved.", icon="💾")
                st.rerun()
        with pc2:
            if st.button("👁 Preview", key=f"cc_prev_{ci}", use_container_width=True):
                st.session_state[f"cc_show_prev_{ci}"] = not st.session_state.get(f"cc_show_prev_{ci}", False)
                st.rerun()
        with pc3:
            if st.button("✅ Mark Ready", key=f"cc_ready_{ci}", use_container_width=True, type="primary"):
                st.session_state.drafts[ci]["status"] = "ready"
                st.toast("Draft marked ready.", icon="✅")
                st.rerun()

        if st.session_state.get(f"cc_show_prev_{ci}", False):
            try:
                components.html(build_email_html(d, d.get("template", 1)), height=2000, scrolling=True)
            except Exception as e:
                st.error(f"Preview error: {e}")

        st.markdown("---")

        # ── Step 3: Recipients ─────────────────────────────────────────────
        st.markdown('<div style="color:#64748b;font-size:0.7rem;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:8px;">③ Recipients</div>', unsafe_allow_html=True)

        if not repo_clients:
            st.info("No clients in repository yet. Go to **🏢 Clients** to add them first.")
        else:
            options = [f"{c['company']}  ({', '.join(c['emails'][:2])}{'…' if len(c['emails'])>2 else ''})" for c in repo_clients]
            selected_opts = st.multiselect(
                "Send to", options, default=options, key="compose_recipients",
                placeholder="Choose clients…",
                label_visibility="collapsed",
            )
            selected_clients = [c for c, opt in zip(repo_clients, options) if opt in selected_opts]
            all_emails = [e for c in selected_clients for e in c.get("emails", [])]

            if all_emails:
                st.markdown(
                    f'<div style="color:#64748b;font-size:0.73rem;margin:6px 0 16px;">'
                    f'{len(selected_clients)} clients · {len(all_emails)} addresses</div>',
                    unsafe_allow_html=True,
                )

            st.markdown("---")

            # ── Step 4: Send ───────────────────────────────────────────────
            st.markdown('<div style="color:#64748b;font-size:0.7rem;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:10px;">④ Send</div>', unsafe_allow_html=True)

            sender_ready = bool(st.session_state.get("resend_api_key"))
            if not sender_ready:
                st.warning("Connect your email sender in the sidebar first.")
            else:
                st.markdown(
                    f'<div style="color:#16a34a;font-size:0.75rem;font-weight:600;margin-bottom:10px;">'
                    f'✓ Sending from: {st.session_state.get("user_email","")}</div>',
                    unsafe_allow_html=True,
                )

            if all_emails:
                if st.button(
                    f"📤  Send to {len(all_emails)} address{'es' if len(all_emails) != 1 else ''}",
                    type="primary", use_container_width=True,
                    disabled=not sender_ready,
                ):
                    subject = d.get("headline", "Report from Convin Data Labs")[:80]
                    with st.spinner(f"Sending to {len(all_emails)} recipient(s)…"):
                        result = gmail_sender.send_report_email(
                            None, all_emails, subject,
                            build_email_html(d, d.get("template", 1)),
                            st.session_state.get("user_email", ""),
                        )
                    if result["sent"]:
                        st.success(f"✓ Sent to: {', '.join(result['sent'])}")
                        st.session_state.drafts[ci]["status"] = "ready"
                    for fail in result["failed"]:
                        if fail["email"] in ("login", "config"):
                            st.error(fail["error"])
                            st.session_state.pop("resend_api_key", None)
                        else:
                            st.error(f"✗ {fail['email']}: {fail['error']}")

    # ── AI Grammar & Spell Check ───────────────────────────────────────────────
    with tab_ai:
        st.markdown('<div style="color:#0f172a;font-size:1rem;font-weight:600;margin-bottom:4px;">AI Writing Assistant</div>', unsafe_allow_html=True)
        st.caption("Fix spelling mistakes and grammar errors in your email drafts using AI.")
        st.markdown("")

        # Source selector
        ai_source = st.radio("Text source:", ["Pick a draft", "Paste custom text"], horizontal=True, key="ai_source")

        if ai_source == "Pick a draft":
            draft_names = [d["name"] for d in st.session_state.drafts]
            ai_draft_name = st.selectbox("Select draft to check:", draft_names, key="ai_draft_pick")
            ai_idx = draft_names.index(ai_draft_name)
            ai_d = st.session_state.drafts[ai_idx]
            ai_text_parts = []
            if ai_d.get("headline"):
                ai_text_parts.append(f"Headline: {ai_d['headline']}")
            if ai_d.get("body"):
                ai_text_parts.append(f"Body: {ai_d['body']}")
            ai_input = "\n\n".join(ai_text_parts) or ""
            st.markdown('<div style="color:#64748b;font-size:0.75rem;margin-bottom:6px;">Text from draft:</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:14px 16px;font-size:0.83rem;color:#475569;white-space:pre-wrap;min-height:60px;">{ai_input or "— draft is empty —"}</div>', unsafe_allow_html=True)
        else:
            ai_input = st.text_area("Paste your text here:", height=160, key="ai_custom_text",
                                    placeholder="Type or paste your headline, body, or any email text…")

        st.markdown("")
        if st.button("✨ Check & Fix Grammar", type="primary", use_container_width=False, key="ai_check_btn"):
            if not ai_input.strip():
                st.warning("Please enter some text to check.")
            else:
                api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
                if not api_key:
                    st.error("ANTHROPIC_API_KEY not found in secrets. Add it to .streamlit/secrets.toml to use AI checking.")
                else:
                    try:
                        import anthropic as _anthropic
                        _client = _anthropic.Anthropic(api_key=api_key)
                        with st.spinner("Checking grammar and spelling…"):
                            _msg = _client.messages.create(
                                model="claude-haiku-4-5-20251001",
                                max_tokens=1024,
                                messages=[{
                                    "role": "user",
                                    "content": (
                                        "You are a professional editor. Fix ALL spelling mistakes and grammar errors "
                                        "in the following text. Keep the meaning, tone, and structure exactly the same. "
                                        "Reply in two clearly labelled sections:\n\n"
                                        "CORRECTED TEXT:\n<the fixed version>\n\n"
                                        "CHANGES MADE:\n<bullet list of what was fixed, or 'No errors found.' if perfect>\n\n"
                                        f"Text to check:\n{ai_input}"
                                    ),
                                }],
                            )
                        _reply = _msg.content[0].text
                        if "CORRECTED TEXT:" in _reply and "CHANGES MADE:" in _reply:
                            _corrected = _reply.split("CORRECTED TEXT:")[1].split("CHANGES MADE:")[0].strip()
                            _changes   = _reply.split("CHANGES MADE:")[1].strip()
                        else:
                            _corrected = _reply
                            _changes   = ""

                        st.markdown('<div style="color:#059669;font-size:0.8rem;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;margin-bottom:8px;">Corrected Text</div>', unsafe_allow_html=True)
                        st.markdown(f'<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:14px 16px;font-size:0.85rem;color:#14532d;white-space:pre-wrap;">{_corrected}</div>', unsafe_allow_html=True)

                        if _changes:
                            st.markdown('<div style="color:#2563eb;font-size:0.8rem;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;margin:14px 0 8px;">Changes Made</div>', unsafe_allow_html=True)
                            st.markdown(f'<div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;padding:14px 16px;font-size:0.83rem;color:#1e3a5f;white-space:pre-wrap;">{_changes}</div>', unsafe_allow_html=True)

                        # Apply to draft option
                        if ai_source == "Pick a draft" and _corrected:
                            st.markdown("")
                            if st.button("Apply corrected text to draft", key="ai_apply_btn"):
                                if ai_d.get("headline") and "Headline:" in ai_input:
                                    _lines = _corrected.split("\n\n")
                                    for _l in _lines:
                                        if _l.startswith("Headline:"):
                                            st.session_state.drafts[ai_idx]["headline"] = _l.replace("Headline:", "").strip()
                                        elif _l.startswith("Body:"):
                                            st.session_state.drafts[ai_idx]["body"] = _l.replace("Body:", "").strip()
                                else:
                                    st.session_state.drafts[ai_idx]["body"] = _corrected
                                st.toast("Draft updated with corrected text.", icon="✅")
                                st.rerun()
                    except Exception as _e:
                        st.error(f"AI check failed: {_e}")


# ─── Route pages ──────────────────────────────────────────────────────────────

if page == "📊 Overview":
    render_overview()
elif page == "🏢 Clients":
    render_clients()
elif page == "📧 Email Maker":
    render_email_maker()
