import sys
import os
import base64 as _b64_logo
sys.path.insert(0, os.path.dirname(__file__))
# v2026.03.25
from datetime import datetime, timezone

# ─── Brand logo (base64 PNG) ──────────────────────────────────────────────────
def _logo_img(size: int = 34, br: int = 8) -> str:
    """Return an <img> tag for the Convin logo at the given size."""
    _logo_path = os.path.join(os.path.dirname(__file__), "convin_logo.png")
    try:
        with open(_logo_path, "rb") as _f:
            _b64 = _b64_logo.b64encode(_f.read()).decode()
        return (f'<img src="data:image/png;base64,{_b64}" '
                f'width="{size}" height="{size}" '
                f'style="border-radius:{br}px;display:block;flex-shrink:0;" />')
    except Exception:
        return f'<div style="width:{size}px;height:{size}px;border-radius:{br}px;background:linear-gradient(135deg,#0B1F3A,#2563EB);display:flex;align-items:center;justify-content:center;font-size:0.6rem;font-weight:900;color:#fff;">CDL</div>'

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import streamlit.components.v1 as components
import base64
import io
from PIL import Image
from data import format_kpi, format_delta, delta_is_positive, KPIMetric
from email_builder import build_email_html, TEMPLATE_NAMES
import client_store
import sent_store
import client_emails_store
import auth
import gmail_sender
import tracking_store
import audit_store
import param_store

# ─── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Convin Data Labs",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── Session state defaults ───────────────────────────────────────────────────

def _blank_draft(idx: int) -> dict:
    return {
        "name": f"Draft {idx + 1}",
        "status": "empty",
        "client": "",
        "subject": "",
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
        "attachment_name": "",
        "attachment_data": "",   # base64-encoded bytes for MIME attachment
        "attachment_mime": "",
        "attachment_url": "",    # URL alternative (shown as Download button in email)
        "scoreboard_enabled": False,
        "scoreboard_title":   "Performance Scoreboard",
        "scoreboard_rows":    [],
        "sb_rows":            [],
    }

if "drafts" not in st.session_state:
    st.session_state.drafts = [_blank_draft(i) for i in range(3)]
# Ensure at least 3 drafts always exist
while len(st.session_state.drafts) < 3:
    st.session_state.drafts.append(_blank_draft(len(st.session_state.drafts)))

if "send_log" not in st.session_state:
    st.session_state.send_log = []

if "current_page" not in st.session_state:
    st.session_state["current_page"] = "Overview"

if "app_mode" not in st.session_state:
    st.session_state["app_mode"] = "Home"

if "show_sidebar" not in st.session_state:
    st.session_state["show_sidebar"] = False

_FONT_SIZE_MAP   = {"Small (13px)": "13px", "Normal (14px)": None, "Large (16px)": "16px", "X-Large (18px)": "18px"}
_FONT_FAMILY_MAP = {"Default (Inter)": None, "Serif (Georgia)": "Georgia,serif", "Classic (Times New Roman)": "'Times New Roman',serif", "Clean (Arial)": "Arial,sans-serif"}

def _email_font_kwargs():
    return {
        "font_size":   _FONT_SIZE_MAP.get(st.session_state.get("email_font_size_pick",   "Normal (14px)")),
        "font_family": _FONT_FAMILY_MAP.get(st.session_state.get("email_font_family_pick", "Default (Inter)")),
    }

# Auto-load Gmail credentials from secrets — only on the very first load,
# NOT on every rerun (so the sidebar "Change" button actually works).
if "gmail_secrets_loaded" not in st.session_state:
    st.session_state["gmail_secrets_loaded"] = True
    if not st.session_state.get("gmail_app_password"):
        pw = st.secrets.get("GMAIL_APP_PASSWORD", "")
        if pw:
            st.session_state["gmail_app_password"] = pw
    if not st.session_state.get("user_email"):
        sender = st.secrets.get("GMAIL_SENDER", "")
        if sender:
            st.session_state["user_email"] = sender

# ─── Feedback landing page (from email star links) ────────────────────────────

_rating_param = st.query_params.get("rating")
if _rating_param:
    try:
        _r = max(1, min(5, int(_rating_param)))
    except (ValueError, TypeError):
        _r = 0
    if _r:
        # Log rating event if tracking params present
        _rating_id = st.query_params.get("id", "")
        _rating_em = st.query_params.get("em", "")
        if _rating_id and _rating_em:
            try:
                import base64 as _b64r
                _rating_email = _b64r.b64decode(_rating_em.encode()).decode("utf-8", errors="replace")
                tracking_store.log_rating(_rating_id, _rating_email, _r)
                tracking_store.log_event(_rating_id, _rating_email, "open")
            except Exception:
                pass
        _stars_filled = "★" * _r + "☆" * (5 - _r)
        st.markdown(f"""
<style>
html, body, [class*="css"] {{ font-family: 'Inter', -apple-system, sans-serif; }}
#MainMenu {{ visibility: hidden; }} footer {{ visibility: hidden; }} header {{ visibility: hidden; }}
.stApp {{ background: #040d1e !important; }}
</style>
<div style="min-height:100vh;display:flex;align-items:center;justify-content:center;padding:40px 16px;">
  <div style="background:#071428;border-radius:24px;padding:56px 48px;max-width:460px;width:100%;
              text-align:center;box-shadow:0 0 60px rgba(37,99,235,0.3),0 4px 32px rgba(0,0,0,0.6);border:1px solid rgba(37,99,235,0.2);">
    <div style="font-size:52px;margin-bottom:20px;">✅</div>
    <div style="font-size:12px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;
                background:linear-gradient(135deg,#0B1F3A,#2563EB);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;margin-bottom:12px;">Feedback received</div>
    <div style="font-size:26px;font-weight:700;color:#e8f0fc;margin-bottom:10px;">Thank you!</div>
    <div style="font-size:15px;color:#6699cc;line-height:1.65;margin-bottom:28px;">
      You rated this report <strong style="color:#e0ecf8;">{_r} out of 5 stars</strong>.<br>
      Your feedback helps us improve future reports.
    </div>
    <div style="font-size:36px;color:#ffaa00;letter-spacing:5px;margin-bottom:28px;text-shadow:0 0 16px rgba(255,170,0,0.5);">{_stars_filled}</div>
    <div style="font-size:13px;color:#334466;">You can close this tab.</div>
  </div>
</div>
""", unsafe_allow_html=True)
        st.stop()

# ─── Click tracking (from email links) ────────────────────────────────────────
_track_param = st.query_params.get("track")
if _track_param in ("click", "open"):
    _track_id  = st.query_params.get("id", "")
    _track_em  = st.query_params.get("em", "")
    _track_url = st.query_params.get("url", "")
    if _track_id and _track_em:
        try:
            import base64 as _b64d
            import urllib.parse as _up2
            _decoded_email = _b64d.b64decode(_track_em.encode()).decode("utf-8", errors="replace")
            tracking_store.log_event(_track_id, _decoded_email, _track_param)
            # Also log as open when click is detected
            if _track_param == "click":
                tracking_store.log_event(_track_id, _decoded_email, "open")
        except Exception:
            pass
    if _track_url:
        try:
            import urllib.parse as _up3
            _dest = _up3.unquote(_track_url)
            st.markdown(f'<meta http-equiv="refresh" content="0;url={_dest}" />', unsafe_allow_html=True)
            st.stop()
        except Exception:
            pass

# ─── Global CSS ───────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

:root {
    --brand-primary:   #2563EB;
    --brand-dark:      #1D4ED8;
    --brand-deep:      #1e40af;
    --brand-navy:      #0B1F3A;
    --brand-bright:    #60A5FA;
    --brand-accent:    #38BDF8;
    --neutral-black:   #0B1F3A;
    --neutral-body:    #1e3a5f;
    --neutral-secondary: #475569;
    --neutral-outline: rgba(37,99,235,0.22);
    --neutral-smoke:   rgba(37,99,235,0.06);
    --bg-page:         #F0F4F9;
    --bg-card:         #ffffff;
    --bg-card-2:       #EBF3FF;
    --bg-blue-xl:      rgba(37,99,235,0.06);
    --bg-blue-shade:   rgba(37,99,235,0.15);
    --gradient-blue:   linear-gradient(135deg, #0B1F3A, #2563EB);
    --gradient-brand:  linear-gradient(135deg, #0B1F3A, #2563EB);
    --glow-blue:       0 0 24px rgba(37,99,235,0.28);
    --glow-strong:     0 0 40px rgba(37,99,235,0.3), 0 0 80px rgba(96,165,250,0.12);
}

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
header    { visibility: hidden; }

/* ── App shell ── */
.stApp { background: var(--bg-page) !important; }
.stApp > div { background: var(--bg-page) !important; }
.block-container {
    padding-top: 0 !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
    max-width: 1300px !important;
    background: var(--bg-page) !important;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] { background: #E8F0FB !important; border-right: 1px solid rgba(37,99,235,0.2) !important; }
section[data-testid="stSidebar"] > div { background: #E8F0FB !important; }
section[data-testid="stSidebar"] label { color: #0B1F3A !important; font-size: 0.86rem !important; font-weight: 500 !important; }
section[data-testid="stSidebar"] p { color: #0B1F3A !important; }
section[data-testid="stSidebar"] span { color: #0B1F3A !important; }
section[data-testid="stSidebar"] .stRadio > div { gap: 2px !important; }
section[data-testid="stSidebar"] .stRadio label {
    padding: 8px 10px !important;
    border-radius: 8px !important;
    transition: background 0.15s !important;
}
section[data-testid="stSidebar"] .stRadio label:has(input:checked) {
    background: rgba(37,99,235,0.12) !important;
    color: var(--brand-primary) !important;
    border-left: 3px solid var(--brand-primary) !important;
}
section[data-testid="stSidebar"] hr { border-color: rgba(37,99,235,0.15) !important; }

/* ── Inputs & textareas ── */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {
    background: #F7FAFF !important;
    border: 1.5px solid rgba(37,99,235,0.22) !important;
    border-radius: 10px !important;
    color: #0B1F3A !important;
    font-size: 0.84rem !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}
[data-testid="stTextInput"] input::placeholder,
[data-testid="stTextArea"] textarea::placeholder { color: #94a3b8 !important; }
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
    border-color: var(--brand-primary) !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.15), var(--glow-blue) !important;
    outline: none !important;
}
[data-testid="stSelectbox"] > div > div {
    background: #F7FAFF !important;
    border: 1.5px solid rgba(37,99,235,0.22) !important;
    border-radius: 10px !important;
    color: #0B1F3A !important;
}
[data-testid="stSelectbox"] > div > div > div,
[data-testid="stSelectbox"] span,
[data-testid="stSelectbox"] p {
    color: #0B1F3A !important;
}
/* Dropdown option list */
[data-testid="stSelectbox"] ul,
[data-baseweb="select"] ul,
[data-baseweb="popover"] ul li,
[data-baseweb="menu"] ul li,
[role="listbox"] li,
[role="option"] {
    background: #ffffff !important;
    color: #0B1F3A !important;
}
[role="option"]:hover,
[data-baseweb="menu"] ul li:hover {
    background: #eef4ff !important;
    color: #0B1F3A !important;
}
[data-testid="stMultiSelect"] > div > div {
    background: #F7FAFF !important;
    border: 1.5px solid rgba(37,99,235,0.22) !important;
    border-radius: 10px !important;
    color: #0B1F3A !important;
}
[data-testid="stMultiSelect"] span,
[data-testid="stMultiSelect"] p {
    color: #0B1F3A !important;
}

/* ── Buttons ── */
.stButton > button {
    border-radius: 8px !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.01em !important;
    transition: all 0.2s ease !important;
    border: none !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #0B1F3A, #2563EB) !important;
    color: #fff !important;
    box-shadow: 0 2px 14px rgba(37,99,235,0.4) !important;
}
.stButton > button[kind="primary"] p,
.stButton > button[kind="primary"] span,
.stButton > button[kind="primary"] div {
    color: #fff !important;
}
.stButton > button[kind="primary"]:hover {
    filter: brightness(1.1) !important;
    box-shadow: 0 4px 24px rgba(37,99,235,0.6), 0 0 40px rgba(96,165,250,0.2) !important;
    transform: translateY(-2px) !important;
}
.stButton > button[kind="secondary"] {
    background: rgba(37,99,235,0.06) !important;
    border: 1px solid rgba(37,99,235,0.22) !important;
    color: #2563EB !important;
}
.stButton > button[kind="secondary"]:hover {
    background: rgba(37,99,235,0.10) !important;
    border-color: rgba(37,99,235,0.45) !important;
    color: #1D4ED8 !important;
    transform: translateY(-1px) !important;
}

/* ── Download button ── */
[data-testid="stDownloadButton"] button {
    background: rgba(37,99,235,0.07) !important;
    border: 1px solid rgba(37,99,235,0.28) !important;
    border-radius: 8px !important;
    color: #2563EB !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    transition: all 0.2s ease !important;
}
[data-testid="stDownloadButton"] button:hover {
    background: rgba(37,99,235,0.14) !important;
    border-color: rgba(37,99,235,0.5) !important;
    box-shadow: 0 0 16px rgba(37,99,235,0.25) !important;
    transform: translateY(-1px) !important;
}

/* ── Tabs ── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 2px solid var(--neutral-outline) !important;
    gap: 0 !important;
    padding: 0 !important;
}
[data-baseweb="tab"] {
    background: transparent !important;
    font-size: 0.83rem !important;
    font-weight: 500 !important;
    color: var(--neutral-secondary) !important;
    padding: 10px 24px !important;
    border-bottom: 2px solid transparent !important;
    margin-bottom: -2px !important;
    transition: color 0.15s !important;
}
[aria-selected="true"][data-baseweb="tab"] {
    color: var(--brand-primary) !important;
    border-bottom: 2px solid var(--brand-primary) !important;
    font-weight: 600 !important;
}
[data-testid="stTabs"] [data-baseweb="tab-panel"] {
    padding-top: 1.5rem !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    background: var(--bg-card) !important;
    border: 1px solid rgba(61,130,245,0.2) !important;
    border-radius: 12px !important;
    box-shadow: 0 4px 20px rgba(61,130,245,0.08) !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}
[data-testid="stExpander"]:hover {
    border-color: rgba(61,130,245,0.4) !important;
    box-shadow: 0 4px 30px rgba(61,130,245,0.15) !important;
}
[data-testid="stExpander"] summary {
    font-size: 0.84rem !important;
    font-weight: 600 !important;
    color: #1e3a5f !important;
}

/* ── Forms ── */
[data-testid="stForm"] {
    background: var(--bg-card) !important;
    border: 1px solid rgba(61,130,245,0.2) !important;
    border-radius: 12px !important;
    box-shadow: 0 4px 20px rgba(61,130,245,0.08) !important;
}

/* ── Alerts ── */
[data-testid="stAlert"] { border-radius: 12px !important; font-size: 0.84rem !important; }

/* ── Divider ── */
hr { border-color: rgba(61,130,245,0.15) !important; margin: 1.5rem 0 !important; }

/* ── Caption / small text ── */
[data-testid="stCaptionContainer"] p { color: #3a6699 !important; font-size: 0.77rem !important; }
label { color: #3a6699 !important; font-size: 0.8rem !important; font-weight: 500 !important; }

/* ──────────────────────────────────────────────────────
   CAMPAIGN ANALYTICS DASHBOARD
────────────────────────────────────────────────────── */

.analytics-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 14px;
    margin-bottom: 14px;
}
.metric-card {
    background: var(--bg-card);
    border: 1px solid rgba(61,130,245,0.18);
    border-radius: 16px;
    padding: 1.3rem 1.5rem 1.1rem;
    box-shadow: 0 4px 24px rgba(61,130,245,0.1), inset 0 1px 0 rgba(255,255,255,0.5);
    position: relative;
    overflow: hidden;
    transition: box-shadow 0.25s, transform 0.25s, border-color 0.25s;
    animation: cardEntry 0.5s ease both;
}
.metric-card:hover {
    box-shadow: 0 8px 40px rgba(61,130,245,0.32), 0 0 60px rgba(61,142,245,0.12), inset 0 1px 0 rgba(255,255,255,0.06);
    border-color: rgba(61,130,245,0.5);
    transform: translateY(-4px);
}
.metric-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    border-radius: 16px 16px 0 0;
    background: rgba(61,130,245,0.3);
}
.metric-card.accent-blue::before   { background: var(--gradient-blue); box-shadow: 0 2px 12px rgba(37,99,235,0.5); }
.metric-card.accent-green::before  { background: linear-gradient(90deg, #0ebc6e, #42ba78); box-shadow: 0 2px 12px rgba(14,188,110,0.5); }
.metric-card.accent-red::before    { background: linear-gradient(90deg, #e72b3b, #60A5FA); box-shadow: 0 2px 12px rgba(231,43,59,0.5); }
.metric-card.accent-amber::before  { background: linear-gradient(90deg, #d97706, #fbbf24); box-shadow: 0 2px 12px rgba(217,119,6,0.5); }

.metric-label {
    font-size: 0.59rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #2a5080;
    margin-bottom: 0.65rem;
}
.metric-value {
    font-size: 2.1rem;
    font-weight: 800;
    background: var(--gradient-brand);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -0.04em;
    line-height: 1;
    margin-bottom: 0.35rem;
}
.metric-max { font-size: 1rem; color: #7a99bb; -webkit-text-fill-color: #7a99bb; font-weight: 500; letter-spacing: 0; }
.metric-sub { font-size: 0.69rem; color: #2a5080; }
.ch-up   { color: #22e885; font-weight: 700; text-shadow: 0 0 10px rgba(34,232,133,0.5); }
.ch-down { color: #ff5566; font-weight: 700; text-shadow: 0 0 10px rgba(255,85,102,0.5); }

/* CSAT breakdown */
.csat-section {
    background: var(--bg-card);
    border: 1px solid rgba(61,130,245,0.18);
    border-radius: 16px;
    padding: 1.6rem 2rem;
    display: grid;
    grid-template-columns: 160px 1fr;
    gap: 2.5rem;
    align-items: center;
    box-shadow: 0 4px 24px rgba(61,130,245,0.1), inset 0 1px 0 rgba(255,255,255,0.5);
    animation: cardEntry 0.5s ease both;
}
.csat-score-side { text-align: center; padding-right: 2rem; border-right: 1px solid rgba(61,130,245,0.15); }
.csat-number { font-size: 3.2rem; font-weight: 800; background: var(--gradient-brand); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; letter-spacing: -0.05em; line-height: 1; filter: drop-shadow(0 0 12px rgba(37,99,235,0.35)); }
.csat-stars { color: #ffaa00; font-size: 1.1rem; margin: 10px 0 6px; letter-spacing: 3px; text-shadow: 0 0 10px rgba(255,170,0,0.5); }
.csat-count { font-size: 0.7rem; color: #7a99bb; }
.bar-row { display: flex; align-items: center; gap: 12px; margin-bottom: 11px; }
.bar-row:last-child { margin-bottom: 0; }
.bar-star  { font-size: 0.67rem; color: #7a99bb; width: 18px; text-align: right; flex-shrink: 0; }
.bar-track { flex: 1; height: 6px; background: rgba(61,130,245,0.12); border-radius: 99px; overflow: hidden; }
.bar-fill  { height: 100%; border-radius: 99px; background: linear-gradient(90deg,#2563EB,#60A5FA); box-shadow: 0 0 8px rgba(37,99,235,0.3); animation: barSlide 1s ease both; }
.bar-pct   { font-size: 0.67rem; color: #3a6699; width: 30px; text-align: right; flex-shrink: 0; }
.bar-count { font-size: 0.64rem; color: #7a99bb; width: 14px; flex-shrink: 0; }
.resp-row { display: flex; align-items: center; gap: 10px; padding: 9px 0; border-bottom: 1px solid rgba(61,130,245,0.12); }
.resp-row:last-child { border-bottom: none; }
.resp-name  { color: #0d1d3a; font-size: 0.78rem; font-weight: 600; min-width: 130px; }
.resp-email { color: #3a6699; font-size: 0.73rem; flex: 1; }
.resp-date  { color: #7a99bb; font-size: 0.68rem; min-width: 50px; text-align: right; }
.resp-stars { color: #ffaa00; font-size: 0.75rem; letter-spacing: 1px; min-width: 70px; text-align: right; text-shadow: 0 0 8px rgba(255,170,0,0.4); }

/* ──────────────────────────────────────────────────────
   PAGE HEADER
────────────────────────────────────────────────────── */

.page-header {
    margin-bottom: 1.8rem;
    padding: 1.2rem 0 1.4rem;
    border-bottom: 1px solid rgba(61,130,245,0.15);
    display: flex;
    align-items: center;
    gap: 14px;
    animation: fadeDown 0.4s ease both;
}
.page-header-icon {
    width: 42px; height: 42px;
    border-radius: 12px;
    background: rgba(37,99,235,0.10);
    display: flex; align-items: center; justify-content: center;
    font-size: 1.2rem;
    flex-shrink: 0;
    border: 1px solid rgba(37,99,235,0.28);
    box-shadow: 0 0 16px rgba(37,99,235,0.18);
}
.page-header-text { flex: 1; }
.page-title {
    font-size: 1.4rem;
    font-weight: 800;
    color: #0d1d3a;
    letter-spacing: -0.03em;
    line-height: 1.2;
}
.page-sub { font-size: 0.82rem; color: #2a5080; margin-top: 0.2rem; font-weight: 400; }

/* ──────────────────────────────────────────────────────
   CLIENT REPOSITORY
────────────────────────────────────────────────────── */

.client-repo-card {
    background: var(--bg-card);
    border: 1px solid rgba(61,130,245,0.16);
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 4px 24px rgba(61,130,245,0.1), inset 0 1px 0 rgba(255,255,255,0.5);
    transition: box-shadow 0.25s, transform 0.2s, border-color 0.25s;
    animation: cardEntry 0.5s ease both;
}
.client-repo-card:hover {
    box-shadow: 0 8px 40px rgba(37,99,235,0.22), 0 0 60px rgba(96,165,250,0.08);
    border-color: rgba(37,99,235,0.4);
    transform: translateY(-3px);
}
.tag-chip {
    display: inline-block;
    background: rgba(37,99,235,0.10);
    color: #2563EB;
    font-size: 0.61rem;
    font-weight: 700;
    padding: 3px 10px;
    border-radius: 99px;
    margin: 2px 3px 0 0;
    border: 1px solid rgba(37,99,235,0.22);
    letter-spacing: 0.02em;
}

/* Stats grid */
.stats-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 1.8rem;
}
.stat-card {
    background: var(--bg-card);
    border: 1px solid rgba(61,130,245,0.15);
    border-radius: 14px;
    padding: 1rem 1.2rem;
    box-shadow: 0 4px 20px rgba(61,130,245,0.09);
    animation: cardEntry 0.5s ease both;
}

/* ──────────────────────────────────────────────────────
   EMAIL MAKER
────────────────────────────────────────────────────── */


.draft-card {
    background: var(--bg-card);
    border: 1px solid rgba(61,130,245,0.15);
    border-radius: 14px;
    padding: 16px 18px;
    margin-bottom: 12px;
    box-shadow: 0 4px 20px rgba(61,130,245,0.09);
    transition: box-shadow 0.25s, border-color 0.25s, transform 0.2s;
}
.draft-card:hover {
    box-shadow: 0 8px 36px rgba(37,99,235,0.18);
    border-color: rgba(37,99,235,0.4);
    transform: translateY(-2px);
}
.client-card {
    background: var(--bg-card);
    border: 1px solid rgba(61,130,245,0.15);
    border-radius: 14px;
    padding: 16px 20px;
    margin-bottom: 10px;
    box-shadow: 0 4px 20px rgba(61,130,245,0.09);
}
.client-name { color: #0d1d3a; font-weight: 600; font-size: 0.9rem; }
.email-pill {
    display: inline-block;
    background: rgba(37,99,235,0.08);
    color: var(--brand-primary);
    font-size: 0.7rem;
    font-weight: 500;
    padding: 3px 10px;
    border-radius: 6px;
    margin: 3px 3px 0 0;
    border: 1px solid rgba(37,99,235,0.24);
}

/* ── Section labels ── */
.section-chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 0.6rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #ffffff;
    background: linear-gradient(135deg,#0B1F3A,#2563EB);
    border: none;
    border-radius: 6px;
    padding: 4px 12px;
    margin-bottom: 14px;
    box-shadow: 0 2px 8px rgba(37,99,235,0.22);
}

/* ── Client avatar ── */
.client-avatar {
    width: 46px; height: 46px;
    border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.82rem; font-weight: 800;
    flex-shrink: 0;
    box-shadow: 0 4px 16px rgba(37,99,235,0.18), 0 0 20px rgba(11,31,58,0.12);
}

/* ── Template card ── */
.tmpl-card {
    border-radius: 10px;
    padding: 10px 10px 8px;
    margin-bottom: 8px;
    cursor: pointer;
    transition: opacity 0.12s, transform 0.12s;
}
.tmpl-card:hover { opacity: 0.85; transform: translateY(-1px); }

/* ── Keyframe Animations ── */
@keyframes cardEntry {
    from { opacity: 0; transform: translateY(16px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes fadeDown {
    from { opacity: 0; transform: translateY(-10px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes barSlide {
    from { width: 0 !important; }
}
@keyframes gradientShift {
    0%   { background-position: 0% 50%; }
    50%  { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}
@keyframes livePulse {
    0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(34,232,133,0.6); }
    50%       { opacity: 0.7; box-shadow: 0 0 0 5px rgba(34,232,133,0); }
}
@keyframes shimmer {
    0%   { background-position: -200% center; }
    100% { background-position: 200% center; }
}

/* ── Nav strip ── */
div[data-testid="stHorizontalBlock"]:has(button[key="nav_settings"]) {
    background: #E2ECFB !important;
    border-bottom: 1px solid rgba(37,99,235,0.18) !important;
    box-shadow: 0 1px 20px rgba(37,99,235,0.07) !important;
}

/* ── Tab overrides ── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    border-bottom-color: rgba(61,130,245,0.18) !important;
}
[data-baseweb="tab"] { color: #475569 !important; }
[aria-selected="true"][data-baseweb="tab"] {
    color: #2563EB !important;
    border-bottom-color: #2563EB !important;
}

/* ── Streamlit overrides ── */
p, .stMarkdown p { color: #1e3a5f !important; }
h1, h2, h3 { color: #0B1F3A !important; }
[data-testid="stMetricValue"] { color: #0B1F3A !important; }

/* ── Live badge ── */
.live-dot {
    display: inline-block;
    width: 7px; height: 7px;
    border-radius: 50%;
    background: #22e885;
    animation: livePulse 2s ease-in-out infinite;
    vertical-align: middle;
    margin-right: 5px;
}

/* ── Stagger card entries ── */
.analytics-grid > *:nth-child(1) { animation-delay: 0.05s; }
.analytics-grid > *:nth-child(2) { animation-delay: 0.10s; }
.analytics-grid > *:nth-child(3) { animation-delay: 0.15s; }
.analytics-grid > *:nth-child(4) { animation-delay: 0.20s; }
</style>
""", unsafe_allow_html=True)

# ─── Login gate ───────────────────────────────────────────────────────────────

def _render_login_page():
    _logo_html = _logo_img(72, 20)
    st.markdown(f"""
    <style>
    @keyframes loginGlow {{
        0%, 100% {{ box-shadow: 0 0 40px rgba(61,130,245,0.2), 0 0 80px rgba(61,130,245,0.08); }}
        50%       {{ box-shadow: 0 0 60px rgba(61,130,245,0.35), 0 0 100px rgba(61,130,245,0.12); }}
    }}
    .login-wrap {{
        max-width: 390px;
        margin: 8vh auto 0;
        background: #ffffff;
        border: 1px solid rgba(61,130,245,0.25);
        border-radius: 24px;
        padding: 3rem 2.5rem 2.5rem;
        animation: loginGlow 4s ease-in-out infinite;
        text-align: center;
    }}
    .login-logo-wrap {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 1.6rem;
        filter: drop-shadow(0 8px 24px rgba(61,130,245,0.35));
    }}
    .login-brand {{ font-size: 0.58rem; font-weight: 700; letter-spacing: 0.15em; text-transform: uppercase; color: #2563EB; margin-bottom: 6px; }}
    .login-title {{ font-size: 1.5rem; font-weight: 800; color: #0d1d3a; margin-bottom: 0.3rem; letter-spacing: -0.03em; line-height: 1.2; }}
    .login-divider {{ width: 40px; height: 3px; background: linear-gradient(90deg, #0B1F3A, #2563EB); border-radius: 2px; margin: 12px auto 20px; box-shadow: 0 0 10px rgba(61,130,245,0.3); }}
    .login-sub {{ font-size: 0.83rem; color: #2a5080; margin-bottom: 2rem; }}
    </style>
    <div class="login-wrap">
        <div class="login-logo-wrap">{_logo_html}</div>
        <div class="login-brand">Convin Data Labs</div>
        <div class="login-title">Insights Dashboard</div>
        <div class="login-divider"></div>
        <div class="login-sub">Sign in to access your analytics</div>
    </div>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1.4, 1])
    with col:
        _preset_email = st.secrets.get("USER_EMAIL", "")
        email = st.text_input("Email", value=_preset_email, placeholder="you@example.com", key="login_email")
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
    <div style="padding:8px 4px 18px;">
        <div style="display:flex;align-items:center;gap:10px;">
            """ + _logo_img(36, 10) + """
            <div>
                <div style="color:#e0ecf8;font-weight:700;font-size:0.9rem;letter-spacing:-0.01em;line-height:1.2;">Convin Data Labs</div>
                <div style="color:#2563EB;font-size:0.6rem;margin-top:2px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;">Settings</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    auth.render_login_sidebar()

    # ── Gmail settings ──────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown('<div style="color:#64748b;font-size:0.7rem;font-weight:700;letter-spacing:0.07em;text-transform:uppercase;margin-bottom:8px;">Gmail Sender</div>', unsafe_allow_html=True)
    if st.session_state.get("gmail_app_password"):
        st.markdown(
            f'<div style="color:#16a34a;font-size:0.75rem;font-weight:600;margin-bottom:6px;">✓ {st.session_state.get("user_email","")}</div>',
            unsafe_allow_html=True,
        )
        if st.button("Change", key="gmail_change_btn", use_container_width=True):
            st.session_state.pop("gmail_app_password", None)
            st.rerun()
    else:
        sb_email = st.text_input(
            "Google / Gmail Address", value=st.session_state.get("user_email", ""),
            placeholder="you@gmail.com or you@yourworkspace.com", key="sb_gmail_email", label_visibility="collapsed",
        )
        sb_apppw = st.text_input(
            "App Password", type="password",
            placeholder="abcd efgh ijkl mnop", key="sb_gmail_pw", label_visibility="collapsed",
        )
        st.caption("Need an App Password? [Google Account → Security → App Passwords](https://myaccount.google.com/apppasswords)")
        if st.button("Connect Gmail", key="sb_gmail_save", type="primary", use_container_width=True):
            _pw = sb_apppw.replace(" ", "")
            if "@" in sb_email and len(_pw) >= 16:
                st.session_state["user_email"]       = sb_email.strip().lower()
                st.session_state["gmail_app_password"] = _pw
                st.toast("Gmail connected.", icon="✅")
                st.rerun()
            else:
                st.error("Enter your Google address and the 16-character App Password.")

    st.markdown("---")
    st.markdown('<div style="color:#444460;font-size:0.68rem;font-weight:500;">Feb 2026 · v1.0</div>', unsafe_allow_html=True)

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
        return '<span style="color:#d22c84;font-weight:600;">✓</span>' if v else '<span style="color:#94a3b8;">—</span>'
    def scbadge(s):
        if s is None:
            return '<span style="color:#94a3b8;">—</span>'
        c = {1:"#f87171",2:"#fb923c",3:"#fbbf24",4:"#34d399",5:"#22c55e"}
        return f'<span style="color:{c[s]};font-weight:700;">{s}★</span>'

    th = 'style="color:#446688;font-size:0.58rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;padding:10px 12px;text-align:left;white-space:nowrap;background:#071528;"'
    tc = 'style="font-size:0.73rem;padding:9px 12px;border-bottom:1px solid rgba(61,130,245,0.06);text-align:center;"'
    headers = ["Email", "DL Report Name", "Del", "Open", "Click", "Resp", "Score", "Date"]
    hrow = f'<tr>{"".join(f"<th {th}>{h}</th>" for h in headers)}</tr>'
    brows = "".join(
        f"""<tr style="transition:background 0.15s;" onmouseover="this.style.background='rgba(37,99,235,0.05)'" onmouseout="this.style.background='transparent'">
          <td style="font-size:0.72rem;padding:9px 12px;border-bottom:1px solid rgba(61,130,245,0.06);color:#c8c8e8;">{r['email']}</td>
          <td style="font-size:0.67rem;padding:9px 12px;border-bottom:1px solid rgba(61,130,245,0.06);color:#5588bb;white-space:nowrap;">{r['campaign']}</td>
          <td {tc}>{dbadge(r['delivered'])}</td>
          <td {tc}>{sbadge(r['opened'])}</td>
          <td {tc}>{sbadge(r['clicked'])}</td>
          <td {tc}>{sbadge(r['responded'])}</td>
          <td {tc}>{scbadge(r['score'])}</td>
          <td style="font-size:0.67rem;padding:9px 12px;border-bottom:1px solid rgba(61,130,245,0.06);color:#334466;text-align:right;">{r['date']}</td>
        </tr>"""
        for r in rows
    )
    return f"""<div style="background:#071428;border:1px solid rgba(61,130,245,0.18);border-radius:14px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.5);">
      <div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;">
        <thead>{hrow}</thead><tbody>{brows}</tbody>
      </table></div></div>"""


# ─── Period content renderer ──────────────────────────────────────────────────

def _render_period_content(period: str):
    # ── Real data from sent_store + tracking_store ─────────────────────────────
    hours_map  = {"Daily": 24, "Weekly": 168, "Monthly": 720}
    _hours     = hours_map.get(period)
    _ts        = tracking_store.get_stats_for_period(_hours)
    _sent_recs = sent_store.load()

    # Filter sent records to the time window
    if _hours is not None:
        from datetime import timedelta, timezone as _tz
        _cutoff    = datetime.now(timezone.utc) - timedelta(hours=_hours)
        _sent_recs = [
            r for r in _sent_recs
            if datetime.fromisoformat(r["timestamp"]) >= _cutoff
        ]

    _total_delivered = sum(len(r.get("sent_to", [])) for r in _sent_recs)
    _total_opens     = len(_ts["opens"]) + len(_ts["clicks"])   # clicks imply open
    _total_clicks    = len(_ts["clicks"])
    _total_ratings   = _ts["total_ratings"]

    _open_rate_pct   = round(_total_opens  / _total_delivered * 100, 1) if _total_delivered else 0
    _click_rate_pct  = round(_total_clicks / _total_delivered * 100, 1) if _total_delivered else 0
    _cto_pct         = round(_total_clicks / _total_opens * 100, 1) if _total_opens else 0

    _period_labels   = {"Daily": "Today", "Weekly": "This Week", "Monthly": "All Time"}
    _real_data = {
        "label":   _period_labels.get(period, period),
        "updated": "Live",
        "metrics": [
            {"label": "Total Sent",     "value": str(_total_delivered),                      "sub": None,                                "change": None, "up_good": True},
            {"label": "Open Rate",      "value": f"{_open_rate_pct}%",                       "sub": f"{_total_opens} opens",             "change": None, "up_good": True},
            {"label": "Click to Open",  "value": f"{_cto_pct}%",                             "sub": f"{_total_clicks} clicks",           "change": None, "up_good": True},
            {"label": "Delivered Rate", "value": "100%",                                     "sub": f"{_total_delivered} emails",        "change": None, "up_good": True},
            {"label": "Bounce Rate",    "value": "0.0%",                                     "sub": None,                                "change": None, "up_good": False},
            {"label": "Response Rate",  "value": f"{round(_total_ratings / _total_delivered * 100, 1) if _total_delivered else 0}%",
                                                                                              "sub": f"{_total_ratings} ratings",        "change": None, "up_good": True},
            {"label": "Avg Rating",     "value": f"{_ts['avg_rating']:.1f}" if _total_ratings else "—",
                                                                                              "sub": "out of 5",                         "change": None, "up_good": True},
        ],
        "csat": {
            "score":     _ts["avg_rating"],
            "responses": _total_ratings,
            "dist":      _ts["dist"],
        },
    }

    # Build real email rows from sent records + tracking events
    _engagement_by_email = {}
    for e in _ts["opens"] + _ts["clicks"] + _ts["ratings"]:
        em = e["email"]
        if em not in _engagement_by_email:
            _engagement_by_email[em] = {"opened": False, "clicked": False, "responded": False, "score": None, "date": e["date"]}
        if e["type"] in ("open", "click"):
            _engagement_by_email[em]["opened"] = True
        if e["type"] == "click":
            _engagement_by_email[em]["clicked"] = True
        if e["type"] == "rating":
            _engagement_by_email[em]["responded"] = True
            _engagement_by_email[em]["score"] = e.get("rating")

    _real_email_rows = []
    seen_emails = set()
    for rec in _sent_recs:
        for em in rec.get("sent_to", []):
            if em in seen_emails:
                continue
            seen_emails.add(em)
            eng = _engagement_by_email.get(em, {})
            _real_email_rows.append({
                "email":     em,
                "campaign":  rec.get("subject", "—"),
                "delivered": True,
                "opened":    eng.get("opened", False),
                "clicked":   eng.get("clicked", False),
                "responded": eng.get("responded", False),
                "score":     eng.get("score"),
                "date":      rec.get("date", "—"),
            })

    _real_opened_rows  = [{"email": e["email"], "campaign": "—", "date": e["date"]} for e in _ts["opens"] + _ts["clicks"]]
    _real_clicked_rows = [{"email": e["email"], "campaign": "—", "date": e["date"]} for e in _ts["clicks"]]

    data  = _real_data
    csat  = data["csat"]
    score = csat["score"]
    stars = "★" * int(score) + "☆" * (5 - int(score))

    email_rows   = _real_email_rows
    opened_rows  = _real_opened_rows
    clicked_rows = _real_clicked_rows

    st.markdown(f"""
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;">
        <div style="color:#e8f0fc;font-size:0.96rem;font-weight:700;letter-spacing:-0.01em;">{data['label']}</div>
        <div style="display:flex;align-items:center;gap:6px;color:#6699cc;font-size:0.7rem;font-weight:500;letter-spacing:0.04em;">
            <span class="live-dot"></span>Updated {data['updated']}
        </div>
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
            return '<div style="color:#334466;font-size:0.78rem;padding:8px 0;">No data for this period.</div>'
        items = "".join(
            f'<div style="display:flex;align-items:center;gap:10px;padding:8px 0;'
            f'border-bottom:1px solid rgba(61,130,245,0.06);">'
            f'<div style="width:8px;height:8px;border-radius:50%;background:linear-gradient(135deg,#0B1F3A,#2563EB);flex-shrink:0;box-shadow:0 0 6px rgba(61,130,245,0.55);"></div>'
            f'<div style="flex:1;min-width:0;">'
            f'<div style="font-size:0.79rem;font-weight:600;color:#c8daee;white-space:nowrap;'
            f'overflow:hidden;text-overflow:ellipsis;">{r["email"]}</div>'
            f'<div style="font-size:0.7rem;color:#5588bb;">{r["campaign"]} · {r["date"]}</div>'
            f'</div>'
            f'<div style="font-size:0.68rem;color:#334466;flex-shrink:0;">{r["date"]}</div>'
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
            <div style="color:#446688;font-size:0.62rem;font-weight:700;letter-spacing:0.11em;text-transform:uppercase;margin-bottom:14px;">Report Score</div>
            <div class="csat-number">{score}<span style="font-size:1.1rem;color:#334466;font-weight:500;-webkit-text-fill-color:#334466;">/5</span></div>
            <div class="csat-stars">{stars}</div>
            <div class="csat-count">{csat['responses']} ratings</div>
        </div>
        <div>
            <div style="color:#446688;font-size:0.62rem;font-weight:700;letter-spacing:0.11em;text-transform:uppercase;margin-bottom:14px;">Rating Distribution</div>
            {bars}
        </div>
    </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    respondents = _ts["respondents"]
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
        <div style="color:#e0ecf8;font-size:0.92rem;font-weight:700;">Email Activity</div>
        <div style="color:#334466;font-size:0.68rem;font-weight:500;">{len(email_rows)} emails</div>
    </div>""", unsafe_allow_html=True)
    st.markdown(_email_table_html(email_rows), unsafe_allow_html=True)

    _render_ai_summary(period, csat, respondents)


# ─── Home landing portal ──────────────────────────────────────────────────────

def render_home():
    _logo_html = _logo_img(52, 12)
    st.markdown(f"""
<style>
@keyframes hFadeUp {{
    from {{ opacity:0; transform:translateY(28px); }}
    to   {{ opacity:1; transform:translateY(0); }}
}}
@keyframes hShimmer {{
    0%   {{ background-position: -400px 0; }}
    100% {{ background-position: 400px 0; }}
}}
@keyframes hPulse {{
    0%,100% {{ box-shadow: 0 0 0 0 rgba(99,179,237,0.4); }}
    50%      {{ box-shadow: 0 0 0 10px rgba(99,179,237,0); }}
}}
@keyframes hFloat {{
    0%,100% {{ transform: translateY(0px); }}
    50%      {{ transform: translateY(-8px); }}
}}

/* ── Hero banner ── */
.h-hero {{
    background: linear-gradient(135deg, #0a0f2e 0%, #0d1b4b 40%, #12236b 70%, #0a1840 100%);
    border-radius: 24px;
    padding: 52px 48px 44px;
    text-align: center;
    position: relative;
    overflow: hidden;
    margin-bottom: 28px;
    animation: hFadeUp 0.5s ease both;
    border: 1px solid rgba(99,179,237,0.15);
}}
.h-hero::before {{
    content: "";
    position: absolute; inset: 0;
    background: radial-gradient(ellipse 80% 60% at 50% 0%, rgba(59,130,246,0.25) 0%, transparent 70%);
    pointer-events: none;
}}
.h-hero::after {{
    content: "";
    position: absolute; bottom: 0; left: 0; right: 0; height: 1px;
    background: linear-gradient(90deg, transparent, rgba(99,179,237,0.5), transparent);
}}
.h-eyebrow {{
    display: inline-block;
    font-size: 0.6rem; font-weight: 800; letter-spacing: 0.25em;
    text-transform: uppercase; color: #63b3ed;
    background: rgba(99,179,237,0.12);
    border: 1px solid rgba(99,179,237,0.3);
    border-radius: 99px; padding: 4px 16px;
    margin-bottom: 20px;
}}
.h-brand {{
    font-size: 3rem; font-weight: 900; color: #ffffff;
    letter-spacing: -0.05em; line-height: 1;
    margin-bottom: 12px;
    text-shadow: 0 0 60px rgba(99,179,237,0.4);
}}
.h-brand span {{
    background: linear-gradient(90deg, #63b3ed, #a78bfa, #63b3ed);
    background-size: 200% auto;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: hShimmer 3s linear infinite;
}}
.h-tagline {{
    font-size: 1rem; font-weight: 500; color: rgba(226,232,240,0.85);
    line-height: 1.6; margin-bottom: 8px;
}}
.h-sub {{
    font-size: 0.72rem; color: rgba(148,163,184,0.7);
    letter-spacing: 0.06em;
}}

/* ── Cards ── */
.h-card {{
    border-radius: 20px;
    padding: 32px 28px 26px;
    position: relative; overflow: hidden;
    transition: transform 0.25s cubic-bezier(.4,0,.2,1), box-shadow 0.25s;
    animation: hFadeUp 0.6s ease both;
    margin-bottom: 12px;
}}
.h-card:hover {{ transform: translateY(-6px); }}

.h-card-cdl {{
    background: linear-gradient(145deg, #1a3a8f 0%, #1e40af 45%, #1d4ed8 100%);
    border: 1px solid rgba(147,197,253,0.4);
    box-shadow: 0 4px 24px rgba(37,99,235,0.35), inset 0 1px 0 rgba(255,255,255,0.1);
}}
.h-card-cdl:hover {{
    box-shadow: 0 20px 60px rgba(37,99,235,0.50), inset 0 1px 0 rgba(255,255,255,0.15);
    border-color: rgba(147,197,253,0.7);
}}
.h-card-sense {{
    background: linear-gradient(145deg, #3b0764 0%, #6d28d9 45%, #7c3aed 100%);
    border: 1px solid rgba(196,181,253,0.4);
    box-shadow: 0 4px 24px rgba(124,58,237,0.35), inset 0 1px 0 rgba(255,255,255,0.1);
}}
.h-card-sense:hover {{
    box-shadow: 0 20px 60px rgba(124,58,237,0.50), inset 0 1px 0 rgba(255,255,255,0.15);
    border-color: rgba(196,181,253,0.7);
}}

/* glow orb top-right of each card */
.h-card::before {{
    content: ""; position: absolute; top: -60px; right: -60px;
    width: 220px; height: 220px; border-radius: 50%; pointer-events: none;
    animation: hFloat 6s ease-in-out infinite;
}}
.h-card-cdl::before  {{ background: radial-gradient(circle, rgba(147,197,253,0.25) 0%, transparent 65%); }}
.h-card-sense::before {{ background: radial-gradient(circle, rgba(196,181,253,0.25) 0%, transparent 65%); }}

.h-icon {{
    font-size: 2.4rem; margin-bottom: 14px; display: block;
    filter: drop-shadow(0 0 12px rgba(255,255,255,0.3));
    animation: hFloat 5s ease-in-out infinite;
}}
.h-card-title {{
    font-size: 1.55rem; font-weight: 900; color: #ffffff;
    letter-spacing: -0.03em; line-height: 1.1; margin-bottom: 6px;
    text-shadow: 0 2px 12px rgba(0,0,0,0.3);
}}
.h-card-sub {{
    font-size: 0.8rem; font-weight: 600; color: rgba(255,255,255,0.75);
    margin-bottom: 16px; line-height: 1.5;
}}
.h-divider {{
    height: 1px; margin: 14px 0;
    background: linear-gradient(90deg, rgba(255,255,255,0.25), rgba(255,255,255,0.05), transparent);
}}
.h-desc {{
    font-size: 0.76rem; color: rgba(255,255,255,0.82);
    line-height: 1.75; margin-bottom: 20px;
    font-weight: 400;
}}
.h-pills {{ display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 4px; }}
.h-pill {{
    font-size: 0.63rem; font-weight: 700;
    color: rgba(255,255,255,0.95);
    background: rgba(255,255,255,0.14);
    border: 1px solid rgba(255,255,255,0.25);
    border-radius: 99px; padding: 4px 12px;
    white-space: nowrap;
    backdrop-filter: blur(4px);
}}

/* ── Stats bar ── */
.h-stats {{
    display: flex; justify-content: space-around; align-items: center;
    background: linear-gradient(135deg, #0a0f2e, #0d1b4b);
    border: 1px solid rgba(99,179,237,0.15);
    border-radius: 16px; padding: 20px 32px;
    margin-top: 8px;
    animation: hFadeUp 0.7s ease both;
}}
.h-stat {{ text-align: center; }}
.h-stat-val {{
    font-size: 1.5rem; font-weight: 900; color: #63b3ed;
    letter-spacing: -0.04em; line-height: 1;
}}
.h-stat-lbl {{
    font-size: 0.6rem; color: rgba(148,163,184,0.7);
    font-weight: 600; letter-spacing: 0.1em;
    text-transform: uppercase; margin-top: 4px;
}}
.h-stat-div {{
    width: 1px; height: 36px;
    background: linear-gradient(180deg, transparent, rgba(99,179,237,0.3), transparent);
}}
</style>

<div class="h-hero">
  <div class="h-eyebrow">⚡ Convin Intelligence Suite</div>
  <div class="h-brand">Convin <span>Data Labs</span></div>
  <div class="h-tagline">One platform. Complete conversation intelligence.</div>
  <div class="h-sub">Select a workspace below to continue</div>
</div>""", unsafe_allow_html=True)

    _col_cdl, _col_sense = st.columns(2)

    with _col_cdl:
        st.markdown("""
<div class="h-card h-card-cdl">
  <span class="h-icon">📊</span>
  <div class="h-card-title">Convin Data Labs</div>
  <div class="h-card-sub">Track every insight. Own every relationship.</div>
  <div class="h-divider"></div>
  <div class="h-desc">
    Centralised insights report feedback, stakeholder email campaigns,
    client management and real-time KPI tracking — all in one place.
  </div>
  <div class="h-pills">
    <span class="h-pill">📬 Campaigns</span>
    <span class="h-pill">⭐ CSAT</span>
    <span class="h-pill">📧 Email delivery</span>
    <span class="h-pill">🏢 Clients</span>
    <span class="h-pill">📈 KPIs</span>
  </div>
</div>""", unsafe_allow_html=True)
        if st.button("Open CDL Dashboard →", key="home_enter_cdl", use_container_width=True, type="primary"):
            st.session_state["app_mode"] = "CDL"
            st.session_state["current_page"] = "Overview"
            st.rerun()

    with _col_sense:
        st.markdown("""
<div class="h-card h-card-sense">
  <span class="h-icon">🎯</span>
  <div class="h-card-title">Convin Sense Audit</div>
  <div class="h-card-sub">Auto-score every call. Never miss a failure.</div>
  <div class="h-divider"></div>
  <div class="h-desc">
    Automated QA scoring, bot failure intelligence, tier-based parameter analysis,
    auditor leaderboards and priority action plans — powered by Convin Sense.
  </div>
  <div class="h-pills">
    <span class="h-pill">🤖 Auto QA</span>
    <span class="h-pill">🧠 Bot intelligence</span>
    <span class="h-pill">👤 Leaderboard</span>
    <span class="h-pill">📊 Tier analysis</span>
    <span class="h-pill">⚡ Auto-fail</span>
  </div>
</div>""", unsafe_allow_html=True)
        if st.button("Open Sense Audit →", key="home_enter_sense", use_container_width=True, type="primary"):
            st.session_state["app_mode"] = "Audit"
            st.session_state["current_page"] = "Audit"
            st.rerun()

    st.markdown("""
<div class="h-stats">
  <div class="h-stat"><div class="h-stat-val">Tier 1–3</div><div class="h-stat-lbl">QA Parameters</div></div>
  <div class="h-stat-div"></div>
  <div class="h-stat"><div class="h-stat-val">Auto</div><div class="h-stat-lbl">Scoring & Fail Detection</div></div>
  <div class="h-stat-div"></div>
  <div class="h-stat"><div class="h-stat-val">Live</div><div class="h-stat-lbl">Supabase Sync</div></div>
  <div class="h-stat-div"></div>
  <div class="h-stat"><div class="h-stat-val">100%</div><div class="h-stat-lbl">Audit Coverage</div></div>
</div>""", unsafe_allow_html=True)


# ─── Overview ─────────────────────────────────────────────────────────────────

def render_overview():
    st.markdown('<hr style="border:none;border-top:1px solid rgba(61,130,245,0.1);margin:4px 0 20px;">', unsafe_allow_html=True)

    st.markdown("""<div class="page-header">
        <div class="page-header-icon">📊</div>
        <div class="page-header-text">
            <div class="page-title">Overview</div>
            <div class="page-sub">Convin Data Labs · Insights Report Feedback Dashboard</div>
        </div>
    </div>""", unsafe_allow_html=True)

    # ── Real-time client & email activity snapshot ────────────────────────────
    _ov_clients   = client_store.load()
    _ov_sent      = sent_store.load()
    _ov_delivered = sum(len(r.get("sent_to", [])) for r in _ov_sent)
    _ov_unique_cl = len({r.get("client","") for r in _ov_sent if r.get("client","")})
    _ov_failed    = sum(len(r.get("failed", [])) for r in _ov_sent)
    _ov_success   = round((_ov_delivered / (_ov_delivered + _ov_failed) * 100), 1) if (_ov_delivered + _ov_failed) else 100.0

    st.markdown('<div class="section-chip">📬 Client Activity (Last 30 Days)</div>', unsafe_allow_html=True)
    st.markdown(f"""<div class="stats-grid" style="grid-template-columns:repeat(5,1fr);margin-bottom:1.2rem;">
        <div class="stat-card" style="border-top:2px solid #2563EB;">
            <div style="color:#2a5080;font-size:0.6rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">Clients</div>
            <div style="background:var(--gradient-brand);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;font-size:1.6rem;font-weight:800;">{len(_ov_clients)}</div>
        </div>
        <div class="stat-card" style="border-top:2px solid #2563EB;">
            <div style="color:#2a5080;font-size:0.6rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">Campaigns Sent</div>
            <div style="color:#2563EB;font-size:1.6rem;font-weight:800;">{len(_ov_sent)}</div>
        </div>
        <div class="stat-card" style="border-top:2px solid #0ebc6e;">
            <div style="color:#2a5080;font-size:0.6rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">Emails Delivered</div>
            <div style="color:#0ebc6e;font-size:1.6rem;font-weight:800;">{_ov_delivered}</div>
        </div>
        <div class="stat-card" style="border-top:2px solid #2563EB;">
            <div style="color:#2a5080;font-size:0.6rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">Clients Reached</div>
            <div style="color:#2563EB;font-size:1.6rem;font-weight:800;">{_ov_unique_cl}</div>
        </div>
        <div class="stat-card" style="border-top:2px solid {'#dc2626' if _ov_failed else '#0ebc6e'};">
            <div style="color:#2a5080;font-size:0.6rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">Delivery Rate</div>
            <div style="color:{'#dc2626' if _ov_success < 90 else '#0ebc6e'};font-size:1.6rem;font-weight:800;">{_ov_success}%</div>
        </div>
    </div>""", unsafe_allow_html=True)

    # Recent send activity list (last 5)
    if _ov_sent:
        _ov_recent5 = _ov_sent[:5]
        rows_html = "".join(
            f'<div style="display:flex;align-items:center;gap:10px;padding:8px 12px;'
            f'border-bottom:1px solid rgba(61,130,245,0.07);">'
            f'<div style="width:7px;height:7px;border-radius:50%;background:linear-gradient(135deg,#0B1F3A,#2563EB);flex-shrink:0;"></div>'
            f'<div style="flex:1;min-width:0;">'
            f'<div style="font-size:0.8rem;font-weight:600;color:#0d1d3a;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">'
            f'{r.get("subject","(no subject)")}</div>'
            f'<div style="font-size:0.69rem;color:#5588bb;">'
            f'{"🏢 " + r["client"] + " · " if r.get("client") else ""}'
            f'{len(r.get("sent_to",[]))} recipient{"s" if len(r.get("sent_to",[]))!=1 else ""}'
            f'</div></div>'
            f'<div style="font-size:0.67rem;color:#7a99bb;flex-shrink:0;">{r.get("date","")}</div>'
            f'</div>'
            for r in _ov_recent5
        )
        st.markdown(
            f'<div style="background:#fff;border:1px solid rgba(61,130,245,0.15);border-radius:12px;'
            f'padding:4px 0;margin-bottom:1.4rem;">'
            f'<div style="padding:10px 14px 6px;color:#2a5080;font-size:0.7rem;font-weight:700;'
            f'letter-spacing:0.08em;text-transform:uppercase;">Recent Campaigns</div>'
            + rows_html + '</div>',
            unsafe_allow_html=True,
        )

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
        actions_html = _card("Recommended Actions",  s.get("actions", []), "#fdf8ff", "#f0e8f8", "#7a1558", "#d22c84")

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

            comments_text = "\n".join(
                f'- {r["name"]} ({r["email"]}): rated {r["rating"]}/5 on {r["date"]}'
                for r in respondents
            ) or "No detailed feedback available."

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
    "Active":   ("rgba(14,188,110,0.12)", "#22e885", "#0ebc6e"),
    "At Risk":  ("rgba(251,191,36,0.12)",  "#fbbf24", "#f59e0b"),
    "Inactive": ("rgba(100,116,139,0.12)", "#7788aa", "#556688"),
}

_AVATAR_GRADS = [
    ("linear-gradient(135deg,#d22c84,#fb6069 52%,#2d84f1)", "#fff"),
    ("linear-gradient(135deg,#059669,#34d399)", "#fff"),
    ("linear-gradient(135deg,#7c3aed,#a78bfa)", "#fff"),
    ("linear-gradient(135deg,#d97706,#fbbf24)", "#fff"),
    ("linear-gradient(135deg,#0284c7,#38bdf8)", "#fff"),
    ("linear-gradient(135deg,#db2777,#f472b6)", "#fff"),
]


def _avatar(company: str, size: int = 40) -> str:
    words = [w for w in company.split() if w]
    if len(words) >= 2:
        initials = (words[0][0] + words[1][0]).upper()
    elif words:
        initials = words[0][:2].upper()
    else:
        initials = "??"
    grad, color = _AVATAR_GRADS[abs(hash(company)) % len(_AVATAR_GRADS)]
    return (
        f'<div style="width:{size}px;height:{size}px;border-radius:{size//3}px;'
        f'background:{grad};color:{color};display:flex;align-items:center;'
        f'justify-content:center;font-size:{size//3}px;font-weight:800;'
        f'flex-shrink:0;letter-spacing:0.02em;">{initials}</div>'
    )


def _clients_detail_panel(c: dict, all_clients: list):
    """Right-panel: full client detail + live edit + email history."""
    cid            = c["id"]
    current_emails = list(c.get("emails", []))
    confirm_del    = st.session_state.get(f"cdel_{cid}", False)

    # ── Big avatar + name header ───────────────────────────────────────────────
    status_bg, status_border, status_text = _STATUS_CFG.get(
        c.get("status", "Active"), _STATUS_CFG["Active"]
    )
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:16px;'
        f'background:#fff;border:1px solid rgba(61,130,245,0.18);border-radius:16px;'
        f'padding:20px 24px;margin-bottom:16px;box-shadow:0 4px 20px rgba(61,130,245,0.08);">'
        f'{_avatar(c.get("company",""), size=56)}'
        f'<div style="flex:1;min-width:0;">'
        f'<div style="font-size:1.15rem;font-weight:800;color:#0d1d3a;margin-bottom:2px;'
        f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{c.get("company","")}</div>'
        f'<div style="font-size:0.82rem;color:#3a6699;">'
        f'{"👤 " + c["contact"] if c.get("contact") else "No contact person"}</div>'
        f'</div>'
        f'<div style="background:{status_bg};border:1px solid {status_border};border-radius:20px;'
        f'padding:4px 14px;font-size:0.72rem;font-weight:700;color:{status_text};'
        f'white-space:nowrap;">{c.get("status","Active")}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Tabs: Details | History ────────────────────────────────────────────────
    tab_det, tab_hist = st.tabs(["✏️  Details & Edit", "📧  Email History"])

    # ── Details tab ───────────────────────────────────────────────────────────
    with tab_det:
        with st.form(f"det_f_{cid}"):
            d1, d2 = st.columns(2)
            with d1:
                new_company = st.text_input("Company Name", value=c.get("company", ""))
            with d2:
                new_contact = st.text_input("Contact Person", value=c.get("contact", ""))

            new_status = st.selectbox(
                "Status", options=["Active", "At Risk", "Inactive"],
                index=["Active", "At Risk", "Inactive"].index(c.get("status", "Active")),
            )
            new_tags  = st.text_input("Tags (comma-separated)",
                                      value=", ".join(c.get("tags", [])),
                                      placeholder="Enterprise, Q1, High Priority")
            new_notes = st.text_area("Notes", value=c.get("notes", ""), height=90,
                                     placeholder="Client context, renewal dates…")

            sb1, sb2 = st.columns(2)
            with sb1:
                saved = st.form_submit_button("💾  Save Changes", type="primary",
                                              use_container_width=True)
            with sb2:
                cancelled = st.form_submit_button("✕  Cancel", use_container_width=True)

            if saved:
                client_store.update(cid, {
                    "company": new_company.strip(),
                    "contact": new_contact.strip(),
                    "status":  new_status,
                    "tags":    [t.strip() for t in new_tags.split(",") if t.strip()],
                    "notes":   new_notes.strip(),
                })
                st.toast("Saved.", icon="✅")
                st.rerun()
            if cancelled:
                st.rerun()

        # ── Email addresses ────────────────────────────────────────────────────
        st.markdown(
            '<div style="color:#2a5080;font-size:0.72rem;font-weight:700;'
            'text-transform:uppercase;letter-spacing:0.06em;margin:16px 0 8px;">📧 Email Addresses</div>',
            unsafe_allow_html=True,
        )
        for idx, em in enumerate(current_emails):
            em_c1, em_c2 = st.columns([8, 1])
            with em_c1:
                st.markdown(
                    f'<div style="background:#f0f8ff;border:1px solid rgba(61,130,245,0.2);'
                    f'border-radius:8px;padding:8px 14px;font-size:0.83rem;color:#1e3a5f;">'
                    f'✉&nbsp; {em}</div>',
                    unsafe_allow_html=True,
                )
            with em_c2:
                if st.button("✕", key=f"rem_em_{cid}_{idx}", use_container_width=True,
                             help="Remove email"):
                    client_store.update(cid, {
                        "emails": [e for j, e in enumerate(current_emails) if j != idx]
                    })
                    st.toast(f"Removed {em}", icon="🗑")
                    st.rerun()

        add_c1, add_c2 = st.columns([8, 1])
        with add_c1:
            new_em = st.text_input("add_email_inp", key=f"new_em_{cid}",
                                   placeholder="Add email address…",
                                   label_visibility="collapsed")
        with add_c2:
            if st.button("＋", key=f"add_em_{cid}", use_container_width=True, help="Add email"):
                if new_em.strip():
                    client_store.update(cid, {"emails": current_emails + [new_em.strip()]})
                    st.toast(f"Added {new_em.strip()}", icon="✅")
                    st.rerun()

        # ── Delete client ──────────────────────────────────────────────────────
        st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)
        if not confirm_del:
            if st.button("🗑  Remove Client", key=f"del_btn_{cid}",
                         use_container_width=True):
                st.session_state[f"cdel_{cid}"] = True
                st.rerun()
        else:
            st.warning("Are you sure? This cannot be undone.")
            conf1, conf2 = st.columns(2)
            with conf1:
                if st.button("⚠️  Yes, delete", key=f"conf_del_{cid}",
                             type="primary", use_container_width=True):
                    client_store.delete(cid)
                    st.session_state.pop("clients_sel_id", None)
                    for _k in [k for k in st.session_state if cid in k]:
                        del st.session_state[_k]
                    st.toast(f"Removed {c.get('company','client')}", icon="🗑")
                    st.rerun()
            with conf2:
                if st.button("Cancel", key=f"cancel_del_{cid}",
                             use_container_width=True):
                    st.session_state.pop(f"cdel_{cid}", None)
                    st.rerun()

    # ── History tab ───────────────────────────────────────────────────────────
    with tab_hist:
        history = client_emails_store.get_for_client(c.get("company", ""))
        if not history:
            st.markdown(
                '<div style="text-align:center;padding:40px 20px;color:#7a99bb;font-size:0.84rem;">'
                '📭 No emails sent to this client yet.</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div style="color:#2a5080;font-size:0.72rem;font-weight:700;'
                f'text-transform:uppercase;letter-spacing:0.06em;margin-bottom:12px;">'
                f'{len(history)} email{"s" if len(history)!=1 else ""} sent</div>',
                unsafe_allow_html=True,
            )
            for h in history:
                sent_pills = " ".join(
                    f'<span style="display:inline-block;background:rgba(61,130,245,0.07);'
                    f'border:1px solid rgba(61,130,245,0.18);border-radius:5px;'
                    f'padding:2px 8px;font-size:0.68rem;color:#1e3a5f;">✉ {e}</span>'
                    for e in h["sent_to"]
                )
                attach_html = (
                    f'<span style="color:#7a99bb;font-size:0.68rem;">📎 {h["attachment_name"]}</span>'
                ) if h.get("attachment_name") else ""
                st.markdown(
                    f'<div style="background:#fff;border:1px solid rgba(61,130,245,0.15);'
                    f'border-radius:10px;padding:12px 14px;margin-bottom:8px;">'
                    f'<div style="display:flex;justify-content:space-between;align-items:flex-start;'
                    f'gap:8px;margin-bottom:6px;">'
                    f'<div style="font-size:0.84rem;font-weight:700;color:#0d1d3a;flex:1;">'
                    f'{h["subject"] or "(no subject)"}</div>'
                    f'<span style="font-size:0.65rem;color:#7a99bb;white-space:nowrap;">'
                    f'{h["date"]}</span></div>'
                    f'<div style="display:flex;flex-wrap:wrap;gap:5px;margin-bottom:6px;">'
                    f'{sent_pills}</div>'
                    + (f'<div style="color:#3a6699;font-size:0.69rem;margin-bottom:4px;">'
                       f'🎨 {h["template_name"]}</div>' if h.get("template_name") else '')
                    + (attach_html + '<br>' if attach_html else '')
                    + (f'<div style="color:#2a5080;font-size:0.71rem;line-height:1.5;margin-top:4px;'
                       f'padding:6px 10px;background:rgba(61,130,245,0.04);border-radius:6px;">'
                       f'{h["body_preview"][:150]}{"…" if len(h["body_preview"])>150 else ""}</div>'
                       if h.get("body_preview") else '')
                    + '</div>',
                    unsafe_allow_html=True,
                )


def _clients_add_panel():
    """Right-panel: add new client form."""
    st.markdown(
        '<div style="font-size:1rem;font-weight:700;color:#0d1d3a;margin-bottom:16px;">➕ New Client</div>',
        unsafe_allow_html=True,
    )
    with st.form("add_client_form", clear_on_submit=True):
        fc1, fc2 = st.columns(2)
        with fc1:
            company = st.text_input("Company Name *", placeholder="e.g. Acme Corp")
        with fc2:
            contact = st.text_input("Contact Person", placeholder="e.g. John Smith")

        st.markdown("**Email Addresses** (at least one required)")
        ec1, ec2, ec3 = st.columns(3)
        with ec1:
            e1 = st.text_input("Primary Email *", placeholder="primary@company.com")
        with ec2:
            e2 = st.text_input("Email 2", placeholder="cc@company.com")
        with ec3:
            e3 = st.text_input("Email 3", placeholder="optional@company.com")

        tags_raw = st.text_input("Tags (comma-separated)", placeholder="Enterprise, Q1, High Priority")
        notes    = st.text_area("Notes", placeholder="Client context, renewal dates…", height=80)

        sb1, sb2 = st.columns(2)
        with sb1:
            submitted = st.form_submit_button("💾  Save Client", type="primary",
                                              use_container_width=True)
        with sb2:
            cancel_add = st.form_submit_button("✕  Cancel", use_container_width=True)

        if submitted:
            if not company.strip():
                st.error("Company name is required.")
            elif not any([e1.strip(), e2.strip(), e3.strip()]):
                st.error("At least one email address is required.")
            else:
                emails = [e for e in [e1, e2, e3] if e.strip()]
                tags   = [t.strip() for t in tags_raw.split(",") if t.strip()]
                new_c, err = client_store.add(
                    company.strip(), contact.strip(), emails, "Active", tags, notes.strip()
                )
                if err:
                    st.error(f"Could not save: {err}")
                else:
                    st.session_state["clients_mode"] = "view"
                    st.session_state["clients_sel_id"] = new_c["id"]
                    st.toast(f"✓ {company} added!", icon="✅")
                    st.rerun()
        if cancel_add:
            st.session_state["clients_mode"] = "view"
            st.rerun()


def render_clients():
    # ── Session-state defaults ─────────────────────────────────────────────────
    if "clients_sel_id" not in st.session_state:
        st.session_state["clients_sel_id"] = None
    if "clients_mode" not in st.session_state:
        st.session_state["clients_mode"] = "view"   # "view" | "add"

    # ── Supabase connection diagnostic ────────────────────────────────────────
    with st.expander("🔌 Supabase connection test", expanded=False):
        url = st.secrets.get("SUPABASE_URL", "")
        key = st.secrets.get("SUPABASE_KEY", "")
        masked_url = url if not url else (url[:12] + "..." + url[-12:] if len(url) > 28 else url)
        masked_key = ("set ✓" if key else "MISSING ✗")
        st.code(f"SUPABASE_URL = {masked_url or 'MISSING ✗'}\nSUPABASE_KEY = {masked_key}")
        if st.button("Run connection test", key="sb_conn_test"):
            if not url or not key:
                st.error("One or both secrets are missing — check Streamlit Cloud → Settings → Secrets")
            else:
                try:
                    from supabase import create_client as _cc
                    _client = _cc(url, key)
                    _res = _client.table("clients").select("id").limit(1).execute()
                    st.success(f"Connected — clients table reachable. Rows sampled: {len(_res.data)}")
                except Exception as _e:
                    st.error(f"Connection failed: {_e}")

    all_clients = client_store.load()

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown("""<div class="page-header">
        <div class="page-header-icon">🏢</div>
        <div class="page-header-text">
            <div class="page-title">Client Repository</div>
            <div class="page-sub">Manage clients and view their complete email history.</div>
        </div>
    </div>""", unsafe_allow_html=True)

    tab_repo, tab_hist = st.tabs(["🏢 Repository", "📋 Email History"])

    # ─── Repository tab ───────────────────────────────────────────────────────
    with tab_repo:
        # ── Stats row ─────────────────────────────────────────────────────────
        total_em  = sum(len(c.get("emails", [])) for c in all_clients)
        active_n  = sum(1 for c in all_clients if c.get("status") == "Active")
        at_risk_n = sum(1 for c in all_clients if c.get("status") == "At Risk")

        st.markdown(f"""<div class="stats-grid" style="grid-template-columns:repeat(4,1fr);margin-bottom:16px;">
            <div class="stat-card" style="border-top:2px solid #2563EB;">
                <div style="color:#2a5080;font-size:0.6rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">Total Clients</div>
                <div style="background:var(--gradient-brand);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;font-size:1.8rem;font-weight:800;letter-spacing:-0.03em;">{len(all_clients)}</div>
            </div>
            <div class="stat-card" style="border-top:2px solid #2563EB;">
                <div style="color:#2a5080;font-size:0.6rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">Email Addresses</div>
                <div style="color:#2563EB;font-size:1.8rem;font-weight:800;">{total_em}</div>
            </div>
            <div class="stat-card" style="border-top:2px solid #0ebc6e;">
                <div style="color:#2a5080;font-size:0.6rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">Active</div>
                <div style="color:#0ebc6e;font-size:1.8rem;font-weight:800;">{active_n}</div>
            </div>
            <div class="stat-card" style="border-top:2px solid #f59e0b;">
                <div style="color:#2a5080;font-size:0.6rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">At Risk</div>
                <div style="color:#f59e0b;font-size:1.8rem;font-weight:800;">{at_risk_n}</div>
            </div>
        </div>""", unsafe_allow_html=True)

        # ── Split pane: left list | right detail ──────────────────────────────
        left_col, right_col = st.columns([2, 3], gap="medium")

        # ────── LEFT PANEL ────────────────────────────────────────────────────
        with left_col:
            search = st.text_input("", placeholder="🔍  Search clients…",
                                   label_visibility="collapsed", key="cl_search")
            sf1, sf2 = st.columns([3, 2])
            with sf1:
                status_filter = st.selectbox("Status", ["All", "Active", "At Risk", "Inactive"],
                                             label_visibility="collapsed", key="cl_status_filter")
            with sf2:
                if st.button("➕  Add Client", use_container_width=True, key="cl_add_btn"):
                    st.session_state["clients_mode"] = "add"
                    st.session_state["clients_sel_id"] = None
                    st.rerun()

            filtered = all_clients
            if search:
                q = search.lower()
                filtered = [c for c in filtered if
                            q in c.get("company", "").lower() or
                            q in c.get("contact", "").lower() or
                            any(q in e.lower() for e in c.get("emails", [])) or
                            any(q in t.lower() for t in c.get("tags", []))]
            if status_filter != "All":
                filtered = [c for c in filtered if c.get("status") == status_filter]

            st.markdown(
                f'<div style="font-size:0.72rem;color:#7a99bb;font-weight:600;'
                f'margin:8px 0 6px;">{len(filtered)} client{"s" if len(filtered)!=1 else ""}</div>',
                unsafe_allow_html=True,
            )

            sel_id = st.session_state.get("clients_sel_id")
            if not filtered:
                st.markdown(
                    '<div style="text-align:center;padding:40px 16px;color:#7a99bb;font-size:0.82rem;">'
                    'No clients found.</div>',
                    unsafe_allow_html=True,
                )
            for c in filtered:
                cid = c["id"]
                is_sel = (sel_id == cid)
                st_bg, st_border, st_col = _STATUS_CFG.get(c.get("status", "Active"), _STATUS_CFG["Active"])
                em_count = len(c.get("emails", []))
                row_bg     = "#e8f0ff" if is_sel else "#fff"
                row_border = "rgba(61,130,245,0.55)" if is_sel else "rgba(61,130,245,0.15)"
                row_lborder = "3px solid #2563EB" if is_sel else "3px solid transparent"
                st.markdown(
                    f'<div style="background:{row_bg};border:1px solid {row_border};'
                    f'border-left:{row_lborder};border-radius:10px;padding:10px 14px;'
                    f'margin-bottom:4px;display:flex;align-items:center;gap:12px;'
                    f'box-shadow:{"0 2px 10px rgba(61,130,245,0.15)" if is_sel else "none"};">'
                    f'{_avatar(c.get("company",""), size=36)}'
                    f'<div style="flex:1;min-width:0;">'
                    f'<div style="font-size:0.84rem;font-weight:700;color:#0d1d3a;'
                    f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">'
                    f'{c.get("company","")}</div>'
                    f'<div style="font-size:0.72rem;color:#5a7aaa;margin-top:1px;">'
                    f'{"👤 " + c["contact"] if c.get("contact") else ""}'
                    f'{"  ·  " if c.get("contact") else ""}'
                    f'{em_count} email{"s" if em_count!=1 else ""}</div>'
                    f'</div>'
                    f'<div style="background:{st_bg};border:1px solid {st_border};border-radius:10px;'
                    f'padding:2px 8px;font-size:0.65rem;font-weight:700;color:{st_col};'
                    f'white-space:nowrap;">{c.get("status","Active")}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                if st.button("Select", key=f"sel_{cid}", use_container_width=True,
                             type="primary" if is_sel else "secondary"):
                    st.session_state["clients_sel_id"] = cid
                    st.session_state["clients_mode"] = "view"
                    st.rerun()

            # Export at bottom of left panel
            if all_clients:
                st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)
                rows = [{"Company": c.get("company",""), "Contact": c.get("contact",""),
                         "Email": e, "Status": c.get("status",""),
                         "Tags": ", ".join(c.get("tags",[])),
                         "Notes": c.get("notes",""), "Added": c.get("added_at","")}
                        for c in all_clients for e in c.get("emails",[])]
                csv = pd.DataFrame(rows).to_csv(index=False)
                st.download_button("⬇️  Export CSV", data=csv,
                                   file_name="convin_clients.csv", mime="text/csv",
                                   use_container_width=True)
                import json as _json
                _bak = _json.dumps(all_clients, indent=2, ensure_ascii=False)
                st.download_button("⬇️  Backup JSON", data=_bak,
                                   file_name="clients_backup.json", mime="application/json",
                                   use_container_width=True)
                _uploaded = st.file_uploader("📥 Restore from backup", type=["json"],
                                             key="client_restore_upload",
                                             label_visibility="visible")
                if _uploaded:
                    try:
                        _restored = _json.loads(_uploaded.read())
                        if isinstance(_restored, list):
                            _save_err = client_store.save(_restored)
                            if _save_err:
                                st.error(f"Restore failed: {_save_err}")
                            else:
                                st.toast(f"Restored {len(_restored)} clients.", icon="✅")
                                st.rerun()
                        else:
                            st.error("Invalid backup file format.")
                    except Exception as _e:
                        st.error(f"Restore failed: {_e}")

        # ────── RIGHT PANEL ───────────────────────────────────────────────────
        with right_col:
            mode   = st.session_state.get("clients_mode", "view")
            sel_id = st.session_state.get("clients_sel_id")

            if mode == "add":
                _clients_add_panel()
            elif sel_id:
                sel_client = next((c for c in all_clients if c["id"] == sel_id), None)
                if sel_client:
                    _clients_detail_panel(sel_client, all_clients)
                else:
                    st.session_state["clients_sel_id"] = None
                    st.rerun()
            else:
                st.markdown(
                    '<div style="display:flex;flex-direction:column;align-items:center;'
                    'justify-content:center;padding:80px 20px;text-align:center;">'
                    '<div style="font-size:2.5rem;margin-bottom:16px;">🏢</div>'
                    '<div style="font-size:0.95rem;font-weight:600;color:#0d1d3a;margin-bottom:8px;">'
                    'Select a client</div>'
                    '<div style="font-size:0.82rem;color:#7a99bb;line-height:1.6;">'
                    'Click any client on the left to view and edit their details,<br>'
                    'or use <strong>➕ Add Client</strong> to create a new one.</div>'
                    '</div>',
                    unsafe_allow_html=True,
                )

    # ─── Email History tab ────────────────────────────────────────────────────
    with tab_hist:
        recent_sends = sent_store.load()
        total_recent = len(recent_sends)
        clients_emailed_30d = len({r.get("client","") for r in recent_sends if r.get("client","")})
        total_addrs = sum(len(c.get("emails", [])) for c in all_clients)

        st.markdown(f"""<div class="stats-grid" style="grid-template-columns:repeat(4,1fr);margin-bottom:16px;">
            <div class="stat-card" style="border-top:2px solid #2563EB;">
                <div style="color:#2a5080;font-size:0.6rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">Total Clients</div>
                <div style="background:var(--gradient-brand);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;font-size:1.8rem;font-weight:800;letter-spacing:-0.03em;">{len(all_clients)}</div>
            </div>
            <div class="stat-card" style="border-top:2px solid #2563EB;">
                <div style="color:#2a5080;font-size:0.6rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">Email Addresses</div>
                <div style="color:#2563EB;font-size:1.8rem;font-weight:800;">{total_addrs}</div>
            </div>
            <div class="stat-card" style="border-top:2px solid #2563EB;">
                <div style="color:#2a5080;font-size:0.6rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">Sends (30d)</div>
                <div style="color:#2563EB;font-size:1.8rem;font-weight:800;">{total_recent}</div>
            </div>
            <div class="stat-card" style="border-top:2px solid #0ebc6e;">
                <div style="color:#2a5080;font-size:0.6rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">Clients Emailed (30d)</div>
                <div style="color:#0ebc6e;font-size:1.8rem;font-weight:800;">{clients_emailed_30d}</div>
            </div>
        </div>""", unsafe_allow_html=True)

        if not all_clients:
            st.markdown(
                '<div style="text-align:center;padding:60px 20px;color:#7a99bb;font-size:0.84rem;">'
                'No clients yet. Add one in the Repository tab.</div>',
                unsafe_allow_html=True,
            )
        else:
            client_names = ["All Clients"] + [c["company"] for c in all_clients]
            sel_col, srch_col = st.columns([2, 3])
            with sel_col:
                selected = st.selectbox(
                    "client", client_names, key="ce_selector", label_visibility="collapsed"
                )
            with srch_col:
                ce_search = st.text_input(
                    "search", placeholder="🔍  Search by email or subject…",
                    key="ce_search", label_visibility="collapsed"
                )

            display_clients = all_clients if selected == "All Clients" else [
                c for c in all_clients if c["company"] == selected
            ]

            for c in display_clients:
                company = c.get("company", "")
                emails  = c.get("emails", [])
                history = client_emails_store.get_for_client(company)

                if ce_search:
                    q = ce_search.lower()
                    history = [
                        h for h in history
                        if q in h.get("subject","").lower()
                        or any(q in e.lower() for e in h.get("sent_to",[]))
                    ]

                status_cfg = _STATUS_CFG.get(c.get("status","Active"), _STATUS_CFG["Active"])

                with st.container(border=True):
                    col_av, col_info = st.columns([1, 10])
                    with col_av:
                        st.markdown(_avatar(company), unsafe_allow_html=True)
                    with col_info:
                        st.markdown(
                            f'<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">'
                            f'<span style="font-size:1rem;font-weight:700;color:#0d1d3a;">{company}</span>'
                            f'<span style="background:{status_cfg[0]};color:{status_cfg[2]};font-size:0.62rem;font-weight:700;'
                            f'padding:2px 10px;border-radius:99px;letter-spacing:0.06em;text-transform:uppercase;">'
                            f'{c.get("status","Active")}</span>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                        if c.get("contact"):
                            st.caption(f"👤 {c['contact']}")

                    st.markdown(
                        '<div style="color:#2a5080;font-size:0.72rem;font-weight:700;'
                        'text-transform:uppercase;letter-spacing:0.06em;margin:10px 0 6px;">📧 Email Addresses</div>',
                        unsafe_allow_html=True,
                    )
                    if emails:
                        email_pills = " ".join(
                            f'<span style="display:inline-block;background:#eef5ff;border:1px solid #b3d0ff;'
                            f'border-radius:8px;padding:6px 14px;margin:3px 4px 3px 0;font-size:0.82rem;'
                            f'color:#0d1d3a;font-weight:500;">✉&nbsp;{e}</span>'
                            for e in emails
                        )
                        st.markdown(email_pills, unsafe_allow_html=True)
                    else:
                        st.caption("No email addresses saved.")

                    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

                    hist_count = len(history)
                    st.markdown(
                        f'<div style="color:#2a5080;font-size:0.72rem;font-weight:700;'
                        f'text-transform:uppercase;letter-spacing:0.06em;margin-bottom:10px;">'
                        f'📨 Send History — {hist_count} email{"s" if hist_count!=1 else ""} (all time)</div>',
                        unsafe_allow_html=True,
                    )
                    if not history:
                        st.markdown(
                            '<div style="text-align:center;padding:16px;color:#7a99bb;font-size:0.82rem;'
                            'background:#f8faff;border-radius:8px;">📭 No emails sent to this client yet.</div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        for h in history:
                            sent_pills = " ".join(
                                f'<span style="display:inline-block;background:rgba(61,130,245,0.07);'
                                f'border:1px solid rgba(61,130,245,0.18);border-radius:5px;'
                                f'padding:2px 8px;font-size:0.68rem;color:#1e3a5f;">✉ {e}</span>'
                                for e in h.get("sent_to", [])
                            )
                            template_html = (
                                f'<div style="color:#3a6699;font-size:0.69rem;margin-bottom:4px;">🎨 {h["template_name"]}</div>'
                            ) if h.get("template_name") else ""
                            attach_html = (
                                f'<span style="color:#7a99bb;font-size:0.68rem;">📎 {h["attachment_name"]}</span><br>'
                            ) if h.get("attachment_name") else ""
                            preview_html = (
                                f'<div style="color:#2a5080;font-size:0.71rem;line-height:1.5;margin-top:6px;'
                                f'padding:6px 10px;background:rgba(61,130,245,0.04);border-radius:6px;">'
                                f'{h["body_preview"][:180]}{"…" if len(h["body_preview"])>180 else ""}</div>'
                            ) if h.get("body_preview") else ""
                            sender_html = (
                                f'<span style="color:#7a99bb;font-size:0.67rem;margin-left:8px;">via {h["sender"]}</span>'
                            ) if h.get("sender") else ""

                            st.markdown(
                                f'<div style="background:#ffffff;border:1px solid rgba(61,130,245,0.15);'
                                f'border-radius:10px;padding:12px 14px;margin-bottom:8px;">'
                                f'<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;margin-bottom:6px;">'
                                f'<div style="font-size:0.84rem;font-weight:700;color:#0d1d3a;flex:1;">'
                                f'{h.get("subject","") or "(no subject)"}{sender_html}</div>'
                                f'<span style="font-size:0.65rem;color:#7a99bb;white-space:nowrap;flex-shrink:0;">{h.get("date","")}</span>'
                                f'</div>'
                                f'<div style="display:flex;flex-wrap:wrap;gap:5px;margin-bottom:6px;">{sent_pills}</div>'
                                + template_html + attach_html + preview_html
                                + f'</div>',
                                unsafe_allow_html=True,
                            )

                st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)


# ─── Client Emails page ───────────────────────────────────────────────────────

def render_client_emails():
    all_clients = client_store.load()

    st.markdown("""<div class="page-header">
        <div class="page-header-icon">📋</div>
        <div class="page-header-text">
            <div class="page-title">Client Emails</div>
            <div class="page-sub">All client email addresses and their complete send history in one place.</div>
        </div>
    </div>""", unsafe_allow_html=True)

    # ── Stats ─────────────────────────────────────────────────────────────────
    total_addrs = sum(len(c.get("emails", [])) for c in all_clients)
    recent_sends = sent_store.load()
    total_recent = len(recent_sends)
    clients_emailed_30d = len({r.get("client","") for r in recent_sends if r.get("client","")})

    st.markdown(f"""<div class="stats-grid" style="grid-template-columns:repeat(4,1fr);">
        <div class="stat-card" style="border-top:2px solid #2563EB;">
            <div style="color:#2a5080;font-size:0.6rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">Total Clients</div>
            <div style="background:var(--gradient-brand);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;font-size:1.8rem;font-weight:800;letter-spacing:-0.03em;">{len(all_clients)}</div>
        </div>
        <div class="stat-card" style="border-top:2px solid #2563EB;">
            <div style="color:#2a5080;font-size:0.6rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">Email Addresses</div>
            <div style="color:#2563EB;font-size:1.8rem;font-weight:800;">{total_addrs}</div>
        </div>
        <div class="stat-card" style="border-top:2px solid #2563EB;">
            <div style="color:#2a5080;font-size:0.6rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">Sends (30d)</div>
            <div style="color:#2563EB;font-size:1.8rem;font-weight:800;">{total_recent}</div>
        </div>
        <div class="stat-card" style="border-top:2px solid #0ebc6e;">
            <div style="color:#2a5080;font-size:0.6rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">Clients Emailed (30d)</div>
            <div style="color:#0ebc6e;font-size:1.8rem;font-weight:800;">{clients_emailed_30d}</div>
        </div>
    </div>""", unsafe_allow_html=True)

    if not all_clients:
        st.markdown(
            '<div style="text-align:center;padding:60px 20px;color:#7a99bb;font-size:0.84rem;">'
            'No clients yet. Add one in the Clients page.</div>',
            unsafe_allow_html=True,
        )
        return

    # ── Client selector ───────────────────────────────────────────────────────
    client_names = ["All Clients"] + [c["company"] for c in all_clients]
    sel_col, srch_col = st.columns([2, 3])
    with sel_col:
        selected = st.selectbox(
            "client", client_names, key="ce_selector", label_visibility="collapsed"
        )
    with srch_col:
        ce_search = st.text_input(
            "search", placeholder="🔍  Search by email or subject…",
            key="ce_search", label_visibility="collapsed"
        )

    display_clients = all_clients if selected == "All Clients" else [
        c for c in all_clients if c["company"] == selected
    ]

    for c in display_clients:
        company = c.get("company", "")
        emails  = c.get("emails", [])
        history = client_emails_store.get_for_client(company)

        # Apply search filter to history
        if ce_search:
            q = ce_search.lower()
            history = [
                h for h in history
                if q in h.get("subject","").lower()
                or any(q in e.lower() for e in h.get("sent_to",[]))
            ]

        status_cfg = _STATUS_CFG.get(c.get("status","Active"), _STATUS_CFG["Active"])

        with st.container(border=True):
            # ── Client header ─────────────────────────────────────────────────
            col_av, col_info = st.columns([1, 10])
            with col_av:
                st.markdown(_avatar(company), unsafe_allow_html=True)
            with col_info:
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">'
                    f'<span style="font-size:1rem;font-weight:700;color:#0d1d3a;">{company}</span>'
                    f'<span style="background:{status_cfg[0]};color:{status_cfg[2]};font-size:0.62rem;font-weight:700;'
                    f'padding:2px 10px;border-radius:99px;letter-spacing:0.06em;text-transform:uppercase;">'
                    f'{c.get("status","Active")}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                if c.get("contact"):
                    st.caption(f"👤 {c['contact']}")

            # ── Email addresses ───────────────────────────────────────────────
            st.markdown(
                '<div style="color:#2a5080;font-size:0.72rem;font-weight:700;'
                'text-transform:uppercase;letter-spacing:0.06em;margin:10px 0 6px;">📧 Email Addresses</div>',
                unsafe_allow_html=True,
            )
            if emails:
                email_pills = " ".join(
                    f'<span style="display:inline-block;background:#eef5ff;border:1px solid #b3d0ff;'
                    f'border-radius:8px;padding:6px 14px;margin:3px 4px 3px 0;font-size:0.82rem;'
                    f'color:#0d1d3a;font-weight:500;">✉&nbsp;{e}</span>'
                    for e in emails
                )
                st.markdown(email_pills, unsafe_allow_html=True)
            else:
                st.caption("No email addresses saved.")

            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

            # ── Send history ──────────────────────────────────────────────────
            hist_count = len(history)
            st.markdown(
                f'<div style="color:#2a5080;font-size:0.72rem;font-weight:700;'
                f'text-transform:uppercase;letter-spacing:0.06em;margin-bottom:10px;">'
                f'📨 Send History — {hist_count} email{"s" if hist_count!=1 else ""} (all time)</div>',
                unsafe_allow_html=True,
            )
            if not history:
                st.markdown(
                    '<div style="text-align:center;padding:16px;color:#7a99bb;font-size:0.82rem;'
                    'background:#f8faff;border-radius:8px;">📭 No emails sent to this client yet.</div>',
                    unsafe_allow_html=True,
                )
            else:
                for h in history:
                    sent_pills = " ".join(
                        f'<span style="display:inline-block;background:rgba(61,130,245,0.07);'
                        f'border:1px solid rgba(61,130,245,0.18);border-radius:5px;'
                        f'padding:2px 8px;font-size:0.68rem;color:#1e3a5f;">✉ {e}</span>'
                        for e in h.get("sent_to", [])
                    )
                    template_html = (
                        f'<div style="color:#3a6699;font-size:0.69rem;margin-bottom:4px;">🎨 {h["template_name"]}</div>'
                    ) if h.get("template_name") else ""
                    attach_html = (
                        f'<span style="color:#7a99bb;font-size:0.68rem;">📎 {h["attachment_name"]}</span><br>'
                    ) if h.get("attachment_name") else ""
                    preview_html = (
                        f'<div style="color:#2a5080;font-size:0.71rem;line-height:1.5;margin-top:6px;'
                        f'padding:6px 10px;background:rgba(61,130,245,0.04);border-radius:6px;">'
                        f'{h["body_preview"][:180]}{"…" if len(h["body_preview"])>180 else ""}</div>'
                    ) if h.get("body_preview") else ""
                    sender_html = (
                        f'<span style="color:#7a99bb;font-size:0.67rem;margin-left:8px;">via {h["sender"]}</span>'
                    ) if h.get("sender") else ""

                    st.markdown(
                        f'<div style="background:#ffffff;border:1px solid rgba(61,130,245,0.15);'
                        f'border-radius:10px;padding:12px 14px;margin-bottom:8px;">'
                        f'<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;margin-bottom:6px;">'
                        f'<div style="font-size:0.84rem;font-weight:700;color:#0d1d3a;flex:1;">'
                        f'{h.get("subject","") or "(no subject)"}{sender_html}</div>'
                        f'<span style="font-size:0.65rem;color:#7a99bb;white-space:nowrap;flex-shrink:0;">{h.get("date","")}</span>'
                        f'</div>'
                        f'<div style="display:flex;flex-wrap:wrap;gap:5px;margin-bottom:6px;">{sent_pills}</div>'
                        + template_html + attach_html + preview_html
                        + f'</div>',
                        unsafe_allow_html=True,
                    )

        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)


# ─── Draft helpers ────────────────────────────────────────────────────────────

STATUS_META = {
    "empty": ("#f1f5f9", "#94a3b8", "Empty"),
    "draft": ("#dcfce7", "#16a34a", "In Progress"),
    "ready": ("#fdf8ff", "#d22c84", "Ready"),
}

_TMPL_TEXT_COLORS = ["#c9a96e", "#d22c84", "#ffffff", "#a78bfa", "#8b5e3c",
                     "#06b6d4", "#ea580c", "#10b981", "#f97316",
                     "#ffffff", "#ffffff", "#d22c84"]
_TMPL_BG_COLORS   = ["#0d1b2a", "#fdf8ff", "#1e3a8a", "#13111f", "#f4ede0",
                     "#040d18", "#fff3e8", "#0b1f14", "#1a1a1a",
                     "#d22c84", "#2d3748", "#d22c84"]


def _single_image_slot(d: dict, url_key: str, cap_key: str, label: str, key_suffix: str):
    """Renders one image upload/paste slot — always visible, drag-and-drop enabled."""
    st.markdown(
        f'<div style="color:#475569;font-size:0.72rem;font-weight:700;letter-spacing:0.04em;'
        f'text-transform:uppercase;margin:10px 0 4px;">🖼 {label}</div>',
        unsafe_allow_html=True,
    )
    current_url = d.get(url_key, "")
    if current_url.startswith("data:") or (current_url.startswith("http") and current_url):
        if current_url.startswith("data:"):
            _, b64_part = current_url.split(",", 1)
            st.image(base64.b64decode(b64_part), width=300)
        else:
            st.image(current_url, width=300)
        if st.button("✕ Remove image", key=f"rm_{url_key}_{key_suffix}", use_container_width=False):
            d[url_key] = ""
            d[cap_key] = ""
            st.rerun()
    else:
        uploaded = st.file_uploader(
            f"Drag & drop or click to upload — PNG, JPG, PDF",
            type=["png", "jpg", "jpeg", "gif", "webp", "pdf"],
            key=f"up_{url_key}_{key_suffix}",
        )
        if uploaded:
            if uploaded.type == "application/pdf":
                import pypdfium2 as pdfium
                pdf = pdfium.PdfDocument(uploaded.read())
                img = pdf[0].render(scale=2).to_pil()
            else:
                img = Image.open(uploaded)
            img.thumbnail((1200, 1200), Image.LANCZOS)
            buf = io.BytesIO()
            if uploaded.type == "image/png":
                img.save(buf, format="PNG", optimize=True)
                mime = "image/png"
            else:
                img = img.convert("RGB")
                img.save(buf, format="JPEG", quality=82, optimize=True)
                mime = "image/jpeg"
            b64 = base64.b64encode(buf.getvalue()).decode()
            d[url_key] = f"data:{mime};base64,{b64}"
            st.rerun()
        d[url_key] = st.text_input(
            "Or paste image/PDF URL", value=current_url,
            key=f"url_{url_key}_{key_suffix}", placeholder="https://…",
        )
    d[cap_key] = st.text_input(
        "Caption (optional)", value=d.get(cap_key, ""),
        key=f"cap_{url_key}_{key_suffix}", placeholder="e.g. Monthly revenue chart",
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


def _attachment_slot(d: dict, key_suffix: str):
    """File attachment or URL — shown as 📎 block in the email + MIME attachment when sending."""
    st.markdown(
        '<div style="color:#64748b;font-size:0.75rem;font-weight:700;letter-spacing:0.06em;'
        'text-transform:uppercase;margin:14px 0 6px;">📎 Attachment</div>',
        unsafe_allow_html=True,
    )

    has_file = bool(d.get("attachment_data"))
    has_url  = bool(d.get("attachment_url"))

    if has_file:
        st.markdown(
            f'<div style="background:#fdf8ff;border:1px solid #f0e8f8;border-radius:8px;'
            f'padding:8px 12px;font-size:0.8rem;color:#d22c84;font-weight:600;margin-bottom:6px;">'
            f'📎 {d["attachment_name"]}</div>',
            unsafe_allow_html=True,
        )
        if st.button("✕ Remove attachment", key=f"rm_att_{key_suffix}"):
            d["attachment_data"] = ""
            d["attachment_name"] = ""
            d["attachment_mime"] = ""
            st.rerun()
    else:
        uploaded = st.file_uploader(
            "Upload file (PDF, Excel, Word, CSV, PPT…)",
            type=["pdf", "xlsx", "xls", "docx", "doc", "csv", "pptx", "ppt", "zip", "txt"],
            key=f"att_up_{key_suffix}",
        )
        if uploaded:
            d["attachment_data"] = base64.b64encode(uploaded.read()).decode()
            d["attachment_name"] = uploaded.name
            d["attachment_mime"] = uploaded.type or "application/octet-stream"
            d["attachment_url"]  = ""   # clear URL if file chosen
            st.rerun()

    st.markdown(
        '<div style="font-size:0.72rem;color:#94a3b8;margin:4px 0 4px;">— or paste a download URL —</div>',
        unsafe_allow_html=True,
    )
    d["attachment_url"] = st.text_input(
        "Attachment URL",
        value=d.get("attachment_url", ""),
        key=f"att_url_{key_suffix}",
        placeholder="https://docs.google.com/… or any download link",
        label_visibility="collapsed",
    )
    if d.get("attachment_url"):
        # Use the last path segment as the display name if no file upload
        if not d.get("attachment_name"):
            seg = d["attachment_url"].rstrip("/").split("/")[-1]
            d["attachment_name"] = seg or "Attachment"
        d["attachment_data"] = ""  # URL takes precedence over file


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
            border = "#d22c84" if is_sel else "#f0e8f8"
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
                d["body"]     = st.text_area("Email Body",  value=d["body"],     key=f"dbody_{i}",   height=120, placeholder="Write the main body of the email…")

                _screenshot_input(d, f"d{i}")
                _attachment_slot(d, f"d{i}")

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
                html_content = build_email_html(draft, draft.get("template", 1), **_email_font_kwargs())
                components.html(html_content, height=2200, scrolling=True)
            except Exception as e:
                st.error(f"Preview error: {e}")


# ─── Email Maker ──────────────────────────────────────────────────────────────

def render_email_maker():
    st.markdown("""<div class="page-header">
        <div class="page-header-icon">📧</div>
        <div class="page-header-text">
            <div class="page-title">Email Maker</div>
            <div class="page-sub">Compose, preview, and send insights report emails.</div>
        </div>
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
        with cc1: d["client"]     = st.text_input("Client Name", value=d["client"],   key=f"cc_client_{ci}", placeholder="e.g. Acme Corp")
        with cc2: d["report_link"] = st.text_input("Report URL",  value=d["report_link"], key=f"cc_link_{ci}", placeholder="https://docs.google.com/…")

        d["subject"]  = st.text_input(
            "Email Subject Line",
            value=d.get("subject", ""),
            key=f"cc_subj_{ci}",
            placeholder="e.g. Your February Analytics Report is Ready",
        )
        d["body"]     = st.text_area("Email Body",                    value=d["body"],     key=f"cc_body_{ci}", height=120, placeholder="Write the main body of the email…")

        _fs_opts = ["Small (13px)", "Normal (14px)", "Large (16px)", "X-Large (18px)"]
        _ff_opts = ["Default (Inter)", "Serif (Georgia)", "Classic (Times New Roman)", "Clean (Arial)"]
        _fscol, _ffcol = st.columns(2)
        with _fscol:
            st.selectbox("Font Size", _fs_opts, index=1, key="email_font_size_pick")
        with _ffcol:
            st.selectbox("Font Style", _ff_opts, index=0, key="email_font_family_pick")

        with st.expander("🖼  Images, Attachment & Survey (optional)", expanded=True):
            _screenshot_input(d, f"c{ci}")
            st.markdown("")
            _attachment_slot(d, f"c{ci}")
            st.markdown("")
            d["survey_question"] = st.text_input("Survey Question", value=d["survey_question"], key=f"cc_sq_{ci}")

        # ── Scoreboard ────────────────────────────────────────────────────────
        with st.expander("📊  Scoreboard (embed in email)", expanded=d.get("scoreboard_enabled", False)):
            _sb_enabled = st.toggle(
                "Include Scoreboard in email",
                value=d.get("scoreboard_enabled", False),
                key=f"cc_sb_on_{ci}",
            )
            d["scoreboard_enabled"] = _sb_enabled

            if _sb_enabled:
                d["scoreboard_title"] = st.text_input(
                    "Scoreboard Title",
                    value=d.get("scoreboard_title", "Performance Scoreboard"),
                    key=f"cc_sb_title_{ci}",
                )

                # Load params to offer as metric labels
                if "sense_custom_audit_params" not in st.session_state:
                    st.session_state["sense_custom_audit_params"] = param_store.load()
                _param_names = [p["name"] for p in st.session_state["sense_custom_audit_params"]]
                _param_map   = {p["name"]: p for p in st.session_state["sense_custom_audit_params"]}

                if "sb_rows" not in d or not isinstance(d.get("sb_rows"), list):
                    d["sb_rows"] = []

                st.markdown('<div style="font-size:0.7rem;color:#64748b;font-weight:600;margin-bottom:6px;">Metrics</div>', unsafe_allow_html=True)

                _rows_updated = []
                for _ri, _row in enumerate(d["sb_rows"]):
                    _rc1, _rc2, _rc3, _rc4 = st.columns([3, 1.5, 2.5, 0.6])
                    with _rc1:
                        _use_custom = _row.get("label", "") not in _param_names
                        _label_opts = _param_names + (["✏️ Custom…"] if _param_names else [])
                        if _param_names and not _use_custom:
                            _sel_idx = _param_names.index(_row["label"]) if _row["label"] in _param_names else 0
                            _sel     = st.selectbox("Metric", _label_opts, index=_sel_idx, key=f"sb_lbl_{ci}_{_ri}", label_visibility="collapsed")
                            if _sel == "✏️ Custom…":
                                _label = st.text_input("Custom label", value="", key=f"sb_cust_{ci}_{_ri}", label_visibility="collapsed")
                            else:
                                _label = _sel
                        else:
                            _label = st.text_input("Metric label", value=_row.get("label", ""), key=f"sb_lbl_t_{ci}_{_ri}", label_visibility="collapsed", placeholder="Metric label")
                    with _rc2:
                        _rtype_opts = list(_TYPE_LABELS.keys())
                        _rtype_src  = _param_map.get(_label, {}).get("input_type", _row.get("type", "text"))
                        _rtype_idx  = _rtype_opts.index(_rtype_src) if _rtype_src in _rtype_opts else 3
                        _rtype = st.selectbox("Type", _rtype_opts, index=_rtype_idx, format_func=lambda k: _TYPE_LABELS[k], key=f"sb_type_{ci}_{_ri}", label_visibility="collapsed")
                    with _rc3:
                        if _rtype == "scoring":
                            _val = str(st.slider("Score", 1, 5, int(_row.get("value", 3)) if str(_row.get("value", "3")).isdigit() else 3, key=f"sb_val_{ci}_{_ri}", label_visibility="collapsed"))
                        elif _rtype == "dropdown" and _label in _param_map:
                            _opts = _param_map[_label].get("options", ["Yes", "No"])
                            _cur  = _row.get("value", _opts[0]) if _row.get("value") in _opts else _opts[0]
                            _val  = st.selectbox("Value", _opts, index=_opts.index(_cur), key=f"sb_val_{ci}_{_ri}", label_visibility="collapsed")
                        elif _rtype == "number":
                            _val = str(st.number_input("Value", value=float(_row.get("value", 0)) if _row.get("value", "") else 0.0, key=f"sb_val_{ci}_{_ri}", label_visibility="collapsed"))
                        else:
                            _val = st.text_input("Value", value=str(_row.get("value", "")), key=f"sb_val_{ci}_{_ri}", label_visibility="collapsed", placeholder="e.g. 87%")
                    with _rc4:
                        if st.button("✕", key=f"sb_rm_{ci}_{_ri}", use_container_width=True, help="Remove row"):
                            continue  # skip this row
                    _rows_updated.append({"label": _label, "value": _val, "type": _rtype})

                d["sb_rows"] = _rows_updated
                d["scoreboard_rows"] = d["sb_rows"]

                if st.button("➕ Add Metric", key=f"sb_add_row_{ci}", use_container_width=False):
                    d["sb_rows"].append({"label": "", "value": "", "type": "text"})
                    d["scoreboard_rows"] = d["sb_rows"]
                    st.rerun()

                if not d["sb_rows"]:
                    st.caption("No metrics yet. Click ➕ Add Metric to start.")

        pc1, pc2, pc3, pc4 = st.columns(4)
        with pc1:
            if st.button("💾 Save", key=f"cc_save_{ci}", use_container_width=True):
                st.session_state.drafts[ci]["status"] = "draft"
                st.toast("Draft saved.", icon="💾")
                st.rerun()
        with pc2:
            if st.button("👁 Preview", key=f"cc_prev_{ci}", use_container_width=True):
                st.session_state[f"cc_show_prev_{ci}"] = not st.session_state.get(f"cc_show_prev_{ci}", False)
                st.rerun()
        with pc3:
            try:
                _dl_html = build_email_html(d, d.get("template", 1), **_email_font_kwargs())
                st.download_button(
                    "⬇️ HTML",
                    data=_dl_html,
                    file_name=f"{d['name'].replace(' ', '_')}.html",
                    mime="text/html",
                    use_container_width=True,
                    key=f"cc_dl_{ci}",
                )
            except Exception:
                st.button("⬇️ HTML", disabled=True, use_container_width=True, key=f"cc_dl_dis_{ci}")
        with pc4:
            if st.button("✅ Ready", key=f"cc_ready_{ci}", use_container_width=True, type="primary"):
                st.session_state.drafts[ci]["status"] = "ready"
                st.toast("Draft marked ready.", icon="✅")
                st.rerun()

        if st.session_state.get(f"cc_show_prev_{ci}", False):
            try:
                components.html(build_email_html(d, d.get("template", 1), **_email_font_kwargs()), height=2000, scrolling=True)
            except Exception as e:
                st.error(f"Preview error: {e}")

        st.markdown("---")

        # ── Step 3: Recipients ─────────────────────────────────────────────
        st.markdown('<div style="color:#64748b;font-size:0.7rem;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:8px;">③ Recipients</div>', unsafe_allow_html=True)

        all_emails: list = []

        if not repo_clients:
            st.info("No clients in repository yet. Go to **🏢 Clients** to add them first.")
        else:
            options = [f"{c['company']}  ({', '.join(c['emails'][:2])}{'…' if len(c['emails'])>2 else ''})" for c in repo_clients]
            selected_opts = st.multiselect(
                "Send to", options, default=[], key="compose_recipients",
                placeholder="Choose clients…",
                label_visibility="collapsed",
            )
            selected_clients = [c for c, opt in zip(repo_clients, options) if opt in selected_opts]
            all_emails = [e for c in selected_clients for e in c.get("emails", [])]

            if selected_clients:
                st.markdown(
                    f'<div style="color:#64748b;font-size:0.73rem;margin:6px 0 8px;">'
                    f'{len(selected_clients)} client{"s" if len(selected_clients) != 1 else ""} · {len(all_emails)} address{"es" if len(all_emails) != 1 else ""}</div>',
                    unsafe_allow_html=True,
                )

        adhoc_raw = st.text_input(
            "Additional recipients (comma-separated)",
            key="compose_adhoc",
            placeholder="extra@email.com, another@company.com",
        )
        adhoc_emails = [e.strip() for e in adhoc_raw.split(",") if e.strip() and "@" in e.strip()]
        all_emails = all_emails + adhoc_emails
        if adhoc_emails:
            st.markdown(
                f'<div style="color:#64748b;font-size:0.73rem;margin:2px 0 8px;">+ {len(adhoc_emails)} extra address{"es" if len(adhoc_emails) != 1 else ""}</div>',
                unsafe_allow_html=True,
            )

        st.markdown("---")

        # ── Step 4: Send ───────────────────────────────────────────────
        st.markdown('<div style="color:#64748b;font-size:0.7rem;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:10px;">④ Send</div>', unsafe_allow_html=True)

        sender_ready = bool(st.session_state.get("gmail_app_password"))
        if not sender_ready:
            st.warning("Connect your email sender in the sidebar first.")
        else:
            st.markdown(
                f'<div style="color:#16a34a;font-size:0.75rem;font-weight:600;margin-bottom:10px;">'
                f'✓ Sending from: {st.session_state.get("user_email","")}</div>',
                unsafe_allow_html=True,
            )

        # Decode attachment bytes for sending (if file was uploaded)
        _att_bytes = base64.b64decode(d["attachment_data"]) if d.get("attachment_data") else None
        _att_name  = d.get("attachment_name") or None
        _att_mime  = d.get("attachment_mime") or None

        send_col, test_col = st.columns([3, 1])
        with test_col:
            if st.button("🧪 Test to Me", key=f"test_send_{ci}", use_container_width=True,
                         disabled=not sender_ready, help="Send a test copy to your own email"):
                _test_addr = st.session_state.get("user_email", "")
                if _test_addr:
                    _subj = (d.get("subject") or "Test Email") + " [TEST]"
                    import uuid as _uuid
                    _send_id = str(_uuid.uuid4())[:8]
                    _fkw = _email_font_kwargs()
                    def _html_builder_test(addr):
                        return build_email_html(d, d.get("template", 1), send_id=_send_id, recipient_email=addr, **_fkw)
                    with st.spinner("Sending test…"):
                        _res = gmail_sender.send_report_email(
                            None, [_test_addr], _subj[:80],
                            build_email_html(d, d.get("template", 1), **_fkw),
                            _test_addr,
                            attachment_name=_att_name,
                            attachment_data=_att_bytes,
                            attachment_mime=_att_mime,
                            html_builder=_html_builder_test,
                        )
                    if _res["sent"]:
                        st.success(f"Test sent to {_test_addr}")
                        _, _log_err = sent_store.log_send(
                            draft_name=d["name"] + " [TEST]",
                            subject=(d.get("subject") or "Test Email") + " [TEST]",
                            template_num=d.get("template", 1),
                            template_name=TEMPLATE_NAMES[d.get("template", 1) - 1][0],
                            client=d.get("client", ""),
                            sent_to=_res["sent"],
                            failed=_res["failed"],
                            body_preview=d.get("body", ""),
                            record_id=_send_id,
                            sender=st.session_state.get("user_email", ""),
                            attachment_name=_att_name or "",
                            is_test=True,
                        )
                        if _log_err:
                            st.warning(f"Email sent but log failed to save: {_log_err}")
                    else:
                        for _f in _res["failed"]:
                            st.error(_f["error"])
                            if _f["email"] == "config":
                                st.session_state.pop("gmail_app_password", None)
                else:
                    st.warning("Sign in to use test send.")

        with send_col:
            if all_emails:
                if st.button(
                    f"📤  Send to {len(all_emails)} address{'es' if len(all_emails) != 1 else ''}",
                    type="primary", use_container_width=True,
                    disabled=not sender_ready,
                ):
                    _subject = (d.get("subject") or "Report from Convin Data Labs")[:80]
                    import uuid as _uuid
                    _send_id = str(_uuid.uuid4())[:8]
                    _fkw = _email_font_kwargs()
                    def _html_builder_prod(addr):
                        return build_email_html(d, d.get("template", 1), send_id=_send_id, recipient_email=addr, **_fkw)
                    with st.spinner(f"Sending to {len(all_emails)} recipient(s)…"):
                        result = gmail_sender.send_report_email(
                            None, all_emails, _subject,
                            build_email_html(d, d.get("template", 1), **_fkw),
                            st.session_state.get("user_email", ""),
                            attachment_name=_att_name,
                            attachment_data=_att_bytes,
                            attachment_mime=_att_mime,
                            html_builder=_html_builder_prod,
                        )
                    from datetime import datetime as _dt
                    st.session_state.send_log.insert(0, {
                        "time":   _dt.now().strftime("%H:%M"),
                        "draft":  d["name"],
                        "sent":   result["sent"],
                        "failed": result["failed"],
                    })
                    if result["sent"]:
                        st.success(f"✓ Sent to: {', '.join(result['sent'])}")
                        st.session_state.drafts[ci]["status"] = "ready"
                        _, _log_err = sent_store.log_send(
                            draft_name=d["name"],
                            subject=_subject,
                            template_num=d.get("template", 1),
                            template_name=TEMPLATE_NAMES[d.get("template", 1) - 1][0],
                            client=d.get("client", ""),
                            sent_to=result["sent"],
                            failed=result["failed"],
                            body_preview=d.get("body", ""),
                            record_id=_send_id,
                            sender=st.session_state.get("user_email", ""),
                            attachment_name=_att_name or "",
                            is_test=False,
                        )
                        if _log_err:
                            st.warning(f"Email sent but log failed to save: {_log_err}")
                        if d.get("client", "").strip():
                            from datetime import datetime as _dt2, timezone as _tz2
                            _hist_err = client_emails_store.log(
                                record_id=_send_id,
                                client_company=d["client"].strip(),
                                date=_dt2.now(_tz2.utc).strftime("%b %d, %Y"),
                                subject=_subject,
                                template_name=TEMPLATE_NAMES[d.get("template", 1) - 1][0],
                                sent_to=result["sent"],
                                body_preview=d.get("body", ""),
                                sender=st.session_state.get("user_email", ""),
                                attachment_name=_att_name or "",
                            )
                            if _hist_err:
                                st.warning(f"Client email history failed to save: {_hist_err}")
                    for fail in result["failed"]:
                        if fail["email"] in ("login", "config"):
                            st.error(fail["error"])
                            st.session_state.pop("gmail_app_password", None)
                        else:
                            st.error(f"✗ {fail['email']}: {fail['error']}")
            else:
                st.button("📤  Send", disabled=True, use_container_width=True, key="send_disabled",
                          help="Add at least one recipient above.")

        # ── Send Log ───────────────────────────────────────────────────
        if st.session_state.get("send_log"):
            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
            with st.expander(f"📋 Send Log  ({len(st.session_state['send_log'])} this session)", expanded=False):
                for _entry in st.session_state["send_log"][:20]:
                    _ok   = f"✓ {len(_entry['sent'])} sent"   if _entry["sent"]   else ""
                    _fail = f"✗ {len(_entry['failed'])} failed" if _entry["failed"] else ""
                    _parts = " · ".join(filter(None, [_ok, _fail]))
                    st.markdown(
                        f'<div style="display:flex;justify-content:space-between;align-items:center;'
                        f'padding:7px 0;border-bottom:1px solid #f1f5f9;font-size:0.78rem;">'
                        f'<span style="color:#0f172a;font-weight:600;">{_entry["draft"]}</span>'
                        f'<span style="color:#64748b;">{_parts}</span>'
                        f'<span style="color:#94a3b8;">{_entry["time"]}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

    # ── AI Grammar & Spell Check ───────────────────────────────────────────────
    with tab_ai:
        st.markdown('<div style="color:#0f172a;font-size:1rem;font-weight:600;margin-bottom:4px;">AI Writing Assistant</div>', unsafe_allow_html=True)
        st.caption("Polish your email body — fix formatting, spacing, and structure for a professional, client-friendly tone.")
        st.markdown("")

        # Source selector
        ai_source = st.radio("Text source:", ["Pick a draft", "Paste custom text"], horizontal=True, key="ai_source")

        if ai_source == "Pick a draft":
            draft_names = [d["name"] for d in st.session_state.drafts]
            ai_draft_name = st.selectbox("Select draft to check:", draft_names, key="ai_draft_pick")
            ai_idx = draft_names.index(ai_draft_name)
            ai_d = st.session_state.drafts[ai_idx]
            ai_text_parts = []
            if ai_d.get("body"):
                ai_text_parts.append(f"Body: {ai_d['body']}")
            ai_input = "\n\n".join(ai_text_parts) or ""
            st.markdown('<div style="color:#64748b;font-size:0.75rem;margin-bottom:6px;">Text from draft:</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:14px 16px;font-size:0.83rem;color:#475569;white-space:pre-wrap;min-height:60px;">{ai_input or "— draft is empty —"}</div>', unsafe_allow_html=True)
        else:
            ai_input = st.text_area("Paste your text here:", height=160, key="ai_custom_text",
                                    placeholder="Type or paste your headline, body, or any email text…")

        st.markdown("")
        if st.button("✨ Polish Email Body", type="primary", use_container_width=False, key="ai_check_btn"):
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
                        with st.spinner("Polishing email body…"):
                            _msg = _client.messages.create(
                                model="claude-haiku-4-5-20251001",
                                max_tokens=1024,
                                messages=[{
                                    "role": "user",
                                    "content": (
                                        "You are an expert in professional business communication.\n\n"
                                        "I will provide you with an email body that may have formatting and spacing issues. "
                                        "Your task is to:\n"
                                        "1. Fix formatting, spacing, and alignment issues\n"
                                        "2. Improve readability with proper paragraph breaks\n"
                                        "3. Keep the tone professional, polished, and client-friendly\n"
                                        "4. Do NOT change the meaning or content\n"
                                        "5. Do NOT add extra information\n"
                                        "6. Keep it concise and clean\n"
                                        "7. Structure it in a way that looks good in email (proper line breaks, sections)\n\n"
                                        "Reply in two clearly labelled sections:\n\n"
                                        "POLISHED TEXT:\n<the improved version>\n\n"
                                        "CHANGES MADE:\n<bullet list of what was improved, or 'No changes needed.' if already clean>\n\n"
                                        f"Email text:\n{ai_input}"
                                    ),
                                }],
                            )
                        _reply = _msg.content[0].text
                        if "POLISHED TEXT:" in _reply and "CHANGES MADE:" in _reply:
                            _corrected = _reply.split("POLISHED TEXT:")[1].split("CHANGES MADE:")[0].strip()
                            _changes   = _reply.split("CHANGES MADE:")[1].strip()
                        else:
                            _corrected = _reply
                            _changes   = ""

                        st.markdown('<div style="color:#059669;font-size:0.8rem;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;margin-bottom:8px;">Polished Text</div>', unsafe_allow_html=True)
                        st.markdown(f'<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:14px 16px;font-size:0.85rem;color:#14532d;white-space:pre-wrap;">{_corrected}</div>', unsafe_allow_html=True)

                        if _changes:
                            st.markdown('<div style="color:#d22c84;font-size:0.8rem;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;margin:14px 0 8px;">Changes Made</div>', unsafe_allow_html=True)
                            st.markdown(f'<div style="background:#fdf8ff;border:1px solid #f0e8f8;border-radius:8px;padding:14px 16px;font-size:0.83rem;color:#7a1558;white-space:pre-wrap;">{_changes}</div>', unsafe_allow_html=True)

                        # Apply to draft option
                        if ai_source == "Pick a draft" and _corrected:
                            st.markdown("")
                            if st.button("Apply corrected text to draft", key="ai_apply_btn"):
                                st.session_state.drafts[ai_idx]["body"] = _corrected
                                st.toast("Draft updated with corrected text.", icon="✅")
                                st.rerun()
                    except Exception as _e:
                        st.error(f"AI check failed: {_e}")


# ─── Sent Emails ──────────────────────────────────────────────────────────────

def render_sent():
    from datetime import datetime as _dt, timedelta, timezone as _tz

    all_records = sent_store.load()

    st.markdown("""<div class="page-header">
        <div class="page-header-icon">📤</div>
        <div class="page-header-text">
            <div class="page-title">Sent Emails</div>
            <div class="page-sub">Emails sent from this dashboard — last 30 days.</div>
        </div>
    </div>""", unsafe_allow_html=True)

    # ── Client filter at the top ──────────────────────────────────────────────
    repo_clients = client_store.load()
    client_names = [c["company"] for c in repo_clients]
    if client_names:
        selected_clients_filter = st.multiselect(
            "Filter by client", client_names,
            default=[],
            placeholder="All clients (select to filter)…",
            key="sent_client_filter",
            label_visibility="collapsed",
        )
    else:
        selected_clients_filter = []

    # ── Last 30 days filter (always applied, with option to see all) ──────────
    _cutoff_30 = _dt.now(_tz.utc) - timedelta(days=30)

    fc1, fc2 = st.columns([4, 1])
    with fc1:
        search = st.text_input("Search", placeholder="Subject or email address…",
                               key="sent_search", label_visibility="collapsed")
    with fc2:
        show_all = st.checkbox("All time", key="sent_all_time")

    if show_all:
        records = all_records
    else:
        records = [
            r for r in all_records
            if _dt.fromisoformat(r["timestamp"]) >= _cutoff_30
        ]

    if selected_clients_filter:
        client_emails = {
            e for c in repo_clients
            if c["company"] in selected_clients_filter
            for e in c.get("emails", [])
        }
        records = [
            r for r in records
            if any(e in client_emails for e in r.get("sent_to", []))
        ]

    # ── Summary stats (scoped to visible period) ──────────────────────────────
    total_sent    = sum(len(r.get("sent_to", [])) for r in records)
    unique_emails = len({e for r in records for e in r.get("sent_to", [])})
    total_failed  = sum(len(r.get("failed", [])) for r in records)

    st.markdown(f"""<div class="stats-grid" style="grid-template-columns:repeat(4,1fr);">
        <div class="stat-card" style="border-top:2px solid #2563EB;">
            <div style="color:#2a5080;font-size:0.6rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">Total Sends</div>
            <div style="background:var(--gradient-brand);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;font-size:1.8rem;font-weight:800;letter-spacing:-0.03em;">{len(records)}</div>
        </div>
        <div class="stat-card" style="border-top:2px solid #0ebc6e;">
            <div style="color:#2a5080;font-size:0.6rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">Emails Delivered</div>
            <div style="color:#0ebc6e;font-size:1.8rem;font-weight:800;">{total_sent}</div>
        </div>
        <div class="stat-card" style="border-top:2px solid #2563EB;">
            <div style="color:#2a5080;font-size:0.6rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">Unique Recipients</div>
            <div style="color:#2563EB;font-size:1.8rem;font-weight:800;">{unique_emails}</div>
        </div>
        <div class="stat-card" style="border-top:2px solid {'#e72b3b' if total_failed else '#94a3b8'};">
            <div style="color:#2a5080;font-size:0.6rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">Failed</div>
            <div style="color:{'#dc2626' if total_failed else '#7a99bb'};font-size:1.8rem;font-weight:800;">{total_failed}</div>
        </div>
    </div>""", unsafe_allow_html=True)

    if not records:
        period_label = "in the last 30 days" if not show_all else "yet"
        st.markdown(f"""
        <div style="text-align:center;padding:5rem 2rem;">
            <div style="font-size:2.8rem;margin-bottom:1rem;">📭</div>
            <div style="font-size:1rem;font-weight:700;color:#3a6699;">No emails sent {period_label}</div>
            <div style="font-size:0.82rem;color:#94a3b8;margin-top:6px;">
                Go to <strong>Email Maker</strong> to compose and send emails.
            </div>
        </div>""", unsafe_allow_html=True)
        return

    # ── Search filter ─────────────────────────────────────────────────────────
    filtered = records
    if search:
        q = search.lower()
        filtered = [r for r in filtered if
                    q in r.get("subject", "").lower() or
                    any(q in e.lower() for e in r.get("sent_to", []))]

    st.markdown(
        f'<div style="color:#2a5080;font-size:0.75rem;font-weight:600;margin-bottom:12px;">'
        f'{len(filtered)} record{"s" if len(filtered) != 1 else ""} · last 30 days</div>',
        unsafe_allow_html=True,
    )

    # ── Records ───────────────────────────────────────────────────────────────
    for rec in filtered:
        _sent     = rec.get("sent_to", [])
        _fail_raw = rec.get("failed", [])
        _fail     = [f if isinstance(f, dict) else {"email": f, "error": ""} for f in _fail_raw]
        _has_f    = bool(_fail)
        _rid      = rec.get("id", "")

        top_color = "#e72b3b" if _has_f else "#2563EB"

        test_badge = (
            '<span style="background:rgba(245,158,11,0.15);color:#fbbf24;font-size:0.6rem;font-weight:700;'
            'letter-spacing:0.06em;text-transform:uppercase;padding:2px 8px;border-radius:99px;'
            'border:1px solid rgba(245,158,11,0.3);margin-left:6px;">TEST</span>'
        ) if rec.get("is_test") else ""

        # Build sent pills — show count label if more than 1
        sent_pills = " ".join(f'<span class="email-pill">✉ {e}</span>' for e in _sent)
        sent_count_label = (
            f'<span style="color:#2a5080;font-size:0.68rem;font-weight:600;margin-right:6px;">'
            f'{len(_sent)} address{"es" if len(_sent)!=1 else ""} delivered:</span>'
        ) if _sent else ""

        fail_pills = " ".join(
            f'<span style="display:inline-block;background:rgba(231,43,59,0.1);color:#dc2626;'
            f'font-size:0.7rem;font-weight:500;padding:3px 10px;border-radius:6px;'
            f'margin:2px 3px 0 0;border:1px solid rgba(231,43,59,0.2);">✕ {f["email"]}</span>'
            for f in _fail
        )
        fail_count_label = (
            f'<span style="color:#dc2626;font-size:0.68rem;font-weight:600;margin-right:6px;">'
            f'{len(_fail)} failed:</span>'
        ) if _fail else ""

        # ── Tracking stats for this send ──
        _tracking = tracking_store.get_stats_for_send(_rid) if _rid else {}
        _opens    = _tracking.get("opens", 0)
        _clicks   = _tracking.get("clicks", 0)
        _ratings  = _tracking.get("ratings", [])
        _avg_r    = (sum(r["rating"] for r in _ratings) / len(_ratings)) if _ratings else None

        def _stat_pill(icon, label, val, color):
            return (f'<div style="display:flex;align-items:center;gap:5px;background:rgba(61,130,245,0.05);'
                    f'border:1px solid rgba(61,130,245,0.15);border-radius:8px;padding:5px 10px;">'
                    f'<span style="font-size:0.8rem;">{icon}</span>'
                    f'<div><div style="color:{color};font-size:0.82rem;font-weight:700;">{val}</div>'
                    f'<div style="color:#2a5080;font-size:0.6rem;letter-spacing:0.06em;text-transform:uppercase;">{label}</div></div>'
                    f'</div>')

        rating_val = f"{_avg_r:.1f}★ ({len(_ratings)})" if _avg_r else "—"
        tracking_html = (
            f'<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:12px;">'
            + _stat_pill("👁", "Opens",   _opens,    "#2563EB")
            + _stat_pill("👆", "Clicks",  _clicks,   "#2563EB")
            + _stat_pill("⭐", "Rating",  rating_val, "#d97706")
            + f'</div>'
        )

        # ── Meta row ──
        meta_parts = []
        if rec.get("client"):
            meta_parts.append(f'<span style="color:#3a6699;">🏢 {rec["client"]}</span>')
        if rec.get("template_name"):
            meta_parts.append(f'<span style="color:#3a6699;">🎨 {rec["template_name"]}</span>')
        if rec.get("attachment_name"):
            meta_parts.append(f'<span style="color:#3a6699;">📎 {rec["attachment_name"]}</span>')
        if rec.get("sender"):
            meta_parts.append(f'<span style="color:#7a99bb;">✉ {rec["sender"]}</span>')
        meta_html = (
            '<div style="display:flex;flex-wrap:wrap;gap:12px;font-size:0.72rem;font-weight:500;margin-top:8px;">'
            + "".join(meta_parts) + '</div>'
        ) if meta_parts else ""

        # ── Body preview ──
        preview = rec.get("body_preview", "")
        preview_html = (
            f'<div style="color:#2a5080;font-size:0.72rem;line-height:1.55;margin-top:8px;'
            f'padding:8px 12px;background:rgba(61,130,245,0.04);border-radius:8px;'
            f'border-left:2px solid rgba(61,130,245,0.3);">'
            f'{preview[:200]}{"…" if len(preview) > 200 else ""}</div>'
        ) if preview else ""

        # ── Failed row ──
        fail_html = (
            f'<div style="margin-top:8px;display:flex;flex-wrap:wrap;align-items:center;gap:4px;">'
            f'{fail_count_label}{fail_pills}</div>'
        ) if _fail else ""

        sent_html = (
            f'<div style="display:flex;flex-wrap:wrap;align-items:center;gap:4px;">'
            f'{sent_count_label}{sent_pills}</div>'
        ) if _sent else ""

        st.markdown(f"""
        <div style="background:#ffffff;border:1px solid rgba(61,130,245,0.18);
                    border-top:3px solid {top_color};border-radius:14px;
                    padding:16px 20px;margin-bottom:12px;
                    box-shadow:0 4px 20px rgba(61,130,245,0.09);">
            <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:10px;">
                <div style="font-size:0.92rem;font-weight:700;color:#0d1d3a;flex:1;">
                    {rec.get("subject","(no subject)")}{test_badge}
                </div>
                <span style="font-size:0.7rem;color:#7a99bb;white-space:nowrap;flex-shrink:0;">
                    {rec.get("date","")} · {rec.get("time","")}
                </span>
            </div>
            {sent_html}
            {fail_html}
            {meta_html}
            {preview_html}
            {tracking_html}
        </div>""", unsafe_allow_html=True)

    # ── Export & Clear ────────────────────────────────────────────────────────
    st.markdown("---")
    ex_col, cl_col, _ = st.columns([2, 2, 3])
    with ex_col:
        def _fail_emails(r):
            raw = r.get("failed", [])
            return ", ".join(f["email"] if isinstance(f, dict) else f for f in raw)
        def _fail_errors(r):
            raw = r.get("failed", [])
            parts = [f.get("error","") for f in raw if isinstance(f, dict) and f.get("error")]
            return " | ".join(parts)
        rows = [
            {
                "ID": r.get("id",""),
                "Date": r.get("date",""), "Time": r.get("time",""),
                "Sender": r.get("sender",""),
                "Draft": r.get("draft_name",""), "Subject": r.get("subject",""),
                "Template": r.get("template_name",""), "Client": r.get("client",""),
                "Attachment": r.get("attachment_name",""),
                "Is Test": "Yes" if r.get("is_test") else "No",
                "Sent To": ", ".join(r.get("sent_to",[])),
                "Sent Count": len(r.get("sent_to",[])),
                "Failed Emails": _fail_emails(r),
                "Failed Errors": _fail_errors(r),
                "Body Preview": r.get("body_preview",""),
            }
            for r in records
        ]
        csv = pd.DataFrame(rows).to_csv(index=False)
        st.download_button("⬇️  Export CSV", data=csv,
                           file_name="sent_emails.csv", mime="text/csv",
                           use_container_width=True)
    with cl_col:
        if st.button("🗑  Clear All History", use_container_width=True):
            sent_store.clear()
            st.toast("Send history cleared.", icon="🗑")
            st.rerun()


# ─── Sidebar CSS toggle (pure Python — no JS needed) ─────────────────────────

def render_quality_engine():
    st.markdown("""<div class="page-header">
        <div class="page-title">🚨 Red Flag Scanner</div>
        <div class="page-sub">Quality Engine · Automated issue detection across reports, feedback, and SLA compliance.</div>
    </div>""", unsafe_allow_html=True)

    # ── Derive all flags from live Supabase data ──────────────────────────────
    from datetime import timedelta as _td
    _now        = datetime.now(timezone.utc)
    _all_events = tracking_store.load()
    _all_sent   = sent_store.load()
    _cutoff_30  = _now - _td(days=30)
    _cutoff_60  = _now - _td(days=60)

    # Low CSAT: real ratings ≤ 2 from tracking_store
    _all_respondents = tracking_store.get_stats_for_period(None)["respondents"]
    low_csat = [r for r in _all_respondents if r["rating"] <= 2]

    # SLA breaches: low-rated (≤ 2) feedback events open > 72 h without resolution
    _SLA_H = 72
    _rating_evts = [e for e in _all_events if e["type"] == "rating" and e.get("rating", 5) <= 2]
    sla_breached = []
    for _e in _rating_evts:
        _ts_e = datetime.fromisoformat(_e["timestamp"])
        _h_open = (_now - _ts_e).total_seconds() / 3600
        if _h_open > _SLA_H:
            sla_breached.append({
                "priority":    "🔴 Critical",
                "name":        _e["email"].split("@")[0].replace(".", " ").title(),
                "email":       _e["email"],
                "score":       _e.get("rating", 0),
                "type":        "CSAT",
                "campaign":    "—",
                "tags":        [],
                "comment":     "",
                "hours_open":  round(_h_open),
                "sla_hours":   _SLA_H,
                "sla_breached": True,
            })

    # Campaign health: derive from sent_store + per-send tracking stats
    critical_rpts = []
    needs_action  = []
    _curr_sent    = [r for r in _all_sent
                     if datetime.fromisoformat(r["timestamp"]) >= _cutoff_30]
    for _rec in _curr_sent:
        _stats     = tracking_store.get_stats_for_send(_rec["id"])
        _n_sent    = len(_rec.get("sent_to", []))
        _ratings   = _stats["ratings"]
        _n_ratings = len(_ratings)
        _avg       = sum(r.get("rating", 0) for r in _ratings) / _n_ratings if _n_ratings else None
        _camp = {
            "name":      _rec.get("subject", "—"),
            "type":      "CSAT",
            "responses": _n_ratings,
            "sent":      _n_sent,
            "score":     round(_avg, 1) if _avg is not None else "—",
            "audience":  _rec.get("client", "—"),
            "sent_at":   _rec.get("date", "—"),
        }
        if _avg is not None and _avg < 2.5:
            _camp["status"] = "🔴 Critical"
            critical_rpts.append(_camp)
        elif _avg is not None and _avg < 3.5:
            _camp["status"] = "⚠️ Needs Action"
            needs_action.append(_camp)

    # Declining KPIs: compare current 30 d vs previous 30 d
    def _period_kpis(events, sent_recs):
        _r   = [e for e in events if e["type"] == "rating"]
        _n_s = sum(len(r.get("sent_to", [])) for r in sent_recs)
        _n_r = len(_r)
        _avg = sum(e.get("rating", 0) for e in _r) / _n_r if _n_r else 0
        _neg = len([e for e in _r if e.get("rating", 5) <= 2])
        _rsp = round(_n_r / _n_s * 100, 1) if _n_s else 0
        _neg_pct = round(_neg / _n_r * 100, 1) if _n_r else 0
        return {"response_rate": _rsp, "avg_score": _avg, "neg_pct": _neg_pct}

    _curr_evts = [e for e in _all_events
                  if datetime.fromisoformat(e["timestamp"]) >= _cutoff_30]
    _prev_evts = [e for e in _all_events
                  if _cutoff_60 <= datetime.fromisoformat(e["timestamp"]) < _cutoff_30]
    _prev_sent = [r for r in _all_sent
                  if _cutoff_60 <= datetime.fromisoformat(r["timestamp"]) < _cutoff_30]

    _ck = _period_kpis(_curr_evts, _curr_sent)
    _pk = _period_kpis(_prev_evts, _prev_sent)

    declining_kpis = []
    for _km in [
        KPIMetric("Response Rate",     _ck["response_rate"], _pk["response_rate"], "percent", True,  "% of report recipients who submitted feedback"),
        KPIMetric("Avg Report Score",  _ck["avg_score"],     _pk["avg_score"],     "score",   True,  "Mean report quality score (1–5)"),
        KPIMetric("Negative Feedback", _ck["neg_pct"],       _pk["neg_pct"],       "percent", False, "% of responses with rating ≤ 2"),
    ]:
        if not delta_is_positive(_km):
            declining_kpis.append(_km)

    n_critical = len(sla_breached) + len(critical_rpts)
    n_high     = len(low_csat) + len(needs_action)
    n_medium   = len(declining_kpis)
    n_total    = n_critical + n_high + n_medium

    # ── Summary bar ──────────────────────────────────────────────────────────
    sc1, sc2, sc3, sc4 = st.columns(4)
    with sc1:
        st.markdown(f"""<div class="metric-card accent-red">
            <div class="metric-label">Critical Flags</div>
            <div class="metric-value">{n_critical}</div>
            <div class="metric-sub">SLA breaches &amp; critical reports</div>
        </div>""", unsafe_allow_html=True)
    with sc2:
        st.markdown(f"""<div class="metric-card accent-amber">
            <div class="metric-label">High Flags</div>
            <div class="metric-value">{n_high}</div>
            <div class="metric-sub">Low CSAT &amp; reports needing action</div>
        </div>""", unsafe_allow_html=True)
    with sc3:
        st.markdown(f"""<div class="metric-card accent-blue">
            <div class="metric-label">Medium Flags</div>
            <div class="metric-value">{n_medium}</div>
            <div class="metric-sub">Declining KPI trends</div>
        </div>""", unsafe_allow_html=True)
    with sc4:
        clear_cls = "accent-green" if n_total == 0 else ""
        st.markdown(f"""<div class="metric-card {clear_cls}">
            <div class="metric-label">Total Open Flags</div>
            <div class="metric-value">{n_total}</div>
            <div class="metric-sub">Across all categories</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

    # ── SLA Breaches ─────────────────────────────────────────────────────────
    if sla_breached:
        st.markdown('<span class="section-chip">🔴 SLA Breaches</span>', unsafe_allow_html=True)
        for item in sla_breached:
            overdue_h = item["hours_open"] - item["sla_hours"]
            tags_html = "".join(f'<span class="tag-chip">{t}</span>' for t in item.get("tags", []))
            stars = "⭐" * item["score"]
            st.markdown(f"""
            <div style="background:#fff5f5;border:1px solid #fecaca;border-radius:12px;padding:16px 20px;margin-bottom:10px;">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
                    <span style="font-size:0.85rem;font-weight:700;color:#dc2626;">{item['priority']}</span>
                    <span style="font-size:0.85rem;font-weight:600;color:#18181b;">{item['name']}</span>
                    <span style="font-size:0.75rem;color:#71717a;">{item['email']}</span>
                    <span style="margin-left:auto;font-size:0.72rem;background:#fecaca;color:#dc2626;font-weight:700;padding:3px 10px;border-radius:6px;">+{overdue_h}h overdue</span>
                </div>
                <div style="font-size:0.78rem;color:#52525b;margin-bottom:8px;">"{item['comment']}"</div>
                <div style="font-size:0.71rem;color:#71717a;">Campaign: {item['campaign']} &nbsp;·&nbsp; Score: {stars} {item['score']}/5 &nbsp;·&nbsp; {tags_html}</div>
            </div>""", unsafe_allow_html=True)

    # ── Critical Reports ──────────────────────────────────────────────────────
    if critical_rpts:
        st.markdown('<span class="section-chip">🔴 Critical Reports</span>', unsafe_allow_html=True)
        for c in critical_rpts:
            resp_rate = round(c["responses"] / c["sent"] * 100, 1) if c["sent"] else 0
            st.markdown(f"""
            <div style="background:#fff5f5;border:1px solid #fecaca;border-radius:12px;padding:16px 20px;margin-bottom:10px;">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
                    <span style="font-size:0.85rem;font-weight:700;color:#dc2626;">{c['status']}</span>
                    <span style="font-size:0.85rem;font-weight:600;color:#18181b;">{c['name']}</span>
                </div>
                <div style="font-size:0.75rem;color:#71717a;">{c['type']} &nbsp;·&nbsp; Score: <strong>{c['score']}</strong> &nbsp;·&nbsp; Audience: {c['audience']} &nbsp;·&nbsp; {c['responses']}/{c['sent']} responses ({resp_rate}%) &nbsp;·&nbsp; Sent {c['sent_at']}</div>
            </div>""", unsafe_allow_html=True)

    # ── Negative Feedback ─────────────────────────────────────────────────────
    if low_csat:
        st.markdown('<span class="section-chip">🟠 Negative Feedback (≤ 2 stars)</span>', unsafe_allow_html=True)
        for r in low_csat:
            filled = "★" * r["rating"]
            empty  = "☆" * (5 - r["rating"])
            st.markdown(f"""
            <div style="background:#fffbeb;border:1px solid #fde68a;border-radius:12px;padding:14px 20px;margin-bottom:10px;display:flex;align-items:center;gap:14px;">
                <span style="font-size:1.1rem;color:#f59e0b;letter-spacing:2px;">{filled}{empty}</span>
                <div style="flex:1;">
                    <div style="font-size:0.82rem;font-weight:600;color:#18181b;">{r['name']}</div>
                    <div style="font-size:0.72rem;color:#71717a;">{r['email']} &nbsp;·&nbsp; {r['date']}</div>
                </div>
                <span style="font-size:0.72rem;background:#fef9c3;color:#d97706;font-weight:700;padding:3px 10px;border-radius:6px;">{r['rating']}/5</span>
            </div>""", unsafe_allow_html=True)

    # ── Reports Needing Action ────────────────────────────────────────────────
    if needs_action:
        st.markdown('<span class="section-chip">🟠 Reports Needing Action</span>', unsafe_allow_html=True)
        for c in needs_action:
            resp_rate = round(c["responses"] / c["sent"] * 100, 1) if c["sent"] else 0
            st.markdown(f"""
            <div style="background:#fffbeb;border:1px solid #fde68a;border-radius:12px;padding:16px 20px;margin-bottom:10px;">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
                    <span style="font-size:0.85rem;font-weight:700;color:#d97706;">{c['status']}</span>
                    <span style="font-size:0.85rem;font-weight:600;color:#18181b;">{c['name']}</span>
                </div>
                <div style="font-size:0.75rem;color:#71717a;">{c['type']} &nbsp;·&nbsp; Score: <strong>{c['score']}</strong> &nbsp;·&nbsp; Audience: {c['audience']} &nbsp;·&nbsp; {c['responses']}/{c['sent']} responses ({resp_rate}%) &nbsp;·&nbsp; Sent {c['sent_at']}</div>
            </div>""", unsafe_allow_html=True)

    # ── Declining KPIs ────────────────────────────────────────────────────────
    if declining_kpis:
        st.markdown('<span class="section-chip">🟡 Declining KPIs</span>', unsafe_allow_html=True)
        for m in declining_kpis:
            st.markdown(f"""
            <div style="background:#fefce8;border:1px solid #fef08a;border-radius:12px;padding:14px 20px;margin-bottom:10px;display:flex;align-items:center;gap:14px;">
                <div style="flex:1;">
                    <div style="font-size:0.82rem;font-weight:600;color:#18181b;">{m.label}</div>
                    <div style="font-size:0.72rem;color:#71717a;">{m.description}</div>
                </div>
                <div style="text-align:right;">
                    <div style="font-size:1.2rem;font-weight:800;color:#18181b;">{format_kpi(m)}</div>
                    <div style="font-size:0.72rem;color:#dc2626;font-weight:700;">{format_delta(m)} vs prev</div>
                </div>
            </div>""", unsafe_allow_html=True)

    if n_total == 0:
        st.markdown("""
        <div style="text-align:center;padding:4rem 2rem;">
            <div style="font-size:2.5rem;">✅</div>
            <div style="font-size:1.1rem;font-weight:700;color:#059669;margin-top:1rem;">All Clear</div>
            <div style="font-size:0.85rem;color:#71717a;margin-top:0.5rem;">No red flags detected across reports, feedback, and delivery.</div>
        </div>""", unsafe_allow_html=True)


# ─── Convin Sense ─────────────────────────────────────────────────────────────

_SENSE_CACHE     = os.path.join(os.path.dirname(__file__), ".sense_cache.pkl")
_SENSE_PROTECTED = os.path.join(os.path.dirname(__file__), ".sense_protected.pkl")
_SENSE_AUDIT_LOG = os.path.join(os.path.dirname(__file__), ".sense_audit_log.pkl")
_SENSE_REGISTRY  = os.path.join(os.path.dirname(__file__), ".sense_registry.pkl")

# ── Client registry ────────────────────────────────────────────────────────────
_SENSE_CLIENTS = [
    {"client": "E-Kart",                          "pm": "Ashutosh",  "status": "Active"},
    {"client": "mPokket",                          "pm": "Sudesha",   "status": "Active"},
    {"client": "Kotak Securities",                 "pm": "Sudesha",   "status": "Active"},
    {"client": "ManMatters",                       "pm": "Sudesha",   "status": "Active"},
    {"client": "Wakefit",                          "pm": "Sudesha",   "status": "Active"},
    {"client": "Reliance General Insurance",       "pm": "Sudesha",   "status": "Active"},
    {"client": "Lemonn",                           "pm": "Shivansh",  "status": "Active"},
    {"client": "Moneyview",                        "pm": "Shivansh",  "status": "Active"},
    {"client": "Apollo Finvest",                   "pm": "Shivansh",  "status": "Active"},
    {"client": "Cleartrip - Holiday Travel",       "pm": "Arnab",     "status": "Active"},
    {"client": "Capital Now",                      "pm": "Arnab",     "status": "Hold"},
    {"client": "AESL Digital",                     "pm": "Arnab",     "status": "Active"},
    {"client": "Teamlease",                        "pm": "Arnab",     "status": "Active"},
    {"client": "Entri App",                        "pm": "Hamza",     "status": "Active"},
    {"client": "EyeQ India",                       "pm": "Hamza",     "status": "Active"},
    {"client": "KollegeApply",                     "pm": "Hamza",     "status": "Active"},
    {"client": "Cleartrip - NPS",                  "pm": "Hamza",     "status": "Active"},
    {"client": "Cleartrip - Refund",               "pm": "Hamza",     "status": "Active"},
    {"client": "Oliveboard",                       "pm": "Suyasha",   "status": "Active"},
    {"client": "Careers360",                       "pm": "Kritik",    "status": "Active"},
    {"client": "Even Insurance",                   "pm": "Manjusha",  "status": "Active"},
    {"client": "Credila",                          "pm": "Bhargava",  "status": "Active"},
    {"client": "JM Financial",                     "pm": "Amith",     "status": "Hold"},
    {"client": "TrueMeds",                         "pm": "Ashutosh",  "status": "Hold"},
    {"client": "Ather",                            "pm": "Ashutosh",  "status": "Hold"},
    {"client": "Mobikwik - Lending Sales",         "pm": "Ashutosh",  "status": "Hold"},
    {"client": "Agrostar",                         "pm": "Hamza",     "status": "Hold"},
    {"client": "Nestaway",                         "pm": "Amith",     "status": "Campaigns Over"},
    {"client": "Shaadi.com",                       "pm": "Bhargava",  "status": "Campaigns Over"},
    {"client": "Hike Education",                   "pm": "Ashutosh",  "status": "Sales Negotiation"},
    {"client": "Grip Invest",                      "pm": "Ashutosh",  "status": "Campaigns Over"},
    {"client": "Guvi",                             "pm": "Sayani",    "status": "Campaigns Over"},
    {"client": "Habuild",                          "pm": "Arnab",     "status": "Sales Negotiation"},
    {"client": "FitPass",                          "pm": "Hamza",     "status": "Sales Negotiation"},
    {"client": "Vyapar",                           "pm": "Arnab",     "status": "Live"},
    {"client": "BACL - Voicebot use case",         "pm": "Sudesha",   "status": "Live"},
    {"client": "ABSLI VRM",                        "pm": "Bhargava",  "status": "Live"},
    {"client": "BACL - Collections",               "pm": "Siddhant",  "status": "Live"},
    {"client": "Cleartrip - Hotel Confirmation",   "pm": "Utsav",     "status": "Live"},
    {"client": "PhysicsWallah",                    "pm": "Utsav",     "status": "Live"},
    {"client": "boAt",                             "pm": "Sudesha",   "status": "Self-Serve Live"},
    {"client": "Nirvasa Health",                   "pm": "Shivansh",  "status": "Onboarding"},
    {"client": "Mobikwik",                         "pm": "Raghav",    "status": "Onboarding"},
    {"client": "Allen - Offline Center",           "pm": "Shubham",   "status": "Onboarding"},
    {"client": "Allen - Attendance",               "pm": "Shubham",   "status": "Onboarding"},
    {"client": "Cashify",                          "pm": "Raghav",    "status": "Onboarding"},
    {"client": "Leap Scholar",                     "pm": "Shivansh",  "status": "Onboarding"},
    {"client": "Bigul",                            "pm": "Shivansh",  "status": "Onboarding"},
    {"client": "Ezobooks",                         "pm": "Shubham",   "status": "Onboarding"},
    {"client": "Miles Education",                  "pm": "Shubham",   "status": "Onboarding"},
    {"client": "ABSLI PO",                         "pm": "Sudesha",   "status": "Onboarding"},
    {"client": "AriseAll",                         "pm": "Sudesha",   "status": "Onboarding"},
]
_SENSE_CLIENT_MAP = {r["client"]: r for r in _SENSE_CLIENTS}
_SENSE_CLIENT_NAMES = [""] + [r["client"] for r in _SENSE_CLIENTS]

# ── Convin Sense built-in tier parameters (formerly "intelligence") ──────────
# Now scored 0–2 like all tier params: 2 = best, 0 = worst.
# Automatically injected into every audit sheet if not already present.
_SENSE_BUILTIN_PARAMS = {
    "Flow Issue": {
        "description": "Conversation flow quality — logical gaps / breakdowns",
        "options":     ["Yes", "No"],  # Yes = issue present (bad), No = no issue (good)
        "inverted":    False,
        "weight":      0.11,
        "color":       "#dc2626",
        "icon":        "🔍",
        "guide":       "Yes = Flow issue detected (breaks scoring)  |  No = No flow issue",
    },
    "Bot Restarted Conversation": {
        "description": "Bot forced a conversation restart",
        "options":     ["Yes", "No"],  # Yes = restart happened (bad), No = no restart (good)
        "inverted":    False,
        "weight":      0.09,
        "color":       "#d97706",
        "icon":        "🔁",
        "guide":       "Yes = Bot restarted conversation (breaks scoring)  |  No = No restart",
    },
    "Bot Repetition": {
        "description": "Bot repeated same message / looped responses",
        "options":     ["Yes", "No"],  # Yes = repetition detected (bad), No = no repetition (good)
        "inverted":    False,
        "weight":      0.07,
        "color":       "#7c3aed",
        "icon":        "🔄",
        "guide":       "Yes = Repetition detected (breaks scoring)  |  No = No repetition",
    },
    "Latency": {
        "description": "Bot response latency / delay during conversation",
        "options":     ["0", "1", "2"],
        "inverted":    False,
        "weight":      0.04,
        "color":       "#0891b2",
        "icon":        "⚡",
        "guide":       "2 = Response within acceptable latency (<500ms)  |  1 = Slight delay (500ms–1s)  |  0 = High latency (>1s) impacted conversation quality",
    },
}
_DEFAULT_PARAM_WEIGHT = 1.0   # weight for any legend param not listed above

# ── Convin Sense QA Audit Schema (Convin.ai standard sheet) ──────────────────
_QA_SCHEMA = {
    "tiers": [
        {
            "label": "TIER 1 · CRITICAL",
            "weight_pct": 63,
            "color": "#dc2626",
            "params": [
                {
                    "col": "Disposition Accuracy",
                    "weight": 0.18,
                    "options": ["0", "1", "2"],
                    "fatal": False,
                    "guide": "2 = Correctly reflects outcome, lead status & entities  |  1 = Minor mismatch  |  0 = Does not align with conversation outcome",
                },
                {
                    "col": "Context Passing",
                    "weight": 0.13,
                    "options": ["0", "1", "2"],
                    "fatal": False,
                    "guide": "2 = Context maintained across all turns / channels  |  1 = Context passed but some info lost  |  0 = Context not maintained; repetitive/irrelevant questions",
                },
                {
                    "col": "Flow Issue",
                    "weight": 0.11,
                    "options": ["Yes", "No"],
                    "fatal": False,
                    "guide": "Yes = Flow issue detected  |  No = No flow issue",
                },
                {
                    "col": "Bot Restarted Conversation",
                    "weight": 0.09,
                    "options": ["Yes", "No"],
                    "fatal": False,
                    "guide": "Yes = Bot restarted conversation  |  No = No restart",
                },
                {
                    "col": "Message Content",
                    "weight": 0.07,
                    "options": ["0", "1", "2"],
                    "fatal": False,
                    "guide": "2 = Bot fully understood intent and responded appropriately  |  1 = Partially understood  |  0 = Bot misunderstood or ignored customer intent",
                },
                {
                    "col": "Follow-up in Specified Time",
                    "weight": 0.05,
                    "options": ["0", "1", "2"],
                    "fatal": False,
                    "guide": "2 = Follow-up within SLA  |  1 = Completed but exceeded SLA timeline  |  0 = No follow-up attempt made",
                },
            ],
        },
        {
            "label": "TIER 2 · IMPORTANT",
            "weight_pct": 29,
            "color": "#f59e0b",
            "params": [
                {
                    "col": "Bot Repetition",
                    "weight": 0.07,
                    "options": ["Yes", "No"],
                    "fatal": False,
                    "guide": "Yes = Repetition detected  |  No = No repetition",
                },
                {
                    "col": "Dead Air/Blank Space",
                    "weight": 0.06,
                    "options": ["0", "1", "2"],
                    "fatal": False,
                    "guide": "2 = No silence/awkward pauses  |  1 = Short acceptable silence 4–5s  |  0 = Long silence >5s; call appeared stuck",
                },
                {
                    "col": "Repeated Calls",
                    "weight": 0.05,
                    "options": ["0", "2"],
                    "fatal": False,
                    "guide": "2 = No unnecessary repeat calls  |  0 = Multiple calls placed to customer within short duration",
                },
                {
                    "col": "Introduction",
                    "weight": 0.05,
                    "options": ["0", "1", "2"],
                    "fatal": False,
                    "guide": "2 = Bot introduced itself, company name & purpose  |  1 = Present but key details missing  |  0 = No introduction provided",
                },
                {
                    "col": "Background Noise",
                    "weight": 0.03,
                    "options": ["0", "2"],
                    "fatal": False,
                    "guide": "2 = Audio clear, no background noise  |  0 = Background noise affected clarity",
                },
                {
                    "col": "Transcription Issues",
                    "weight": 0.03,
                    "options": ["0", "2"],
                    "fatal": False,
                    "guide": "2 = Transcription accurate and complete  |  0 = Inaccuracies impacted audit reliability",
                },
                {
                    "col": "Latency",
                    "weight": 0.04,
                    "options": ["0", "1", "2"],
                    "fatal": False,
                    "guide": "2 = Response within acceptable latency (<500ms)  |  1 = Slight delay (500ms–1s)  |  0 = High latency (>1s) impacted conversation quality",
                },
            ],
        },
        {
            "label": "TIER 3 · QUALITY",
            "weight_pct": 8,
            "color": "#2563EB",
            "params": [
                {
                    "col": "Language Switch",
                    "weight": 0.02,
                    "options": ["0", "1", "2"],
                    "fatal": False,
                    "guide": "2 = Switched language correctly per customer preference  |  1 = No switch required  |  0 = Failed to switch despite customer indication",
                },
                {
                    "col": "Script Issue in Transcript",
                    "weight": 0.02,
                    "options": ["0", "2"],
                    "fatal": False,
                    "guide": "2 = Approved script followed correctly  |  0 = Bot deviated from script / used incorrect phrasing",
                },
                {
                    "col": "TTS Issues (Voice)",
                    "weight": 0.02,
                    "options": ["0", "2"],
                    "fatal": False,
                    "guide": "2 = No voice quality issues  |  0 = Tempo inconsistency, sudden voice change, giggles, or volume issues",
                },
                {
                    "col": "Template Issues",
                    "weight": 0.01,
                    "options": ["0", "2"],
                    "fatal": False,
                    "guide": "2 = Correct template followed  |  0 = Incorrect or outdated template used",
                },
                {
                    "col": "Pronunciation Issue",
                    "weight": 0.01,
                    "options": ["0", "2"],
                    "fatal": False,
                    "guide": "2 = Pronunciation clear and understandable  |  0 = Issues impacted customer understanding",
                },
                {
                    "col": "Abrupt Disconnection",
                    "weight": 0.00,
                    "options": ["0", "Fatal"],
                    "fatal": True,
                    "guide": "0 = Call ended smoothly as per designed flow  |  Fatal = Call ended abruptly before logical closure (Auto-Fail)",
                },
                {
                    "col": "NBA Not Executed",
                    "weight": 0.00,
                    "options": ["0", "2"],
                    "fatal": False,
                    "guide": "2 = NBA executed correctly or not applicable  |  0 = NBA was generated but not executed by bot",
                },
            ],
        },
    ],
    # Intelligence list is now empty — Flow Issue, Bot Restarted Conversation,
    # and Bot Repetition are standard tier params (Tier 1 / Tier 2).
    "intelligence": [],
    "lead_stage_opts":   ["Cold", "Warm", "Hot", "Not Interested", "RNR"],
    "lead_stage_scores": {"Cold": 30, "Warm": 70, "Hot": 90, "Not Interested": 0, "RNR": 10},
    "lead_score_cols":   ["Lead Stage", "Correct Disposition", "Correct Disposition (Expected)"],
    "auto_cols":         ["Lead Score", "Lead Composite", "Bot Score", "Intelligence Score", "Status", "Fatal?"],
    "metadata_cols":     ["Audit Date", "QA", "Client", "Campaign Name", "PM / CSM", "Bot Name", "Disposition", "Lead Number", "Lead Link", "Conversation Link"],
    # Status bands: Bot Score ≥ 80 Pass | 60–79 Needs Review | < 60 Fail | Fatal → Auto-Fail
    "status_bands": [
        {"min": 80,  "label": "Pass",         "color": "#0ebc6e"},
        {"min": 60,  "label": "Needs Review", "color": "#f59e0b"},
        {"min":  0,  "label": "Fail",         "color": "#dc2626"},
        {"min": -1,  "label": "Auto-Fail",    "color": "#7f1d1d"},
    ],
}


def _qa_status(bot_score, is_fatal):
    if is_fatal:
        return "Auto-Fail"
    for band in _QA_SCHEMA["status_bands"]:
        if bot_score >= band["min"]:
            return band["label"]
    return "Fail"


def _qa_status_color(status):
    for band in _QA_SCHEMA["status_bands"]:
        if band["label"] == status:
            return band["color"]
    return "#aabbcc"


def _compute_qa_score(pv):
    """Compute Bot Score, Intelligence Score, Status, Fatal?, Lead Score, Lead Composite."""
    # Fatal detection
    is_fatal = any(
        p.get("fatal") and str(pv.get(p["col"], "")).strip() == "Fatal"
        for tier in _QA_SCHEMA["tiers"]
        for p in tier["params"]
    )

    # Bot Score (QA tier params only — weights sum to 1.0, max score per param = 2)
    if is_fatal:
        bot_score = 0.0
    else:
        ws = tw = 0.0
        for tier in _QA_SCHEMA["tiers"]:
            for p in tier["params"]:
                if p["weight"] > 0:
                    _raw = str(pv.get(p["col"], "")).strip()
                    if _raw.upper() == "NA" or _raw == "":
                        continue  # not applicable — skip without penalty
                    s = None
                    try:
                        s = float(_raw)
                    except (ValueError, TypeError):
                        # Text option (e.g. Yes/No) — map by position in options list
                        # first option = 0, last option = 2 (max score per param)
                        _opts = p.get("options", [])
                        _oi = next((i for i, o in enumerate(_opts)
                                    if str(o).strip().lower() == _raw.lower()), None)
                        if _oi is not None and len(_opts) > 1:
                            s = round(_oi / (len(_opts) - 1) * 2, 4)
                    if s is not None:
                        ws += s * p["weight"]
                        tw += p["weight"] * 2.0
        bot_score = round(ws / tw * 100, 2) if tw > 0 else 0.0

    # Intelligence Score (Convin Sense params — separate 0–100 metric)
    _iparts = []
    for _ip in _QA_SCHEMA["intelligence"]:
        v = str(pv.get(_ip["col"], "")).strip()
        s = _ip["score_map"].get(v)
        if s is not None:
            _iparts.append((s, _ip["weight"]))
    _itw = sum(w for _, w in _iparts)
    intel_score = round(sum(s * w for s, w in _iparts) / (_itw * 2.0) * 100, 1) if _itw > 0 else None

    status = _qa_status(bot_score, is_fatal)

    # Lead composite
    lead_score_raw = _QA_SCHEMA["lead_stage_scores"].get(str(pv.get("Lead Stage", "")), None)
    lead_composite = None
    if lead_score_raw is not None:
        lead_composite = float(lead_score_raw)

    return {
        "Bot Score":          bot_score,
        "Intelligence Score": intel_score if intel_score is not None else "",
        "Status":             status,
        "Fatal?":             "YES" if is_fatal else "NO",
        "Lead Score":         lead_score_raw if lead_score_raw is not None else "",
        "Lead Composite":     lead_composite if lead_composite is not None else "",
    }


def _builtin_cfg(col_name):
    """Return built-in config dict if col_name matches a Convin Sense param."""
    _cl = str(col_name).strip().lower()
    for k, cfg in _SENSE_BUILTIN_PARAMS.items():
        if k.lower() in _cl or _cl in k.lower():
            return cfg
    return None

def _merge_builtin_params(legend_map):
    """Return legend_map enriched with Convin Sense built-in params."""
    merged = dict(legend_map)
    for param, cfg in _SENSE_BUILTIN_PARAMS.items():
        if not any(param.lower() in k.lower() or k.lower() in param.lower()
                   for k in merged):
            merged[param] = cfg["options"]
    return merged

def _is_protected_sheet(name):
    _l = name.strip().lower()
    return any(k in _l for k in ("legend", "audit"))

def _sense_save(sheets, fname):
    try:
        import pickle
        with open(_SENSE_CACHE, "wb") as _f:
            pickle.dump({"sheets": sheets, "fname": fname}, _f)
    except Exception:
        pass

def _sense_save_protected(sheets, fname):
    """Save only Legend + Audit sheets to a separate, clear-proof cache."""
    try:
        import pickle
        protected = {k: v for k, v in sheets.items() if _is_protected_sheet(k)}
        if protected:
            with open(_SENSE_PROTECTED, "wb") as _f:
                pickle.dump({"sheets": protected, "fname": fname}, _f)
    except Exception:
        pass

def _sense_load():
    try:
        import pickle
        if os.path.exists(_SENSE_CACHE):
            with open(_SENSE_CACHE, "rb") as _f:
                return pickle.load(_f)
    except Exception:
        pass
    return None

def _sense_load_protected():
    try:
        import pickle
        if os.path.exists(_SENSE_PROTECTED):
            with open(_SENSE_PROTECTED, "rb") as _f:
                return pickle.load(_f)
    except Exception:
        pass
    return None

def _sense_clear_cache():
    """Clear only the regular cache. Protected sheets are NEVER deleted here."""
    try:
        if os.path.exists(_SENSE_CACHE):
            os.remove(_SENSE_CACHE)
    except Exception:
        pass

def _audit_log_save(records):
    pass  # no-op — writes go through audit_store.append() directly

def _audit_log_load():
    return audit_store.load()


def _registry_save(data):
    try:
        import pickle
        with open(_SENSE_REGISTRY, "wb") as _f:
            pickle.dump(data, _f)
    except Exception:
        pass

def _registry_load():
    try:
        import pickle
        if os.path.exists(_SENSE_REGISTRY):
            with open(_SENSE_REGISTRY, "rb") as _f:
                return pickle.load(_f)
    except Exception:
        pass
    return None

def _registry_init():
    """Populate session state registry keys from file or defaults on first load."""
    if st.session_state.get("_registry_initialized"):
        return
    _saved = _registry_load()
    _default_pms = sorted(set(r["pm"] for r in _SENSE_CLIENTS))
    _default_cms: list = []
    _default_qas = ["Animesh", "Shubham", "Aman", "Navya", "Alan"]
    _default_clients = [{"client": r["client"], "pm": r["pm"], "cm": "", "status": r["status"]} for r in _SENSE_CLIENTS]
    if _saved:
        st.session_state.setdefault("sense_registry_pms",     _saved.get("pms",     _default_pms))
        st.session_state.setdefault("sense_registry_cms",     _saved.get("cms",     _default_cms))
        st.session_state.setdefault("sense_registry_qas",     _saved.get("qas",     _default_qas))
        st.session_state.setdefault("sense_registry_clients", _saved.get("clients", _default_clients))
    else:
        st.session_state.setdefault("sense_registry_pms",     _default_pms)
        st.session_state.setdefault("sense_registry_cms",     _default_cms)
        st.session_state.setdefault("sense_registry_qas",     _default_qas)
        st.session_state.setdefault("sense_registry_clients", _default_clients)
    st.session_state["_registry_initialized"] = True

def _registry_persist():
    """Write current session state registry to disk."""
    _registry_save({
        "pms":     st.session_state.get("sense_registry_pms", []),
        "cms":     st.session_state.get("sense_registry_cms", []),
        "qas":     st.session_state.get("sense_registry_qas", []),
        "clients": st.session_state.get("sense_registry_clients", []),
    })



def _parse_legend(legend_df):
    """Extract {parameter: [score_options]} from a legend sheet."""
    result = {}
    if legend_df is None or legend_df.empty:
        return result

    # Clean column names
    legend_df = legend_df.copy()
    legend_df.columns = [str(c).strip() for c in legend_df.columns]

    cols = legend_df.columns.tolist()
    _param_kw = ("param", "criteria", "category", "metric", "indicator", "question",
                 "field", "name", "item", "parameter", "attribute")
    _score_kw = ("score", "rating", "value", "option", "grade", "mark", "point", "scale")

    param_col = next((c for c in cols if any(k in c.lower() for k in _param_kw)), None)
    score_col = next((c for c in cols if any(k in c.lower() for k in _score_kw)), None)

    if param_col and score_col:
        for _, row in legend_df.iterrows():
            p = str(row[param_col]).strip()
            s = str(row[score_col]).strip()
            if p and p.lower() not in ("nan", "none", ""):
                result.setdefault(p, [])
                if s and s.lower() not in ("nan", "none", ""):
                    if s not in result[p]:
                        result[p].append(s)
        return result

    # Fallback: first col = parameter name, rest of cols = valid score values per row
    if len(cols) >= 2:
        for _, row in legend_df.iterrows():
            p = str(row[cols[0]]).strip()
            if p and p.lower() not in ("nan", "none", ""):
                vals = []
                for c in cols[1:]:
                    v = str(row[c]).strip()
                    if v and v.lower() not in ("nan", "none", "") and v not in vals:
                        vals.append(v)
                if vals:
                    result[p] = vals

    # Fallback 2: treat every column's unique non-null values as score options
    if not result:
        for col in cols:
            vals = (legend_df[col].dropna().astype(str)
                    .str.strip()
                    .loc[lambda s: ~s.str.lower().isin(("nan", "none", ""))]
                    .unique().tolist())
            if vals:
                result[col] = vals

    return result


def _match_legend(col_name, legend_map):
    """Return score options for col_name if it fuzzy-matches a legend parameter."""
    col_l = str(col_name).strip().lower()
    for param, opts in legend_map.items():
        param_l = param.strip().lower()
        if param_l == col_l or param_l in col_l or col_l in param_l:
            return opts
    return None


def _score_to_numeric(series, options=None, inverted=False):
    """Convert a score series to 0–1 floats where 1.0 = best performance.
    inverted=True for defect params (None/No = best → 1.0, Critical/Multiple = 0.0).
    """
    _BINARY_POS = {"yes", "pass", "ok", "good", "true", "1", "compliant", "met", "done", "complete"}
    _BINARY_NEG = {"no", "fail", "bad", "false", "0", "non-compliant", "not met", "incomplete", "na", "n/a"}
    s = series.astype(str).str.strip().str.lower().replace({"nan": None, "none": None, "": None})

    result = None
    # Try numeric first
    try:
        num = pd.to_numeric(s, errors="coerce")
        if num.notna().sum() > 0:
            _min, _max = num.min(), num.max()
            result = (num - _min) / (_max - _min) if _max > _min else num.clip(0, 1)
    except Exception:
        pass

    if result is None:
        # Ordinal rank by option order from legend (first option = rank 0, last = rank 1)
        if options:
            _rank = {str(o).strip().lower(): i / max(len(options) - 1, 1)
                     for i, o in enumerate(options)}
            result = s.map(lambda v: _rank.get(v) if v is not None else None)

    if result is None:
        # Binary fallback
        _vals = set(s.dropna().unique())
        if _vals <= (_BINARY_POS | _BINARY_NEG):
            result = s.map(lambda v: 1.0 if v in _BINARY_POS else (0.0 if v in _BINARY_NEG else None))

    if result is None:
        return None

    # Invert so that for defect params: low severity (first option) → 1.0 (perfect)
    if inverted:
        result = result.map(lambda v: round(1.0 - v, 6) if v is not None else None)
    return result


def _gen_qa_insights(audit_df):
    """Rule-based Key Insights + Action Items from QA audit data."""
    insights, actions = [], []
    if audit_df is None or audit_df.empty:
        return {"insights": insights, "actions": actions}
    if not ("Bot Score" in audit_df.columns and "Status" in audit_df.columns):
        return {"insights": insights, "actions": actions}

    total      = len(audit_df)
    _bs        = pd.to_numeric(audit_df["Bot Score"], errors="coerce")
    _st        = audit_df["Status"].astype(str).str.strip()
    _avg       = round(_bs.dropna().mean(), 1) if _bs.dropna().notna().any() else None
    pass_count   = int((_st == "Pass").sum())
    review_count = int((_st == "Needs Review").sum())
    fail_count   = int((_st == "Fail").sum())
    fatal_count  = int((_st == "Auto-Fail").sum())
    pass_rate    = round(pass_count  / total * 100, 1) if total else 0
    fail_rate    = round((fail_count + fatal_count) / total * 100, 1) if total else 0
    fatal_rate   = round(fatal_count / total * 100, 1) if total else 0
    _target      = 80.0

    # Auto-fail critical alert
    if fatal_count > 0:
        insights.append({"type": "critical",
            "title": f"🚨 {fatal_count} Auto-Fail{'s' if fatal_count>1 else ''} Detected",
            "detail": f"{fatal_rate}% of audits triggered a fatal disconnection. Abrupt call drops have been recorded — immediate investigation required."})
        actions.append({"priority": "high", "category": "Technical",
            "action": f"Investigate {fatal_count} auto-fail conversation{'s' if fatal_count>1 else ''} for root cause (network drops, bot logic errors, or CTI integration failures)",
            "impact": "Eliminating fatal disconnections directly protects lead conversion and bot trust scores."})

    # Pass rate vs target
    if pass_rate < _target:
        _gap = round(_target - pass_rate, 1)
        insights.append({"type": "warning" if pass_rate >= 60 else "critical",
            "title": f"⚠️ Pass Rate {pass_rate}% — {_gap}% Below {int(_target)}% Target",
            "detail": f"{pass_count} passed, {review_count} need review, {fail_count} failed out of {total} total. Coaching focus needed."})
        actions.append({"priority": "high" if pass_rate < 60 else "medium", "category": "Coaching",
            "action": f"Target the {review_count} 'Needs Review' audits (60–79% band) — these are closest to the pass threshold and fastest to convert",
            "impact": f"Moving all review cases to Pass would add +{round(review_count/total*100,1)}% to overall pass rate."})
    else:
        insights.append({"type": "success",
            "title": f"✅ Strong Pass Rate: {pass_rate}%",
            "detail": f"{pass_count} of {total} audits passed — {round(pass_rate - _target, 1)}pp above the {int(_target)}% target. Performance is on track."})

    # Best / worst auditor
    if "QA" in audit_df.columns:
        _auditor_stats = []
        for _aud, _grp in audit_df.groupby("QA"):
            _g_st    = _grp["Status"].astype(str).str.strip()
            _g_fail  = int(_g_st.isin(["Fail", "Auto-Fail"]).sum())
            _g_pass  = int((_g_st == "Pass").sum())
            _g_bs    = pd.to_numeric(_grp["Bot Score"], errors="coerce").dropna()
            _g_avg   = round(_g_bs.mean(), 1) if len(_g_bs) else None
            _auditor_stats.append({"name": str(_aud), "total": len(_grp), "fail": _g_fail,
                                   "pass": _g_pass, "avg": _g_avg,
                                   "fail_rate": round(_g_fail / len(_grp) * 100, 1) if len(_grp) else 0})
        if _auditor_stats:
            _best  = max(_auditor_stats, key=lambda x: x["avg"] or 0)
            _worst = min(_auditor_stats, key=lambda x: x["avg"] or 100)
            if _best["avg"] is not None:
                insights.append({"type": "success",
                    "title": f"🏆 Top Performer: {_best['name']}",
                    "detail": f"Avg score {_best['avg']}% across {_best['total']} audits ({_best['pass']} passes). Ideal coaching benchmark for the team."})
            if _worst["avg"] is not None and _worst["name"] != _best["name"] and _worst["avg"] < 72:
                insights.append({"type": "warning",
                    "title": f"📉 Needs Attention: {_worst['name']}",
                    "detail": f"Avg score {_worst['avg']}% with {_worst['fail']} fails ({_worst['fail_rate']}% fail rate) — below 72% performance threshold."})
                actions.append({"priority": "high", "category": "Coaching",
                    "action": f"Schedule 1:1 coaching for {_worst['name']} focusing on Tier-1 Critical parameters (highest weighted failures)",
                    "impact": f"Raising {_worst['name']}'s score to pass threshold directly reduces team-level fail rate."})

    # Weakest campaign
    if "Campaign Name" in audit_df.columns:
        _camp_stats = []
        for _cn, _cgrp in audit_df.groupby("Campaign Name"):
            _cbs = pd.to_numeric(_cgrp["Bot Score"], errors="coerce").dropna()
            if len(_cbs):
                _camp_stats.append({"name": str(_cn), "avg": round(_cbs.mean(), 1), "total": len(_cgrp)})
        if _camp_stats:
            _wc = min(_camp_stats, key=lambda x: x["avg"])
            if _wc["avg"] < 72:
                insights.append({"type": "warning",
                    "title": f"🎯 Underperforming Campaign: {_wc['name']}",
                    "detail": f"'{_wc['name']}' avg {_wc['avg']}% across {_wc['total']} audits — review bot scripts and conversation flows."})
                actions.append({"priority": "medium", "category": "Campaign",
                    "action": f"Audit the bot script for '{_wc['name']}' — check Tier-1 flow parameters (DA, CP, MC, FT) for drop-off points",
                    "impact": "Fixing script issues in this campaign can improve its pass rate and overall portfolio score."})

    # Intelligence parameter issues
    for _ip in _QA_SCHEMA["intelligence"]:
        _col = next((c for c in audit_df.columns if _ip["col"].lower() in str(c).lower()), None)
        if _col:
            _clean  = audit_df[_col].replace("", None).dropna().astype(str).str.strip()
            _issues = int((_clean != _ip["options"][0]).sum())
            _pct    = round(_issues / total * 100, 1) if total else 0
            if _pct > 15:
                insights.append({"type": "warning",
                    "title": f"{_ip['icon']} {_ip['col']}: {_pct}% Issue Rate",
                    "detail": f"{_issues} conversations flagged — above 15% threshold. {_ip['desc']}"})
                actions.append({"priority": "medium", "category": "Bot Quality",
                    "action": f"Pull conversation logs with '{_ip['col']}' issues and trace to the triggering bot node or API call",
                    "impact": f"Reducing {_ip['col'].lower()} defect rate from {_pct}% to <10% improves Intelligence Score."})

    # Large review queue
    if review_count > 0:
        _rr = round(review_count / total * 100, 1)
        if _rr > 20:
            insights.append({"type": "info",
                "title": f"📋 Review Queue: {review_count} Audits ({_rr}%)",
                "detail": f"{_rr}% of audits are in the 60–79% band — high volume of borderline cases. Prioritise coaching to convert these."})
            actions.append({"priority": "low", "category": "Process",
                "action": f"Sort borderline audits by score descending and coach the 75–79% group first — smallest effort, highest conversion probability",
                "impact": "Clearing the review queue improves pass rate accuracy and shortens coaching cycles."})

    # High top-decile cluster
    if _avg is not None:
        _above90 = int((_bs.dropna() >= 90).sum())
        _pct90   = round(_above90 / total * 100, 1)
        if _pct90 > 25:
            insights.append({"type": "success",
                "title": f"⭐ {_pct90}% of Audits Scored 90%+",
                "detail": f"{_above90} high-performing conversations — extract these as training examples for low-scoring agents."})

    # Score consistency (standard deviation)
    if _avg is not None and len(_bs.dropna()) >= 5:
        _std = round(float(_bs.dropna().std()), 1)
        if _std > 15:
            insights.append({"type": "warning",
                "title": f"📉 High Score Variance (σ = {_std})",
                "detail": f"Wide spread in bot scores indicates inconsistent training or uneven campaign difficulty. Target σ < 10 for a stable, predictable bot."})
            actions.append({"priority": "medium", "category": "Training",
                "action": "Segment audits by campaign and QA, then identify which sub-groups have the highest variance — pinpoint outlier conversations.",
                "impact": "Reducing score variance improves coaching predictability and overall pass-rate stability."})
        elif _std < 8:
            insights.append({"type": "success",
                "title": f"📐 Consistent Performance (σ = {_std})",
                "detail": f"Low variance means the bot behaves predictably across conversations — a strong signal of stable training and script quality."})

    # Best campaign (counterpart to weakest)
    if "Campaign Name" in audit_df.columns:
        _camp_stats2 = []
        for _cn2, _cgrp2 in audit_df.groupby("Campaign Name"):
            _cbs2 = pd.to_numeric(_cgrp2["Bot Score"], errors="coerce").dropna()
            if len(_cbs2) >= 3:
                _camp_stats2.append({"name": str(_cn2), "avg": round(_cbs2.mean(), 1), "total": len(_cgrp2)})
        if _camp_stats2:
            _bc2 = max(_camp_stats2, key=lambda x: x["avg"])
            if _bc2["avg"] >= 80:
                insights.append({"type": "success",
                    "title": f"🚀 Best Campaign: {_bc2['name']}",
                    "detail": f"Avg {_bc2['avg']}% across {_bc2['total']} audits — top-performing campaign. Use its script and flows as a reference template."})

    # First-half vs second-half score trend
    if _avg is not None and total >= 10:
        _mid = total // 2
        _first_h = round(float(_bs.iloc[:_mid].dropna().mean()), 1) if len(_bs.iloc[:_mid].dropna()) else None
        _last_h  = round(float(_bs.iloc[_mid:].dropna().mean()), 1) if len(_bs.iloc[_mid:].dropna()) else None
        if _first_h is not None and _last_h is not None:
            _diff = round(_last_h - _first_h, 1)
            if _diff >= 5:
                insights.append({"type": "success",
                    "title": f"📈 Positive Trend (+{_diff}% over dataset)",
                    "detail": f"Second-half avg {_last_h}% vs first-half {_first_h}% — improving trajectory. Bot updates or coaching cycles are showing results."})
            elif _diff <= -5:
                insights.append({"type": "warning",
                    "title": f"📉 Declining Trend ({_diff}% over dataset)",
                    "detail": f"Second-half avg {_last_h}% vs first-half {_first_h}% — performance is slipping. Check for recent script changes or new campaign launches."})
                actions.append({"priority": "high", "category": "Investigation",
                    "action": "Compare latest 20% of audits against earlier batches — identify specific parameter drops that coincide with the decline.",
                    "impact": "Early detection of drift prevents a campaign-wide score degradation from compounding."})

    # Tier-1 critical parameter deep-dive (Flow Issue, Bot Restarted, Bot Repetition)
    _t1_alert_params = [
        ("Flow Issue",                   "No", "🔍", "flow disruptions — bot exited the intended script path"),
        ("Bot Restarted Conversation",   "No", "🔁", "conversation restarts — bot lost context mid-call"),
        ("Bot Repetition",               "No", "🔄", "repetitive bot responses — duplicate script loops detected"),
    ]
    for _tpn, _best_val, _icon, _desc in _t1_alert_params:
        _tc = next((c for c in audit_df.columns if _tpn.lower() in str(c).lower()), None)
        if _tc:
            _tv = audit_df[_tc].replace("", None).dropna().astype(str).str.strip()
            _t_issues = int((_tv.str.lower() != _best_val.lower()).sum())
            _t_pct    = round(_t_issues / total * 100, 1) if total else 0
            if _t_pct > 10:
                insights.append({"type": "critical" if _t_pct > 30 else "warning",
                    "title": f"{_icon} {_tpn}: {_t_pct}% Issue Rate ({_t_issues} calls)",
                    "detail": f"{_t_issues} conversations had {_desc}. This is a Tier-1 Critical parameter — direct impact on overall bot score."})
                actions.append({"priority": "high" if _t_pct > 30 else "medium", "category": "Bot Quality",
                    "action": f"Pull the {_t_issues} '{_tpn}' flagged conversations, identify the common trigger node, and apply a targeted script fix.",
                    "impact": f"Fixing {_tpn} issues in {_t_pct}% of calls can recover significant weighted score points (Tier-1 weight ~11–9%)."})

    # Disposition × score correlation
    if "Disposition" in audit_df.columns and _avg is not None:
        _disp_scores = []
        for _dn, _dg in audit_df.groupby("Disposition"):
            _dns = pd.to_numeric(_dg["Bot Score"], errors="coerce").dropna()
            if len(_dns) >= 3:
                _disp_scores.append({"disp": str(_dn), "avg": round(float(_dns.mean()), 1), "n": len(_dns)})
        if _disp_scores:
            _worst_d = min(_disp_scores, key=lambda x: x["avg"])
            _best_d  = max(_disp_scores, key=lambda x: x["avg"])
            if _worst_d["avg"] < _avg - 8:
                insights.append({"type": "info",
                    "title": f"🔗 Lowest Score on '{_worst_d['disp']}' calls ({_worst_d['avg']}%)",
                    "detail": f"Calls ending as '{_worst_d['disp']}' average {_worst_d['avg']}% — {round(_avg - _worst_d['avg'], 1)}pp below overall mean. Bot may be under-scripted for this outcome."})
                actions.append({"priority": "medium", "category": "Script",
                    "action": f"Review the conversation flow for calls ending as '{_worst_d['disp']}' — likely missing handling for objections or redirects.",
                    "impact": f"Improving score on this disposition segment by 10pp directly raises the overall average."})
            if _best_d["avg"] >= _avg + 8:
                insights.append({"type": "success",
                    "title": f"💎 Highest Score on '{_best_d['disp']}' calls ({_best_d['avg']}%)",
                    "detail": f"Calls ending as '{_best_d['disp']}' average {_best_d['avg']}% — {round(_best_d['avg'] - _avg, 1)}pp above overall mean. Model the bot behaviour from these interactions."})

    # Weakest QA-schema parameter (Tier-1 focus)
    if total >= 5:
        _t1_params = [_p for _t in _QA_SCHEMA["tiers"] if "TIER 1" in _t.get("label","") for _p in _t["params"]]
        _p_avgs = []
        for _tp in _t1_params:
            _pc = next((c for c in audit_df.columns if _tp["col"].lower() in str(c).lower()), None)
            if _pc:
                _pv = pd.to_numeric(audit_df[_pc], errors="coerce").dropna()
                if len(_pv):
                    _pmax_vals = [int(o) for o in _tp.get("options", ["0","1","2"]) if str(o).lstrip("-").isdigit()]
                    _pmax = max(_pmax_vals) if _pmax_vals else 2
                    _p_avgs.append({"col": _tp["col"], "pct": round(float(_pv.mean()) / _pmax * 100, 1)})
        if _p_avgs:
            _weakest_p = min(_p_avgs, key=lambda x: x["pct"])
            if _weakest_p["pct"] < 65:
                insights.append({"type": "critical" if _weakest_p["pct"] < 50 else "warning",
                    "title": f"🎯 Weakest Tier-1 Param: {_weakest_p['col']} ({_weakest_p['pct']}%)",
                    "detail": f"'{_weakest_p['col']}' scores only {_weakest_p['pct']}% on average — the single biggest drag on weighted bot score. This is a Tier-1 Critical parameter."})
                actions.append({"priority": "high", "category": "Bot Quality",
                    "action": f"Prioritise a dedicated sprint on '{_weakest_p['col']}' — review its scoring criteria, add more training examples, and test with edge-case conversations.",
                    "impact": f"Raising '{_weakest_p['col']}' by 20pp would be the highest-ROI improvement available given its Tier-1 weighting."})

    return {"insights": insights, "actions": actions}


def _render_sense_scorecard(sheets, legend_map):
    """Full QA Scorecard — weighted scoring, intelligence params, agent breakdown."""

    # ── Merge built-in Convin Sense params into legend map ────────────────────
    legend_map = _merge_builtin_params(legend_map)

    # ── Find audit sheet (prefer name match, then column-content fallback) ──────
    audit_df   = None
    audit_name = None
    _AUDIT_NAME_KW = ("audit", "qa", "review", "score")
    _AUDIT_COL_KW  = {"Bot Score", "Status", "QA", "Campaign Name"}
    for k, v in sheets.items():
        if any(kw in k.lower() for kw in _AUDIT_NAME_KW):
            _safe_k  = k.replace(" ", "_").lower()
            audit_df = st.session_state.get(f"sense_audit_edits_{_safe_k}", v).copy()
            audit_name = k
            break
    if audit_df is None:
        # Fallback: pick the sheet whose columns best match known audit columns
        _best_k, _best_v, _best_score = None, None, 0
        for k, v in sheets.items():
            if hasattr(v, "columns"):
                _sc = len(_AUDIT_COL_KW & set(str(c).strip() for c in v.columns))
                if _sc > _best_score:
                    _best_score, _best_k, _best_v = _sc, k, v
        if _best_k and _best_score > 0:
            _safe_k  = _best_k.replace(" ", "_").lower()
            audit_df = st.session_state.get(f"sense_audit_edits_{_safe_k}", _best_v).copy()
            audit_name = _best_k

    # ── Merge form-submitted audit log into audit_df ──────────────────────────
    _form_log = st.session_state.get("sense_audit_log")
    if _form_log is None:
        _form_log = _audit_log_load()
        if _form_log:
            st.session_state["sense_audit_log"] = _form_log
    if _form_log:
        _log_df = pd.DataFrame([{k: v for k, v in r.items() if k != "_row_id"} for r in _form_log])
        if audit_df is not None:
            _appended = _log_df.reindex(columns=audit_df.columns, fill_value="")
            audit_df  = pd.concat([audit_df, _appended], ignore_index=True)
        else:
            audit_df  = _log_df
            audit_name = "Form Submissions"

    if audit_df is None:
        st.markdown(
            '<div style="text-align:center;padding:3rem;color:#5588bb;font-size:0.9rem;">'
            '📋 No data yet. Upload a file with an <strong>Audit Sheet</strong>, '
            'or submit your first QA audit using the <strong>✍️ New Audit</strong> tab.</div>',
            unsafe_allow_html=True,
        )
        return

    # ── Inject missing built-in columns ───────────────────────────────────────
    for param in _SENSE_BUILTIN_PARAMS:
        if not any(param.lower() in str(c).lower() or str(c).lower() in param.lower()
                   for c in audit_df.columns):
            audit_df[param] = ""

    # ── Global filter bar ─────────────────────────────────────────────────────
    if True:
        _sf1, _sf2, _sf3, _sf4, _sf5 = st.columns([2, 2, 2, 1.4, 1.4])
        with _sf1:
            _cli_opts_sc = ["All Clients"] + sorted(audit_df["Client"].dropna().astype(str).unique().tolist()) if "Client" in audit_df.columns else ["All Clients"]
            _sc_cli = st.selectbox("Client", _cli_opts_sc, key="sc_filter_client")
        with _sf2:
            _camp_src = audit_df[audit_df["Client"].astype(str)==_sc_cli]["Campaign Name"] if (_sc_cli!="All Clients" and "Client" in audit_df.columns and "Campaign Name" in audit_df.columns) else (audit_df["Campaign Name"] if "Campaign Name" in audit_df.columns else pd.Series(dtype=str))
            _camp_opts_sc = ["All Campaigns"] + sorted(_camp_src.dropna().astype(str).unique().tolist())
            _sc_camp = st.selectbox("Campaign", _camp_opts_sc, key="sc_filter_camp")
        with _sf3:
            _qa_opts_sc = ["All QA"] + sorted(audit_df["QA"].dropna().astype(str).unique().tolist()) if "QA" in audit_df.columns else ["All QA"]
            _sc_qa = st.selectbox("QA", _qa_opts_sc, key="sc_filter_qa")
        _sc_min = _sc_max = _sc_dc = None
        with _sf4:
            _DATE_KW_SC = ("audit date","date","created","submitted","period","time")
            _sc_dc = next((c for c in audit_df.columns if any(k in str(c).lower() for k in _DATE_KW_SC)), None)
            if _sc_dc:
                try:
                    _sc_dates = pd.to_datetime(audit_df[_sc_dc], errors="coerce").dropna()
                    _sc_min = _sc_dates.min().date()
                    _sc_max = _sc_dates.max().date()
                    _sc_from = st.date_input("From", value=_sc_min, key="sc_filter_from")
                except Exception:
                    _sc_from = None
            else:
                _sc_from = None
        with _sf5:
            if _sc_dc and _sc_from is not None and _sc_max is not None:
                try:
                    _sc_to = st.date_input("To", value=_sc_max, key="sc_filter_to")
                except Exception:
                    _sc_to = None
            else:
                _sc_to = None
            if st.button("✕ Clear", key="sc_clear_filters", use_container_width=True):
                for _k in ["sc_filter_client","sc_filter_camp","sc_filter_qa","sc_filter_from","sc_filter_to"]:
                    st.session_state.pop(_k, None)
                st.rerun()

        # Apply filters
        _sc_total_before = len(audit_df)
        if _sc_cli  != "All Clients"   and "Client"       in audit_df.columns: audit_df = audit_df[audit_df["Client"].astype(str)==_sc_cli].copy()
        if _sc_camp != "All Campaigns" and "Campaign Name" in audit_df.columns: audit_df = audit_df[audit_df["Campaign Name"].astype(str)==_sc_camp].copy()
        if _sc_qa   != "All QA"        and "QA"            in audit_df.columns: audit_df = audit_df[audit_df["QA"].astype(str)==_sc_qa].copy()
        if _sc_dc and _sc_from is not None and _sc_to is not None:
            try:
                audit_df = audit_df.copy()
                audit_df["_sc_date_tmp"] = pd.to_datetime(audit_df[_sc_dc], errors="coerce")
                audit_df = audit_df[(audit_df["_sc_date_tmp"].dt.date >= _sc_from) & (audit_df["_sc_date_tmp"].dt.date <= _sc_to)].copy()
                audit_df = audit_df.drop(columns=["_sc_date_tmp"])
            except Exception:
                pass
        _active_filters = any([_sc_cli!="All Clients", _sc_camp!="All Campaigns", _sc_qa!="All QA", _sc_from is not None])
        if _active_filters:
            st.markdown(f'<div style="font-size:0.7rem;color:#2563EB;margin-bottom:8px;background:rgba(61,130,245,0.06);border-radius:6px;padding:5px 12px;">🔍 Showing <strong>{len(audit_df):,}</strong> of <strong>{_sc_total_before:,}</strong> audits</div>', unsafe_allow_html=True)

    # ── Detect scored columns ─────────────────────────────────────────────────
    scored_cols = [c for c in audit_df.columns if _match_legend(c, legend_map)]

    # ── Detect whether this is QA schema data (has Bot Score / Status) ────────
    _has_qa_schema = ("Bot Score" in audit_df.columns and "Status" in audit_df.columns)

    # ── Detect grouping / date columns ────────────────────────────────────────
    _GRP_KW  = ("auditor","agent","rep","analyst","team","name","user","operator","staff","reviewer","caller")
    _DATE_KW = ("audit date","date","time","month","week","day","period","created","submitted")
    group_col = next((c for c in audit_df.columns if any(k == str(c).strip().lower() or k in str(c).lower() for k in _GRP_KW)), None)
    date_col  = next((c for c in audit_df.columns if any(k in str(c).lower() for k in _DATE_KW)), None)

    # ── Scoring: use Bot Score column if QA schema, else compute from legend ──
    if _has_qa_schema:
        _row_scores_pct = pd.to_numeric(audit_df["Bot Score"], errors="coerce")
        _row_scores     = _row_scores_pct / 100.0
        total_weight    = 1.0   # not applicable but used in header
        _custom_weights = {}
        for col in scored_cols:
            _bcfg = _builtin_cfg(col)
            _custom_weights[col] = float(_bcfg["weight"]) if _bcfg else _DEFAULT_PARAM_WEIGHT
    else:
        _custom_weights = {}
        for col in scored_cols:
            _bcfg  = _builtin_cfg(col)
            _def_w = float(_bcfg["weight"]) if _bcfg else float(_DEFAULT_PARAM_WEIGHT)
            _custom_weights[col] = st.session_state.get(f"sense_w_{col}", _def_w)

        _score_parts = []
        for c in scored_cols:
            opts  = legend_map.get(c) or _match_legend(c, legend_map) or []
            _bcfg = _builtin_cfg(c)
            _inv  = _bcfg["inverted"] if _bcfg else False
            _w    = _custom_weights[c]
            _ns   = _score_to_numeric(audit_df[c], opts, inverted=_inv)
            if _ns is not None:
                _score_parts.append((_ns, _w))

        total_weight = sum(w for _, w in _score_parts)
        if _score_parts and total_weight > 0:
            _row_scores = sum(s * w for s, w in _score_parts) / total_weight
        else:
            _row_scores = None

    # ── KPI calculations ──────────────────────────────────────────────────────
    total_rows = len(audit_df)
    if _has_qa_schema:
        _valid_bs    = _row_scores_pct.dropna()
        avg_score    = round(_valid_bs.mean(), 1) if len(_valid_bs) else None
        scored_rows  = int(_valid_bs.notna().sum())
        partial_rows = 0
        completion_pct = round(scored_rows / total_rows * 100, 1) if total_rows else 0
        _status_col    = audit_df["Status"].astype(str).str.strip()
        pass_count     = int((_status_col == "Pass").sum())
        review_count   = int((_status_col == "Needs Review").sum())
        fail_count     = int((_status_col == "Fail").sum())
        fatal_count    = int((_status_col == "Auto-Fail").sum())
        pass_rate      = round(pass_count / total_rows * 100, 1) if total_rows else None
        fatal_rate     = round(fatal_count / total_rows * 100, 1) if total_rows else None
    else:
        if scored_cols:
            _scored_mask = audit_df[scored_cols].replace("", None).notna().all(axis=1)
            scored_rows  = int(_scored_mask.sum())
            partial_rows = int((audit_df[scored_cols].replace("", None).notna().any(axis=1) & ~_scored_mask).sum())
        else:
            scored_rows = partial_rows = 0
        completion_pct = round(scored_rows / total_rows * 100, 1) if total_rows else 0
        avg_score  = round(_row_scores.mean() * 100, 1)          if _row_scores is not None else None
        pass_rate  = round((_row_scores >= 0.5).mean() * 100, 1) if _row_scores is not None else None
        pass_count = fatal_count = fatal_rate = None

    # ── Convin Sense intelligence KPIs (defect counts) ───────────────────────
    _intel_kpis = {}
    for _ip in _QA_SCHEMA["intelligence"]:
        _col = next((c for c in audit_df.columns
                     if _ip["col"].lower() in str(c).lower() or str(c).lower() in _ip["col"].lower()), None)
        if _col:
            _clean = audit_df[_col].replace("", None).dropna().astype(str).str.strip()
            _good  = _ip["options"][0]
            _dc    = int((_clean != _good).sum())
            _dp    = round(_dc / total_rows * 100, 1) if total_rows else 0
            _intel_kpis[_ip["col"]] = {"count": _dc, "pct": _dp,
                                       "color": _ip["color"], "icon": _ip["icon"],
                                       "desc": _ip["desc"]}

    # ── Page header ───────────────────────────────────────────────────────────
    _src_label      = "Convin.ai QA Schema" if _has_qa_schema else audit_name
    _auditor_count  = audit_df["QA"].nunique() if "QA" in audit_df.columns else 0
    _campaign_count = audit_df["Campaign Name"].nunique() if "Campaign Name" in audit_df.columns else 0
    st.markdown(
        f'<div style="display:flex;align-items:center;justify-content:space-between;'
        f'margin-bottom:1.2rem;flex-wrap:wrap;gap:8px;">'
        f'<div>'
        f'<div style="font-size:1.2rem;font-weight:900;color:#0d1d3a;letter-spacing:-0.02em;">📊 QA Scorecard</div>'
        f'<div style="font-size:0.72rem;color:#5588bb;margin-top:2px;">'
        f'Source: <strong>{_src_label}</strong>'
        f' &nbsp;·&nbsp; <strong>{total_rows:,}</strong> audits'
        f'{f" &nbsp;·&nbsp; <strong>{_auditor_count}</strong> auditors" if _auditor_count else ""}'
        f'{f" &nbsp;·&nbsp; <strong>{_campaign_count}</strong> campaigns" if _campaign_count else ""}'
        f'</div>'
        f'</div>'
        f'<div style="font-size:0.67rem;color:#aabbcc;background:#fff;'
        f'border:1px solid #e4e7ec;border-radius:8px;padding:4px 10px;">'
        f'{pd.Timestamp.now().strftime("%d %b %Y  %H:%M")}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Hero row: gauge + KPI cards ───────────────────────────────────────────
    if _has_qa_schema:
        _fc        = "#dc2626" if (fatal_count or 0) > 0 else "#0ebc6e"
        _gs        = avg_score or 0
        _gc_gauge  = "#0ebc6e" if _gs >= 80 else "#f59e0b" if _gs >= 60 else "#dc2626"
        _arc_total = 219.9   # π × 70
        _arc_fill  = round(_arc_total * _gs / 100, 1)
        _slabel    = _qa_status(_gs, False)
        _sc_col    = _qa_status_color(_slabel)
        _rr        = round(review_count / total_rows * 100, 1) if total_rows else 0
        _fr2       = round(fail_count   / total_rows * 100, 1) if total_rows else 0
        _afr       = round(fatal_count  / total_rows * 100, 1) if total_rows else 0
        _compl_c   = "#0ebc6e" if completion_pct >= 80 else "#f59e0b" if completion_pct >= 50 else "#dc2626"
        # Disposition accuracy KPI
        if "Correct Disposition" in audit_df.columns:
            _cd_col   = audit_df["Correct Disposition"].replace("", None).dropna().astype(str).str.strip()
            _cd_yes   = int((_cd_col.str.lower() == "yes").sum())
            _cd_total = len(_cd_col)
            _disp_acc = round(_cd_yes / _cd_total * 100, 1) if _cd_total else None
        else:
            _disp_acc = None

        _gauge_svg = (
            f'<svg width="160" height="100" viewBox="0 0 160 100" style="display:block;margin:auto;">'
            f'<path d="M 10 85 A 70 70 0 0 1 150 85" fill="none" stroke="#edf2fb" stroke-width="14" stroke-linecap="round"/>'
            f'<path d="M 10 85 A 70 70 0 0 1 150 85" fill="none" stroke="{_gc_gauge}" stroke-width="14"'
            f' stroke-linecap="round" stroke-dasharray="{_arc_fill} 1000"/>'
            f'<text x="80" y="73" text-anchor="middle" font-size="27" font-weight="900" fill="{_gc_gauge}"'
            f' font-family="Inter,sans-serif">{_gs}%</text>'
            f'<text x="80" y="90" text-anchor="middle" font-size="9.5" fill="#5588bb" font-family="Inter,sans-serif">Avg Bot Score</text>'
            f'</svg>'
        )

        st.markdown(f"""
<div style="display:grid;grid-template-columns:190px 1fr;gap:16px;margin-bottom:1.4rem;align-items:stretch;">
  <div style="background:#fff;border:1px solid #e4e7ec;border-radius:14px;
    padding:18px 12px 12px;display:flex;flex-direction:column;align-items:center;justify-content:center;">
    {_gauge_svg}
    <div style="margin-top:8px;background:{_sc_col}18;border:1px solid {_sc_col}55;
      border-radius:20px;padding:3px 16px;font-size:0.72rem;font-weight:800;color:{_sc_col};">{_slabel}</div>
    <div style="font-size:0.62rem;color:#aabbcc;margin-top:6px;">{total_rows:,} total audits</div>
  </div>
  <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;grid-auto-rows:min-content;">
    <div style="background:#fff;border:1px solid #e4e7ec;border-left:3px solid #2563EB;border-radius:10px;padding:13px 14px;">
      <div style="font-size:0.57rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#2563EB;margin-bottom:4px;">Total Audits</div>
      <div style="font-size:1.65rem;font-weight:900;color:#2563EB;line-height:1;">{total_rows:,}</div>
      <div style="font-size:0.62rem;color:#aabbcc;margin-top:3px;">{_auditor_count} auditor{"s" if _auditor_count != 1 else ""}</div>
    </div>
    <div style="background:#fff;border:1px solid #e4e7ec;border-left:3px solid #0ebc6e;border-radius:10px;padding:13px 14px;">
      <div style="font-size:0.57rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#0ebc6e;margin-bottom:4px;">Pass ≥80%</div>
      <div style="font-size:1.65rem;font-weight:900;color:#0ebc6e;line-height:1;">{pass_count:,}</div>
      <div style="height:4px;background:#f0f2f5;border-radius:2px;margin-top:5px;overflow:hidden;"><div style="width:{pass_rate or 0}%;height:100%;background:#0ebc6e;border-radius:2px;"></div></div>
      <div style="font-size:0.62rem;color:#5588bb;margin-top:2px;">{pass_rate}% pass rate</div>
    </div>
    <div style="background:#fff;border:1px solid #e4e7ec;border-left:3px solid #f59e0b;border-radius:10px;padding:13px 14px;">
      <div style="font-size:0.57rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#f59e0b;margin-bottom:4px;">Needs Review</div>
      <div style="font-size:1.65rem;font-weight:900;color:#f59e0b;line-height:1;">{review_count:,}</div>
      <div style="height:4px;background:#f0f2f5;border-radius:2px;margin-top:5px;overflow:hidden;"><div style="width:{_rr}%;height:100%;background:#f59e0b;border-radius:2px;"></div></div>
      <div style="font-size:0.62rem;color:#5588bb;margin-top:2px;">60–79% range</div>
    </div>
    <div style="background:#fff;border:1px solid #e4e7ec;border-left:3px solid #dc2626;border-radius:10px;padding:13px 14px;">
      <div style="font-size:0.57rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#dc2626;margin-bottom:4px;">Fail &lt;60%</div>
      <div style="font-size:1.65rem;font-weight:900;color:#dc2626;line-height:1;">{fail_count:,}</div>
      <div style="height:4px;background:#f0f2f5;border-radius:2px;margin-top:5px;overflow:hidden;"><div style="width:{_fr2}%;height:100%;background:#dc2626;border-radius:2px;"></div></div>
      <div style="font-size:0.62rem;color:#5588bb;margin-top:2px;">{_fr2}% of total</div>
    </div>
    <div style="background:#fff;border:1px solid #e4e7ec;border-left:3px solid {_fc};border-radius:10px;padding:13px 14px;">
      <div style="font-size:0.57rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:{_fc};margin-bottom:4px;">Auto-Fail</div>
      <div style="font-size:1.65rem;font-weight:900;color:{_fc};line-height:1;">{fatal_count:,}</div>
      <div style="height:4px;background:#f0f2f5;border-radius:2px;margin-top:5px;overflow:hidden;"><div style="width:{_afr}%;height:100%;background:{_fc};border-radius:2px;"></div></div>
      <div style="font-size:0.62rem;color:#5588bb;margin-top:2px;">Fatal trigger</div>
    </div>
    <div style="background:#fff;border:1px solid #e4e7ec;border-left:3px solid {_compl_c};border-radius:10px;padding:13px 14px;">
      <div style="font-size:0.57rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:{_compl_c};margin-bottom:4px;">Completion</div>
      <div style="font-size:1.65rem;font-weight:900;color:{_compl_c};line-height:1;">{completion_pct}%</div>
      <div style="height:4px;background:#f0f2f5;border-radius:2px;margin-top:5px;overflow:hidden;"><div style="width:{completion_pct}%;height:100%;background:{_compl_c};border-radius:2px;"></div></div>
      <div style="font-size:0.62rem;color:#5588bb;margin-top:2px;">{scored_rows:,} scored</div>
    </div>
    {'<div style="background:#fff;border:1px solid #e4e7ec;border-left:3px solid ' + ("#0ebc6e" if (_disp_acc or 0) >= 80 else "#f59e0b" if (_disp_acc or 0) >= 60 else "#dc2626") + ';border-radius:10px;padding:13px 14px;"><div style="font-size:0.57rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:' + ("#0ebc6e" if (_disp_acc or 0) >= 80 else "#f59e0b" if (_disp_acc or 0) >= 60 else "#dc2626") + ';margin-bottom:4px;">Disposition Accuracy</div><div style="font-size:1.65rem;font-weight:900;color:' + ("#0ebc6e" if (_disp_acc or 0) >= 80 else "#f59e0b" if (_disp_acc or 0) >= 60 else "#dc2626") + ';line-height:1;">' + str(_disp_acc) + '%</div><div style="height:4px;background:#f0f2f5;border-radius:2px;margin-top:5px;overflow:hidden;"><div style="width:' + str(_disp_acc) + '%;height:100%;background:' + ("#0ebc6e" if (_disp_acc or 0) >= 80 else "#f59e0b" if (_disp_acc or 0) >= 60 else "#dc2626") + ';border-radius:2px;"></div></div><div style="font-size:0.62rem;color:#5588bb;margin-top:2px;">correct dispositions</div></div>' if _disp_acc is not None else ''}
  </div>
</div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""<div class="stats-grid" style="grid-template-columns:repeat(5,1fr);margin-bottom:1rem;">
          <div class="stat-card" style="border-top:2px solid #2563EB;">
            <div style="color:#2a5080;font-size:0.58rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:5px;">Total Rows</div>
            <div style="color:#2563EB;font-size:1.7rem;font-weight:800;">{total_rows:,}</div>
          </div>
          <div class="stat-card" style="border-top:2px solid #0ebc6e;">
            <div style="color:#2a5080;font-size:0.58rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:5px;">Fully Scored</div>
            <div style="color:#0ebc6e;font-size:1.7rem;font-weight:800;">{scored_rows:,}</div>
            <div style="font-size:0.65rem;color:#5588bb;margin-top:2px;">{partial_rows} partial</div>
          </div>
          <div class="stat-card" style="border-top:2px solid {'#dc2626' if completion_pct<50 else '#f59e0b' if completion_pct<80 else '#0ebc6e'};">
            <div style="color:#2a5080;font-size:0.58rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:5px;">Completion</div>
            <div style="color:{'#dc2626' if completion_pct<50 else '#f59e0b' if completion_pct<80 else '#0ebc6e'};font-size:1.7rem;font-weight:800;">{completion_pct}%</div>
          </div>
          <div class="stat-card" style="border-top:2px solid #7c3aed;">
            <div style="color:#2a5080;font-size:0.58rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:5px;">Weighted Score</div>
            <div style="color:#7c3aed;font-size:1.7rem;font-weight:800;">{"—" if avg_score is None else f"{avg_score}%"}</div>
          </div>
          <div class="stat-card" style="border-top:2px solid {'#0ebc6e' if pass_rate and pass_rate>=70 else '#dc2626' if pass_rate is not None else '#aabbcc'};">
            <div style="color:#2a5080;font-size:0.58rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:5px;">Pass Rate</div>
            <div style="color:{'#0ebc6e' if pass_rate and pass_rate>=70 else '#dc2626' if pass_rate is not None else '#aabbcc'};font-size:1.7rem;font-weight:800;">{"—" if pass_rate is None else f"{pass_rate}%"}</div>
          </div>
        </div>""", unsafe_allow_html=True)

    # ── Key Insights + Action Items ───────────────────────────────────────────
    if _has_qa_schema:
        _qi = _gen_qa_insights(audit_df)
        _all_insights = _qi.get("insights", [])
        _all_actions  = _qi.get("actions",  [])
        if _all_insights or _all_actions:
            _ins_cols = st.columns([3, 2])
            with _ins_cols[0]:
                st.markdown('<div class="section-chip">💡 Key Insights</div>', unsafe_allow_html=True)
                _TYPE_CFG = {
                    "critical": ("#fff1f2", "#e11d48", "#9f1239", "#fecdd3"),
                    "warning":  ("#fffbf0", "#d97706", "#92400e", "#fde68a"),
                    "success":  ("#ecfdf5", "#059669", "#064e3b", "#a7f3d0"),
                    "info":     ("#eef2ff", "#4f46e5", "#312e81", "#c7d2fe"),
                }
                for _ins in _all_insights:
                    _tcfg = _TYPE_CFG.get(_ins["type"], _TYPE_CFG["info"])
                    st.markdown(
                        f'<div style="background:{_tcfg[0]};border:1px solid {_tcfg[3]};'
                        f'border-left:4px solid {_tcfg[1]};border-radius:10px;'
                        f'padding:12px 16px;margin-bottom:8px;">'
                        f'<div style="font-size:0.78rem;font-weight:700;color:{_tcfg[2]};margin-bottom:4px;">{_ins["title"]}</div>'
                        f'<div style="font-size:0.72rem;color:{_tcfg[2]};opacity:0.85;line-height:1.5;">{_ins["detail"]}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
            with _ins_cols[1]:
                st.markdown('<div class="section-chip">🎯 Action Items</div>', unsafe_allow_html=True)
                _PRI_CFG = {
                    "high":   ("#dc2626", "🔴", "#fef2f2"),
                    "medium": ("#f59e0b", "🟡", "#fffbeb"),
                    "low":    ("#16a34a", "🟢", "#f0fdf4"),
                }
                for _act in _all_actions:
                    _pcfg = _PRI_CFG.get(_act["priority"], _PRI_CFG["low"])
                    st.markdown(
                        f'<div style="background:{_pcfg[2]};border:1px solid {_pcfg[0]}33;'
                        f'border-radius:10px;padding:12px 15px;margin-bottom:8px;">'
                        f'<div style="display:flex;align-items:center;gap:7px;margin-bottom:5px;">'
                        f'<span style="font-size:0.75rem;">{_pcfg[1]}</span>'
                        f'<span style="font-size:0.65rem;font-weight:700;letter-spacing:0.08em;'
                        f'text-transform:uppercase;color:{_pcfg[0]};">{_act["priority"].upper()} · {_act["category"]}</span>'
                        f'</div>'
                        f'<div style="font-size:0.73rem;font-weight:600;color:#0d1d3a;margin-bottom:5px;line-height:1.4;">{_act["action"]}</div>'
                        f'<div style="font-size:0.65rem;color:#5588bb;line-height:1.4;border-top:1px solid {_pcfg[0]}22;padding-top:5px;">'
                        f'Impact: {_act["impact"]}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

    # ── Convin Sense Intelligence strip ───────────────────────────────────────
    if _intel_kpis:
        st.markdown('<div class="section-chip">🧠 Sense Intelligence</div>', unsafe_allow_html=True)
        _intel_cards = ""
        for param, kpi in _intel_kpis.items():
            _alert = kpi["pct"] > 20
            _intel_cards += (
                f'<div style="background:#fff;border:1px solid {kpi["color"]}33;border-left:4px solid {kpi["color"]};'
                f'border-radius:12px;padding:14px 18px;flex:1;min-width:200px;">'
                f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">'
                f'<span style="font-size:1.2rem;">{kpi["icon"]}</span>'
                f'<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:{kpi["color"]};">{param}</div>'
                f'</div>'
                f'<div style="font-size:0.7rem;color:#5588bb;margin-bottom:10px;">{kpi["desc"]}</div>'
                f'<div style="display:flex;align-items:baseline;gap:8px;">'
                f'<div style="font-size:1.8rem;font-weight:900;color:{kpi["color"]};">{kpi["count"]:,}</div>'
                f'<div style="font-size:0.78rem;color:#5588bb;">issues detected</div>'
                f'</div>'
                f'<div style="height:6px;background:#f0f2f5;border-radius:3px;margin-top:8px;overflow:hidden;">'
                f'<div style="width:{min(kpi["pct"],100)}%;height:100%;background:{kpi["color"]};border-radius:3px;"></div>'
                f'</div>'
                f'<div style="font-size:0.65rem;color:{"#dc2626" if _alert else "#5588bb"};margin-top:4px;font-weight:{"700" if _alert else "400"};">'
                f'{"⚠️ " if _alert else ""}{kpi["pct"]}% of conversations affected</div>'
                f'</div>'
            )
        st.markdown(
            f'<div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:1.4rem;">{_intel_cards}</div>',
            unsafe_allow_html=True,
        )

    if not scored_cols:
        st.info("No scored parameters detected. Upload a file with an Audit Sheet and Legend, or the built-in parameters will appear automatically.")
        return

    # ── Weight editor ─────────────────────────────────────────────────────────
    with st.expander("⚙️ Adjust Parameter Weights", expanded=False):
        st.markdown(
            '<div style="font-size:0.71rem;color:#5588bb;margin-bottom:10px;">'
            'Weights control how much each parameter influences the overall score. '
            'Built-in tier params have pre-set weights but are adjustable here.</div>',
            unsafe_allow_html=True,
        )
        _w_cols = st.columns(min(len(scored_cols), 4))
        for wi, col in enumerate(scored_cols):
            _bcfg  = _builtin_cfg(col)
            _def_w = float(_bcfg["weight"]) if _bcfg else float(_DEFAULT_PARAM_WEIGHT)
            with _w_cols[wi % len(_w_cols)]:
                _w_val = max(0.0, float(st.session_state.get(f"sense_w_{col}", _def_w)))
                _new_w = st.number_input(
                    str(col), min_value=0.0, max_value=5.0,
                    value=_w_val,
                    step=0.1, key=f"sense_w_{col}", format="%.1f",
                )
                _custom_weights[col] = _new_w

    # ── Tier breakdown (QA schema only) ──────────────────────────────────────
    if _has_qa_schema and scored_cols:
        st.markdown('<div class="section-chip">📊 Score Breakdown by Tier</div>', unsafe_allow_html=True)
        _tier_row = ""
        for _tier in _QA_SCHEMA["tiers"]:
            _tc = _tier["color"]
            _tier_params = [p["col"] for p in _tier["params"] if p["weight"] > 0]
            _scores_for_tier = []
            for _tp in _tier_params:
                _col_match = next((c for c in audit_df.columns if c == _tp), None)
                if _col_match:
                    _ns = pd.to_numeric(audit_df[_col_match].replace("", None), errors="coerce")
                    _valid = _ns.dropna()
                    if len(_valid):
                        _scores_for_tier.append(_valid.mean() / 2.0)  # normalise 0-2 → 0-1
            _tier_avg = round(sum(_scores_for_tier) / len(_scores_for_tier) * 100, 1) if _scores_for_tier else None
            _tier_row += (
                f'<div style="flex:1;min-width:160px;background:#fff;border:1px solid {_tc}33;'
                f'border-top:3px solid {_tc};border-radius:10px;padding:12px 16px;">'
                f'<div style="font-size:0.62rem;font-weight:700;color:{_tc};letter-spacing:0.08em;'
                f'text-transform:uppercase;margin-bottom:4px;">{_tier["label"]}</div>'
                f'<div style="font-size:0.62rem;color:#aabbcc;margin-bottom:8px;">{_tier["weight_pct"]}% of score</div>'
                f'<div style="font-size:1.9rem;font-weight:900;color:{_tc};">{"—" if _tier_avg is None else f"{_tier_avg}%"}</div>'
                f'<div style="height:5px;background:#f0f2f5;border-radius:3px;margin-top:6px;overflow:hidden;">'
                f'<div style="width:{_tier_avg or 0}%;height:100%;background:{_tc};border-radius:3px;"></div></div>'
                f'</div>'
            )
        st.markdown(
            f'<div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:1.2rem;">{_tier_row}</div>',
            unsafe_allow_html=True,
        )

    # ── Actionable Alerts ─────────────────────────────────────────────────────
    if _has_qa_schema and len(audit_df) > 0:
        _alerts = []
        _bs_all  = pd.to_numeric(audit_df["Bot Score"], errors="coerce")
        _st_all  = audit_df["Status"].astype(str).str.strip()
        _fat_all = int((_st_all == "Auto-Fail").sum())
        _rev_all = int((_st_all == "Needs Review").sum())
        _pr_all  = round(int((_st_all=="Pass").sum()) / len(audit_df) * 100, 1) if len(audit_df) else 0
        # Auto-fails alert
        if _fat_all > 0:
            _alerts.append(("🚨", "#dc2626", "#fef2f2", f"{_fat_all} Auto-Fail(s) detected", f"Review these {_fat_all} calls immediately — fatal bot disconnections hurt conversion and client trust."))
        # Pass rate alert
        if _pr_all < 80:
            _alerts.append(("⚠️", "#f59e0b", "#fffbeb", f"Pass rate {_pr_all}% is below 80% target", f"{_rev_all} audits in 'Needs Review' (60–79%) are the fastest to push to Pass — prioritise coaching these."))
        # Weakest client
        if "Client" in audit_df.columns:
            _cli_sc = []
            for _cli, _cg in audit_df.groupby("Client"):
                _cb = pd.to_numeric(_cg["Bot Score"], errors="coerce").dropna()
                if len(_cb) >= 3:
                    _cli_sc.append((_cli, round(_cb.mean(), 1)))
            if _cli_sc:
                _cli_sc.sort(key=lambda x: x[1])
                _wc = _cli_sc[0]
                if _wc[1] < 75:
                    _alerts.append(("📉", "#7c3aed", "#fdf8ff", f"Client at risk: {_wc[0]} ({_wc[1]}% avg)", f"Lowest-scoring client. Run a dedicated coaching sprint and flag issues to the PM."))
        # Weakest campaign
        if "Campaign Name" in audit_df.columns:
            _camp_sc2 = []
            for _cn2, _cg2 in audit_df.groupby("Campaign Name"):
                _cb2 = pd.to_numeric(_cg2["Bot Score"], errors="coerce").dropna()
                if len(_cb2) >= 3:
                    _camp_sc2.append((_cn2, round(_cb2.mean(), 1)))
            if _camp_sc2:
                _camp_sc2.sort(key=lambda x: x[1])
                _wcamp = _camp_sc2[0]
                if _wcamp[1] < 75:
                    _alerts.append(("🎯", "#2563EB", "#fff0f8", f"Weak campaign: {_wcamp[0]} ({_wcamp[1]}% avg)", f"This campaign needs a bot parameter review — check Disposition Accuracy and Context Passing first."))
        # Weakest param
        _wp_list = []
        for _tier2 in _QA_SCHEMA["tiers"]:
            for _p2 in _tier2["params"]:
                if _p2["col"] in audit_df.columns:
                    _pmax2_vals = [int(o) for o in _p2["options"] if o not in ("NA",) and str(o).lstrip("-").isdigit()]
                    _pmax2 = max(_pmax2_vals) if _pmax2_vals else 2
                    _pv2 = audit_df[_p2["col"]].astype(str).str.strip()
                    _pv2 = _pv2[~_pv2.str.upper().isin(["NA",""])]
                    _pn2 = pd.to_numeric(_pv2, errors="coerce").dropna()
                    if len(_pn2):
                        _wp_list.append((_p2["col"], round(_pn2.mean()/_pmax2*100,1)))
        if _wp_list:
            _wp_list.sort(key=lambda x: x[1])
            _wp = _wp_list[0]
            if _wp[1] < 70:
                _alerts.append(("🔧", "#f59e0b", "#fffbeb", f"Weakest parameter: {_wp[0]} ({_wp[1]}% avg)", f"This parameter is dragging down Bot Score. Prioritise bot tuning/retraining for this area."))

        if _alerts:
            st.markdown('<div class="section-chip">🚦 Action Required</div>', unsafe_allow_html=True)
            _al_c1, _al_c2 = st.columns(2)
            for _ai3, (_icon3, _col3, _bg3, _title3, _detail3) in enumerate(_alerts):
                with (_al_c1 if _ai3 % 2 == 0 else _al_c2):
                    st.markdown(
                        f'<div style="background:{_bg3};border-left:4px solid {_col3};border-radius:8px;'
                        f'padding:11px 14px;margin-bottom:8px;">'
                        f'<div style="font-size:0.78rem;font-weight:700;color:{_col3};margin-bottom:3px;">{_icon3} {_title3}</div>'
                        f'<div style="font-size:0.7rem;color:#444;line-height:1.5;">{_detail3}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

    # ── Campaign breakdown (QA schema only) ──────────────────────────────────
    if _has_qa_schema and "Campaign Name" in audit_df.columns:
        _camp_rows_html = ""
        for _cn, _cgrp in audit_df.groupby("Campaign Name", sort=False):
            if not str(_cn).strip() or str(_cn).strip() == "nan":
                continue
            _cbs = pd.to_numeric(_cgrp["Bot Score"], errors="coerce").dropna()
            if _cbs.empty:
                continue
            _cavg = round(_cbs.mean(), 1)
            _cc   = _qa_status_color(_qa_status(_cavg, False))
            _cpass  = int((_cgrp["Status"].astype(str).str.strip() == "Pass").sum())
            _creview= int((_cgrp["Status"].astype(str).str.strip() == "Needs Review").sum())
            _cfail  = len(_cgrp) - _cpass - _creview
            _camp_rows_html += (
                f'<div style="display:flex;align-items:center;gap:12px;padding:9px 14px;background:#fff;'
                f'border:1px solid rgba(61,130,245,0.08);border-left:3px solid {_cc};'
                f'border-radius:10px;margin-bottom:5px;">'
                f'<div style="flex:1;font-size:0.8rem;font-weight:600;color:#0d1d3a;'
                f'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{_cn}</div>'
                f'<div style="display:flex;gap:5px;">'
                f'<span style="background:#0ebc6e18;border:1px solid #0ebc6e44;border-radius:4px;padding:1px 7px;font-size:0.6rem;font-weight:700;color:#0ebc6e;">{_cpass}P</span>'
                f'<span style="background:#f59e0b18;border:1px solid #f59e0b44;border-radius:4px;padding:1px 7px;font-size:0.6rem;font-weight:700;color:#f59e0b;">{_creview}R</span>'
                f'<span style="background:#dc262618;border:1px solid #dc262644;border-radius:4px;padding:1px 7px;font-size:0.6rem;font-weight:700;color:#dc2626;">{_cfail}F</span>'
                f'</div>'
                f'<div style="width:130px;height:7px;background:#f0f2f5;border-radius:4px;overflow:hidden;">'
                f'<div style="width:{min(_cavg,100)}%;height:100%;background:{_cc};border-radius:4px;"></div></div>'
                f'<div style="width:46px;text-align:right;font-size:0.83rem;font-weight:800;color:{_cc};">{_cavg}%</div>'
                f'<div style="width:56px;text-align:right;font-size:0.65rem;color:#aabbcc;">{len(_cgrp)} audits</div>'
                f'</div>'
            )
        if _camp_rows_html:
            st.markdown('<div class="section-chip">🎯 Score by Campaign</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="margin-bottom:1.2rem;">{_camp_rows_html}</div>', unsafe_allow_html=True)

    # ── Auditor × Campaign cross-matrix ───────────────────────────────────────
    if (_has_qa_schema and "QA" in audit_df.columns and "Campaign Name" in audit_df.columns):
        with st.expander("🔀 QA × Campaign Score Matrix", expanded=False):
            try:
                _mx = audit_df.copy()
                _mx["_bs"] = pd.to_numeric(_mx["Bot Score"], errors="coerce")
                _pivot = _mx.pivot_table(index="QA", columns="Campaign Name",
                                         values="_bs", aggfunc="mean").round(1)
                if not _pivot.empty:
                    st.markdown(
                        '<div style="font-size:0.7rem;color:#5588bb;margin-bottom:10px;">'
                        'Each cell shows the average Bot Score for that auditor × campaign combination. '
                        'Blank = no data.</div>',
                        unsafe_allow_html=True,
                    )
                    # Colour-coded table
                    def _cell_color(v):
                        if pd.isna(v):
                            return "background:#fff;color:#aabbcc;"
                        c = "#0ebc6e" if v >= 80 else "#f59e0b" if v >= 60 else "#dc2626"
                        return f"background:{c}18;color:{c};font-weight:700;"
                    _cells_html = '<table style="width:100%;border-collapse:separate;border-spacing:4px;">'
                    _cells_html += '<tr><th style="text-align:left;font-size:0.65rem;color:#aabbcc;padding:4px 8px;">Auditor</th>'
                    for _cc in _pivot.columns:
                        _cells_html += f'<th style="font-size:0.65rem;color:#5588bb;padding:4px 8px;text-align:center;max-width:100px;overflow:hidden;">{_cc}</th>'
                    _cells_html += '</tr>'
                    for _aud_row in _pivot.index:
                        _cells_html += f'<tr><td style="font-size:0.73rem;font-weight:600;color:#0d1d3a;padding:4px 8px;white-space:nowrap;">{_aud_row}</td>'
                        for _cc in _pivot.columns:
                            _v = _pivot.loc[_aud_row, _cc]
                            _cs = _cell_color(_v)
                            _cells_html += f'<td style="{_cs}border-radius:6px;padding:5px 10px;text-align:center;font-size:0.75rem;">{"—" if pd.isna(_v) else f"{_v}%"}</td>'
                        _cells_html += '</tr>'
                    _cells_html += '</table>'
                    st.markdown(_cells_html, unsafe_allow_html=True)
                    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
            except Exception:
                pass

    # ── Lead Quality Analysis ─────────────────────────────────────────────────
    if _has_qa_schema and "Lead Stage" in audit_df.columns:
        with st.expander("🏷️ Lead Quality Drill-Down", expanded=False):
            try:
                _lc1, _lc2 = st.columns(2)
                with _lc1:
                    st.markdown(
                        '<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.08em;'
                        'text-transform:uppercase;color:#5588bb;margin-bottom:8px;">Lead Stage Distribution</div>',
                        unsafe_allow_html=True,
                    )
                    _ls_vc  = audit_df["Lead Stage"].replace("", None).dropna().value_counts()
                    _ls_order = list(_QA_SCHEMA.get("lead_stage_opts", [])) or _ls_vc.index.tolist()
                    _LS_COLORS = {"Hot": "#dc2626", "Warm": "#f59e0b", "Cold": "#2563EB",
                                  "Not Interested": "#aabbcc", "RNR": "#7c3aed", "": "#edf2fb"}
                    _ls_html = ""
                    for _ls_name in _ls_order:
                        if _ls_name not in _ls_vc.index:
                            continue
                        _lsv  = int(_ls_vc[_ls_name])
                        _lspct = round(_lsv / total * 100, 1)
                        _lsc  = _LS_COLORS.get(_ls_name, "#2563EB")
                        _ls_html += (
                            f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">'
                            f'<div style="width:110px;font-size:0.73rem;color:#0d1d3a;font-weight:600;flex-shrink:0;">{_ls_name}</div>'
                            f'<div style="flex:1;height:16px;background:#f0f2f5;border-radius:3px;overflow:hidden;">'
                            f'<div style="width:{_lspct}%;height:100%;background:{_lsc};border-radius:3px;"></div></div>'
                            f'<div style="width:75px;text-align:right;font-size:0.71rem;color:#5588bb;flex-shrink:0;">'
                            f'{_lsv:,} ({_lspct}%)</div>'
                            f'</div>'
                        )
                    st.markdown(
                        f'<div style="background:#fff;border:1px solid #e4e7ec;'
                        f'border-radius:10px;padding:12px 16px;">{_ls_html}</div>',
                        unsafe_allow_html=True,
                    )
                with _lc2:
                    st.markdown(
                        '<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.08em;'
                        'text-transform:uppercase;color:#5588bb;margin-bottom:8px;">Disposition Accuracy</div>',
                        unsafe_allow_html=True,
                    )
                    _disp_html = ""
                    # Correct Disposition breakdown
                    if "Correct Disposition" in audit_df.columns:
                        _cd_vc = audit_df["Correct Disposition"].replace("", None).dropna().value_counts()
                        _cd_total = _cd_vc.sum()
                        _CD_COLORS = {"Yes": "#0ebc6e", "No": "#dc2626", "NA": "#94a3b8"}
                        for _cdv in ["Yes", "No", "NA"]:
                            if _cdv not in _cd_vc.index: continue
                            _cdn = int(_cd_vc[_cdv])
                            _cdp = round(_cdn / _cd_total * 100, 1) if _cd_total else 0
                            _cdc = _CD_COLORS.get(_cdv, "#2563EB")
                            _disp_html += (
                                f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:7px;">'
                                f'<div style="width:30px;font-size:0.72rem;font-weight:700;color:{_cdc};">{_cdv}</div>'
                                f'<div style="flex:1;height:14px;background:#f0f2f5;border-radius:3px;overflow:hidden;">'
                                f'<div style="width:{_cdp}%;height:100%;background:{_cdc};border-radius:3px;"></div></div>'
                                f'<div style="width:70px;text-align:right;font-size:0.7rem;color:#5588bb;flex-shrink:0;">{_cdn} ({_cdp}%)</div>'
                                f'</div>'
                            )
                    # Wrong disposition → expected breakdown
                    if "Correct Disposition (Expected)" in audit_df.columns:
                        _exp = (audit_df["Correct Disposition (Expected)"]
                                .replace("", None).dropna()
                                .astype(str).str.strip())
                        _exp = _exp[_exp != "nan"]
                        if len(_exp):
                            _exp_vc = _exp.value_counts().head(5)
                            _disp_html += (
                                f'<div style="font-size:0.62rem;font-weight:700;color:#dc2626;'
                                f'letter-spacing:0.08em;text-transform:uppercase;margin:10px 0 6px;">Expected (when Wrong)</div>'
                            )
                            for _ev, _ec in _exp_vc.items():
                                _disp_html += (
                                    f'<div style="display:flex;align-items:center;justify-content:space-between;'
                                    f'padding:4px 0;border-bottom:1px solid rgba(220,38,38,0.08);">'
                                    f'<div style="font-size:0.72rem;color:#0d1d3a;">{_ev}</div>'
                                    f'<div style="font-size:0.72rem;font-weight:700;color:#dc2626;">{_ec}×</div>'
                                    f'</div>'
                                )
                    # Qualified leads
                    _hot  = int((audit_df["Lead Stage"] == "Hot").sum())
                    _warm = int((audit_df["Lead Stage"] == "Warm").sum())
                    _qualif_pct = round((_hot + _warm) / total * 100, 1) if total else 0
                    _disp_html += (
                        f'<div style="margin-top:10px;background:#2563EB18;border:1px solid #2563EB44;'
                        f'border-radius:8px;padding:8px 12px;text-align:center;">'
                        f'<div style="font-size:0.62rem;font-weight:700;color:#2563EB;letter-spacing:0.08em;'
                        f'text-transform:uppercase;margin-bottom:2px;">Qualified Leads (Hot+Warm)</div>'
                        f'<div style="font-size:1.5rem;font-weight:900;color:#2563EB;">{_qualif_pct}%</div>'
                        f'<div style="font-size:0.62rem;color:#5588bb;">{_hot+_warm} of {total}</div>'
                        f'</div>'
                    )
                    st.markdown(
                        f'<div style="background:#fff;border:1px solid #e4e7ec;'
                        f'border-radius:10px;padding:12px 16px;">{_disp_html}</div>',
                        unsafe_allow_html=True,
                    )
                # Lead stage × campaign
                if "Campaign Name" in audit_df.columns:
                    st.markdown(
                        '<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.08em;'
                        'text-transform:uppercase;color:#5588bb;margin:14px 0 8px;">Lead Stage by Campaign</div>',
                        unsafe_allow_html=True,
                    )
                    _lsc_pivot = audit_df.groupby(["Campaign Name", "Lead Stage"]).size().unstack(fill_value=0)
                    if not _lsc_pivot.empty:
                        st.dataframe(_lsc_pivot, use_container_width=True)
            except Exception:
                pass

    # ── Score Trend Over Time ─────────────────────────────────────────────────
    if _has_qa_schema and "Audit Date" in audit_df.columns:
        with st.expander("📈 Score Trend Over Time", expanded=True):
            try:
                _trend_df = audit_df.copy()
                _trend_df["_date_parsed"] = pd.to_datetime(_trend_df["Audit Date"], errors="coerce")
                _trend_df = _trend_df.dropna(subset=["_date_parsed"])
                _trend_df["Bot Score"] = pd.to_numeric(_trend_df["Bot Score"], errors="coerce")
                if len(_trend_df) >= 3:
                    _daily = (
                        _trend_df.groupby(_trend_df["_date_parsed"].dt.date)
                        .agg(Avg_Score=("Bot Score", "mean"), Count=("Bot Score", "count"))
                        .reset_index()
                        .rename(columns={"_date_parsed": "Date"})
                        .sort_values("Date")
                    )
                    _daily["Avg_Score"] = _daily["Avg_Score"].round(1)
                    # Render as SVG sparkline
                    _dates  = _daily["Date"].tolist()
                    _scores = _daily["Avg_Score"].tolist()
                    _n      = len(_scores)
                    if _n >= 2:
                        _W, _H = 700, 120
                        _PAD   = 30
                        _mn, _mx = min(_scores), max(_scores)
                        _rng = max(_mx - _mn, 10)
                        def _sx(i):  return _PAD + i / (_n - 1) * (_W - 2 * _PAD)
                        def _sy(v):  return _PAD + (1 - (v - _mn) / _rng) * (_H - 2 * _PAD)
                        _pts = " ".join(f"{_sx(i):.1f},{_sy(s):.1f}" for i, s in enumerate(_scores))
                        _area_pts = (f"M {_sx(0):.1f},{_H} " +
                                     " ".join(f"L {_sx(i):.1f},{_sy(s):.1f}" for i, s in enumerate(_scores)) +
                                     f" L {_sx(_n-1):.1f},{_H} Z")
                        _trend_svg = (
                            f'<svg width="100%" viewBox="0 0 {_W} {_H}" style="border-radius:8px;" preserveAspectRatio="none">'
                            f'<defs><linearGradient id="tg" x1="0" y1="0" x2="0" y2="1">'
                            f'<stop offset="0%" stop-color="#2563EB" stop-opacity="0.18"/>'
                            f'<stop offset="100%" stop-color="#2563EB" stop-opacity="0.01"/>'
                            f'</linearGradient></defs>'
                            f'<path d="{_area_pts}" fill="url(#tg)"/>'
                            f'<polyline points="{_pts}" fill="none" stroke="#2563EB" stroke-width="2.5" stroke-linejoin="round"/>'
                        )
                        for i, (s, d) in enumerate(zip(_scores, _dates)):
                            _c = "#0ebc6e" if s >= 80 else "#f59e0b" if s >= 60 else "#dc2626"
                            _trend_svg += f'<circle cx="{_sx(i):.1f}" cy="{_sy(s):.1f}" r="4" fill="{_c}" stroke="#fff" stroke-width="1.5"/>'
                        # Date labels (show max 6 evenly)
                        _step = max(1, _n // 6)
                        for i in range(0, _n, _step):
                            _trend_svg += (f'<text x="{_sx(i):.1f}" y="{_H-4}" text-anchor="middle" '
                                           f'font-size="8" fill="#aabbcc" font-family="Inter,sans-serif">'
                                           f'{str(_dates[i])[-5:]}</text>')
                        # Score labels
                        for i, s in enumerate(_scores):
                            if i % max(1, _n // 8) == 0:
                                _trend_svg += (f'<text x="{_sx(i):.1f}" y="{_sy(s):.1f - 8}" text-anchor="middle" '
                                               f'font-size="8.5" fill="#2563EB" font-weight="700" font-family="Inter,sans-serif">{s}%</text>')
                        _trend_svg += '</svg>'
                        # Summary stats beside chart
                        _tr_c1, _tr_c2 = st.columns([4, 1])
                        with _tr_c1:
                            st.markdown(
                                f'<div style="background:#fff;border:1px solid #e4e7ec;border-radius:12px;padding:12px 16px;">'
                                f'{_trend_svg}</div>',
                                unsafe_allow_html=True,
                            )
                        with _tr_c2:
                            _first5  = _scores[:max(1, _n//2)]
                            _last5   = _scores[max(1, _n//2):]
                            _trend_d = round(sum(_last5)/len(_last5) - sum(_first5)/len(_first5), 1) if _first5 and _last5 else 0
                            _tc_     = "#0ebc6e" if _trend_d >= 0 else "#dc2626"
                            _tarr    = "↑" if _trend_d >= 0 else "↓"
                            st.markdown(
                                f'<div style="background:#fff;border:1px solid #e4e7ec;border-radius:12px;padding:16px;height:100%;">'
                                f'<div style="font-size:0.62rem;color:#5588bb;margin-bottom:4px;">Trend</div>'
                                f'<div style="font-size:1.6rem;font-weight:900;color:{_tc_};">{_tarr} {abs(_trend_d)}%</div>'
                                f'<div style="font-size:0.62rem;color:#5588bb;margin-top:2px;">vs first half</div>'
                                f'<div style="margin-top:12px;font-size:0.62rem;color:#5588bb;">Peak</div>'
                                f'<div style="font-size:1.2rem;font-weight:800;color:#0ebc6e;">{max(_scores)}%</div>'
                                f'<div style="margin-top:6px;font-size:0.62rem;color:#5588bb;">Low</div>'
                                f'<div style="font-size:1.2rem;font-weight:800;color:#dc2626;">{min(_scores)}%</div>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )
            except Exception:
                pass

    # ── Custom Parameters Analysis ────────────────────────────────────────────
    _custom_params_in_data = [
        cp for cp in st.session_state.get("sense_custom_audit_params", [])
        if cp["name"] in audit_df.columns
    ]
    if _custom_params_in_data:
        with st.expander("⭐ Custom Parameters Analysis", expanded=True):
            try:
                _cp_cols = st.columns(min(len(_custom_params_in_data), 3))
                for _cpi, _cp in enumerate(_custom_params_in_data):
                    with _cp_cols[_cpi % len(_cp_cols)]:
                        _cpv = audit_df[_cp["name"]].replace("", None).dropna().astype(str).str.strip()
                        _cpv = _cpv[_cpv.str.lower() != "nan"]
                        _yes = int((_cpv.str.lower() == "yes").sum())
                        _no  = int((_cpv.str.lower() == "no").sum())
                        _na  = int((_cpv.str.lower() == "na").sum())
                        _tot = len(_cpv)
                        _yes_pct = round(_yes / _tot * 100, 1) if _tot else 0
                        _no_pct  = round(_no  / _tot * 100, 1) if _tot else 0
                        _cmt_col = f"{_cp['name']} Comment"
                        _cmt_count = int(audit_df[_cmt_col].replace("", None).dropna().astype(str).str.strip().str.len().gt(0).sum()) if _cmt_col in audit_df.columns else 0
                        st.markdown(
                            f'<div style="background:#fff;border:1px solid #e4e7ec;border-radius:12px;padding:14px 16px;margin-bottom:8px;">'
                            f'<div style="font-size:0.68rem;font-weight:700;color:#0ebc6e;letter-spacing:0.06em;text-transform:uppercase;margin-bottom:8px;">⭐ {_cp["name"]}</div>'
                            f'<div style="display:flex;gap:8px;margin-bottom:10px;">'
                            f'<div style="flex:1;background:#ecfdf5;border:1px solid #6ee7b7;border-radius:8px;padding:8px;text-align:center;">'
                            f'<div style="font-size:1.4rem;font-weight:900;color:#0ebc6e;">{_yes}</div>'
                            f'<div style="font-size:0.62rem;color:#059669;font-weight:700;">Yes</div>'
                            f'<div style="font-size:0.62rem;color:#5588bb;">{_yes_pct}%</div>'
                            f'</div>'
                            f'<div style="flex:1;background:#fef2f2;border:1px solid #fca5a5;border-radius:8px;padding:8px;text-align:center;">'
                            f'<div style="font-size:1.4rem;font-weight:900;color:#dc2626;">{_no}</div>'
                            f'<div style="font-size:0.62rem;color:#dc2626;font-weight:700;">No</div>'
                            f'<div style="font-size:0.62rem;color:#5588bb;">{_no_pct}%</div>'
                            f'</div>'
                            f'<div style="flex:1;background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:8px;text-align:center;">'
                            f'<div style="font-size:1.4rem;font-weight:900;color:#94a3b8;">{_na}</div>'
                            f'<div style="font-size:0.62rem;color:#94a3b8;font-weight:700;">NA</div>'
                            f'</div>'
                            f'</div>'
                            f'<div style="height:6px;background:#f0f2f5;border-radius:3px;overflow:hidden;display:flex;">'
                            f'<div style="width:{_yes_pct}%;background:#0ebc6e;"></div>'
                            f'<div style="width:{_no_pct}%;background:#dc2626;"></div>'
                            f'</div>'
                            f'<div style="font-size:0.62rem;color:#5588bb;margin-top:6px;">'
                            f'{_cmt_count} comment{"s" if _cmt_count != 1 else ""} recorded · {_tot} responses</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                        if _cp.get("guide"):
                            st.markdown(
                                f'<div style="font-size:0.65rem;color:#7a99bb;font-style:italic;margin-top:2px;padding:0 4px;">'
                                f'📌 {_cp["guide"]}</div>',
                                unsafe_allow_html=True,
                            )
            except Exception:
                pass

            # ── Remarks Summary ────────────────────────────────────────────
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            st.markdown(
                '<div style="font-size:0.72rem;font-weight:800;color:#0B1F3A;letter-spacing:0.08em;'
                'text-transform:uppercase;margin-bottom:10px;border-bottom:2px solid #E2EAF6;padding-bottom:6px;">'
                '💬 Custom Parameter Remarks</div>',
                unsafe_allow_html=True,
            )

            # Collect per-param comments
            _cp_remark_map = {}
            _all_cp_remarks = []
            for _cp2 in _custom_params_in_data:
                _cmt2_col = f"{_cp2['name']} Comment"
                if _cmt2_col in audit_df.columns:
                    _cmts2 = audit_df[_cmt2_col].replace("", None).dropna().astype(str).str.strip()
                    _cmts2 = _cmts2[_cmts2.str.lower().str.len() > 0]
                    _cmts2 = _cmts2[~_cmts2.str.lower().isin(["nan","none",""])]
                    _cp_remark_map[_cp2["name"]] = _cmts2.tolist()
                    _all_cp_remarks.extend(_cmts2.tolist())

            if not _all_cp_remarks:
                st.markdown(
                    '<div style="font-size:0.72rem;color:#94a3b8;padding:8px 0;">No comments recorded for custom parameters yet.</div>',
                    unsafe_allow_html=True,
                )
            else:
                # Per-param comment pills
                for _pname, _prmks in _cp_remark_map.items():
                    if not _prmks: continue
                    st.markdown(
                        f'<div style="font-size:0.68rem;font-weight:700;color:#0ebc6e;margin-bottom:4px;">⭐ {_pname} — {len(_prmks)} remark{"s" if len(_prmks)!=1 else ""}</div>',
                        unsafe_allow_html=True,
                    )
                    for _rm in _prmks[:5]:
                        st.markdown(
                            f'<div style="background:#f8fffe;border-left:3px solid #6ee7b7;border-radius:0 6px 6px 0;'
                            f'padding:6px 12px;margin-bottom:4px;font-size:0.71rem;color:#374151;line-height:1.5;">{_rm}</div>',
                            unsafe_allow_html=True,
                        )
                    if len(_prmks) > 5:
                        st.markdown(
                            f'<div style="font-size:0.65rem;color:#94a3b8;margin-bottom:8px;">+{len(_prmks)-5} more remarks</div>',
                            unsafe_allow_html=True,
                        )

                # AI summary button
                st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
                _cp_ai_key = "cp_remarks_ai_summary"
                _api_key_cp = st.session_state.get("api_key", "")
                _cp_ai_col1, _cp_ai_col2 = st.columns([3, 1])
                with _cp_ai_col2:
                    if st.button("✨ Generate Detailed Summary", key="cp_remarks_ai_btn", use_container_width=True):
                        if not _api_key_cp:
                            st.warning("Add your Anthropic API key in Settings.")
                        else:
                            _cp_rm_text = "\n".join(
                                f"[{pn}] {rm}"
                                for pn, rms in _cp_remark_map.items()
                                for rm in rms
                            )
                            _total_rm = sum(len(v) for v in _cp_remark_map.values())
                            _cp_prompt = (
                                f"You are a senior QA analytics expert writing a detailed management report. "
                                f"The following are ALL reviewer remarks collected from {_total_rm} QA audit records "
                                f"for client '{_cli_label if '_cli_label' in dir() else 'N/A'}', "
                                f"campaign '{_camp_label if '_camp_label' in dir() else 'N/A'}'. "
                                f"These custom parameters are binary call-action checks (e.g. 'Was call patching done?', 'Was transfer attempted?'). "
                                f"Each remark explains WHY the auditor marked Yes/No/NA.\n\n"
                                f"ALL REMARKS:\n{_cp_rm_text}\n\n"
                                f"Write a comprehensive, detailed summary report. Return ONLY valid JSON (no markdown) with these keys:\n"
                                f'{{"executive_summary": "4-5 sentence executive overview covering overall adherence health, most critical failures, and business impact", '
                                f'"per_param": [{{"name": "exact param name", "total_remarks": 0, "key_finding": "2-3 sentence detailed finding for this param", "common_reasons_failed": ["reason 1", "reason 2"], "common_reasons_passed": ["reason 1"], "pattern": "any pattern observed (time-based, agent-based, campaign-based)"}}], '
                                f'"recurring_themes": ["detailed theme 1 with context", "detailed theme 2", "detailed theme 3"], '
                                f'"agent_behaviour_patterns": "2-3 sentences on patterns in how agents are handling these call actions", '
                                f'"risk_areas": [{{"area": "risk area name", "severity": "high/medium/low", "detail": "detailed explanation"}}], '
                                f'"coaching_recommendations": [{{"title": "recommendation title", "detail": "detailed actionable steps", "priority": "high/medium/low"}}], '
                                f'"positive_highlights": ["specific positive finding 1 with detail", "specific positive finding 2"]}}'
                            )
                            try:
                                import anthropic as _anth2, json as _jcp
                                _ac2 = _anth2.Anthropic(api_key=_api_key_cp)
                                with st.spinner("Generating detailed summary…"):
                                    _cp_msg = _ac2.messages.create(
                                        model="claude-haiku-4-5-20251001",
                                        max_tokens=2000,
                                        messages=[{"role": "user", "content": _cp_prompt}],
                                    )
                                _cp_raw = _cp_msg.content[0].text.strip()
                                if _cp_raw.startswith("```"):
                                    _cp_raw = _cp_raw.split("```")[1]
                                    if _cp_raw.startswith("json"): _cp_raw = _cp_raw[4:]
                                st.session_state[_cp_ai_key] = _jcp.loads(_cp_raw)
                                st.rerun()
                            except Exception as _cpe:
                                st.error(f"AI error: {_cpe}")

                # Show AI summary if available
                _cp_ai = st.session_state.get(_cp_ai_key)
                if _cp_ai:
                    st.markdown(
                        f'<div style="background:#f5f3ff;border:1px solid #ddd6fe;border-radius:12px;padding:20px 22px;margin-top:8px;">'
                        f'<div style="font-size:0.68rem;font-weight:800;letter-spacing:0.1em;text-transform:uppercase;color:#7c3aed;margin-bottom:14px;">✨ Detailed Remarks Summary Report</div>',
                        unsafe_allow_html=True,
                    )

                    # Executive Summary
                    if _cp_ai.get("executive_summary"):
                        st.markdown(
                            f'<div style="background:#ede9fe;border-radius:8px;padding:14px 16px;margin-bottom:16px;">'
                            f'<div style="font-size:0.65rem;font-weight:800;color:#6d28d9;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">📋 Executive Summary</div>'
                            f'<div style="font-size:0.78rem;color:#3b0764;line-height:1.75;">{_cp_ai["executive_summary"]}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

                    # Per-param detailed breakdown
                    if _cp_ai.get("per_param"):
                        st.markdown(
                            '<div style="font-size:0.65rem;font-weight:800;color:#7c3aed;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:8px;">⭐ Per-Parameter Breakdown</div>',
                            unsafe_allow_html=True,
                        )
                        for _ppi in _cp_ai["per_param"]:
                            _fail_r = _ppi.get("common_reasons_failed") or []
                            _pass_r = _ppi.get("common_reasons_passed") or []
                            _fail_html = "".join(f'<li style="margin-bottom:3px;">{r}</li>' for r in _fail_r)
                            _pass_html = "".join(f'<li style="margin-bottom:3px;">{r}</li>' for r in _pass_r)
                            _pattern  = _ppi.get("pattern","")
                            st.markdown(
                                f'<div style="background:#fff;border:1px solid #e4e7ec;border-radius:10px;padding:14px 16px;margin-bottom:10px;">'
                                f'<div style="font-size:0.72rem;font-weight:800;color:#0B1F3A;margin-bottom:6px;">⭐ {_ppi.get("name","")} '
                                f'<span style="font-size:0.62rem;color:#7c3aed;font-weight:600;">({_ppi.get("total_remarks",0)} remarks)</span></div>'
                                f'<div style="font-size:0.74rem;color:#374151;line-height:1.65;margin-bottom:8px;">{_ppi.get("key_finding","")}</div>'
                                f'<div style="display:flex;gap:12px;">'
                                f'<div style="flex:1;">'
                                f'<div style="font-size:0.62rem;font-weight:700;color:#dc2626;margin-bottom:4px;">❌ Why Failed</div>'
                                f'<ul style="margin:0;padding-left:16px;font-size:0.69rem;color:#7f1d1d;line-height:1.6;">{_fail_html or "<li>—</li>"}</ul>'
                                f'</div>'
                                f'<div style="flex:1;">'
                                f'<div style="font-size:0.62rem;font-weight:700;color:#059669;margin-bottom:4px;">✅ Why Passed</div>'
                                f'<ul style="margin:0;padding-left:16px;font-size:0.69rem;color:#065f46;line-height:1.6;">{_pass_html or "<li>—</li>"}</ul>'
                                f'</div>'
                                f'</div>'
                                + (f'<div style="margin-top:8px;font-size:0.67rem;color:#6d28d9;background:#f5f3ff;border-radius:4px;padding:5px 10px;">🔍 Pattern: {_pattern}</div>' if _pattern else "")
                                + f'</div>',
                                unsafe_allow_html=True,
                            )

                    # Recurring themes
                    if _cp_ai.get("recurring_themes"):
                        st.markdown(
                            '<div style="font-size:0.65rem;font-weight:800;color:#7c3aed;letter-spacing:0.1em;text-transform:uppercase;margin:12px 0 6px;">🔁 Recurring Themes</div>',
                            unsafe_allow_html=True,
                        )
                        for _ti, _th in enumerate(_cp_ai["recurring_themes"], 1):
                            st.markdown(
                                f'<div style="background:#faf5ff;border-left:3px solid #a78bfa;border-radius:0 6px 6px 0;padding:8px 12px;margin-bottom:6px;font-size:0.73rem;color:#3b0764;line-height:1.6;">'
                                f'<strong>#{_ti}</strong> {_th}</div>',
                                unsafe_allow_html=True,
                            )

                    # Agent behaviour patterns
                    if _cp_ai.get("agent_behaviour_patterns"):
                        st.markdown(
                            f'<div style="background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:12px 14px;margin:10px 0;">'
                            f'<div style="font-size:0.62rem;font-weight:800;color:#d97706;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:5px;">👤 Agent Behaviour Patterns</div>'
                            f'<div style="font-size:0.74rem;color:#78350f;line-height:1.65;">{_cp_ai["agent_behaviour_patterns"]}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

                    # Risk areas
                    _risk_bg = {"high":"#fff1f2","medium":"#fffbeb","low":"#f0fdf4"}
                    _risk_bc = {"high":"#dc2626","medium":"#d97706","low":"#059669"}
                    if _cp_ai.get("risk_areas"):
                        st.markdown(
                            '<div style="font-size:0.65rem;font-weight:800;color:#dc2626;letter-spacing:0.1em;text-transform:uppercase;margin:12px 0 6px;">⚠️ Risk Areas</div>',
                            unsafe_allow_html=True,
                        )
                        for _ra in _cp_ai["risk_areas"]:
                            _rsev = str(_ra.get("severity","low")).lower()
                            st.markdown(
                                f'<div style="background:{_risk_bg.get(_rsev,"#f0fdf4")};border-left:3px solid {_risk_bc.get(_rsev,"#059669")};'
                                f'border-radius:0 6px 6px 0;padding:8px 12px;margin-bottom:6px;">'
                                f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:3px;">'
                                f'<span style="font-size:0.7rem;font-weight:700;color:{_risk_bc.get(_rsev,"#059669")};">{_ra.get("area","")}</span>'
                                f'<span style="font-size:0.58rem;font-weight:800;text-transform:uppercase;color:#fff;background:{_risk_bc.get(_rsev,"#059669")};padding:1px 7px;border-radius:8px;">{_rsev}</span>'
                                f'</div>'
                                f'<div style="font-size:0.71rem;color:#374151;line-height:1.6;">{_ra.get("detail","")}</div>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )

                    # Coaching recommendations
                    _pri_bc2 = {"high":"#dc2626","medium":"#d97706","low":"#059669"}
                    if _cp_ai.get("coaching_recommendations"):
                        st.markdown(
                            '<div style="font-size:0.65rem;font-weight:800;color:#2563EB;letter-spacing:0.1em;text-transform:uppercase;margin:12px 0 6px;">💡 Coaching Recommendations</div>',
                            unsafe_allow_html=True,
                        )
                        for _cri, _cr in enumerate(_cp_ai["coaching_recommendations"], 1):
                            _cpri = str(_cr.get("priority","medium")).lower()
                            st.markdown(
                                f'<div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;padding:12px 14px;margin-bottom:8px;">'
                                f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:5px;">'
                                f'<span style="background:#2563EB;color:#fff;border-radius:50%;width:20px;height:20px;font-size:0.65rem;font-weight:900;display:inline-flex;align-items:center;justify-content:center;flex-shrink:0;">{_cri}</span>'
                                f'<span style="font-size:0.72rem;font-weight:700;color:#0B1F3A;">{_cr.get("title","")}</span>'
                                f'<span style="font-size:0.58rem;font-weight:800;text-transform:uppercase;color:#fff;background:{_pri_bc2.get(_cpri,"#d97706")};padding:1px 7px;border-radius:8px;margin-left:auto;">{_cpri}</span>'
                                f'</div>'
                                f'<div style="font-size:0.72rem;color:#1e3a5f;line-height:1.65;">{_cr.get("detail","")}</div>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )

                    # Positive highlights
                    if _cp_ai.get("positive_highlights"):
                        st.markdown(
                            '<div style="font-size:0.65rem;font-weight:800;color:#059669;letter-spacing:0.1em;text-transform:uppercase;margin:12px 0 6px;">✅ Positive Highlights</div>',
                            unsafe_allow_html=True,
                        )
                        for _ph in _cp_ai["positive_highlights"]:
                            st.markdown(
                                f'<div style="background:#f0fdf4;border-left:3px solid #059669;border-radius:0 6px 6px 0;'
                                f'padding:8px 12px;margin-bottom:6px;font-size:0.73rem;color:#064e3b;line-height:1.6;">{_ph}</div>',
                                unsafe_allow_html=True,
                            )

                    st.markdown('</div>', unsafe_allow_html=True)
                    if st.button("↺ Regenerate", key="cp_remarks_ai_regen", use_container_width=False):
                        st.session_state.pop(_cp_ai_key, None)
                        st.rerun()

            # ── Call Drop Stage Dashboard ──────────────────────────────────
            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
            st.markdown(
                '<div style="font-size:0.72rem;font-weight:800;color:#0B1F3A;letter-spacing:0.08em;'
                'text-transform:uppercase;margin-bottom:10px;border-bottom:2px solid #E2EAF6;padding-bottom:6px;">'
                '📉 Call Drop Stage Analysis</div>',
                unsafe_allow_html=True,
            )
            # Tier 1 params (critical stage 1 of conversation flow)
            _t1_cols = [p["col"] for t in _QA_SCHEMA["tiers"] if "TIER 1" in t["label"] for p in t["params"]]
            _t2_cols = [p["col"] for t in _QA_SCHEMA["tiers"] if "TIER 2" in t["label"] for p in t["params"]]
            _t3_cols = [p["col"] for t in _QA_SCHEMA["tiers"] if "TIER 3" in t["label"] for p in t["params"]]

            def _tier_fail(df, cols):
                """Rows where at least one param in cols scored 0 (fail)."""
                present = [c for c in cols if c in df.columns]
                if not present: return 0
                mask = df[present].apply(lambda c: pd.to_numeric(c, errors="coerce") == 0).any(axis=1)
                return int(mask.sum())

            _total_calls_cd = len(audit_df)
            _auto_fail_cd   = int((audit_df["Status"].astype(str).str.strip() == "Auto-Fail").sum()) if "Status" in audit_df.columns else 0
            _t1_fail = _tier_fail(audit_df, _t1_cols)
            _t2_fail = _tier_fail(audit_df, _t2_cols)
            _t3_fail = _tier_fail(audit_df, _t3_cols)

            _drop_stages = [
                ("Stage 1 — Critical Flow",   _t1_fail,     "#dc2626", "Tier 1 params (Disposition, Context, Flow Issue)"),
                ("Stage 2 — Quality Issues",  _t2_fail,     "#f59e0b", "Tier 2 params (Repetition, Dead Air, Introduction)"),
                ("Stage 3 — Edge Cases",      _t3_fail,     "#2563EB", "Tier 3 params (Language, Tone, Latency)"),
                ("Auto-Fail — Abrupt Drop",   _auto_fail_cd,"#7f1d1d", "Abrupt Disconnection or Fatal param triggered"),
            ]
            _ds_c1, _ds_c2 = st.columns([2, 1])
            with _ds_c1:
                for _dsl, _dsn, _dsc, _dsd in _drop_stages:
                    _dsp = round(_dsn / _total_calls_cd * 100, 1) if _total_calls_cd else 0
                    st.markdown(
                        f'<div style="margin-bottom:10px;">'
                        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:3px;">'
                        f'<div style="font-size:0.72rem;font-weight:700;color:#0B1F3A;">{_dsl}</div>'
                        f'<div style="font-size:0.72rem;font-weight:900;color:{_dsc};">{_dsn} calls &nbsp;({_dsp}%)</div>'
                        f'</div>'
                        f'<div style="height:8px;background:#f0f2f5;border-radius:4px;overflow:hidden;">'
                        f'<div style="width:{_dsp}%;height:100%;background:{_dsc};border-radius:4px;"></div></div>'
                        f'<div style="font-size:0.62rem;color:#94a3b8;margin-top:2px;">{_dsd}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
            with _ds_c2:
                _worst_stage = max(_drop_stages, key=lambda x: x[1])
                _clean_calls = _total_calls_cd - max(_t1_fail, _t2_fail, _t3_fail, _auto_fail_cd)
                st.markdown(
                    f'<div style="background:#fff;border:1px solid #e4e7ec;border-radius:12px;padding:16px;text-align:center;">'
                    f'<div style="font-size:0.65rem;font-weight:700;color:#94a3b8;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:8px;">Highest Drop Point</div>'
                    f'<div style="font-size:1.1rem;font-weight:900;color:{_worst_stage[2]};line-height:1.2;margin-bottom:4px;">{_worst_stage[0].split("—")[0].strip()}</div>'
                    f'<div style="font-size:1.6rem;font-weight:900;color:{_worst_stage[2]};">{_worst_stage[1]}</div>'
                    f'<div style="font-size:0.65rem;color:#94a3b8;">calls affected</div>'
                    f'<div style="height:1px;background:#f0f2f5;margin:10px 0;"></div>'
                    f'<div style="font-size:0.65rem;font-weight:700;color:#94a3b8;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:4px;">Clean Calls</div>'
                    f'<div style="font-size:1.4rem;font-weight:900;color:#059669;">{max(0,_clean_calls)}</div>'
                    f'<div style="font-size:0.65rem;color:#94a3b8;">no stage failures</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            # ── Per-Call Details Table ─────────────────────────────────────
            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
            st.markdown(
                '<div style="font-size:0.72rem;font-weight:800;color:#0B1F3A;letter-spacing:0.08em;'
                'text-transform:uppercase;margin-bottom:10px;border-bottom:2px solid #E2EAF6;padding-bottom:6px;">'
                '🔎 Per-Call Custom Parameter Details</div>',
                unsafe_allow_html=True,
            )
            # Build per-call rows
            _id_col  = next((c for c in ["Lead Number", "Phone Number", "Lead Link"] if c in audit_df.columns), None)
            _qa_col  = "QA" if "QA" in audit_df.columns else None
            _sc_col  = "Bot Score" if "Bot Score" in audit_df.columns else None
            _st_col  = "Status" if "Status" in audit_df.columns else None
            _dt_col  = next((c for c in audit_df.columns if "audit date" in c.lower() or c.lower() == "date"), None)
            _disp_col = "Disposition" if "Disposition" in audit_df.columns else None

            # Table header
            _cp_names = [cp["name"] for cp in _custom_params_in_data]
            _th_cells = "".join(
                f'<th style="padding:7px 10px;text-align:left;font-size:10px;font-weight:800;color:#0B1F3A;'
                f'white-space:nowrap;background:#F0F4F9;">{h}</th>'
                for h in (
                    (["Date"] if _dt_col else []) +
                    (["Lead / ID"] if _id_col else []) +
                    (["QA"] if _qa_col else []) +
                    (["Score", "Status"] if _sc_col else []) +
                    (["Disposition"] if _disp_col else []) +
                    _cp_names
                )
            )
            _tbl = f'<div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;font-size:12px;"><thead><tr>{_th_cells}</tr></thead><tbody>'

            _status_colors = {"Pass":"#059669","Needs Review":"#d97706","Fail":"#dc2626","Auto-Fail":"#7f1d1d"}
            _yn_bg = {"yes":"#ecfdf5","no":"#fef2f2","na":"#f8fafc"}
            _yn_c  = {"yes":"#059669","no":"#dc2626","na":"#94a3b8"}

            for _ri, (_, _row) in enumerate(audit_df.iterrows()):
                _bg = "#fff" if _ri % 2 == 0 else "#fafafa"
                _cells = ""
                if _dt_col:
                    _cells += f'<td style="padding:6px 10px;color:#475569;white-space:nowrap;">{str(_row.get(_dt_col,"—"))[:10]}</td>'
                if _id_col:
                    _lid = str(_row.get(_id_col,"—")).strip()[:20]
                    _ll  = str(_row.get("Lead Link","")).strip()
                    _lnk = f'<a href="{_ll}" style="color:#2563EB;font-weight:600;">{_lid}</a>' if _ll.startswith("http") else f'<span style="font-weight:600;color:#0B1F3A;">{_lid}</span>'
                    _cells += f'<td style="padding:6px 10px;white-space:nowrap;">{_lnk}</td>'
                if _qa_col:
                    _cells += f'<td style="padding:6px 10px;color:#475569;">{str(_row.get(_qa_col,"—")).strip()[:16]}</td>'
                if _sc_col:
                    _bs_v = pd.to_numeric(_row.get(_sc_col, None), errors="coerce")
                    _bs_c = "#059669" if (_bs_v or 0) >= 80 else "#d97706" if (_bs_v or 0) >= 60 else "#dc2626"
                    _cells += f'<td style="padding:6px 10px;font-weight:800;color:{_bs_c};text-align:center;">{int(_bs_v) if pd.notna(_bs_v) else "—"}%</td>'
                    _st_v = str(_row.get(_st_col,"—")).strip()
                    _st_c = _status_colors.get(_st_v, "#475569")
                    _cells += f'<td style="padding:6px 10px;text-align:center;"><span style="background:{_st_c}20;color:{_st_c};font-size:10px;font-weight:700;padding:2px 7px;border-radius:8px;">{_st_v}</span></td>'
                if _disp_col:
                    _cells += f'<td style="padding:6px 10px;color:#475569;">{str(_row.get(_disp_col,"—")).strip()[:18]}</td>'
                for _cpn in _cp_names:
                    _cpval = str(_row.get(_cpn, "—")).strip().lower()
                    _cpcmt = str(_row.get(f"{_cpn} Comment", "")).strip()
                    if _cpcmt.lower() in ("nan", "none", ""): _cpcmt = ""
                    _cbg   = _yn_bg.get(_cpval, "#f8fafc")
                    _ccc   = _yn_c.get(_cpval, "#475569")
                    _val_html = f'<span style="color:{_ccc};font-weight:800;font-size:11px;">{_cpval.upper() if _cpval in ("yes","no","na") else _cpval}</span>'
                    _cmt_html = (f'<div style="font-size:10px;color:#7c3aed;font-style:italic;margin-top:3px;'
                                 f'line-height:1.4;text-align:left;white-space:normal;">{_cpcmt}</div>') if _cpcmt else ""
                    _cells += (f'<td style="padding:6px 10px;background:{_cbg};vertical-align:top;">'
                               f'{_val_html}{_cmt_html}</td>')
                _tbl += f'<tr style="border-bottom:1px solid #F0F4F9;background:{_bg};">{_cells}</tr>'

            _tbl += '</tbody></table></div>'
            st.markdown(_tbl, unsafe_allow_html=True)
            st.markdown(
                f'<div style="font-size:0.65rem;color:#94a3b8;margin-top:6px;">Purple italic = remark text · {len(audit_df)} calls shown</div>',
                unsafe_allow_html=True,
            )

    # ── Top-5 Weakest Parameters (QA schema only) ─────────────────────────────
    if _has_qa_schema and scored_cols:
        with st.expander("🔍 Parameter Weakness Analysis", expanded=False):
            try:
                _param_fail_rates = []
                for _pcol in scored_cols:
                    _bcfg = _builtin_cfg(_pcol)
                    _opts  = (legend_map.get(_pcol) or _match_legend(_pcol, legend_map) or [])
                    _ns    = _score_to_numeric(audit_df[_pcol].replace("", None), _opts,
                                               inverted=(_bcfg["inverted"] if _bcfg else False))
                    if _ns is not None:
                        _valid = _ns.dropna()
                        if len(_valid):
                            _mean_s  = round(_valid.mean() * 100, 1)
                            _fail_n  = int((_valid < 0.5).sum())
                            _fail_p  = round(_fail_n / len(_valid) * 100, 1)
                            _tier_l  = "—"
                            for _t in _QA_SCHEMA["tiers"]:
                                if any(_p["col"] == _pcol for _p in _t["params"]):
                                    _tier_l = _t["label"]
                                    break
                            _param_fail_rates.append({"param": _pcol, "avg": _mean_s,
                                                      "fail_pct": _fail_p, "tier": _tier_l,
                                                      "color": _bcfg["color"] if _bcfg else "#2563EB"})
                _param_fail_rates.sort(key=lambda x: x["fail_pct"], reverse=True)
                if _param_fail_rates:
                    st.markdown(
                        '<div style="font-size:0.7rem;color:#5588bb;margin-bottom:10px;">'
                        'Parameters ranked by failure rate — highest-impact coaching targets appear first.</div>',
                        unsafe_allow_html=True,
                    )
                    for _pfr in _param_fail_rates[:8]:
                        _pfc = "#dc2626" if _pfr["fail_pct"] > 30 else "#f59e0b" if _pfr["fail_pct"] > 15 else "#0ebc6e"
                        st.markdown(
                            f'<div style="display:flex;align-items:center;gap:10px;padding:7px 12px;'
                            f'background:#fff;border:1px solid rgba(61,130,245,0.08);border-left:3px solid {_pfc};'
                            f'border-radius:8px;margin-bottom:5px;">'
                            f'<div style="flex:1;font-size:0.73rem;font-weight:600;color:#0d1d3a;">{_pfr["param"]}</div>'
                            f'<div style="font-size:0.65rem;color:#aabbcc;width:90px;text-align:center;">{_pfr["tier"]}</div>'
                            f'<div style="width:140px;height:9px;background:#f0f2f5;border-radius:3px;overflow:hidden;">'
                            f'<div style="width:{min(_pfr["fail_pct"],100)}%;height:100%;background:{_pfc};border-radius:3px;"></div></div>'
                            f'<div style="width:55px;text-align:right;font-size:0.73rem;font-weight:700;color:{_pfc};">{_pfr["fail_pct"]}%</div>'
                            f'<div style="width:60px;text-align:right;font-size:0.65rem;color:#5588bb;">avg {_pfr["avg"]}%</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
            except Exception:
                pass

    # ── All Parameter Performance ─────────────────────────────────────────────
    st.markdown('<div class="section-chip">📊 All Parameter Performance</div>', unsafe_allow_html=True)
    _app_tiers = _QA_SCHEMA.get("tiers", []) if _has_qa_schema else []
    _app_tier_cols_done = set()
    _app_tier_cols_list = st.columns(max(len(_app_tiers), 1)) if _app_tiers else [st]

    for _app_ti, _app_tier in enumerate(_app_tiers):
        with _app_tier_cols_list[_app_ti]:
            _ap_color = _app_tier["color"]
            _ap_rows_html = ""
            _ap_has = False
            for _app_p in _app_tier["params"]:
                _app_col = _app_p["col"]
                _app_tier_cols_done.add(_app_col)
                if _app_col not in audit_df.columns:
                    continue
                _pmx_vals = [int(o) for o in _app_p.get("options", ["0","1","2"]) if str(o).lstrip("-").isdigit()]
                _pmx = max(_pmx_vals) if _pmx_vals else 2
                _pv_num = pd.to_numeric(
                    audit_df[_app_col].astype(str).str.strip().replace({"NA":"","nan":"","Fatal":"","Yes":"1","No":"0"}),
                    errors="coerce",
                ).dropna()
                _avg_pct = round(_pv_num.mean() / _pmx * 100, 1) if len(_pv_num) else None
                if _avg_pct is None:
                    continue
                _ap_has = True
                _bclr = "#059669" if _avg_pct >= 80 else "#d97706" if _avg_pct >= 60 else "#dc2626"
                _icon = "✅" if _avg_pct >= 80 else "⚠️" if _avg_pct >= 60 else "🔴"
                _ap_rows_html += (
                    f'<div style="margin-bottom:8px;">'
                    f'<div style="display:flex;justify-content:space-between;margin-bottom:3px;">'
                    f'<div style="font-size:0.67rem;font-weight:600;color:#0B1F3A;'
                    f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:150px;">{_icon} {_app_col}</div>'
                    f'<div style="font-size:0.67rem;font-weight:800;color:{_bclr};flex-shrink:0;margin-left:4px;">{_avg_pct}%</div>'
                    f'</div>'
                    f'<div style="height:8px;background:#F1F5F9;border-radius:4px;overflow:hidden;">'
                    f'<div style="width:{_avg_pct}%;height:100%;background:linear-gradient(90deg,{_ap_color},{_bclr});border-radius:4px;"></div>'
                    f'</div></div>'
                )
            if _ap_has:
                st.markdown(
                    f'<div style="background:#fff;border:1px solid #E2EAF6;border-top:3px solid {_ap_color};'
                    f'border-radius:10px;padding:14px 16px;margin-bottom:10px;">'
                    f'<div style="font-size:0.61rem;font-weight:800;color:{_ap_color};letter-spacing:0.1em;'
                    f'text-transform:uppercase;margin-bottom:12px;">{_app_tier["label"]}</div>'
                    f'{_ap_rows_html}</div>',
                    unsafe_allow_html=True,
                )

    # Custom params performance (scored_cols not already in QA tiers)
    _custom_perf_cols = [c for c in scored_cols if c not in _app_tier_cols_done]
    if _custom_perf_cols:
        _cp_rows_html = ""
        for _cpc in _custom_perf_cols:
            if _cpc not in audit_df.columns:
                continue
            _bcfg2 = _builtin_cfg(_cpc)
            _opts2 = legend_map.get(_cpc) or _match_legend(_cpc, legend_map) or []
            _ns2 = _score_to_numeric(audit_df[_cpc], _opts2, inverted=_bcfg2.get("inverted", False) if _bcfg2 else False)
            _avg2 = round((_ns2.mean() if _ns2 is not None and _ns2.notna().sum() > 0 else None) * 100, 1) if (_ns2 is not None and _ns2.notna().sum() > 0) else None
            if _avg2 is None:
                continue
            _bclr2 = "#059669" if _avg2 >= 80 else "#d97706" if _avg2 >= 60 else "#dc2626"
            _icon2 = "✅" if _avg2 >= 80 else "⚠️" if _avg2 >= 60 else "🔴"
            _cp_rows_html += (
                f'<div style="margin-bottom:8px;">'
                f'<div style="display:flex;justify-content:space-between;margin-bottom:3px;">'
                f'<div style="font-size:0.67rem;font-weight:600;color:#0B1F3A;'
                f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:200px;">{_icon2} {_cpc}</div>'
                f'<div style="font-size:0.67rem;font-weight:800;color:{_bclr2};flex-shrink:0;margin-left:4px;">{_avg2}%</div>'
                f'</div>'
                f'<div style="height:8px;background:#F1F5F9;border-radius:4px;overflow:hidden;">'
                f'<div style="width:{_avg2}%;height:100%;background:linear-gradient(90deg,#2563EB,{_bclr2});border-radius:4px;"></div>'
                f'</div></div>'
            )
        if _cp_rows_html:
            st.markdown(
                f'<div style="background:#fff;border:1px solid #E2EAF6;border-top:3px solid #2563EB;'
                f'border-radius:10px;padding:14px 16px;margin-bottom:10px;">'
                f'<div style="font-size:0.61rem;font-weight:800;color:#2563EB;letter-spacing:0.1em;'
                f'text-transform:uppercase;margin-bottom:12px;">Custom / Other Parameters</div>'
                f'{_cp_rows_html}</div>',
                unsafe_allow_html=True,
            )

    # ── Bot-wise Score leaderboard ────────────────────────────────────────────
    _bot_col = "Bot Name" if "Bot Name" in audit_df.columns else group_col
    if _bot_col and (scored_cols or _has_qa_schema):
        st.markdown(f'<div class="section-chip">🤖 Bot-wise Score</div>', unsafe_allow_html=True)
        _grp_rows = []
        for agent, grp in audit_df.groupby(_bot_col, sort=False):
            _row = {"Agent": str(agent), "Audits": len(grp)}
            if _has_qa_schema:
                _bs_grp = pd.to_numeric(grp.get("Bot Score", pd.Series(dtype=float)), errors="coerce").dropna()
                _ws = _bs_grp.mean() / 100.0 if len(_bs_grp) else None
                _st  = grp.get("Status", pd.Series(dtype=str)).astype(str).str.strip()
                _row["Pass"]         = int((_st == "Pass").sum())
                _row["Needs Review"] = int((_st == "Needs Review").sum())
                _row["Fail"]         = int((_st == "Fail").sum())
                _row["Fatal"]        = int((_st == "Auto-Fail").sum())
            else:
                _wsc, _wts = [], []
                for c in scored_cols:
                    opts  = legend_map.get(c) or _match_legend(c, legend_map) or []
                    _bcfg = _builtin_cfg(c)
                    _inv  = _bcfg["inverted"] if _bcfg else False
                    _w    = _custom_weights.get(c, _DEFAULT_PARAM_WEIGHT)
                    _ns   = _score_to_numeric(grp[c], opts, inverted=_inv)
                    if _ns is not None and _ns.notna().sum() > 0:
                        _m = _ns.mean()
                        _row[c] = f"{round(_m*100,1)}%"
                        _wsc.append(_m * _w); _wts.append(_w)
                    else:
                        _vc = grp[c].replace("", None).dropna().value_counts()
                        _row[c] = _vc.index[0] if len(_vc) else "—"
                _ws = sum(_wsc) / sum(_wts) if _wts else None
                _row["Pass"] = _row["Needs Review"] = _row["Fail"] = _row["Fatal"] = 0
            _row["_score_raw"] = round(_ws * 100, 1) if _ws is not None else None
            _row["Score"]      = f"{_row['_score_raw']}%" if _row["_score_raw"] is not None else "—"
            _row["Completion"] = f"{round(grp[scored_cols].replace('',None).notna().all(axis=1).mean()*100,1)}%" if scored_cols else "100%"
            _grp_rows.append(_row)

        if _grp_rows:
            _ranked = sorted(
                [r for r in _grp_rows if r.get("_score_raw") is not None],
                key=lambda r: r["_score_raw"], reverse=True,
            )
            _rank_html = ""
            for _ri, _ar in enumerate(_ranked[:12]):
                _sc    = _ar["_score_raw"]
                _gc    = _qa_status_color(_qa_status(_sc, False))
                _bg    = "rgba(14,188,110,0.03)" if _ri == 0 else "#fff"
                _bdr   = "#0ebc6e44" if _ri == 0 else "rgba(61,130,245,0.08)"
                _medal = ["🥇","🥈","🥉"][_ri] if _ri < 3 else f'<span style="font-size:0.72rem;color:#aabbcc;">#{_ri+1}</span>'
                _p  = _ar.get("Pass", 0)
                _rv = _ar.get("Needs Review", 0)
                _fl = _ar.get("Fail", 0) + _ar.get("Fatal", 0)
                _rank_html += (
                    f'<div style="display:flex;align-items:center;gap:10px;padding:10px 14px;'
                    f'background:{_bg};border:1px solid {_bdr};border-radius:11px;margin-bottom:6px;">'
                    f'<div style="width:26px;text-align:center;flex-shrink:0;font-size:1rem;">{_medal}</div>'
                    f'<div style="flex:1;min-width:0;">'
                    f'<div style="font-size:0.84rem;font-weight:700;color:#0d1d3a;'
                    f'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{_ar["Agent"]}</div>'
                    f'<div style="display:flex;gap:5px;margin-top:3px;">'
                    f'<span style="background:#0ebc6e18;border:1px solid #0ebc6e55;border-radius:4px;'
                    f'padding:1px 7px;font-size:0.6rem;font-weight:700;color:#0ebc6e;">{_p} Pass</span>'
                    f'<span style="background:#f59e0b18;border:1px solid #f59e0b55;border-radius:4px;'
                    f'padding:1px 7px;font-size:0.6rem;font-weight:700;color:#f59e0b;">{_rv} Review</span>'
                    f'<span style="background:#dc262618;border:1px solid #dc262655;border-radius:4px;'
                    f'padding:1px 7px;font-size:0.6rem;font-weight:700;color:#dc2626;">{_fl} Fail</span>'
                    f'</div>'
                    f'</div>'
                    f'<div style="width:150px;height:9px;background:#f0f2f5;border-radius:5px;overflow:hidden;flex-shrink:0;">'
                    f'<div style="width:{min(_sc,100)}%;height:100%;background:{_gc};border-radius:5px;"></div></div>'
                    f'<div style="width:50px;text-align:right;font-size:0.88rem;font-weight:900;color:{_gc};flex-shrink:0;">{_sc}%</div>'
                    f'<div style="width:52px;text-align:right;font-size:0.65rem;color:#aabbcc;flex-shrink:0;">{_ar["Audits"]} audits</div>'
                    f'</div>'
                )
            st.markdown(f'<div style="margin-bottom:1.2rem;">{_rank_html}</div>', unsafe_allow_html=True)

            # Bar chart
            _chart_df = pd.DataFrame(
                {"Score (%)": [r["_score_raw"] for r in _ranked]},
                index=[r["Agent"] for r in _ranked],
            )
            st.bar_chart(_chart_df, use_container_width=True)

            # Full parameter table (collapsible)
            with st.expander("📊 Full Parameter Breakdown by Bot", expanded=False):
                _tbl = [{k: v for k, v in r.items() if k != "_score_raw"} for r in _grp_rows]
                st.dataframe(pd.DataFrame(_tbl), use_container_width=True, hide_index=True)

    # ── QA Score Trends ───────────────────────────────────────────────────────
    _trend_scores = (
        pd.to_numeric(audit_df["Bot Score"], errors="coerce")
        if _has_qa_schema and "Bot Score" in audit_df.columns
        else (_row_scores * 100 if _row_scores is not None else None)
    )
    if date_col and _trend_scores is not None:
        st.markdown(f'<div class="section-chip">📅 QA Score Trends — {date_col}</div>', unsafe_allow_html=True)
        try:
            _td = audit_df[[date_col]].copy()
            _td["score"] = _trend_scores.values
            if _bot_col and _bot_col in audit_df.columns:
                _td["group"] = audit_df[_bot_col].values
            _td[date_col] = pd.to_datetime(_td[date_col], errors="coerce")
            _td = _td.dropna(subset=[date_col, "score"]).sort_values(date_col)

            _tc1, _tc2 = st.columns([4, 1])
            with _tc2:
                _period = st.selectbox("Period", ["Daily", "Weekly", "Monthly"],
                                       index=1, key="sense_trend_period")
            _freq = {"Daily": "D", "Weekly": "W", "Monthly": "M"}[_period]
            try:
                _agg = (_td.set_index(date_col)[["score"]]
                        .resample(_freq).mean().dropna().round(1)
                        .rename(columns={"score": "Avg Score (%)"}))
            except Exception:
                _agg = pd.DataFrame()
            with _tc1:
                if not _agg.empty:
                    st.line_chart(_agg, use_container_width=True)

            if _bot_col and "group" in _td.columns:
                with st.expander(f"📊 Score Trend by {_bot_col}", expanded=False):
                    try:
                        _apt = _td.pivot_table(
                            index=pd.Grouper(key=date_col, freq=_freq),
                            columns="group", values="score", aggfunc="mean",
                        ).round(1)
                        if not _apt.empty:
                            st.line_chart(_apt, use_container_width=True)
                    except Exception:
                        pass
        except Exception:
            pass

    # ── Incomplete rows ────────────────────────────────────────────────────────
    _incomplete = audit_df[~audit_df[scored_cols].replace("", None).notna().all(axis=1)] if scored_cols else pd.DataFrame()
    if not _incomplete.empty:
        with st.expander(f"⚠️ {len(_incomplete):,} rows not fully scored", expanded=False):
            st.dataframe(_incomplete, use_container_width=True, height=300)
            st.download_button(
                "⬇ Download incomplete rows",
                data=_incomplete.to_csv(index=False).encode("utf-8"),
                file_name="incomplete_rows.csv", mime="text/csv",
                key="sense_dl_incomplete",
            )

    # ── Custom Parameters ──────────────────────────────────────────────────────
    st.markdown(
        '<hr style="border:none;border-top:1px solid rgba(37,99,235,0.12);margin:2rem 0 1.4rem;">',
        unsafe_allow_html=True,
    )
    _render_param_manager(key_sfx="_sc")


def _render_sense_sheet(df, sheet_name, fname, sheets=None):
    """Renders a single sheet. Audit sheets get an editable data_editor with score dropdowns."""
    _safe     = sheet_name.replace(" ", "_").lower()
    _is_audit = any(k in _safe for k in ("audit", "qa", "review", "score", "evaluat"))

    if _is_audit:
        # ── Parse legend + merge built-in params FIRST (needed for KPI strip) ──
        legend_map = {}
        if sheets:
            for k, v in sheets.items():
                if "legend" in k.lower():
                    legend_map = _parse_legend(v)
                    break
        legend_map = _merge_builtin_params(legend_map)

        # ── Load or init editable copy (inject missing built-in cols) ────────
        edit_key = f"sense_audit_edits_{_safe}"
        if edit_key not in st.session_state:
            _init = df.copy()
            for param in _SENSE_BUILTIN_PARAMS:
                if not any(param.lower() in str(c).lower() or str(c).lower() in param.lower()
                           for c in _init.columns):
                    _init[param] = ""
            for col in _init.columns:
                opts = _match_legend(col, legend_map)
                if opts:
                    _init[col] = _init[col].astype(str).str.strip().replace("nan", "")
            st.session_state[edit_key] = _init

        working_df = st.session_state[edit_key]

        # ── Build column config (scored cols now known before KPI strip) ──────
        col_config  = {}
        scored_cols = []
        for col in working_df.columns:
            opts = _match_legend(col, legend_map)
            if opts:
                scored_cols.append(col)
                _bcfg = _builtin_cfg(col)
                _lbl  = f"{_bcfg['icon']} {col}" if _bcfg else str(col)
                col_config[col] = st.column_config.SelectboxColumn(
                    label=_lbl,
                    options=[""] + opts,
                    required=False,
                    width="medium",
                )

        # ── Scoring summary for KPI strip ──────────────────────────────────
        _scored_mask  = working_df[scored_cols].replace("", None).notna().all(axis=1) if scored_cols else pd.Series([False]*len(working_df))
        _scored_rows  = int(_scored_mask.sum())
        _completion   = round(_scored_rows / len(working_df) * 100, 1) if len(working_df) else 0
        null_pct      = round(working_df.isnull().sum().sum() / working_df.size * 100, 1) if working_df.size else 0
    else:
        scored_cols  = []
        _scored_rows = 0
        _completion  = 0.0
        null_pct     = round(df.isnull().sum().sum() / df.size * 100, 1) if df.size else 0

    # ── KPI strip (accurate for both audit and non-audit) ────────────────────
    _display_df = working_df if _is_audit else df
    st.markdown(f"""<div class="stats-grid" style="grid-template-columns:repeat(4,1fr);margin-bottom:1rem;">
        <div class="stat-card" style="border-top:2px solid #2563EB;">
            <div style="color:#2a5080;font-size:0.6rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:4px;">Rows</div>
            <div style="color:#2563EB;font-size:1.5rem;font-weight:800;">{len(_display_df):,}</div>
        </div>
        <div class="stat-card" style="border-top:2px solid #2563EB;">
            <div style="color:#2a5080;font-size:0.6rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:4px;">Total Columns</div>
            <div style="color:#2563EB;font-size:1.5rem;font-weight:800;">{len(_display_df.columns)}</div>
        </div>
        <div class="stat-card" style="border-top:2px solid #7c3aed;">
            <div style="color:#2a5080;font-size:0.6rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:4px;">{"Scored Params" if _is_audit else "Numeric Cols"}</div>
            <div style="color:#7c3aed;font-size:1.5rem;font-weight:800;">{len(scored_cols) if _is_audit else len(_display_df.select_dtypes(include="number").columns)}</div>
            {f'<div style="font-size:0.65rem;color:#5588bb;margin-top:2px;">{_completion}% rows complete</div>' if _is_audit else ""}
        </div>
        <div class="stat-card" style="border-top:2px solid {'#dc2626' if null_pct > 5 else '#0ebc6e'};">
            <div style="color:#2a5080;font-size:0.6rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:4px;">Missing Values</div>
            <div style="color:{'#dc2626' if null_pct > 5 else '#0ebc6e'};font-size:1.5rem;font-weight:800;">{null_pct}%</div>
        </div>
    </div>""", unsafe_allow_html=True)

    if _is_audit:
        # ── Legend reference ──────────────────────────────────────────────────
        with st.expander("📖 Score Legend — all parameters & valid values", expanded=False):
            _rows_html = ""
            for param, opts in legend_map.items():
                _bcfg = _builtin_cfg(param)
                _tag  = f'<span style="background:rgba(37,99,235,0.1);border:1px solid rgba(37,99,235,0.3);border-radius:4px;padding:1px 6px;font-size:0.6rem;color:#2563EB;margin-left:6px;">🧠 Intelligence</span>' if _bcfg else ""
                _desc = f'<div style="font-size:0.65rem;color:#7a99bb;margin-top:2px;">{_bcfg["description"]}</div>' if _bcfg else ""
                _chips = "".join(
                    f'<span style="background:rgba(61,130,245,0.08);border:1px solid rgba(61,130,245,0.2);'
                    f'border-radius:6px;padding:2px 9px;font-size:0.7rem;color:#2563EB;">{o}</span>'
                    for o in opts
                )
                _rows_html += (
                    f'<div style="padding:8px 0;border-bottom:1px solid rgba(61,130,245,0.07);">'
                    f'<div style="display:flex;align-items:center;gap:4px;margin-bottom:5px;">'
                    f'<span style="font-size:0.76rem;font-weight:700;color:#0d1d3a;">{param}</span>{_tag}</div>'
                    f'{_desc}'
                    f'<div style="display:flex;flex-wrap:wrap;gap:5px;margin-top:5px;">{_chips}</div>'
                    f'</div>'
                )
            st.markdown(_rows_html, unsafe_allow_html=True)

        if scored_cols and not col_config:
            st.info("No audit sheet columns matched legend parameters. All columns are freely editable.")

        # ── Search / filter ───────────────────────────────────────────────────
        search = st.text_input("🔍 Search rows", key=f"sense_search_{_safe}",
                               placeholder="Filter across all columns…")
        _display_df = working_df.copy()
        if search:
            mask = _display_df.astype(str).apply(
                lambda c: c.str.contains(search, case=False, na=False)).any(axis=1)
            _display_df = _display_df[mask]

        st.markdown(
            f'<div style="font-size:0.74rem;color:#5588bb;margin-bottom:4px;">'
            f'{len(_display_df):,} of {len(working_df):,} rows &nbsp;·&nbsp; '
            f'<span style="color:#7c3aed;font-weight:600;">{len(scored_cols)} scored column{"s" if len(scored_cols)!=1 else ""}</span>'
            f' with dropdown</div>',
            unsafe_allow_html=True,
        )

        # ── Editable table ────────────────────────────────────────────────────
        edited = st.data_editor(
            _display_df,
            column_config=col_config,
            use_container_width=True,
            height=520,
            num_rows="fixed",
            key=f"sense_editor_{_safe}",
        )

        # Merge edits back into full working_df (search may have filtered rows)
        if search:
            working_df.loc[_display_df.index] = edited.values
        else:
            working_df = edited
        st.session_state[edit_key] = working_df
        # Persist scored edits so they survive hot-reloads
        _sense_save(st.session_state.get("sense_sheets", {}),
                    st.session_state.get("sense_filename", "data"))

        # ── Actions row ───────────────────────────────────────────────────────
        dl_col, reset_col = st.columns([4, 1])
        with dl_col:
            st.download_button(
                label="⬇ Download Scored Audit Sheet",
                data=working_df.to_csv(index=False).encode("utf-8"),
                file_name=f"{fname.rsplit('.',1)[0]}_scored_audit.csv",
                mime="text/csv",
                key=f"sense_dl_{_safe}",
            )
        with reset_col:
            _protected = _is_protected_sheet(sheet_name)
            if _protected:
                st.markdown(
                    '<div style="text-align:center;font-size:0.7rem;color:#2563EB;padding:6px 0;'
                    'border:1px solid rgba(37,99,235,0.25);border-radius:6px;">🔒 Protected</div>',
                    unsafe_allow_html=True,
                )
            else:
                if st.button("↺ Reset scores", key=f"sense_reset_{_safe}", use_container_width=True):
                    st.session_state.pop(edit_key, None)
                    st.rerun()

    else:
        # ── Non-audit sheet: read-only searchable table ───────────────────────
        search = st.text_input("🔍 Search rows", key=f"sense_search_{_safe}",
                               placeholder="Filter across all columns…")
        _df = df.copy()
        if search:
            mask = _df.astype(str).apply(
                lambda c: c.str.contains(search, case=False, na=False)).any(axis=1)
            _df = _df[mask]

        st.markdown(
            f'<div style="font-size:0.74rem;color:#5588bb;margin-bottom:4px;">'
            f'{len(_df):,} of {len(df):,} rows shown</div>',
            unsafe_allow_html=True,
        )
        st.dataframe(_df, use_container_width=True, height=480)

        st.download_button(
            label=f"⬇ Download — {sheet_name}",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name=f"{fname.rsplit('.',1)[0]}_{_safe}.csv",
            mime="text/csv",
            key=f"sense_dl_{_safe}",
        )


def _render_sense_insights(df, fname, sheets=None, legend_map=None):
    """Comprehensive Insights Dashboard — rule-based analytics + AI deep-dive."""
    legend_map = _merge_builtin_params(legend_map or {})
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Build audit_df — always seeds from form log / seed records ────────────
    _form_log_ins = st.session_state.get("sense_audit_log")
    if _form_log_ins is None:
        _form_log_ins = _audit_log_load()
        if _form_log_ins:
            st.session_state["sense_audit_log"] = _form_log_ins

    _audit_df_ins = None
    _all_sheets   = sheets or {}
    _AUDIT_NAME_KW_I = ("audit", "qa", "review", "score")
    _AUDIT_COL_KW_I  = {"Bot Score", "Status", "QA", "Campaign Name"}
    for _sk, _sv in _all_sheets.items():
        if any(kw in _sk.lower() for kw in _AUDIT_NAME_KW_I):
            _audit_df_ins = _sv.copy()
            break
    if _audit_df_ins is None:
        # Fallback: pick sheet whose columns best match known audit columns
        _bi_k, _bi_v, _bi_sc = None, None, 0
        for _sk, _sv in _all_sheets.items():
            if hasattr(_sv, "columns"):
                _s = len(_AUDIT_COL_KW_I & set(str(c).strip() for c in _sv.columns))
                if _s > _bi_sc:
                    _bi_sc, _bi_k, _bi_v = _s, _sk, _sv
        if _bi_k and _bi_sc > 0:
            _audit_df_ins = _bi_v.copy()

    if _form_log_ins:
        _log_df_ins = pd.DataFrame([{k: v for k, v in r.items() if k != "_row_id"} for r in _form_log_ins])
        if _audit_df_ins is not None:
            _audit_df_ins = pd.concat([_audit_df_ins,
                                       _log_df_ins.reindex(columns=_audit_df_ins.columns, fill_value="")],
                                      ignore_index=True)
        else:
            _audit_df_ins = _log_df_ins

    # Use audit_df as AI sheet if no other sheets uploaded
    if not _all_sheets and _audit_df_ins is not None:
        _all_sheets = {"Audit": _audit_df_ins}
    elif not _all_sheets:
        _all_sheets = {"Data": df} if df is not None and not (hasattr(df, "empty") and df.empty) else {}

    _has_qa_ins = (_audit_df_ins is not None and
                   "Bot Score" in (_audit_df_ins.columns if _audit_df_ins is not None else []) and
                   "Status"    in (_audit_df_ins.columns if _audit_df_ins is not None else []))

    # ── TABS ──────────────────────────────────────────────────────────────────
    _itab_labels = ["📊 Overview", "🏆 Performance", "📈 Trends", "🔬 Parameters", "📋 Reports"]
    _i1, _i2, _i3, _i4, _i5 = st.tabs(_itab_labels)

    # ══════════════════════════════════════════════════════════════════════════
    # Tab 1 — Overview
    # ══════════════════════════════════════════════════════════════════════════
    with _i1:
        if not _has_qa_ins:
            st.info("No QA schema data found. Submit audits via the ✍️ New Audit tab first.")
        else:
            if not sheets:
                st.markdown(
                    '<div style="background:rgba(61,130,245,0.08);border:1px solid rgba(61,130,245,0.2);'
                    'border-radius:8px;padding:9px 16px;margin-bottom:12px;font-size:0.73rem;color:#2563EB;">'
                    '📊 <strong>Demo data</strong> — showing seed audits. Upload a file or submit audits via ✍️ New Audit to see your own data.</div>',
                    unsafe_allow_html=True,
                )
            # ── Client / Campaign / Bot Name filter bar ──────────────────────
            _ins_fc1, _ins_fc2, _ins_fc3, _ins_fc4 = st.columns([2, 2, 2, 1])
            with _ins_fc1:
                _ins_cli_opts = ["All Clients"] + sorted(_audit_df_ins["Client"].dropna().astype(str).unique().tolist()) if "Client" in _audit_df_ins.columns else ["All Clients"]
                _ins_cli = st.selectbox("Client", _ins_cli_opts, key="ins_filter_client")
            with _ins_fc2:
                if _ins_cli != "All Clients" and "Client" in _audit_df_ins.columns and "Campaign Name" in _audit_df_ins.columns:
                    _ins_camp_src = _audit_df_ins[_audit_df_ins["Client"].astype(str) == _ins_cli]["Campaign Name"]
                else:
                    _ins_camp_src = _audit_df_ins["Campaign Name"] if "Campaign Name" in _audit_df_ins.columns else pd.Series(dtype=str)
                _ins_camp_opts = ["All Campaigns"] + sorted(_ins_camp_src.dropna().astype(str).unique().tolist())
                _ins_camp = st.selectbox("Campaign", _ins_camp_opts, key="ins_filter_camp")
            with _ins_fc3:
                _ins_bot_src = _audit_df_ins["Bot Name"] if "Bot Name" in _audit_df_ins.columns else pd.Series(dtype=str)
                _ins_bot_opts = ["All Bots"] + sorted(_ins_bot_src.dropna().astype(str).unique().tolist())
                _ins_bot = st.selectbox("Bot Name", _ins_bot_opts, key="ins_filter_bot")
            with _ins_fc4:
                if st.button("↺ Reset", key="ins_filter_reset", use_container_width=True):
                    for _k in ["ins_filter_client", "ins_filter_camp", "ins_filter_bot"]:
                        st.session_state.pop(_k, None)
                    st.rerun()
            _ins_df = _audit_df_ins.copy()
            if _ins_cli != "All Clients" and "Client" in _ins_df.columns:
                _ins_df = _ins_df[_ins_df["Client"].astype(str) == _ins_cli]
            if _ins_camp != "All Campaigns" and "Campaign Name" in _ins_df.columns:
                _ins_df = _ins_df[_ins_df["Campaign Name"].astype(str) == _ins_camp]
            if _ins_bot != "All Bots" and "Bot Name" in _ins_df.columns:
                _ins_df = _ins_df[_ins_df["Bot Name"].astype(str) == _ins_bot]
            if len(_ins_df) != len(_audit_df_ins):
                st.markdown(f'<div style="font-size:0.7rem;color:#2563EB;background:rgba(37,99,235,0.06);border-radius:6px;padding:4px 12px;margin-bottom:8px;">🔍 Filtered: <strong>{len(_ins_df):,}</strong> of <strong>{len(_audit_df_ins):,}</strong> audits</div>', unsafe_allow_html=True)
                _audit_df_ins_view = _ins_df
            else:
                _audit_df_ins_view = _audit_df_ins

            _qi2 = _gen_qa_insights(_audit_df_ins_view)
            total_i  = len(_audit_df_ins_view)
            _bs_i    = pd.to_numeric(_audit_df_ins_view["Bot Score"], errors="coerce")
            _st_i    = _audit_df_ins_view["Status"].astype(str).str.strip()
            _avg_i   = round(_bs_i.dropna().mean(), 1) if _bs_i.dropna().notna().any() else None
            pass_i   = int((_st_i == "Pass").sum())
            review_i = int((_st_i == "Needs Review").sum())
            fail_i   = int((_st_i == "Fail").sum())
            fatal_i  = int((_st_i == "Auto-Fail").sum())
            pass_rate_i = round(pass_i / total_i * 100, 1) if total_i else 0
            fail_rate_i = round((fail_i + fatal_i) / total_i * 100, 1) if total_i else 0

            # ── KPI Band — vibrant soft gradient cards ────────────────────────
            _bc = "#059669" if (_avg_i or 0) >= 80 else "#d97706" if (_avg_i or 0) >= 60 else "#dc2626"
            _pr_c = "#059669" if pass_rate_i >= 80 else "#d97706" if pass_rate_i >= 60 else "#dc2626"
            def _kpi_card(val, label, grad, txt="#fff", shadow="rgba(37,99,235,0.2)", accent=None):
                ac = accent or grad
                return (f'<div style="background:#fff;border-radius:14px;padding:0;'
                        f'box-shadow:0 2px 10px rgba(11,31,58,0.08);overflow:hidden;'
                        f'transition:box-shadow 0.2s,transform 0.2s;cursor:default;'
                        f'border:1px solid #E2EAF6;" '
                        f'onmouseover="this.style.boxShadow=\'0 8px 24px {shadow}\';this.style.transform=\'translateY(-3px)\'" '
                        f'onmouseout="this.style.boxShadow=\'0 2px 10px rgba(11,31,58,0.08)\';this.style.transform=\'translateY(0)\'">'
                        f'<div style="height:4px;background:{grad};"></div>'
                        f'<div style="padding:16px 14px 14px;text-align:center;">'
                        f'<div style="font-size:1.9rem;font-weight:900;color:#0B1F3A;line-height:1.05;letter-spacing:-0.03em;">{val}</div>'
                        f'<div style="font-size:0.59rem;font-weight:700;color:#64748b;letter-spacing:0.10em;text-transform:uppercase;margin-top:5px;">{label}</div>'
                        f'</div></div>')
            _kc1,_kc2,_kc3,_kc4,_kc5,_kc6 = st.columns(6)
            _kc1.markdown(_kpi_card(total_i,  "Total Audits",   "linear-gradient(135deg,#0B1F3A,#2563EB)", shadow="rgba(37,99,235,0.22)"), unsafe_allow_html=True)
            _kc2.markdown(_kpi_card(f"{_avg_i or '—'}%", "Avg Score", "linear-gradient(135deg,#0891b2,#06b6d4)" if (_avg_i or 0)>=80 else "linear-gradient(135deg,#d97706,#f59e0b)" if (_avg_i or 0)>=60 else "linear-gradient(135deg,#dc2626,#ef4444)", shadow="rgba(8,145,178,0.2)"), unsafe_allow_html=True)
            _kc3.markdown(_kpi_card(f"{pass_rate_i}%", "Pass Rate",  "linear-gradient(135deg,#059669,#10b981)" if pass_rate_i>=80 else "linear-gradient(135deg,#d97706,#f59e0b)" if pass_rate_i>=60 else "linear-gradient(135deg,#dc2626,#ef4444)", shadow="rgba(5,150,105,0.2)"), unsafe_allow_html=True)
            _kc4.markdown(_kpi_card(pass_i,   "Passed",          "linear-gradient(135deg,#059669,#10b981)", shadow="rgba(5,150,105,0.22)"), unsafe_allow_html=True)
            _kc5.markdown(_kpi_card(review_i, "Needs Review",    "linear-gradient(135deg,#d97706,#f59e0b)", shadow="rgba(217,119,6,0.22)"), unsafe_allow_html=True)
            _kc6.markdown(_kpi_card(fatal_i,  "Auto-Fails",      "linear-gradient(135deg,#dc2626,#f43f5e)" if fatal_i else "linear-gradient(135deg,#6b7280,#9ca3af)", shadow="rgba(220,38,38,0.22)"), unsafe_allow_html=True)
            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

            # ── Status Distribution Bar ───────────────────────────────────────
            _sd_cfg = [("✅ Pass", "#0ebc6e", pass_i), ("🟡 Needs Review", "#f59e0b", review_i),
                       ("❌ Fail", "#ef4444", fail_i), ("🚨 Auto-Fail", "#dc2626", fatal_i)]
            _sd_html = ""
            for _sn, _sc, _sv in _sd_cfg:
                _sp = round(_sv / total_i * 100, 1) if total_i else 0
                _sd_html += (
                    f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:5px;">'
                    f'<div style="width:110px;font-size:0.71rem;font-weight:600;color:#0d1d3a;flex-shrink:0;">{_sn}</div>'
                    f'<div style="flex:1;height:14px;background:#f0f2f5;border-radius:3px;overflow:hidden;">'
                    f'<div style="width:{_sp}%;height:100%;background:{_sc};border-radius:3px;"></div></div>'
                    f'<div style="width:80px;text-align:right;font-size:0.7rem;font-weight:700;color:{_sc};flex-shrink:0;">{_sv:,} ({_sp}%)</div>'
                    f'</div>'
                )
            _ov_l, _ov_r = st.columns([3, 2])
            with _ov_l:
                st.markdown('<div class="section-chip">📊 Status Distribution</div>', unsafe_allow_html=True)
                st.markdown(f'<div style="background:#fff;border:1px solid #e4e7ec;border-radius:10px;padding:14px 18px;margin-bottom:1rem;">{_sd_html}</div>', unsafe_allow_html=True)

            # ── Disposition Breakdown ─────────────────────────────────────────
            with _ov_r:
                if "Disposition" in _audit_df_ins_view.columns:
                    _disp_vc = _audit_df_ins_view["Disposition"].astype(str).str.strip()
                    _disp_vc = _disp_vc[~_disp_vc.isin(["", "nan", "— select —", "None"])]
                    _disp_counts = _disp_vc.value_counts()
                    if len(_disp_counts):
                        st.markdown('<div class="section-chip">📋 Disposition Mix</div>', unsafe_allow_html=True)
                        _disp_total = _disp_counts.sum()
                        _disp_colors = {"Interested":"#0ebc6e","Converted":"#16a34a","Warm Follow-up":"#2563EB",
                                        "Not Interested":"#f59e0b","DNC":"#dc2626","Wrong Number":"#ef4444",
                                        "Language Barrier":"#7c3aed","Voicemail / No Answer":"#6b7280","Other":"#aabbcc"}
                        _dh = ""
                        for _dn, _dv in _disp_counts.head(8).items():
                            _dp = round(_dv / _disp_total * 100, 1)
                            _dc = _disp_colors.get(str(_dn), "#5588bb")
                            _dh += (f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">'
                                    f'<div style="width:100px;font-size:0.67rem;color:#0d1d3a;font-weight:600;flex-shrink:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{_dn}</div>'
                                    f'<div style="flex:1;height:12px;background:#f0f2f5;border-radius:3px;overflow:hidden;">'
                                    f'<div style="width:{_dp}%;height:100%;background:{_dc};border-radius:3px;"></div></div>'
                                    f'<div style="width:50px;text-align:right;font-size:0.67rem;font-weight:700;color:{_dc};flex-shrink:0;">{_dp}%</div>'
                                    f'</div>')
                        st.markdown(f'<div style="background:#fff;border:1px solid #e4e7ec;border-radius:10px;padding:12px 16px;margin-bottom:1rem;">{_dh}</div>', unsafe_allow_html=True)

            # ── What Went Right / What Went Wrong ────────────────────────────
            # Compute per-parameter averages across ALL tier params
            _param_avgs = []
            for _tier in _QA_SCHEMA["tiers"]:
                for _p in _tier["params"]:
                    if _p["col"] not in _audit_df_ins_view.columns:
                        continue
                    _pmax_v = [int(o) for o in _p["options"] if str(o).lstrip("-").isdigit()]
                    _pmax = max(_pmax_v) if _pmax_v else 2
                    _pvals = pd.to_numeric(
                        _audit_df_ins_view[_p["col"]].astype(str).str.strip().replace({"NA":"","nan":"","Fatal":""}),
                        errors="coerce").dropna()
                    if len(_pvals) == 0:
                        continue
                    _pavg = round(_pvals.mean() / _pmax * 100, 1)
                    _param_avgs.append({"col": _p["col"], "pct": _pavg, "tier": _tier["label"], "color": _tier["color"], "n": len(_pvals)})

            _went_right = [p for p in _param_avgs if p["pct"] >= 80]
            _went_wrong = [p for p in _param_avgs if p["pct"] < 70]
            _went_right.sort(key=lambda x: -x["pct"])
            _went_wrong.sort(key=lambda x: x["pct"])

            _wrL, _wwR = st.columns(2)
            with _wrL:
                st.markdown(
                    '<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">'
                    '<div style="background:linear-gradient(135deg,#059669,#10b981);border-radius:8px;'
                    'padding:4px 12px;font-size:0.62rem;font-weight:800;color:#fff;letter-spacing:0.1em;text-transform:uppercase;">✅ What Went Right</div>'
                    f'<div style="font-size:0.65rem;color:#64748b;">{len(_went_right)} param{"s" if len(_went_right)!=1 else ""} performing well</div>'
                    '</div>',
                    unsafe_allow_html=True,
                )
                if _went_right:
                    _wr_html = ""
                    for _wrp in _went_right[:8]:
                        _t_short = _wrp["tier"].split("·")[-1].strip()
                        _wr_html += (
                            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">'
                            f'<div style="width:160px;font-size:0.71rem;font-weight:600;color:#0B1F3A;flex-shrink:0;'
                            f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{_wrp["col"]}</div>'
                            f'<div style="flex:1;height:10px;background:#D1FAE5;border-radius:5px;overflow:hidden;">'
                            f'<div style="width:{_wrp["pct"]}%;height:100%;background:linear-gradient(90deg,#059669,#34D399);border-radius:5px;"></div></div>'
                            f'<div style="width:38px;font-size:0.71rem;font-weight:800;color:#059669;flex-shrink:0;text-align:right;">{_wrp["pct"]}%</div>'
                            f'</div>'
                        )
                    st.markdown(f'<div style="background:#fff;border:1px solid #D1FAE5;border-left:3px solid #059669;border-radius:10px;padding:14px 16px;">{_wr_html}</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div style="background:#F8FAFF;border:1px solid #DBEAFE;border-radius:10px;padding:14px 16px;font-size:0.73rem;color:#64748b;text-align:center;">No parameters above 80% yet</div>', unsafe_allow_html=True)

            with _wwR:
                st.markdown(
                    '<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">'
                    '<div style="background:linear-gradient(135deg,#dc2626,#f43f5e);border-radius:8px;'
                    'padding:4px 12px;font-size:0.62rem;font-weight:800;color:#fff;letter-spacing:0.1em;text-transform:uppercase;">⚠️ What Went Wrong</div>'
                    f'<div style="font-size:0.65rem;color:#64748b;">{len(_went_wrong)} param{"s" if len(_went_wrong)!=1 else ""} need attention</div>'
                    '</div>',
                    unsafe_allow_html=True,
                )
                if _went_wrong:
                    _ww_html = ""
                    for _wwp in _went_wrong[:8]:
                        _urgency = "#dc2626" if _wwp["pct"] < 50 else "#d97706"
                        _bg_bar  = "#FEE2E2" if _wwp["pct"] < 50 else "#FEF3C7"
                        _ww_html += (
                            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">'
                            f'<div style="width:160px;font-size:0.71rem;font-weight:600;color:#0B1F3A;flex-shrink:0;'
                            f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{_wwp["col"]}</div>'
                            f'<div style="flex:1;height:10px;background:{_bg_bar};border-radius:5px;overflow:hidden;">'
                            f'<div style="width:{_wwp["pct"]}%;height:100%;background:{_urgency};border-radius:5px;"></div></div>'
                            f'<div style="width:38px;font-size:0.71rem;font-weight:800;color:{_urgency};flex-shrink:0;text-align:right;">{_wwp["pct"]}%</div>'
                            f'</div>'
                        )
                    st.markdown(f'<div style="background:#fff;border:1px solid #FEE2E2;border-left:3px solid #dc2626;border-radius:10px;padding:14px 16px;">{_ww_html}</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div style="background:#F0FDF4;border:1px solid #BBF7D0;border-radius:10px;padding:14px 16px;font-size:0.73rem;color:#059669;text-align:center;">🎉 All parameters performing well!</div>', unsafe_allow_html=True)

            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

            # ── Top 5 Best Calls Handled ──────────────────────────────────────
            st.markdown('<div class="section-chip">🏅 Top 5 Best Calls Handled</div>', unsafe_allow_html=True)
            _bs_col = pd.to_numeric(_audit_df_ins_view["Bot Score"], errors="coerce")
            _top5_df = _audit_df_ins_view.copy()
            _top5_df["_bs_num"] = _bs_col
            _top5_df = _top5_df.dropna(subset=["_bs_num"]).sort_values("_bs_num", ascending=False).head(5)
            if not _top5_df.empty:
                _top5_html = ""
                _medal = ["🥇","🥈","🥉","4️⃣","5️⃣"]
                for _ri, (_, _row) in enumerate(_top5_df.iterrows()):
                    _sc  = float(_row["_bs_num"])
                    _sta = str(_row.get("Status","—")).strip()
                    _qa  = str(_row.get("QA","—")).strip() if "QA" in _row.index else "—"
                    _cam = str(_row.get("Campaign Name","—")).strip() if "Campaign Name" in _row.index else "—"
                    _ld  = str(_row.get("Lead Number", _row.get("Lead", _row.get("Phone Number","—")))).strip()
                    _ld  = _ld[:18] if _ld != "—" else f"#{_ri+1}"
                    _sc_c = "#059669" if _sc >= 80 else "#d97706"
                    # Key strong params (scored 2 out of 2)
                    _strong = [p["col"] for p in [q for t in _QA_SCHEMA["tiers"] for q in t["params"]]
                               if p["col"] in _row.index and str(_row[p["col"]]).strip() == "2"][:3]
                    _strong_chips = "".join(
                        f'<span style="background:#EBF5FF;border:1px solid #BFDBFE;border-radius:4px;'
                        f'padding:1px 6px;font-size:0.58rem;font-weight:700;color:#2563EB;margin-right:3px;">{s}</span>'
                        for s in _strong
                    )
                    _top5_html += (
                        f'<div style="display:grid;grid-template-columns:2rem 2.5rem 1fr 1fr 1fr auto;'
                        f'align-items:center;gap:10px;padding:10px 16px;'
                        f'border-top:{"none" if _ri==0 else "1px solid #F1F5F9"};">'
                        f'<div style="font-size:1.1rem;text-align:center;">{_medal[_ri]}</div>'
                        f'<div style="background:linear-gradient(135deg,#0B1F3A,#2563EB);border-radius:8px;'
                        f'padding:4px 0;text-align:center;font-size:0.85rem;font-weight:900;color:#fff;">{int(_sc)}</div>'
                        f'<div>'
                        f'<div style="font-size:0.73rem;font-weight:700;color:#0B1F3A;">{_ld}</div>'
                        f'<div style="font-size:0.62rem;color:#64748b;margin-top:1px;">{_cam[:22] if _cam!="—" else ""}</div>'
                        f'</div>'
                        f'<div style="font-size:0.69rem;color:#475569;">👤 {_qa[:16]}</div>'
                        f'<div style="display:flex;flex-wrap:wrap;gap:2px;">{_strong_chips if _strong_chips else "<span style=\"font-size:0.62rem;color:#94a3b8;\">—</span>"}</div>'
                        f'<div style="background:#ECFDF5;border:1px solid #A7F3D0;border-radius:6px;'
                        f'padding:2px 8px;font-size:0.65rem;font-weight:700;color:#059669;white-space:nowrap;">{_sta}</div>'
                        f'</div>'
                    )
                st.markdown(
                    f'<div style="background:#fff;border:1px solid #E2EAF6;border-radius:12px;overflow:hidden;'
                    f'box-shadow:0 2px 8px rgba(11,31,58,0.06);">'
                    f'<div style="background:linear-gradient(135deg,#0B1F3A,#1D4ED8);padding:10px 16px;'
                    f'display:grid;grid-template-columns:2rem 2.5rem 1fr 1fr 1fr auto;gap:10px;align-items:center;">'
                    f'<div style="font-size:0.6rem;font-weight:800;color:rgba(255,255,255,0.5);text-transform:uppercase;">#</div>'
                    f'<div style="font-size:0.6rem;font-weight:800;color:rgba(255,255,255,0.5);text-transform:uppercase;">Score</div>'
                    f'<div style="font-size:0.6rem;font-weight:800;color:rgba(255,255,255,0.5);text-transform:uppercase;">Lead / ID</div>'
                    f'<div style="font-size:0.6rem;font-weight:800;color:rgba(255,255,255,0.5);text-transform:uppercase;">QA</div>'
                    f'<div style="font-size:0.6rem;font-weight:800;color:rgba(255,255,255,0.5);text-transform:uppercase;">Strong Params</div>'
                    f'<div style="font-size:0.6rem;font-weight:800;color:rgba(255,255,255,0.5);text-transform:uppercase;">Status</div>'
                    f'</div>'
                    f'{_top5_html}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

            # ── Top 5 Worst Calls with Conversation Links ─────────────────────
            st.markdown('<div class="section-chip">🚨 Top 5 Worst Calls — Needs Attention</div>', unsafe_allow_html=True)
            _worst5_df = _audit_df_ins_view.copy()
            _worst5_df["_bs_num"] = pd.to_numeric(_worst5_df["Bot Score"], errors="coerce")
            _worst5_df = _worst5_df.dropna(subset=["_bs_num"]).sort_values("_bs_num", ascending=True).head(5)
            if not _worst5_df.empty:
                _w5_html = ""
                _w5_medal = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣"]
                for _w5i, (_, _w5row) in enumerate(_worst5_df.iterrows()):
                    _w5sc  = float(_w5row["_bs_num"])
                    _w5sta = str(_w5row.get("Status","—")).strip()
                    _w5qa  = str(_w5row.get("QA","—")).strip() if "QA" in _w5row.index else "—"
                    _w5cam = str(_w5row.get("Campaign Name","—")).strip() if "Campaign Name" in _w5row.index else "—"
                    _w5ld  = str(_w5row.get("Lead Number", _w5row.get("Lead", _w5row.get("Phone Number","—")))).strip()
                    _w5ld  = _w5ld[:18] if _w5ld not in ("—","nan","") else f"#{_w5i+1}"
                    _w5link = str(_w5row.get("Conversation Link","")).strip()
                    _w5link_html = (f'<a href="{_w5link}" target="_blank" style="font-size:0.62rem;color:#2563EB;font-weight:700;'
                                    f'text-decoration:none;background:#EBF5FF;border:1px solid #BFDBFE;border-radius:4px;'
                                    f'padding:2px 7px;white-space:nowrap;">🔗 View Call</a>') if _w5link and _w5link.startswith("http") else '<span style="font-size:0.62rem;color:#aabbcc;">—</span>'
                    _w5sc_c = "#dc2626" if _w5sc < 60 else "#d97706"
                    _w5_fail_params = [p["col"] for p in [q for t in _QA_SCHEMA["tiers"] for q in t["params"]]
                                       if p["col"] in _w5row.index and str(_w5row[p["col"]]).strip() == "0"][:3]
                    _w5_fail_chips = "".join(
                        f'<span style="background:#FEE2E2;border:1px solid #FECACA;border-radius:4px;'
                        f'padding:1px 5px;font-size:0.58rem;font-weight:700;color:#dc2626;margin-right:3px;">{s}</span>'
                        for s in _w5_fail_params
                    )
                    _w5_html += (
                        f'<div style="display:grid;grid-template-columns:2rem 2.5rem 1fr 1fr 1fr auto;'
                        f'align-items:center;gap:10px;padding:10px 16px;'
                        f'border-top:{"none" if _w5i==0 else "1px solid #F1F5F9"};">'
                        f'<div style="font-size:1.1rem;text-align:center;">{_w5_medal[_w5i]}</div>'
                        f'<div style="background:linear-gradient(135deg,#7F1D1D,#dc2626);border-radius:8px;'
                        f'padding:4px 0;text-align:center;font-size:0.85rem;font-weight:900;color:#fff;">{int(_w5sc)}</div>'
                        f'<div>'
                        f'<div style="font-size:0.73rem;font-weight:700;color:#0B1F3A;">{_w5ld}</div>'
                        f'<div style="font-size:0.62rem;color:#64748b;margin-top:1px;">{_w5cam[:22] if _w5cam!="—" else ""}</div>'
                        f'</div>'
                        f'<div style="font-size:0.69rem;color:#475569;">👤 {_w5qa[:16]}</div>'
                        f'<div style="display:flex;flex-wrap:wrap;gap:2px;">{_w5_fail_chips if _w5_fail_chips else "<span style=\"font-size:0.62rem;color:#94a3b8;\">—</span>"}</div>'
                        f'<div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px;">'
                        f'{_w5link_html}'
                        f'<div style="background:#FEF2F2;border:1px solid #FECACA;border-radius:6px;padding:2px 8px;'
                        f'font-size:0.65rem;font-weight:700;color:#dc2626;white-space:nowrap;">{_w5sta}</div>'
                        f'</div>'
                        f'</div>'
                    )
                st.markdown(
                    f'<div style="background:#fff;border:1px solid #FECACA;border-radius:12px;overflow:hidden;'
                    f'box-shadow:0 2px 8px rgba(220,38,38,0.08);">'
                    f'<div style="background:linear-gradient(135deg,#7F1D1D,#dc2626);padding:10px 16px;'
                    f'display:grid;grid-template-columns:2rem 2.5rem 1fr 1fr 1fr auto;gap:10px;align-items:center;">'
                    f'<div style="font-size:0.6rem;font-weight:800;color:rgba(255,255,255,0.5);text-transform:uppercase;">#</div>'
                    f'<div style="font-size:0.6rem;font-weight:800;color:rgba(255,255,255,0.5);text-transform:uppercase;">Score</div>'
                    f'<div style="font-size:0.6rem;font-weight:800;color:rgba(255,255,255,0.5);text-transform:uppercase;">Lead / ID</div>'
                    f'<div style="font-size:0.6rem;font-weight:800;color:rgba(255,255,255,0.5);text-transform:uppercase;">QA</div>'
                    f'<div style="font-size:0.6rem;font-weight:800;color:rgba(255,255,255,0.5);text-transform:uppercase;">Failed Params</div>'
                    f'<div style="font-size:0.6rem;font-weight:800;color:rgba(255,255,255,0.5);text-transform:uppercase;">Conversation</div>'
                    f'</div>'
                    f'{_w5_html}'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

            # ── Parameter-wise Insights (ALL parameters) ─────────────────────
            st.markdown('<div class="section-chip">🔬 Parameter-wise Performance — All Tiers</div>', unsafe_allow_html=True)
            _tier_cols = st.columns(len(_QA_SCHEMA["tiers"]))
            for _tc_i, _tier_g in enumerate(_QA_SCHEMA["tiers"]):
                with _tier_cols[_tc_i]:
                    _tclr = _tier_g["color"]
                    _tier_rows_html = ""
                    _has_any = False
                    for _pp in _tier_g["params"]:
                        _pmx_v = [int(o) for o in _pp["options"] if str(o).lstrip("-").isdigit()]
                        _pmx = max(_pmx_v) if _pmx_v else 2
                        if _pp["col"] not in _audit_df_ins_view.columns:
                            _bar_pct = None
                        else:
                            _pv2 = pd.to_numeric(
                                _audit_df_ins_view[_pp["col"]].astype(str).str.strip().replace({"NA":"","nan":"","Fatal":""}),
                                errors="coerce").dropna()
                            _bar_pct = round(_pv2.mean() / _pmx * 100, 1) if len(_pv2) else None
                        if _bar_pct is None:
                            continue
                        _has_any = True
                        _bclr = "#059669" if _bar_pct >= 80 else "#d97706" if _bar_pct >= 60 else "#dc2626"
                        _icon = "✅" if _bar_pct >= 80 else "⚠️" if _bar_pct >= 60 else "🔴"
                        _tier_rows_html += (
                            f'<div style="margin-bottom:8px;">'
                            f'<div style="display:flex;justify-content:space-between;margin-bottom:3px;">'
                            f'<div style="font-size:0.67rem;font-weight:600;color:#0B1F3A;'
                            f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:150px;">'
                            f'{_icon} {_pp["col"]}</div>'
                            f'<div style="font-size:0.67rem;font-weight:800;color:{_bclr};flex-shrink:0;margin-left:4px;">{_bar_pct}%</div>'
                            f'</div>'
                            f'<div style="height:8px;background:#F1F5F9;border-radius:4px;overflow:hidden;">'
                            f'<div style="width:{_bar_pct}%;height:100%;background:linear-gradient(90deg,{_tclr},{_bclr});border-radius:4px;"></div>'
                            f'</div>'
                            f'</div>'
                        )
                    if _has_any:
                        st.markdown(
                            f'<div style="background:#fff;border:1px solid #E2EAF6;border-top:3px solid {_tclr};'
                            f'border-radius:10px;padding:14px 16px;min-height:120px;">'
                            f'<div style="font-size:0.61rem;font-weight:800;color:{_tclr};letter-spacing:0.1em;'
                            f'text-transform:uppercase;margin-bottom:12px;">{_tier_g["label"]}</div>'
                            f'{_tier_rows_html}</div>',
                            unsafe_allow_html=True,
                        )

            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

            # ── Key Insights (sorted: critical → warning → success) ───────────
            _TYPE_CFG2 = {
                "critical": ("#FFF1F2","#dc2626","#7F1D1D","#FECDD3"),
                "warning":  ("#FFFBEB","#D97706","#78350F","#FDE68A"),
                "success":  ("#ECFDF5","#059669","#064E3B","#A7F3D0"),
                "info":     ("#EBF5FF","#2563EB","#0B1F3A","#BFDBFE"),
            }
            _pri_order = {"critical": 0, "warning": 1, "info": 2, "success": 3}
            _sorted_ins = sorted(_qi2.get("insights", []), key=lambda x: _pri_order.get(x.get("type","info"), 2))
            if _sorted_ins:
                st.markdown('<div class="section-chip">💡 Key Insights & Callouts</div>', unsafe_allow_html=True)

                # ── Hero callouts — critical alerts rendered full-width ──────
                _criticals = [i for i in _sorted_ins if i.get("type") == "critical"]
                _rest_ins  = [i for i in _sorted_ins if i.get("type") != "critical"]
                for _crit in _criticals:
                    st.markdown(
                        f'<div style="background:linear-gradient(135deg,#7F1D1D 0%,#991B1B 100%);'
                        f'border-radius:14px;padding:18px 22px;margin-bottom:10px;'
                        f'box-shadow:0 4px 18px rgba(220,38,38,0.28);'
                        f'display:flex;align-items:flex-start;gap:16px;">'
                        f'<div style="font-size:2rem;line-height:1;flex-shrink:0;margin-top:2px;">🚨</div>'
                        f'<div>'
                        f'<div style="font-size:0.85rem;font-weight:800;color:#FECDD3;letter-spacing:0.02em;margin-bottom:5px;">{_crit["title"]}</div>'
                        f'<div style="font-size:0.74rem;color:rgba(254,205,211,0.88);line-height:1.55;">{_crit["detail"]}</div>'
                        f'</div>'
                        f'<div style="margin-left:auto;flex-shrink:0;background:#dc2626;border-radius:20px;'
                        f'padding:3px 11px;font-size:0.58rem;font-weight:800;color:#fff;letter-spacing:0.1em;'
                        f'text-transform:uppercase;align-self:flex-start;white-space:nowrap;">CRITICAL</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                # ── Warning callouts — prominent single-col strips ───────────
                _warnings = [i for i in _rest_ins if i.get("type") == "warning"]
                _non_warn = [i for i in _rest_ins if i.get("type") != "warning"]
                if _warnings:
                    _wc_l, _wc_r = st.columns(2)
                    for _wi, _wi_ins in enumerate(_warnings):
                        _wc = _TYPE_CFG2["warning"]
                        with (_wc_l if _wi % 2 == 0 else _wc_r):
                            st.markdown(
                                f'<div style="background:{_wc[0]};border:1px solid {_wc[3]};'
                                f'border-left:5px solid {_wc[1]};border-radius:10px;'
                                f'padding:13px 16px;margin-bottom:8px;">'
                                f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">'
                                f'<span style="font-size:0.62rem;font-weight:800;letter-spacing:0.10em;text-transform:uppercase;'
                                f'color:{_wc[1]};background:{_wc[3]};padding:2px 8px;border-radius:10px;">WARNING</span>'
                                f'<span style="font-size:0.78rem;font-weight:700;color:{_wc[2]};">{_wi_ins["title"]}</span></div>'
                                f'<div style="font-size:0.71rem;color:{_wc[2]};opacity:0.88;line-height:1.5;padding-left:2px;">{_wi_ins["detail"]}</div>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )

                # ── Success + Info callouts — 2-col grid ────────────────────
                if _non_warn:
                    _ic1, _ic2 = st.columns(2)
                    for _ii, _ins in enumerate(_non_warn):
                        _tcfg2 = _TYPE_CFG2.get(_ins["type"], _TYPE_CFG2["info"])
                        with (_ic1 if _ii % 2 == 0 else _ic2):
                            st.markdown(
                                f'<div style="background:{_tcfg2[0]};border:1px solid {_tcfg2[3]};'
                                f'border-left:4px solid {_tcfg2[1]};border-radius:10px;'
                                f'padding:12px 16px;margin-bottom:8px;">'
                                f'<div style="font-size:0.78rem;font-weight:700;color:{_tcfg2[2]};margin-bottom:4px;">{_ins["title"]}</div>'
                                f'<div style="font-size:0.71rem;color:{_tcfg2[2]};opacity:0.88;line-height:1.5;">{_ins["detail"]}</div>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )

            # ── Priority Actions ──────────────────────────────────────────────
            _PRI_CFG2 = {
                "high":   ("#dc2626","🔴","#FFF1F2","#FECDD3"),
                "medium": ("#D97706","🟡","#FFFBEB","#FDE68A"),
                "low":    ("#059669","🟢","#ECFDF5","#A7F3D0"),
            }
            _sorted_acts = sorted(_qi2.get("actions",[]), key=lambda x: {"high":0,"medium":1,"low":2}.get(x.get("priority","low"),2))
            if _sorted_acts:
                st.markdown('<div class="section-chip">🎯 Priority Actions</div>', unsafe_allow_html=True)
                # Numbered action list — high-priority items get accent treatment
                _high_acts = [a for a in _sorted_acts if a.get("priority") == "high"]
                _other_acts = [a for a in _sorted_acts if a.get("priority") != "high"]
                for _ai_n, _act in enumerate(_high_acts, 1):
                    _pcfg2 = _PRI_CFG2["high"]
                    st.markdown(
                        f'<div style="background:linear-gradient(135deg,#0B1F3A,#1e3a5f);'
                        f'border-radius:12px;padding:14px 18px;margin-bottom:8px;'
                        f'box-shadow:0 3px 12px rgba(11,31,58,0.18);display:flex;align-items:flex-start;gap:14px;">'
                        f'<div style="background:#dc2626;color:#fff;border-radius:50%;width:28px;height:28px;'
                        f'display:flex;align-items:center;justify-content:center;font-size:0.78rem;font-weight:900;flex-shrink:0;">{_ai_n}</div>'
                        f'<div style="flex:1;">'
                        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">'
                        f'<span style="font-size:0.58rem;font-weight:800;letter-spacing:0.10em;text-transform:uppercase;'
                        f'color:#FECDD3;background:#dc2626;padding:2px 9px;border-radius:10px;">HIGH · {_act["category"]}</span>'
                        f'</div>'
                        f'<div style="font-size:0.74rem;font-weight:700;color:#F1F5F9;margin-bottom:6px;line-height:1.45;">{_act["action"]}</div>'
                        f'<div style="font-size:0.66rem;color:#94a3b8;line-height:1.4;border-top:1px solid rgba(255,255,255,0.1);padding-top:5px;">'
                        f'💥 Impact: {_act["impact"]}</div>'
                        f'</div></div>',
                        unsafe_allow_html=True,
                    )
                if _other_acts:
                    _ac1, _ac2 = st.columns(2)
                    for _ai2, _act in enumerate(_other_acts):
                        _pcfg2 = _PRI_CFG2.get(_act["priority"], _PRI_CFG2["low"])
                        with (_ac1 if _ai2 % 2 == 0 else _ac2):
                            st.markdown(
                                f'<div style="background:{_pcfg2[2]};border:1px solid {_pcfg2[3]};'
                                f'border-left:4px solid {_pcfg2[0]};border-radius:10px;'
                                f'padding:12px 15px;margin-bottom:8px;">'
                                f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:5px;">'
                                f'<span>{_pcfg2[1]}</span>'
                                f'<span style="font-size:0.62rem;font-weight:800;letter-spacing:0.08em;text-transform:uppercase;color:{_pcfg2[0]};">'
                                f'{_act["priority"].upper()} · {_act["category"]}</span></div>'
                                f'<div style="font-size:0.73rem;font-weight:600;color:#0B1F3A;margin-bottom:5px;line-height:1.4;">{_act["action"]}</div>'
                                f'<div style="font-size:0.65rem;color:#475569;line-height:1.4;border-top:1px solid {_pcfg2[0]}22;padding-top:5px;">'
                                f'Impact: {_act["impact"]}</div>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )

            # ── Build & Send One-Pager Email ──────────────────────────────────
            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
            st.markdown('<div class="section-chip">📧 Build One-Pager Email</div>', unsafe_allow_html=True)
            st.markdown(
                '<div style="font-size:0.72rem;color:#475569;margin-bottom:12px;">'
                'Tick the sections and individual insights / actions you want in the email, then generate a beautiful one-pager report.</div>',
                unsafe_allow_html=True)
            with st.expander("📧 Select Sections & Generate Email Draft", expanded=True):
                _now_str   = pd.Timestamp.now().strftime("%d %b %Y")
                _cli_label  = _ins_cli  if _ins_cli  != "All Clients"   else "All Clients"
                _camp_label = _ins_camp if _ins_camp != "All Campaigns" else "All Campaigns"
                _bot_label  = _ins_bot  if _ins_bot  != "All Bots"      else "All Bots"
                _avg_str   = f"{_avg_i}%" if _avg_i else "—"

                # ── Pre-compute data for email blocks ─────────────────────────
                _em_camp_rows = []
                if "Campaign Name" in _audit_df_ins_view.columns:
                    for _cn3, _cg3 in _audit_df_ins_view.groupby("Campaign Name"):
                        _cbs3 = pd.to_numeric(_cg3["Bot Score"], errors="coerce").dropna()
                        if len(_cbs3):
                            _cs3 = _cg3["Status"].astype(str).str.strip() if "Status" in _cg3.columns else pd.Series()
                            _cp3 = round(int((_cs3=="Pass").sum())/len(_cg3)*100,1) if len(_cg3) else 0
                            _cf3 = round(int((_cs3.isin(["Fail","Auto-Fail"])).sum())/len(_cg3)*100,1) if len(_cg3) else 0
                            _em_camp_rows.append({"name":str(_cn3),"avg":round(_cbs3.mean(),1),"n":len(_cg3),"pass":_cp3,"fail":_cf3})
                _em_qa_rows = []
                if "QA" in _audit_df_ins_view.columns:
                    for _qn3, _qg3 in _audit_df_ins_view.groupby("QA"):
                        _qbs3 = pd.to_numeric(_qg3["Bot Score"], errors="coerce").dropna()
                        if len(_qbs3):
                            _qp3 = round(int((_qg3["Status"].astype(str).str.strip()=="Pass").sum())/len(_qg3)*100,1)
                            _em_qa_rows.append({"name":str(_qn3),"avg":round(_qbs3.mean(),1),"n":len(_qg3),"pass":_qp3})
                _em_param_rows = []
                for _etier in _QA_SCHEMA["tiers"]:
                    for _ep in _etier["params"]:
                        if _ep["col"] not in _audit_df_ins_view.columns: continue
                        _epv = pd.to_numeric(_audit_df_ins_view[_ep["col"]].astype(str).str.strip().replace({"NA":"","nan":"","Fatal":""}),errors="coerce").dropna()
                        if len(_epv) == 0: continue
                        _epmx = max([int(o) for o in _ep["options"] if str(o).lstrip("-").isdigit()], default=2)
                        _em_param_rows.append({"col":_ep["col"],"pct":round(_epv.mean()/_epmx*100,1),"tier":_etier["label"],"color":_etier["color"]})
                _em_param_rows.sort(key=lambda x: x["pct"])

                # ── Custom param rows for email ───────────────────────────────
                _em_custom_rows = []
                for _ecp in st.session_state.get("sense_custom_audit_params", []):
                    if _ecp["name"] not in _audit_df_ins_view.columns: continue
                    _ecpv = _audit_df_ins_view[_ecp["name"]].replace("", None).dropna().astype(str).str.strip()
                    _ecpv = _ecpv[_ecpv.str.lower() != "nan"]
                    _ec_tot = len(_ecpv)
                    if _ec_tot == 0: continue
                    _ec_yes = int((_ecpv.str.lower() == "yes").sum())
                    _ec_no  = int((_ecpv.str.lower() == "no").sum())
                    _ec_na  = int((_ecpv.str.lower() == "na").sum())
                    _ec_cmt_col = f"{_ecp['name']} Comment"
                    _ec_cmts = int(_audit_df_ins_view[_ec_cmt_col].replace("",None).dropna().astype(str).str.strip().str.len().gt(0).sum()) if _ec_cmt_col in _audit_df_ins_view.columns else 0
                    _em_custom_rows.append({
                        "name": _ecp["name"],
                        "yes": _ec_yes, "no": _ec_no, "na": _ec_na, "tot": _ec_tot,
                        "yes_pct": round(_ec_yes/_ec_tot*100,1),
                        "no_pct":  round(_ec_no /_ec_tot*100,1),
                        "cmts": _ec_cmts,
                    })

                # ── Collect remarks text for AI summary ───────────────────────
                _remark_lines = []
                for _rdf_col in ["Notes", "Improvement Suggestion"]:
                    if _rdf_col in _audit_df_ins_view.columns:
                        for _rv in _audit_df_ins_view[_rdf_col].dropna().astype(str).str.strip():
                            if _rv and _rv.lower() not in ("", "nan", "none"):
                                _remark_lines.append(_rv)
                for _ecp2 in st.session_state.get("sense_custom_audit_params", []):
                    _cmt2 = f"{_ecp2['name']} Comment"
                    if _cmt2 in _audit_df_ins_view.columns:
                        for _rv2 in _audit_df_ins_view[_cmt2].dropna().astype(str).str.strip():
                            if _rv2 and _rv2.lower() not in ("", "nan", "none"):
                                _remark_lines.append(_rv2)

                # ── SECTION SELECTION ─────────────────────────────────────────
                st.markdown('<div style="font-size:0.75rem;font-weight:800;color:#0B1F3A;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:10px;border-bottom:2px solid #E2EAF6;padding-bottom:6px;">✅ Choose Sections to Include</div>', unsafe_allow_html=True)
                _eml_c1, _eml_c2, _eml_c3 = st.columns(3)
                with _eml_c1:
                    em_kpis   = st.checkbox(f"📊 KPI Summary  ({total_i:,} audits · {_avg_str} avg · {pass_rate_i}% pass)", value=True, key="em_kpis")
                    em_status = st.checkbox(f"🟢 Status Mix  ({pass_i} Pass · {review_i} Review · {fail_i} Fail · {fatal_i} Auto-Fail)", value=True, key="em_status")
                    _disp_count_em = int(_audit_df_ins_view["Disposition"].replace("",None).dropna().count()) if "Disposition" in _audit_df_ins_view.columns else 0
                    em_disp   = st.checkbox(f"🎯 Disposition Mix  ({_disp_count_em} with disposition)", value=bool(_disp_count_em), key="em_disp")
                with _eml_c2:
                    em_wr     = st.checkbox(f"✅ What Went Right  ({len(_went_right)} param{'s' if len(_went_right)!=1 else ''})", value=bool(_went_right), key="em_wr")
                    em_ww     = st.checkbox(f"⚠️ What Went Wrong  ({len(_went_wrong)} param{'s' if len(_went_wrong)!=1 else ''})", value=bool(_went_wrong), key="em_ww")
                    em_best5  = st.checkbox("🏅 Top 5 Best Calls", value=True, key="em_best5")
                    em_worst5 = st.checkbox("🚨 Top 5 Worst Calls", value=True, key="em_worst5")
                with _eml_c3:
                    em_camp      = st.checkbox(f"🎯 Campaign Breakdown  ({len(_em_camp_rows)} campaigns)", value=bool(_em_camp_rows), key="em_camp")
                    em_qa_tbl    = st.checkbox(f"👤 QA Team Performance  ({len(_em_qa_rows)} auditors)", value=bool(_em_qa_rows), key="em_qa_tbl")
                    em_params    = st.checkbox(f"🔬 Parameter Details  ({len(_em_param_rows)} params)", value=bool(_em_param_rows), key="em_params")
                    em_custom_ps = st.checkbox(f"⭐ Custom Parameters  ({len(_em_custom_rows)} params)", value=bool(_em_custom_rows), key="em_custom_ps")
                    em_remarks   = st.checkbox(f"💬 Remarks Summary  ({len(_remark_lines)} remarks)", value=bool(_remark_lines), key="em_remarks")

                # ── AI Remarks Summary generator ──────────────────────────────
                _remarks_key = "ins_em_remarks_summary"
                if em_remarks and _remark_lines:
                    _api_key_rm = st.session_state.get("api_key", "")
                    _rm_col1, _rm_col2 = st.columns([3, 1])
                    with _rm_col1:
                        _existing = st.session_state.get(_remarks_key)
                        if _existing:
                            st.markdown(
                                '<div style="font-size:0.68rem;color:#059669;font-weight:700;margin-bottom:4px;">✅ Remarks summary ready — will be included in email</div>',
                                unsafe_allow_html=True,
                            )
                        else:
                            st.markdown(
                                f'<div style="font-size:0.68rem;color:#475569;margin-bottom:4px;">💬 {len(_remark_lines)} remarks found (Notes + Improvement Suggestions + Custom Comments). Click to summarise with AI.</div>',
                                unsafe_allow_html=True,
                            )
                    with _rm_col2:
                        if st.button("✨ Summarise Remarks", key="ins_em_gen_remarks", use_container_width=True):
                            if not _api_key_rm:
                                st.warning("Add your Anthropic API key in Settings to use AI summary.")
                            else:
                                _rm_text = "\n".join(f"- {r}" for r in _remark_lines[:80])
                                _rm_prompt = (
                                    f"You are a QA analytics expert. Below are reviewer remarks, notes, and improvement suggestions from QA audit records "
                                    f"for client '{_cli_label}', campaign '{_camp_label}', bot '{_bot_label}'.\n\n"
                                    f"Remarks:\n{_rm_text}\n\n"
                                    f"Return ONLY valid JSON (no markdown) with exactly these keys:\n"
                                    f'{{"summary": "2-3 sentence overall summary of recurring themes", '
                                    f'"positive": ["positive insight 1", "positive insight 2"], '
                                    f'"concerns": ["concern 1", "concern 2", "concern 3"], '
                                    f'"suggestions": ["suggestion 1", "suggestion 2"]}}'
                                )
                                try:
                                    import anthropic as _anth, json as _jrm
                                    _anth_c = _anth.Anthropic(api_key=_api_key_rm)
                                    with st.spinner("Summarising remarks with AI…"):
                                        _rm_msg = _anth_c.messages.create(
                                            model="claude-haiku-4-5-20251001",
                                            max_tokens=600,
                                            messages=[{"role": "user", "content": _rm_prompt}],
                                        )
                                    _rm_raw = _rm_msg.content[0].text.strip()
                                    if _rm_raw.startswith("```"):
                                        _rm_raw = _rm_raw.split("```")[1]
                                        if _rm_raw.startswith("json"): _rm_raw = _rm_raw[4:]
                                    st.session_state[_remarks_key] = _jrm.loads(_rm_raw)
                                    st.rerun()
                                except Exception as _rme:
                                    st.error(f"AI error: {_rme}")

                # ── PER-INSIGHT SELECTION ──────────────────────────────────────
                _em_ins_sel = {}
                if _sorted_ins:
                    st.markdown('<div style="font-size:0.75rem;font-weight:800;color:#0B1F3A;letter-spacing:0.08em;text-transform:uppercase;margin:14px 0 8px;border-bottom:2px solid #E2EAF6;padding-bottom:6px;">💡 Key Insights — Tick to Include</div>', unsafe_allow_html=True)
                    _type_badge = {"critical":"🚨 CRITICAL","warning":"⚠️ WARNING","success":"✅ SUCCESS","info":"ℹ️ INFO"}
                    _ins_cols_split = st.columns(2)
                    for _ei, _eins in enumerate(_sorted_ins):
                        _e_badge = _type_badge.get(_eins.get("type","info"),"ℹ️ INFO")
                        _e_default = True
                        with _ins_cols_split[_ei % 2]:
                            _em_ins_sel[_ei] = st.checkbox(
                                f"{_e_badge} · {_eins['title'][:55]}",
                                value=_e_default, key=f"em_ins_{_ei}",
                                help=_eins.get("detail","")[:200]
                            )

                # ── PER-ACTION SELECTION ──────────────────────────────────────
                _em_act_sel = {}
                if _sorted_acts:
                    st.markdown('<div style="font-size:0.75rem;font-weight:800;color:#0B1F3A;letter-spacing:0.08em;text-transform:uppercase;margin:14px 0 8px;border-bottom:2px solid #E2EAF6;padding-bottom:6px;">🎯 Priority Actions — Tick to Include</div>', unsafe_allow_html=True)
                    _pri_badge = {"high":"🔴 HIGH","medium":"🟡 MED","low":"🟢 LOW"}
                    _act_cols_split = st.columns(2)
                    for _ea, _eact in enumerate(_sorted_acts):
                        _ea_badge = _pri_badge.get(_eact.get("priority","low"),"🟢 LOW")
                        with _act_cols_split[_ea % 2]:
                            _em_act_sel[_ea] = st.checkbox(
                                f"{_ea_badge} · {_eact['action'][:60]}",
                                value=True, key=f"em_act_{_ea}",
                                help=f"Impact: {_eact.get('impact','')[:200]}"
                            )

                st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

                # ── TEMPLATE SELECTOR ────────────────────────────────────────
                _tpl_options = {
                    "1 — Executive Dark (Navy/Blue)":       1,
                    "2 — Minimal White (Clean/Modern)":     2,
                    "3 — Bold Red (Urgent/Alert)":           3,
                    "4 — Corporate Teal (Professional)":    4,
                    "5 — Premium Gradient (Purple/Pink)":   5,
                    "6 — Midnight Ink (Black/Gold)":        6,
                    "7 — Arctic (Ice Blue/Silver)":         7,
                    "8 — Warm Slate (Charcoal/Amber)":      8,
                    "9 — Rose Gold (Blush/Copper)":         9,
                    "10 — Deep Ocean (Indigo/Cyan)":        10,
                }
                _tpl_choice_label = st.selectbox(
                    "Email Template Design",
                    list(_tpl_options.keys()),
                    key="ins_em_tpl_choice",
                )
                _em_tpl_id = _tpl_options[_tpl_choice_label]

                # ── EMAIL GENERATOR ───────────────────────────────────────────
                def _build_email():
                    _tpl = st.session_state.get("ins_em_tpl_choice", "1 — Executive Dark (Navy/Blue)")
                    _tid = _tpl_options.get(_tpl, 1)

                    # ── Shared body builder (sections) ────────────────────────
                    def _body_sections():
                        _B = ""
                        # KPI Summary
                        if em_kpis:
                            _pass_c = "#059669" if pass_rate_i>=80 else "#d97706" if pass_rate_i>=60 else "#dc2626"
                            _avg_c  = "#059669" if (_avg_i or 0)>=80 else "#d97706" if (_avg_i or 0)>=60 else "#dc2626"
                            _B += f'''<div style="margin-bottom:24px;">
<div style="font-size:11px;font-weight:800;letter-spacing:0.14em;text-transform:uppercase;color:#2563EB;margin-bottom:12px;padding-bottom:6px;border-bottom:2px solid #EBF5FF;">📊 KPI Summary</div>
<table style="width:100%;border-collapse:collapse;"><tr>
  <td style="width:16.6%;padding:0 6px 0 0;vertical-align:top;"><div style="background:#F0F4F9;border-radius:10px;padding:14px 12px;text-align:center;"><div style="font-size:24px;font-weight:900;color:#0B1F3A;">{total_i:,}</div><div style="font-size:9px;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:0.08em;margin-top:4px;">Total Audits</div></div></td>
  <td style="width:16.6%;padding:0 6px;vertical-align:top;"><div style="background:#F0F4F9;border-radius:10px;padding:14px 12px;text-align:center;"><div style="font-size:24px;font-weight:900;color:{_avg_c};">{_avg_str}</div><div style="font-size:9px;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:0.08em;margin-top:4px;">Avg Score</div></div></td>
  <td style="width:16.6%;padding:0 6px;vertical-align:top;"><div style="background:#F0F4F9;border-radius:10px;padding:14px 12px;text-align:center;"><div style="font-size:24px;font-weight:900;color:{_pass_c};">{pass_rate_i}%</div><div style="font-size:9px;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:0.08em;margin-top:4px;">Pass Rate</div></div></td>
  <td style="width:16.6%;padding:0 6px;vertical-align:top;"><div style="background:#ECFDF5;border-radius:10px;padding:14px 12px;text-align:center;"><div style="font-size:24px;font-weight:900;color:#059669;">{pass_i}</div><div style="font-size:9px;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:0.08em;margin-top:4px;">Passed</div></div></td>
  <td style="width:16.6%;padding:0 6px;vertical-align:top;"><div style="background:#FFFBEB;border-radius:10px;padding:14px 12px;text-align:center;"><div style="font-size:24px;font-weight:900;color:#d97706;">{review_i}</div><div style="font-size:9px;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:0.08em;margin-top:4px;">Review</div></div></td>
  <td style="width:16.6%;padding:0 0 0 6px;vertical-align:top;"><div style="background:#FFF1F2;border-radius:10px;padding:14px 12px;text-align:center;"><div style="font-size:24px;font-weight:900;color:#dc2626;">{fail_i+fatal_i}</div><div style="font-size:9px;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:0.08em;margin-top:4px;">Fail / Auto-Fail</div></div></td>
</tr></table></div>'''
                        # Status Distribution
                        if em_status:
                            _B += f'''<div style="margin-bottom:24px;">
<div style="font-size:11px;font-weight:800;letter-spacing:0.14em;text-transform:uppercase;color:#2563EB;margin-bottom:12px;padding-bottom:6px;border-bottom:2px solid #EBF5FF;">🟢 Status Distribution</div>
<table style="width:100%;border-collapse:collapse;font-size:13px;">'''
                            for _sn2, _sc2, _sv2 in [("✅ Pass","#059669",pass_i),("🟡 Needs Review","#d97706",review_i),("❌ Fail","#dc2626",fail_i),("🚨 Auto-Fail","#7f1d1d",fatal_i)]:
                                _sp2 = round(_sv2/total_i*100,1) if total_i else 0
                                _B += f'<tr><td style="padding:7px 0;width:140px;font-weight:600;color:#374151;">{_sn2}</td><td style="padding:7px 8px;"><div style="background:#f0f4f9;border-radius:4px;overflow:hidden;height:12px;"><div style="width:{_sp2}%;height:100%;background:{_sc2};border-radius:4px;"></div></div></td><td style="padding:7px 0 7px 8px;text-align:right;font-weight:700;color:{_sc2};white-space:nowrap;">{_sv2:,} ({_sp2}%)</td></tr>'
                            _B += '</table></div>'
                        # Disposition
                        if em_disp and "Disposition" in _audit_df_ins_view.columns:
                            _dv_em = _audit_df_ins_view["Disposition"].astype(str).str.strip()
                            _dv_em = _dv_em[~_dv_em.isin(["","nan","— select —","None"])]
                            _dc_em = _dv_em.value_counts().head(8)
                            if len(_dc_em):
                                _B += '<div style="margin-bottom:24px;"><div style="font-size:11px;font-weight:800;letter-spacing:0.14em;text-transform:uppercase;color:#2563EB;margin-bottom:12px;padding-bottom:6px;border-bottom:2px solid #EBF5FF;">🎯 Disposition Mix</div>'
                                _dcols_em = {"Interested":"#059669","Converted":"#16a34a","Warm Follow-up":"#2563EB","Not Interested":"#f59e0b","DNC":"#dc2626","Wrong Number":"#ef4444","Language Barrier":"#7c3aed","Voicemail / No Answer":"#6b7280","Other":"#aabbcc"}
                                _B += '<table style="width:100%;border-collapse:collapse;font-size:13px;">'
                                for _dn2, _dv2 in _dc_em.items():
                                    _dp2 = round(_dv2/_dc_em.sum()*100,1)
                                    _dc2 = _dcols_em.get(str(_dn2),"#5588bb")
                                    _B += f'<tr><td style="padding:6px 0;width:160px;font-weight:600;color:#374151;">{_dn2}</td><td style="padding:6px 8px;"><div style="background:#f0f4f9;border-radius:3px;overflow:hidden;height:10px;"><div style="width:{_dp2}%;height:100%;background:{_dc2};border-radius:3px;"></div></div></td><td style="padding:6px 0 6px 8px;text-align:right;font-weight:700;color:{_dc2};white-space:nowrap;">{_dv2} ({_dp2}%)</td></tr>'
                                _B += '</table></div>'
                        # What Went Right
                        if em_wr and _went_right:
                            _B += '<div style="margin-bottom:24px;"><div style="font-size:11px;font-weight:800;letter-spacing:0.14em;text-transform:uppercase;color:#059669;margin-bottom:12px;padding-bottom:6px;border-bottom:2px solid #D1FAE5;">✅ What Went Right</div>'
                            _B += '<table style="width:100%;border-collapse:collapse;font-size:13px;">'
                            for _wrpe in _went_right[:8]:
                                _B += f'<tr><td style="padding:6px 0;width:200px;font-weight:600;color:#0B1F3A;">{_wrpe["col"]}</td><td style="padding:6px 8px;"><div style="background:#D1FAE5;border-radius:4px;overflow:hidden;height:10px;"><div style="width:{_wrpe["pct"]}%;height:100%;background:linear-gradient(90deg,#059669,#34D399);border-radius:4px;"></div></div></td><td style="padding:6px 0 6px 8px;text-align:right;font-weight:800;color:#059669;white-space:nowrap;">{_wrpe["pct"]}%</td></tr>'
                            _B += '</table></div>'
                        # What Went Wrong
                        if em_ww and _went_wrong:
                            _B += '<div style="margin-bottom:24px;"><div style="font-size:11px;font-weight:800;letter-spacing:0.14em;text-transform:uppercase;color:#dc2626;margin-bottom:12px;padding-bottom:6px;border-bottom:2px solid #FEE2E2;">⚠️ What Went Wrong</div>'
                            _B += '<table style="width:100%;border-collapse:collapse;font-size:13px;">'
                            for _wwpe in _went_wrong[:8]:
                                _urgency_e = "#dc2626" if _wwpe["pct"] < 50 else "#d97706"
                                _bg_e = "#FEE2E2" if _wwpe["pct"] < 50 else "#FEF3C7"
                                _B += f'<tr><td style="padding:6px 0;width:200px;font-weight:600;color:#0B1F3A;">{_wwpe["col"]}</td><td style="padding:6px 8px;"><div style="background:{_bg_e};border-radius:4px;overflow:hidden;height:10px;"><div style="width:{_wwpe["pct"]}%;height:100%;background:{_urgency_e};border-radius:4px;"></div></div></td><td style="padding:6px 0 6px 8px;text-align:right;font-weight:800;color:{_urgency_e};white-space:nowrap;">{_wwpe["pct"]}%</td></tr>'
                            _B += '</table></div>'
                        # Top 5 Best
                        if em_best5 and not _top5_df.empty:
                            _B += '<div style="margin-bottom:24px;"><div style="font-size:11px;font-weight:800;letter-spacing:0.14em;text-transform:uppercase;color:#2563EB;margin-bottom:12px;padding-bottom:6px;border-bottom:2px solid #EBF5FF;">🏅 Top 5 Best Calls</div>'
                            _B += '<table style="width:100%;border-collapse:collapse;font-size:12px;"><thead><tr style="background:#F0F4F9;"><th style="padding:8px;text-align:left;font-weight:700;color:#0B1F3A;">Lead / ID</th><th style="padding:8px;text-align:center;font-weight:700;color:#0B1F3A;">Score</th><th style="padding:8px;text-align:left;font-weight:700;color:#0B1F3A;">Campaign</th><th style="padding:8px;text-align:left;font-weight:700;color:#0B1F3A;">QA</th><th style="padding:8px;text-align:center;font-weight:700;color:#0B1F3A;">Status</th></tr></thead><tbody>'
                            for _ri_e, (_, _row_e) in enumerate(_top5_df.iterrows()):
                                _sc_e = float(_row_e.get("_bs_num",0))
                                _ld_e = str(_row_e.get("Lead Number",_row_e.get("Phone Number",f"#{_ri_e+1}"))).strip()[:20]
                                _cm_e = str(_row_e.get("Campaign Name","—")).strip()[:25]
                                _qa_e = str(_row_e.get("QA","—")).strip()[:16]
                                _st_e = str(_row_e.get("Status","—")).strip()
                                _B += f'<tr style="border-bottom:1px solid #F0F4F9;"><td style="padding:7px 8px;font-weight:600;color:#0B1F3A;">{_ld_e}</td><td style="padding:7px 8px;text-align:center;font-weight:900;color:#059669;">{int(_sc_e)}%</td><td style="padding:7px 8px;color:#475569;">{_cm_e}</td><td style="padding:7px 8px;color:#475569;">{_qa_e}</td><td style="padding:7px 8px;text-align:center;"><span style="background:#ECFDF5;color:#059669;border-radius:4px;padding:2px 8px;font-weight:700;font-size:11px;">{_st_e}</span></td></tr>'
                            _B += '</tbody></table></div>'
                        # Top 5 Worst
                        if em_worst5 and not _worst5_df.empty:
                            _B += '<div style="margin-bottom:24px;"><div style="font-size:11px;font-weight:800;letter-spacing:0.14em;text-transform:uppercase;color:#dc2626;margin-bottom:12px;padding-bottom:6px;border-bottom:2px solid #FEE2E2;">🚨 Top 5 Worst Calls — Needs Attention</div>'
                            _B += '<table style="width:100%;border-collapse:collapse;font-size:12px;"><thead><tr style="background:#FFF1F2;"><th style="padding:8px;text-align:left;font-weight:700;color:#0B1F3A;">Lead / ID</th><th style="padding:8px;text-align:center;font-weight:700;color:#0B1F3A;">Score</th><th style="padding:8px;text-align:left;font-weight:700;color:#0B1F3A;">Campaign</th><th style="padding:8px;text-align:left;font-weight:700;color:#0B1F3A;">QA</th><th style="padding:8px;text-align:center;font-weight:700;color:#0B1F3A;">Conversation</th></tr></thead><tbody>'
                            for _wi_e, (_, _wrow_e) in enumerate(_worst5_df.iterrows()):
                                _wsc_e = float(_wrow_e.get("_bs_num",0))
                                _wld_e = str(_wrow_e.get("Lead Number",_wrow_e.get("Phone Number",f"#{_wi_e+1}"))).strip()[:20]
                                _wcm_e = str(_wrow_e.get("Campaign Name","—")).strip()[:25]
                                _wqa_e = str(_wrow_e.get("QA","—")).strip()[:16]
                                _wlnk_e = str(_wrow_e.get("Conversation Link","")).strip()
                                _wlnk_html = f'<a href="{_wlnk_e}" style="color:#2563EB;font-weight:700;font-size:11px;">🔗 View</a>' if _wlnk_e.startswith("http") else "—"
                                _B += f'<tr style="border-bottom:1px solid #FEE2E2;"><td style="padding:7px 8px;font-weight:600;color:#0B1F3A;">{_wld_e}</td><td style="padding:7px 8px;text-align:center;font-weight:900;color:#dc2626;">{int(_wsc_e)}%</td><td style="padding:7px 8px;color:#475569;">{_wcm_e}</td><td style="padding:7px 8px;color:#475569;">{_wqa_e}</td><td style="padding:7px 8px;text-align:center;">{_wlnk_html}</td></tr>'
                            _B += '</tbody></table></div>'
                        # Campaign Breakdown
                        if em_camp and _em_camp_rows:
                            _B += '<div style="margin-bottom:24px;"><div style="font-size:11px;font-weight:800;letter-spacing:0.14em;text-transform:uppercase;color:#2563EB;margin-bottom:12px;padding-bottom:6px;border-bottom:2px solid #EBF5FF;">🎯 Campaign Breakdown</div>'
                            _B += '<table style="width:100%;border-collapse:collapse;font-size:13px;"><thead><tr style="background:#F0F4F9;"><th style="padding:8px 12px;text-align:left;font-weight:700;color:#0B1F3A;">Campaign</th><th style="padding:8px;text-align:center;font-weight:700;color:#0B1F3A;">Audits</th><th style="padding:8px;text-align:center;font-weight:700;color:#0B1F3A;">Avg Score</th><th style="padding:8px;text-align:center;font-weight:700;color:#0B1F3A;">Pass Rate</th><th style="padding:8px;text-align:center;font-weight:700;color:#0B1F3A;">Fail Rate</th></tr></thead><tbody>'
                            for _cr in sorted(_em_camp_rows, key=lambda x: -x["avg"]):
                                _cc = "#059669" if _cr["avg"]>=80 else "#d97706" if _cr["avg"]>=60 else "#dc2626"
                                _B += f'<tr style="border-bottom:1px solid #F0F4F9;"><td style="padding:8px 12px;font-weight:600;color:#0B1F3A;">{_cr["name"]}</td><td style="padding:8px;text-align:center;color:#475569;">{_cr["n"]}</td><td style="padding:8px;text-align:center;font-weight:900;color:{_cc};">{_cr["avg"]}%</td><td style="padding:8px;text-align:center;color:#059669;font-weight:700;">{_cr["pass"]}%</td><td style="padding:8px;text-align:center;color:#dc2626;font-weight:700;">{_cr["fail"]}%</td></tr>'
                            _B += '</tbody></table></div>'
                        # QA Team
                        if em_qa_tbl and _em_qa_rows:
                            _B += '<div style="margin-bottom:24px;"><div style="font-size:11px;font-weight:800;letter-spacing:0.14em;text-transform:uppercase;color:#2563EB;margin-bottom:12px;padding-bottom:6px;border-bottom:2px solid #EBF5FF;">👤 QA Team Performance</div>'
                            _B += '<table style="width:100%;border-collapse:collapse;font-size:13px;"><thead><tr style="background:#F0F4F9;"><th style="padding:8px 12px;text-align:left;font-weight:700;color:#0B1F3A;">Auditor</th><th style="padding:8px;text-align:center;font-weight:700;color:#0B1F3A;">Audits</th><th style="padding:8px;text-align:center;font-weight:700;color:#0B1F3A;">Avg Score</th><th style="padding:8px;text-align:center;font-weight:700;color:#0B1F3A;">Pass Rate</th></tr></thead><tbody>'
                            for _qr in sorted(_em_qa_rows, key=lambda x: -x["avg"]):
                                _qc = "#059669" if _qr["avg"]>=80 else "#d97706" if _qr["avg"]>=60 else "#dc2626"
                                _B += f'<tr style="border-bottom:1px solid #F0F4F9;"><td style="padding:8px 12px;font-weight:600;color:#0B1F3A;">{_qr["name"]}</td><td style="padding:8px;text-align:center;color:#475569;">{_qr["n"]}</td><td style="padding:8px;text-align:center;font-weight:900;color:{_qc};">{_qr["avg"]}%</td><td style="padding:8px;text-align:center;color:#059669;font-weight:700;">{_qr["pass"]}%</td></tr>'
                            _B += '</tbody></table></div>'
                        # Parameters
                        if em_params and _em_param_rows:
                            _B += '<div style="margin-bottom:24px;"><div style="font-size:11px;font-weight:800;letter-spacing:0.14em;text-transform:uppercase;color:#2563EB;margin-bottom:12px;padding-bottom:6px;border-bottom:2px solid #EBF5FF;">🔬 Parameter Performance (Weakest First)</div>'
                            _B += '<table style="width:100%;border-collapse:collapse;font-size:12px;"><thead><tr style="background:#F0F4F9;"><th style="padding:7px 12px;text-align:left;font-weight:700;color:#0B1F3A;">Parameter</th><th style="padding:7px;text-align:left;font-weight:700;color:#0B1F3A;width:40%;">Performance</th><th style="padding:7px;text-align:right;font-weight:700;color:#0B1F3A;">Score</th></tr></thead><tbody>'
                            for _pr2 in _em_param_rows[:16]:
                                _pc2 = "#059669" if _pr2["pct"]>=80 else "#d97706" if _pr2["pct"]>=60 else "#dc2626"
                                _B += f'<tr style="border-bottom:1px solid #F0F4F9;"><td style="padding:6px 12px;font-weight:600;color:#0B1F3A;">{_pr2["col"]}</td><td style="padding:6px 8px;"><div style="background:#f0f4f9;border-radius:3px;overflow:hidden;height:10px;"><div style="width:{_pr2["pct"]}%;height:100%;background:{_pr2["color"]};border-radius:3px;"></div></div></td><td style="padding:6px 8px;text-align:right;font-weight:800;color:{_pc2};">{_pr2["pct"]}%</td></tr>'
                            _B += '</tbody></table></div>'
                        # Custom Parameters Dashboard
                        if em_custom_ps and _em_custom_rows:
                            _B += '<div style="margin-bottom:24px;"><div style="font-size:11px;font-weight:800;letter-spacing:0.14em;text-transform:uppercase;color:#0ebc6e;margin-bottom:12px;padding-bottom:6px;border-bottom:2px solid #D1FAE5;">⭐ Custom Parameters</div>'
                            _B += '<table style="width:100%;border-collapse:collapse;" cellpadding="0" cellspacing="0"><tr>'
                            _cols_per_row = 3
                            for _eci, _ecp in enumerate(_em_custom_rows):
                                if _eci > 0 and _eci % _cols_per_row == 0:
                                    _B += '</tr><tr>'
                                _yes_w = _ecp["yes_pct"]
                                _no_w  = _ecp["no_pct"]
                                _na_w  = max(0, 100 - _yes_w - _no_w)
                                _health_c = "#059669" if _ecp["yes_pct"] >= 70 else "#d97706" if _ecp["yes_pct"] >= 50 else "#dc2626"
                                _B += (
                                    f'<td style="padding:4px;width:33%;vertical-align:top;">'
                                    f'<div style="background:#f8fffe;border:1px solid #a7f3d0;border-radius:10px;padding:12px 10px;">'
                                    f'<div style="font-size:10px;font-weight:800;color:#065f46;letter-spacing:0.05em;text-transform:uppercase;margin-bottom:8px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{_ecp["name"]}</div>'
                                    f'<div style="display:flex;gap:4px;margin-bottom:8px;">'
                                    f'<div style="flex:1;background:#ecfdf5;border-radius:6px;padding:6px 4px;text-align:center;">'
                                    f'<div style="font-size:18px;font-weight:900;color:#059669;line-height:1;">{_ecp["yes"]}</div>'
                                    f'<div style="font-size:9px;font-weight:700;color:#059669;margin-top:2px;">YES</div>'
                                    f'<div style="font-size:9px;color:#64748b;">{_ecp["yes_pct"]}%</div>'
                                    f'</div>'
                                    f'<div style="flex:1;background:#fef2f2;border-radius:6px;padding:6px 4px;text-align:center;">'
                                    f'<div style="font-size:18px;font-weight:900;color:#dc2626;line-height:1;">{_ecp["no"]}</div>'
                                    f'<div style="font-size:9px;font-weight:700;color:#dc2626;margin-top:2px;">NO</div>'
                                    f'<div style="font-size:9px;color:#64748b;">{_ecp["no_pct"]}%</div>'
                                    f'</div>'
                                    f'<div style="flex:1;background:#f8fafc;border-radius:6px;padding:6px 4px;text-align:center;">'
                                    f'<div style="font-size:18px;font-weight:900;color:#94a3b8;line-height:1;">{_ecp["na"]}</div>'
                                    f'<div style="font-size:9px;font-weight:700;color:#94a3b8;margin-top:2px;">NA</div>'
                                    f'<div style="font-size:9px;color:#64748b;">&nbsp;</div>'
                                    f'</div>'
                                    f'</div>'
                                    f'<div style="height:5px;background:#e2e8f0;border-radius:3px;overflow:hidden;display:flex;">'
                                    f'<div style="width:{_yes_w}%;background:#059669;"></div>'
                                    f'<div style="width:{_no_w}%;background:#dc2626;"></div>'
                                    f'<div style="width:{_na_w}%;background:#cbd5e1;"></div>'
                                    f'</div>'
                                    f'<div style="font-size:9px;color:#64748b;margin-top:5px;text-align:right;">{_ecp["tot"]} resp · {_ecp["cmts"]} cmts</div>'
                                    f'</div></td>'
                                )
                            # pad remaining cells if row is incomplete
                            _rem = _cols_per_row - (len(_em_custom_rows) % _cols_per_row)
                            if _rem < _cols_per_row:
                                for _ in range(_rem):
                                    _B += '<td style="padding:4px;width:33%;"></td>'
                            _B += '</tr></table>'
                            # ── Key Insights for custom params ──────────────
                            if len(_em_custom_rows) >= 1:
                                _cp_sorted_fail = sorted(_em_custom_rows, key=lambda x: x["yes_pct"])
                                _cp_sorted_pass = sorted(_em_custom_rows, key=lambda x: -x["yes_pct"])
                                _cp_total_calls  = max(_em_custom_rows[0]["tot"], 1)
                                _cp_overall_yes  = round(sum(r["yes"] for r in _em_custom_rows) / max(sum(r["tot"] for r in _em_custom_rows), 1) * 100, 1)
                                _cp_health_c = "#059669" if _cp_overall_yes >= 70 else "#d97706" if _cp_overall_yes >= 50 else "#dc2626"
                                _cp_health_l = "High Adherence" if _cp_overall_yes >= 70 else "Partial Adherence" if _cp_overall_yes >= 50 else "Low Adherence — Action Required"
                                _B += f'<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;padding:14px 16px;margin-top:10px;">'
                                _B += f'<div style="font-size:10px;font-weight:800;letter-spacing:0.1em;text-transform:uppercase;color:#059669;margin-bottom:10px;">📌 Call Action Adherence — Key Insights</div>'
                                # Overall line
                                _B += (f'<div style="font-size:12px;color:#0B1F3A;margin-bottom:12px;line-height:1.6;">'
                                       f'Across <strong>{_cp_total_calls:,} calls</strong>, agents completed custom call actions at an average rate of '
                                       f'<strong style="color:{_cp_health_c};">{_cp_overall_yes}%</strong> — '
                                       f'<span style="color:{_cp_health_c};font-weight:700;">{_cp_health_l}</span>.</div>')
                                # Skipped / not done
                                _cp_fail = [r for r in _cp_sorted_fail if r["yes_pct"] < 70][:3]
                                if _cp_fail:
                                    _B += '<div style="font-size:11px;font-weight:700;color:#dc2626;margin-bottom:6px;">🔴 Not Done / Skipped Most Often</div>'
                                    for _cpf in _cp_fail:
                                        _cpf_c  = "#dc2626" if _cpf["yes_pct"] < 50 else "#d97706"
                                        _skip_n = _cpf["no"] + _cpf["na"]
                                        _B += (f'<div style="background:#fff;border:1px solid #fecaca;border-radius:8px;padding:8px 12px;margin-bottom:6px;">'
                                               f'<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:5px;">'
                                               f'<div style="font-size:12px;font-weight:700;color:#0B1F3A;">{_cpf["name"]}</div>'
                                               f'<span style="font-size:10px;font-weight:800;color:#fff;background:{_cpf_c};padding:2px 8px;border-radius:10px;">{_cpf["yes_pct"]}% Done</span>'
                                               f'</div>'
                                               f'<div style="background:#fee2e2;border-radius:3px;height:7px;overflow:hidden;margin-bottom:5px;">'
                                               f'<div style="width:{_cpf["yes_pct"]}%;height:100%;background:{_cpf_c};"></div></div>'
                                               f'<div style="font-size:11px;color:#64748b;">'
                                               f'<strong style="color:#dc2626;">{_skip_n} calls</strong> did not complete this action '
                                               f'({round(_skip_n/_cpf["tot"]*100,1) if _cpf["tot"] else 0}% skip rate)</div>'
                                               f'</div>')
                                # Completed consistently
                                _cp_pass = [r for r in _cp_sorted_pass if r["yes_pct"] >= 70][:2]
                                if _cp_pass:
                                    _B += '<div style="font-size:11px;font-weight:700;color:#059669;margin-top:8px;margin-bottom:6px;">🟢 Completed Consistently</div>'
                                    for _cpp in _cp_pass:
                                        _B += (f'<div style="background:#fff;border:1px solid #bbf7d0;border-radius:8px;padding:8px 12px;margin-bottom:6px;">'
                                               f'<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:5px;">'
                                               f'<div style="font-size:12px;font-weight:700;color:#0B1F3A;">{_cpp["name"]}</div>'
                                               f'<span style="font-size:10px;font-weight:800;color:#fff;background:#059669;padding:2px 8px;border-radius:10px;">{_cpp["yes_pct"]}% Done</span>'
                                               f'</div>'
                                               f'<div style="background:#dcfce7;border-radius:3px;height:7px;overflow:hidden;margin-bottom:5px;">'
                                               f'<div style="width:{_cpp["yes_pct"]}%;height:100%;background:#059669;"></div></div>'
                                               f'<div style="font-size:11px;color:#64748b;">'
                                               f'<strong style="color:#059669;">{_cpp["yes"]} of {_cpp["tot"]} calls</strong> had this action completed</div>'
                                               f'</div>')
                                _B += '</div>'
                            _B += '</div>'
                        # Remarks Summary (AI)
                        _rm_data = st.session_state.get(_remarks_key)
                        if em_remarks and _rm_data:
                            _B += '<div style="margin-bottom:24px;"><div style="font-size:11px;font-weight:800;letter-spacing:0.14em;text-transform:uppercase;color:#7c3aed;margin-bottom:12px;padding-bottom:6px;border-bottom:2px solid #ede9fe;">💬 Remarks Summary</div>'
                            # Overall summary
                            if _rm_data.get("summary"):
                                _B += f'<div style="background:#f5f3ff;border-left:4px solid #7c3aed;border-radius:0 8px 8px 0;padding:12px 16px;margin-bottom:14px;font-size:13px;color:#3b0764;line-height:1.65;">{_rm_data["summary"]}</div>'
                            # Three columns: positive / concerns / suggestions
                            _B += '<table style="width:100%;border-collapse:collapse;" cellpadding="0" cellspacing="8"><tr style="vertical-align:top;">'
                            # Positive
                            _pos = _rm_data.get("positive") or []
                            _B += '<td style="width:33%;padding:0 6px 0 0;vertical-align:top;">'
                            _B += '<div style="background:#ecfdf5;border-radius:8px;padding:12px;">'
                            _B += '<div style="font-size:10px;font-weight:800;color:#059669;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:8px;">✅ Positive</div>'
                            for _pi in _pos:
                                _B += f'<div style="font-size:12px;color:#065f46;line-height:1.55;margin-bottom:5px;padding-left:10px;border-left:2px solid #6ee7b7;">• {_pi}</div>'
                            if not _pos: _B += '<div style="font-size:11px;color:#94a3b8;">—</div>'
                            _B += '</div></td>'
                            # Concerns
                            _con = _rm_data.get("concerns") or []
                            _B += '<td style="width:33%;padding:0 3px;vertical-align:top;">'
                            _B += '<div style="background:#fff1f2;border-radius:8px;padding:12px;">'
                            _B += '<div style="font-size:10px;font-weight:800;color:#dc2626;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:8px;">⚠️ Concerns</div>'
                            for _ci in _con:
                                _B += f'<div style="font-size:12px;color:#7f1d1d;line-height:1.55;margin-bottom:5px;padding-left:10px;border-left:2px solid #fca5a5;">• {_ci}</div>'
                            if not _con: _B += '<div style="font-size:11px;color:#94a3b8;">—</div>'
                            _B += '</div></td>'
                            # Suggestions
                            _sug = _rm_data.get("suggestions") or []
                            _B += '<td style="width:33%;padding:0 0 0 6px;vertical-align:top;">'
                            _B += '<div style="background:#eff6ff;border-radius:8px;padding:12px;">'
                            _B += '<div style="font-size:10px;font-weight:800;color:#2563EB;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:8px;">💡 Suggestions</div>'
                            for _si in _sug:
                                _B += f'<div style="font-size:12px;color:#1e3a5f;line-height:1.55;margin-bottom:5px;padding-left:10px;border-left:2px solid #93c5fd;">• {_si}</div>'
                            if not _sug: _B += '<div style="font-size:11px;color:#94a3b8;">—</div>'
                            _B += '</div></td>'
                            _B += '</tr></table></div>'
                        # Key Insights
                        _sel_ins_list = [ins for i, ins in enumerate(_sorted_ins) if _em_ins_sel.get(i, True)]
                        if _sel_ins_list:
                            _type_icon_em = {"critical":"🚨","warning":"⚠️","success":"✅","info":"ℹ️"}
                            _type_bg_em   = {"critical":"#FFF1F2","warning":"#FFFBEB","success":"#ECFDF5","info":"#EBF5FF"}
                            _type_bc_em   = {"critical":"#dc2626","warning":"#D97706","success":"#059669","info":"#2563EB"}
                            _type_tc_em   = {"critical":"#7F1D1D","warning":"#78350F","success":"#064E3B","info":"#0B1F3A"}
                            _B += '<div style="margin-bottom:24px;"><div style="font-size:11px;font-weight:800;letter-spacing:0.14em;text-transform:uppercase;color:#2563EB;margin-bottom:12px;padding-bottom:6px;border-bottom:2px solid #EBF5FF;">💡 Key Insights</div>'
                            for _ins_e in _sel_ins_list:
                                _t = _ins_e.get("type","info")
                                _B += f'<div style="background:{_type_bg_em.get(_t,"#EBF5FF")};border-left:4px solid {_type_bc_em.get(_t,"#2563EB")};border-radius:0 8px 8px 0;padding:12px 16px;margin-bottom:10px;">'
                                _B += f'<div style="font-size:13px;font-weight:800;color:{_type_tc_em.get(_t,"#0B1F3A")};margin-bottom:5px;">{_type_icon_em.get(_t,"ℹ️")} {_ins_e["title"]}</div>'
                                _B += f'<div style="font-size:12px;color:{_type_tc_em.get(_t,"#374151")};line-height:1.6;">{_ins_e.get("detail","")}</div>'
                                _B += '</div>'
                            _B += '</div>'
                        # Priority Actions
                        _sel_act_list = [act for i, act in enumerate(_sorted_acts) if _em_act_sel.get(i, True)]
                        if _sel_act_list:
                            _pri_bg_em = {"high":"#FFF1F2","medium":"#FFFBEB","low":"#ECFDF5"}
                            _pri_bc_em = {"high":"#dc2626","medium":"#D97706","low":"#059669"}
                            _pri_lbl_em = {"high":"🔴 HIGH","medium":"🟡 MEDIUM","low":"🟢 LOW"}
                            _B += '<div style="margin-bottom:24px;"><div style="font-size:11px;font-weight:800;letter-spacing:0.14em;text-transform:uppercase;color:#2563EB;margin-bottom:12px;padding-bottom:6px;border-bottom:2px solid #EBF5FF;">🎯 Priority Actions</div>'
                            for _ai_e, _act_e in enumerate(_sel_act_list, 1):
                                _p = _act_e.get("priority","low")
                                _B += f'<div style="background:{_pri_bg_em.get(_p,"#ECFDF5")};border-left:4px solid {_pri_bc_em.get(_p,"#059669")};border-radius:0 8px 8px 0;padding:12px 16px;margin-bottom:10px;">'
                                _B += f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;"><span style="font-size:10px;font-weight:800;letter-spacing:0.1em;text-transform:uppercase;color:#fff;background:{_pri_bc_em.get(_p,"#059669")};padding:2px 9px;border-radius:10px;">#{_ai_e} · {_pri_lbl_em.get(_p,"")} · {_act_e.get("category","")}</span></div>'
                                _B += f'<div style="font-size:13px;font-weight:700;color:#0B1F3A;margin-bottom:5px;line-height:1.5;">{_act_e["action"]}</div>'
                                _B += f'<div style="font-size:11px;color:#64748b;line-height:1.5;border-top:1px solid rgba(0,0,0,0.06);padding-top:5px;">💥 Impact: {_act_e.get("impact","")}</div>'
                                _B += '</div>'
                            _B += '</div>'
                        return _B

                    _content = _body_sections()
                    _meta_row = f'📅 {_now_str} &nbsp;·&nbsp; 🏢 {_cli_label} &nbsp;·&nbsp; 🎯 {_camp_label} &nbsp;·&nbsp; 🤖 {_bot_label}'
                    _footer = (f'<div style="border-top:1px solid #E2EAF6;margin-top:16px;padding-top:16px;text-align:center;">'
                               f'<div style="font-size:11px;color:#94a3b8;line-height:1.7;">'
                               f'Auto-generated by <strong style="color:#2563EB;">Convin Sense Audit</strong> · Auto QA Data Insights<br>'
                               f'Report Date: {_now_str} &nbsp;·&nbsp; Client: {_cli_label} &nbsp;·&nbsp; Campaign: {_camp_label} &nbsp;·&nbsp; Bot: {_bot_label}'
                               f'</div></div>')

                    # ── Template 1: Executive Dark (Navy/Blue) ────────────────
                    if _tid == 1:
                        _S = '<div style="font-family:\'Segoe UI\',Arial,sans-serif;max-width:660px;margin:0 auto;background:#f0f4f9;padding:0;">'
                        _S += f'''<div style="background:linear-gradient(135deg,#0B1F3A 0%,#1D4ED8 100%);border-radius:16px 16px 0 0;padding:32px 36px 28px;">
  <div style="font-size:10px;font-weight:800;letter-spacing:0.18em;text-transform:uppercase;color:rgba(255,255,255,0.55);margin-bottom:6px;">CONVIN SENSE AUDIT &nbsp;·&nbsp; AUTO QA DATA INSIGHTS</div>
  <div style="font-size:26px;font-weight:900;color:#fff;line-height:1.15;margin-bottom:6px;">Convin Sense Audit Report</div>
  <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:14px;">
    <span style="background:rgba(255,255,255,0.12);border-radius:20px;padding:4px 12px;font-size:11px;color:rgba(255,255,255,0.9);">📅 {_now_str}</span>
    <span style="background:rgba(255,255,255,0.12);border-radius:20px;padding:4px 12px;font-size:11px;color:rgba(255,255,255,0.9);">🏢 {_cli_label}</span>
    <span style="background:rgba(255,255,255,0.12);border-radius:20px;padding:4px 12px;font-size:11px;color:rgba(255,255,255,0.9);">🎯 {_camp_label}</span>
    <span style="background:rgba(255,255,255,0.12);border-radius:20px;padding:4px 12px;font-size:11px;color:rgba(255,255,255,0.9);">🤖 {_bot_label}</span>
  </div>
</div>'''
                        _S += f'<div style="background:#fff;border-radius:0 0 16px 16px;padding:28px 36px;">{_content}{_footer}</div></div>'
                        return _S

                    # ── Template 2: Minimal White ────────────────────────────
                    elif _tid == 2:
                        _S = '<div style="font-family:\'Helvetica Neue\',Arial,sans-serif;max-width:660px;margin:0 auto;background:#ffffff;border:1px solid #e8ecf0;border-radius:12px;overflow:hidden;">'
                        _S += f'''<div style="padding:32px 40px 24px;border-bottom:3px solid #2563EB;">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;">
    <div style="width:6px;height:40px;background:#2563EB;border-radius:3px;"></div>
    <div>
      <div style="font-size:9px;font-weight:800;letter-spacing:0.2em;text-transform:uppercase;color:#94a3b8;margin-bottom:3px;">CONVIN SENSE AUDIT</div>
      <div style="font-size:24px;font-weight:800;color:#0B1F3A;line-height:1.2;">Convin Sense Audit Report</div>
    </div>
  </div>
  <div style="display:flex;gap:8px;flex-wrap:wrap;">
    <span style="border:1px solid #e2e8f0;border-radius:6px;padding:4px 10px;font-size:11px;color:#475569;">📅 {_now_str}</span>
    <span style="border:1px solid #dbeafe;background:#eff6ff;border-radius:6px;padding:4px 10px;font-size:11px;color:#2563EB;font-weight:600;">🏢 {_cli_label}</span>
    <span style="border:1px solid #dbeafe;background:#eff6ff;border-radius:6px;padding:4px 10px;font-size:11px;color:#2563EB;font-weight:600;">🎯 {_camp_label}</span>
    <span style="border:1px solid #dbeafe;background:#eff6ff;border-radius:6px;padding:4px 10px;font-size:11px;color:#2563EB;font-weight:600;">🤖 {_bot_label}</span>
  </div>
</div>'''
                        _S += f'<div style="padding:28px 40px;">{_content}{_footer}</div></div>'
                        return _S

                    # ── Template 3: Bold Red / Alert ─────────────────────────
                    elif _tid == 3:
                        _S = '<div style="font-family:\'Segoe UI\',Arial,sans-serif;max-width:660px;margin:0 auto;background:#fff5f5;border-radius:14px;overflow:hidden;border:1px solid #fecaca;">'
                        _S += f'''<div style="background:linear-gradient(135deg,#7f1d1d 0%,#dc2626 60%,#ef4444 100%);padding:30px 36px 26px;">
  <div style="font-size:9px;font-weight:800;letter-spacing:0.22em;text-transform:uppercase;color:rgba(255,255,255,0.6);margin-bottom:8px;">&#9888; CONVIN SENSE AUDIT &nbsp;·&nbsp; QA PERFORMANCE ALERT</div>
  <div style="font-size:26px;font-weight:900;color:#fff;line-height:1.15;margin-bottom:4px;">Convin Sense Audit Report</div>
  <div style="font-size:12px;color:rgba(255,255,255,0.7);margin-bottom:14px;">Performance review requiring attention</div>
  <div style="display:flex;gap:8px;flex-wrap:wrap;">
    <span style="background:rgba(0,0,0,0.25);border-radius:20px;padding:4px 12px;font-size:11px;color:#fff;">📅 {_now_str}</span>
    <span style="background:rgba(0,0,0,0.25);border-radius:20px;padding:4px 12px;font-size:11px;color:#fff;">🏢 {_cli_label}</span>
    <span style="background:rgba(0,0,0,0.25);border-radius:20px;padding:4px 12px;font-size:11px;color:#fff;">🎯 {_camp_label}</span>
    <span style="background:rgba(0,0,0,0.25);border-radius:20px;padding:4px 12px;font-size:11px;color:#fff;">🤖 {_bot_label}</span>
  </div>
</div>'''
                        _S += f'<div style="padding:28px 36px;background:#fff;">{_content}{_footer}</div></div>'
                        return _S

                    # ── Template 4: Corporate Teal ───────────────────────────
                    elif _tid == 4:
                        _S = '<div style="font-family:Georgia,\'Times New Roman\',serif;max-width:660px;margin:0 auto;background:#f0fdf4;border-radius:14px;overflow:hidden;">'
                        _S += f'''<div style="background:linear-gradient(135deg,#064e3b 0%,#059669 70%,#10b981 100%);padding:32px 40px 28px;">
  <div style="font-size:9px;font-weight:800;letter-spacing:0.22em;text-transform:uppercase;color:rgba(255,255,255,0.55);margin-bottom:8px;font-family:Arial,sans-serif;">CONVIN SENSE AUDIT &nbsp;·&nbsp; PROFESSIONAL QA REPORT</div>
  <div style="font-size:27px;font-weight:700;color:#fff;line-height:1.2;margin-bottom:4px;">Convin Sense Audit Report</div>
  <div style="width:48px;height:3px;background:rgba(255,255,255,0.5);border-radius:2px;margin:10px 0 14px;"></div>
  <div style="display:flex;gap:8px;flex-wrap:wrap;font-family:Arial,sans-serif;">
    <span style="background:rgba(255,255,255,0.15);border-radius:4px;padding:4px 10px;font-size:11px;color:rgba(255,255,255,0.9);">📅 {_now_str}</span>
    <span style="background:rgba(255,255,255,0.15);border-radius:4px;padding:4px 10px;font-size:11px;color:rgba(255,255,255,0.9);">🏢 {_cli_label}</span>
    <span style="background:rgba(255,255,255,0.15);border-radius:4px;padding:4px 10px;font-size:11px;color:rgba(255,255,255,0.9);">🎯 {_camp_label}</span>
    <span style="background:rgba(255,255,255,0.15);border-radius:4px;padding:4px 10px;font-size:11px;color:rgba(255,255,255,0.9);">🤖 {_bot_label}</span>
  </div>
</div>'''
                        _S += f'<div style="padding:28px 40px;background:#fff;font-family:Arial,sans-serif;">{_content}{_footer}</div></div>'
                        return _S

                    # ── Template 5: Premium Gradient (Purple/Pink) ───────────
                    elif _tid == 5:
                        _S = '<div style="font-family:\'Segoe UI\',Arial,sans-serif;max-width:660px;margin:0 auto;background:#faf5ff;border-radius:16px;overflow:hidden;box-shadow:0 8px 40px rgba(109,40,217,0.12);">'
                        _S += f'''<div style="background:linear-gradient(135deg,#4c1d95 0%,#7c3aed 45%,#db2777 100%);padding:34px 40px 30px;position:relative;">
  <div style="font-size:9px;font-weight:800;letter-spacing:0.22em;text-transform:uppercase;color:rgba(255,255,255,0.55);margin-bottom:8px;">✦ CONVIN SENSE AUDIT &nbsp;·&nbsp; PREMIUM ANALYTICS</div>
  <div style="font-size:28px;font-weight:900;color:#fff;line-height:1.15;margin-bottom:4px;letter-spacing:-0.01em;">Convin Sense Audit Report</div>
  <div style="font-size:12px;color:rgba(255,255,255,0.65);margin-bottom:14px;">Powered by Convin Sense Intelligence</div>
  <div style="display:flex;gap:8px;flex-wrap:wrap;">
    <span style="background:rgba(255,255,255,0.15);backdrop-filter:blur(4px);border:1px solid rgba(255,255,255,0.2);border-radius:20px;padding:4px 12px;font-size:11px;color:#fff;">📅 {_now_str}</span>
    <span style="background:rgba(255,255,255,0.15);backdrop-filter:blur(4px);border:1px solid rgba(255,255,255,0.2);border-radius:20px;padding:4px 12px;font-size:11px;color:#fff;">🏢 {_cli_label}</span>
    <span style="background:rgba(255,255,255,0.15);backdrop-filter:blur(4px);border:1px solid rgba(255,255,255,0.2);border-radius:20px;padding:4px 12px;font-size:11px;color:#fff;">🎯 {_camp_label}</span>
    <span style="background:rgba(255,255,255,0.15);backdrop-filter:blur(4px);border:1px solid rgba(255,255,255,0.2);border-radius:20px;padding:4px 12px;font-size:11px;color:#fff;">🤖 {_bot_label}</span>
  </div>
</div>'''
                        _S += f'<div style="padding:28px 40px;background:#fff;">{_content}{_footer}</div></div>'
                        return _S

                    # ── Template 6: Midnight Ink (Black/Gold) ────────────────
                    if _tid == 6:
                        _S = '<div style="font-family:\'Segoe UI\',Arial,sans-serif;max-width:660px;margin:0 auto;background:#0a0a0a;border-radius:16px;overflow:hidden;">'
                        _S += f'''<div style="background:#0a0a0a;border-top:3px solid #c9a84c;padding:34px 40px 28px;">
  <div style="font-size:9px;font-weight:800;letter-spacing:0.25em;text-transform:uppercase;color:#c9a84c;margin-bottom:10px;">✦ CONVIN SENSE AUDIT &nbsp;·&nbsp; EXECUTIVE QA REPORT</div>
  <div style="font-size:28px;font-weight:900;color:#f5f0e8;line-height:1.15;letter-spacing:-0.01em;margin-bottom:4px;">Convin Sense Audit Report</div>
  <div style="width:40px;height:2px;background:#c9a84c;border-radius:1px;margin:10px 0 14px;"></div>
  <div style="display:flex;gap:8px;flex-wrap:wrap;">
    <span style="border:1px solid #c9a84c33;background:#c9a84c15;border-radius:4px;padding:4px 10px;font-size:11px;color:#c9a84c;">📅 {_now_str}</span>
    <span style="border:1px solid #c9a84c33;background:#c9a84c15;border-radius:4px;padding:4px 10px;font-size:11px;color:#c9a84c;">🏢 {_cli_label}</span>
    <span style="border:1px solid #c9a84c33;background:#c9a84c15;border-radius:4px;padding:4px 10px;font-size:11px;color:#c9a84c;">🎯 {_camp_label}</span>
    <span style="border:1px solid #c9a84c33;background:#c9a84c15;border-radius:4px;padding:4px 10px;font-size:11px;color:#c9a84c;">🤖 {_bot_label}</span>
  </div>
</div>'''
                        _dark_footer = (f'<div style="border-top:1px solid #2a2a2a;margin-top:16px;padding-top:16px;text-align:center;">'
                                        f'<div style="font-size:11px;color:#666;line-height:1.7;">'
                                        f'Auto-generated by <strong style="color:#c9a84c;">Convin Sense Audit</strong> · Auto QA Data Insights<br>'
                                        f'Report Date: {_now_str} &nbsp;·&nbsp; Client: {_cli_label} &nbsp;·&nbsp; Campaign: {_camp_label} &nbsp;·&nbsp; Bot: {_bot_label}'
                                        f'</div></div>')
                        _S += f'<div style="padding:28px 40px;background:#111111;">{_content}{_dark_footer}</div></div>'
                        return _S

                    # ── Template 7: Arctic (Ice Blue/Silver) ─────────────────
                    elif _tid == 7:
                        _S = '<div style="font-family:\'Segoe UI\',Arial,sans-serif;max-width:660px;margin:0 auto;background:#f0f7ff;border-radius:16px;overflow:hidden;border:1px solid #bfdbfe;">'
                        _S += f'''<div style="background:linear-gradient(135deg,#dbeafe 0%,#e0f2fe 50%,#f0f9ff 100%);padding:32px 40px 26px;border-bottom:1px solid #bfdbfe;">
  <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:16px;">
    <div>
      <div style="font-size:9px;font-weight:800;letter-spacing:0.22em;text-transform:uppercase;color:#0369a1;margin-bottom:8px;">CONVIN SENSE AUDIT &nbsp;·&nbsp; QA INTELLIGENCE</div>
      <div style="font-size:27px;font-weight:800;color:#0c2d5e;line-height:1.15;letter-spacing:-0.02em;">Convin Sense<br>Audit Report</div>
    </div>
    <div style="text-align:right;flex-shrink:0;">
      <div style="background:#0369a1;color:#fff;border-radius:8px;padding:6px 14px;font-size:10px;font-weight:700;letter-spacing:0.05em;text-transform:uppercase;">QA Report</div>
      <div style="font-size:10px;color:#0369a1;margin-top:6px;font-weight:600;">{_now_str}</div>
    </div>
  </div>
  <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:16px;">
    <span style="background:#fff;border:1px solid #93c5fd;border-radius:20px;padding:4px 11px;font-size:11px;color:#1e40af;font-weight:600;">🏢 {_cli_label}</span>
    <span style="background:#fff;border:1px solid #93c5fd;border-radius:20px;padding:4px 11px;font-size:11px;color:#1e40af;font-weight:600;">🎯 {_camp_label}</span>
    <span style="background:#fff;border:1px solid #93c5fd;border-radius:20px;padding:4px 11px;font-size:11px;color:#1e40af;font-weight:600;">🤖 {_bot_label}</span>
  </div>
</div>'''
                        _S += f'<div style="padding:28px 40px;background:#fff;">{_content}{_footer}</div></div>'
                        return _S

                    # ── Template 8: Warm Slate (Charcoal/Amber) ──────────────
                    elif _tid == 8:
                        _S = '<div style="font-family:Georgia,\'Times New Roman\',serif;max-width:660px;margin:0 auto;background:#fafaf9;border-radius:14px;overflow:hidden;border:1px solid #e7e5e4;">'
                        _S += f'''<div style="background:linear-gradient(160deg,#292524 0%,#44403c 100%);padding:34px 40px 28px;">
  <div style="font-size:9px;font-weight:700;letter-spacing:0.22em;text-transform:uppercase;color:#fbbf24;margin-bottom:10px;font-family:Arial,sans-serif;">CONVIN SENSE AUDIT &nbsp;·&nbsp; PERFORMANCE REVIEW</div>
  <div style="font-size:28px;font-weight:700;color:#fafaf9;line-height:1.2;margin-bottom:4px;">Convin Sense Audit Report</div>
  <div style="font-size:12px;color:#a8a29e;font-style:italic;margin-bottom:14px;font-family:Arial,sans-serif;">Thoughtful QA analysis, delivered clearly.</div>
  <div style="display:flex;gap:8px;flex-wrap:wrap;font-family:Arial,sans-serif;">
    <span style="background:#57534e;border-radius:4px;padding:4px 10px;font-size:11px;color:#e7e5e4;">📅 {_now_str}</span>
    <span style="background:#57534e;border-radius:4px;padding:4px 10px;font-size:11px;color:#e7e5e4;">🏢 {_cli_label}</span>
    <span style="background:#57534e;border-radius:4px;padding:4px 10px;font-size:11px;color:#e7e5e4;">🎯 {_camp_label}</span>
    <span style="background:#57534e;border-radius:4px;padding:4px 10px;font-size:11px;color:#e7e5e4;">🤖 {_bot_label}</span>
  </div>
</div>'''
                        _S += f'<div style="padding:28px 40px;background:#fff;font-family:Arial,sans-serif;">{_content}{_footer}</div></div>'
                        return _S

                    # ── Template 9: Rose Gold (Blush/Copper) ─────────────────
                    elif _tid == 9:
                        _S = '<div style="font-family:\'Segoe UI\',Arial,sans-serif;max-width:660px;margin:0 auto;background:#fff9f7;border-radius:16px;overflow:hidden;border:1px solid #fcd5c0;">'
                        _S += f'''<div style="background:linear-gradient(135deg,#881337 0%,#be123c 40%,#c2410c 75%,#b45309 100%);padding:32px 40px 28px;">
  <div style="font-size:9px;font-weight:800;letter-spacing:0.22em;text-transform:uppercase;color:rgba(255,220,200,0.75);margin-bottom:8px;">✦ CONVIN SENSE AUDIT &nbsp;·&nbsp; QA EXCELLENCE</div>
  <div style="font-size:27px;font-weight:900;color:#fff;line-height:1.15;letter-spacing:-0.01em;margin-bottom:4px;">Convin Sense Audit Report</div>
  <div style="font-size:12px;color:rgba(255,220,200,0.7);margin-bottom:14px;">Performance insights crafted with precision</div>
  <div style="display:flex;gap:8px;flex-wrap:wrap;">
    <span style="background:rgba(255,255,255,0.18);border:1px solid rgba(255,255,255,0.3);border-radius:20px;padding:4px 12px;font-size:11px;color:#fff;">📅 {_now_str}</span>
    <span style="background:rgba(255,255,255,0.18);border:1px solid rgba(255,255,255,0.3);border-radius:20px;padding:4px 12px;font-size:11px;color:#fff;">🏢 {_cli_label}</span>
    <span style="background:rgba(255,255,255,0.18);border:1px solid rgba(255,255,255,0.3);border-radius:20px;padding:4px 12px;font-size:11px;color:#fff;">🎯 {_camp_label}</span>
    <span style="background:rgba(255,255,255,0.18);border:1px solid rgba(255,255,255,0.3);border-radius:20px;padding:4px 12px;font-size:11px;color:#fff;">🤖 {_bot_label}</span>
  </div>
</div>'''
                        _S += f'<div style="padding:28px 40px;background:#fff;">{_content}{_footer}</div></div>'
                        return _S

                    # ── Template 10: Deep Ocean (Indigo/Cyan) ────────────────
                    else:
                        _S = '<div style="font-family:\'Segoe UI\',Arial,sans-serif;max-width:660px;margin:0 auto;background:#f0fdfa;border-radius:16px;overflow:hidden;">'
                        _S += f'''<div style="background:linear-gradient(135deg,#0f172a 0%,#1e3a5f 40%,#0e7490 80%,#06b6d4 100%);padding:32px 40px 28px;">
  <div style="font-size:9px;font-weight:800;letter-spacing:0.22em;text-transform:uppercase;color:rgba(103,232,249,0.75);margin-bottom:8px;">◈ CONVIN SENSE AUDIT &nbsp;·&nbsp; DEEP ANALYTICS</div>
  <div style="font-size:28px;font-weight:900;color:#fff;line-height:1.15;letter-spacing:-0.01em;margin-bottom:4px;">Convin Sense Audit Report</div>
  <div style="font-size:12px;color:rgba(186,230,253,0.8);margin-bottom:14px;">Powered by Convin Sense Intelligence Engine</div>
  <div style="display:flex;gap:8px;flex-wrap:wrap;">
    <span style="background:rgba(6,182,212,0.2);border:1px solid rgba(6,182,212,0.4);border-radius:20px;padding:4px 12px;font-size:11px;color:#a5f3fc;">📅 {_now_str}</span>
    <span style="background:rgba(6,182,212,0.2);border:1px solid rgba(6,182,212,0.4);border-radius:20px;padding:4px 12px;font-size:11px;color:#a5f3fc;">🏢 {_cli_label}</span>
    <span style="background:rgba(6,182,212,0.2);border:1px solid rgba(6,182,212,0.4);border-radius:20px;padding:4px 12px;font-size:11px;color:#a5f3fc;">🎯 {_camp_label}</span>
    <span style="background:rgba(6,182,212,0.2);border:1px solid rgba(6,182,212,0.4);border-radius:20px;padding:4px 12px;font-size:11px;color:#a5f3fc;">🤖 {_bot_label}</span>
  </div>
</div>'''
                        _S += f'<div style="padding:28px 40px;background:#fff;">{_content}{_footer}</div></div>'
                        return _S

                # ── PREVIEW ───────────────────────────────────────────────────
                _gen_col, _prev_col = st.columns([1, 1])
                with _gen_col:
                    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                    _do_preview = st.button("👁 Generate & Preview Draft", key="ins_em_preview_btn", use_container_width=True, type="primary")
                if _do_preview or st.session_state.get("ins_em_preview_ready"):
                    st.session_state["ins_em_preview_ready"] = True
                    _final_html = _build_email()
                    st.session_state["ins_em_html"] = _final_html
                    import streamlit.components.v1 as _cmp
                    st.markdown('<div style="font-size:0.72rem;font-weight:700;color:#0B1F3A;margin:12px 0 6px;">📄 Email Preview</div>', unsafe_allow_html=True)
                    _cmp.html(_final_html, height=640, scrolling=True)

                # ── SEND ──────────────────────────────────────────────────────
                if st.session_state.get("ins_em_html"):
                    st.markdown('<div style="font-size:0.72rem;font-weight:700;color:#0B1F3A;margin:14px 0 6px;">📤 Send Email</div>', unsafe_allow_html=True)
                    _send_c1, _send_c2 = st.columns([3, 2])
                    with _send_c1:
                        _send_to_raw = st.text_input("Recipients (comma-separated)", placeholder="ceo@company.com, pm@company.com", key="ins_email_to")
                    with _send_c2:
                        _now_str2 = pd.Timestamp.now().strftime("%d %b %Y")
                        _subj_parts = ["Convin Sense Audit Report"]
                        if _cli_label != "All Clients": _subj_parts.append(_cli_label)
                        if _camp_label != "All Campaigns": _subj_parts.append(_camp_label)
                        _subj_parts.append(_now_str2)
                        _send_subj = st.text_input("Subject", value=" — ".join(_subj_parts), key="ins_email_subj")
                    if st.button("📤 Send Now", key="ins_send_email_btn", type="primary", use_container_width=True):
                        _to_list = [e.strip() for e in _send_to_raw.split(",") if "@" in e.strip()]
                        if not _to_list:
                            st.error("Add at least one valid email address.")
                        else:
                            from gmail_sender import send_report_email as _sre
                            _res = _sre({}, _to_list, _send_subj, st.session_state["ins_em_html"],
                                        from_email=st.session_state.get("user_email",""))
                            if _res.get("sent"):
                                st.success(f"✓ Sent to {len(_res['sent'])} recipient(s): {', '.join(_res['sent'])}")
                                st.session_state.pop("ins_em_preview_ready", None)
                                st.session_state.pop("ins_em_html", None)
                            for _f in _res.get("failed",[]):
                                st.error(f"✗ {_f['email']}: {_f['error']}")

    # ══════════════════════════════════════════════════════════════════════════
    # Tab 2 — Performance Rankings
    # ══════════════════════════════════════════════════════════════════════════
    with _i2:
        if not _has_qa_ins:
            st.info("No QA schema data found.")
        else:
            def _health(avg): return ("🟢 Good", "#0ebc6e") if (avg or 0) >= 80 else ("🟡 Review", "#f59e0b") if (avg or 0) >= 65 else ("🔴 Critical", "#dc2626")

            # ── QA Rankings ───────────────────────────────────────────────────
            if "QA" in _audit_df_ins.columns:
                st.markdown('<div class="section-chip">👤 QA Leaderboard</div>', unsafe_allow_html=True)
                _qa_rows = []
                for _aud, _ag in _audit_df_ins.groupby("QA"):
                    _ag_bs = pd.to_numeric(_ag["Bot Score"], errors="coerce").dropna()
                    _ag_st = _ag["Status"].astype(str).str.strip()
                    _ag_avg = round(_ag_bs.mean(), 1) if len(_ag_bs) else None
                    _ag_pr  = round(int((_ag_st=="Pass").sum()) / len(_ag) * 100, 1) if len(_ag) else 0
                    _ag_rev = int((_ag_st=="Needs Review").sum())
                    _ag_fat = int((_ag_st=="Auto-Fail").sum())
                    _hb, _ = _health(_ag_avg)
                    _qa_rows.append({"QA": str(_aud), "Audits": len(_ag),
                                     "Avg Score": f"{_ag_avg}%" if _ag_avg else "—",
                                     "Pass Rate": f"{_ag_pr}%", "Review": _ag_rev,
                                     "Auto-Fails": _ag_fat, "Health": _hb})
                _qa_rows.sort(key=lambda x: float(x["Avg Score"].rstrip("%")) if x["Avg Score"] != "—" else 0, reverse=True)
                st.dataframe(pd.DataFrame(_qa_rows), use_container_width=True, hide_index=True)

            # ── Client Rankings ───────────────────────────────────────────────
            if "Client" in _audit_df_ins.columns:
                st.markdown('<div class="section-chip">🏢 Client Leaderboard</div>', unsafe_allow_html=True)
                _cl_rows = []
                for _cli, _cg in _audit_df_ins.groupby("Client"):
                    _cg_bs = pd.to_numeric(_cg["Bot Score"], errors="coerce").dropna()
                    _cg_st = _cg["Status"].astype(str).str.strip()
                    _cg_avg = round(_cg_bs.mean(), 1) if len(_cg_bs) else None
                    _cg_pr  = round(int((_cg_st=="Pass").sum()) / len(_cg) * 100, 1) if len(_cg) else 0
                    _cg_fat = int((_cg_st=="Auto-Fail").sum())
                    _cg_rev = int((_cg_st=="Needs Review").sum())
                    _cg_camps = _cg["Campaign Name"].dropna().astype(str).nunique() if "Campaign Name" in _cg.columns else "—"
                    _hb, _ = _health(_cg_avg)
                    _cl_rows.append({"Client": str(_cli), "Audits": len(_cg), "Campaigns": _cg_camps,
                                     "Avg Score": f"{_cg_avg}%" if _cg_avg else "—",
                                     "Pass Rate": f"{_cg_pr}%", "Review": _cg_rev,
                                     "Auto-Fails": _cg_fat, "Health": _hb})
                _cl_rows.sort(key=lambda x: float(x["Avg Score"].rstrip("%")) if x["Avg Score"] != "—" else 0, reverse=True)
                st.dataframe(pd.DataFrame(_cl_rows), use_container_width=True, hide_index=True)

            # ── Campaign Rankings ─────────────────────────────────────────────
            if "Campaign Name" in _audit_df_ins.columns:
                st.markdown('<div class="section-chip">🎯 Campaign Leaderboard</div>', unsafe_allow_html=True)
                _cp_rows = []
                for _cn, _cpg in _audit_df_ins.groupby("Campaign Name"):
                    _cpg_bs  = pd.to_numeric(_cpg["Bot Score"], errors="coerce").dropna()
                    _cpg_st  = _cpg["Status"].astype(str).str.strip()
                    _cpg_avg = round(_cpg_bs.mean(), 1) if len(_cpg_bs) else None
                    _cpg_pr  = round(int((_cpg_st=="Pass").sum()) / len(_cpg) * 100, 1) if len(_cpg) else 0
                    _cpg_fat = int((_cpg_st=="Auto-Fail").sum())
                    _cpg_rev = int((_cpg_st=="Needs Review").sum())
                    _cpg_cli = _cpg["Client"].dropna().astype(str).iloc[0] if "Client" in _cpg.columns and len(_cpg) else "—"
                    _hb, _ = _health(_cpg_avg)
                    _cp_rows.append({"Campaign": str(_cn), "Client": _cpg_cli, "Audits": len(_cpg),
                                     "Avg Score": f"{_cpg_avg}%" if _cpg_avg else "—",
                                     "Pass Rate": f"{_cpg_pr}%", "Review": _cpg_rev,
                                     "Auto-Fails": _cpg_fat, "Health": _hb})
                _cp_rows.sort(key=lambda x: float(x["Avg Score"].rstrip("%")) if x["Avg Score"] != "—" else 0, reverse=True)
                st.dataframe(pd.DataFrame(_cp_rows), use_container_width=True, hide_index=True)

    # ══════════════════════════════════════════════════════════════════════════
    # Tab 3 — Trends
    # ══════════════════════════════════════════════════════════════════════════
    with _i3:
        if not _has_qa_ins or _audit_df_ins is None:
            st.info("No QA data available.")
        else:
            if not sheets:
                st.markdown(
                    '<div style="background:rgba(37,99,235,0.07);border:1px solid rgba(37,99,235,0.18);'
                    'border-radius:8px;padding:9px 16px;margin-bottom:14px;font-size:0.73rem;color:#2563EB;">'
                    '📊 <strong>Demo data</strong> — showing 25 seed audits across 4 auditors & 3 campaigns.</div>',
                    unsafe_allow_html=True,
                )

            # ── Shared Plotly layout ──────────────────────────────────────────
            def _plotly_layout(title="", yaxis_title="", xaxis_title=""):
                return dict(
                    title=dict(text=title, font=dict(family="Inter,sans-serif", size=14, color="#0B1F3A"), x=0, xanchor="left"),
                    font=dict(family="Inter,sans-serif", size=11, color="#475569"),
                    plot_bgcolor="#FFFFFF",
                    paper_bgcolor="#FFFFFF",
                    hovermode="x unified",
                    hoverlabel=dict(bgcolor="#0B1F3A", font_color="#FFFFFF", font_size=12, font_family="Inter,sans-serif", bordercolor="#2563EB"),
                    xaxis=dict(title=xaxis_title, showgrid=False, zeroline=False, tickfont=dict(size=10, color="#94a3b8"), linecolor="#E2EAF6", tickcolor="#E2EAF6"),
                    yaxis=dict(title=yaxis_title, showgrid=True, gridcolor="#F1F5F9", zeroline=False, tickfont=dict(size=10, color="#94a3b8"), ticksuffix="%", range=[0, 105]),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=11), bgcolor="rgba(0,0,0,0)", borderwidth=0),
                    margin=dict(l=10, r=10, t=48, b=10),
                    height=320,
                )

            _CONVIN_COLORS = ["#2563EB","#059669","#d97706","#dc2626","#7c3aed","#0891b2","#b45309","#be185d"]

            _DATE_KW2 = ("audit date","date","time","month","week","day","period","created","submitted")
            _dc2 = next((c for c in _audit_df_ins.columns if any(k in str(c).lower() for k in _DATE_KW2)), None)
            if _dc2 is None:
                st.info("No date column found — trends require a date column (e.g. 'Audit Date').")
            else:
                try:
                    _td2 = _audit_df_ins.copy()
                    _td2["_date"] = pd.to_datetime(_td2[_dc2], errors="coerce")
                    _td2["_bs"]   = pd.to_numeric(_td2["Bot Score"], errors="coerce")
                    _td2 = _td2.dropna(subset=["_date", "_bs"]).sort_values("_date")
                    _td2["_pass"] = (_td2["Status"].astype(str).str.strip() == "Pass").astype(int)

                    _tr_c1, _tr_c2 = st.columns([5, 1])
                    with _tr_c2:
                        _t_period = st.selectbox("Granularity", ["Daily", "Weekly", "Monthly"],
                                                  index=1, key="insights_trend_period")
                    _t_freq = {"Daily": "D", "Weekly": "W", "Monthly": "M"}[_t_period]

                    # ── 1. Score & Pass Rate over time ────────────────────────
                    _agg2 = (_td2.set_index("_date")[["_bs", "_pass"]]
                             .resample(_t_freq).agg({"_bs": "mean", "_pass": "mean"})
                             .dropna(how="all").round(2))
                    _agg2["pass_pct"] = (_agg2["_pass"] * 100).round(1)

                    if not _agg2.empty:
                        _dates = _agg2.index.strftime("%d %b %Y" if _t_period == "Daily" else ("%d %b" if _t_period == "Weekly" else "%b %Y"))
                        _fig1 = go.Figure()
                        # Avg Bot Score — filled area
                        _fig1.add_trace(go.Scatter(
                            x=_dates, y=_agg2["_bs"].tolist(),
                            name="Avg Bot Score", mode="lines+markers",
                            line=dict(color="#2563EB", width=2.5, shape="spline"),
                            marker=dict(size=6, color="#2563EB", line=dict(width=1.5, color="#fff")),
                            fill="tozeroy", fillcolor="rgba(37,99,235,0.08)",
                            hovertemplate="<b>%{y:.1f}%</b><extra>Avg Bot Score</extra>",
                        ))
                        # Pass Rate — filled area
                        _fig1.add_trace(go.Scatter(
                            x=_dates, y=_agg2["pass_pct"].tolist(),
                            name="Pass Rate", mode="lines+markers",
                            line=dict(color="#059669", width=2.5, shape="spline", dash="dot"),
                            marker=dict(size=6, color="#059669", line=dict(width=1.5, color="#fff")),
                            fill="tozeroy", fillcolor="rgba(5,150,105,0.06)",
                            hovertemplate="<b>%{y:.1f}%</b><extra>Pass Rate</extra>",
                        ))
                        # Reference line at 80%
                        _fig1.add_hline(y=80, line_dash="dash", line_color="rgba(217,119,6,0.45)",
                                        annotation_text="Target 80%", annotation_position="top right",
                                        annotation_font=dict(size=10, color="#d97706"))
                        _fig1.update_layout(**_plotly_layout("📈  Score & Pass Rate Over Time", "Score / Rate (%)", _dc2))
                        with _tr_c1:
                            st.plotly_chart(_fig1, use_container_width=True, config={"displayModeBar": False})

                    st.divider()

                    # ── 2. Per-QA score trend + Per-campaign in columns ───────
                    _c_qa, _c_camp = st.columns(2)

                    if "QA" in _audit_df_ins.columns:
                        with _c_qa:
                            st.markdown('<div class="section-chip">👤 Score Trend by QA</div>', unsafe_allow_html=True)
                            try:
                                _aud_pt = _td2.pivot_table(
                                    index=pd.Grouper(key="_date", freq=_t_freq),
                                    columns="QA", values="_bs", aggfunc="mean").round(1)
                                if not _aud_pt.empty:
                                    _fig2 = go.Figure()
                                    _dts2 = _aud_pt.index.strftime("%d %b" if _t_period in ("Daily","Weekly") else "%b %Y")
                                    for _ci, _agent in enumerate(_aud_pt.columns):
                                        _col = _CONVIN_COLORS[_ci % len(_CONVIN_COLORS)]
                                        _fig2.add_trace(go.Scatter(
                                            x=_dts2, y=_aud_pt[_agent].tolist(),
                                            name=str(_agent), mode="lines+markers",
                                            line=dict(color=_col, width=2, shape="spline"),
                                            marker=dict(size=5, color=_col, line=dict(width=1, color="#fff")),
                                            hovertemplate=f"<b>%{{y:.1f}}%</b><extra>{_agent}</extra>",
                                        ))
                                    _lay2 = _plotly_layout("", "Avg Bot Score (%)", _dc2)
                                    _lay2["height"] = 260
                                    _lay2["margin"] = dict(l=10, r=10, t=18, b=10)
                                    _fig2.update_layout(**_lay2)
                                    st.plotly_chart(_fig2, use_container_width=True, config={"displayModeBar": False})
                            except Exception:
                                st.info("Not enough data for QA trend.")

                    if "Campaign Name" in _audit_df_ins.columns:
                        with _c_camp:
                            st.markdown('<div class="section-chip">🎯 Score Trend by Campaign</div>', unsafe_allow_html=True)
                            try:
                                _camp_pt = _td2.pivot_table(
                                    index=pd.Grouper(key="_date", freq=_t_freq),
                                    columns="Campaign Name", values="_bs", aggfunc="mean").round(1)
                                if not _camp_pt.empty:
                                    _fig3 = go.Figure()
                                    _dts3 = _camp_pt.index.strftime("%d %b" if _t_period in ("Daily","Weekly") else "%b %Y")
                                    for _ci, _camp in enumerate(_camp_pt.columns):
                                        _col = _CONVIN_COLORS[_ci % len(_CONVIN_COLORS)]
                                        _fig3.add_trace(go.Scatter(
                                            x=_dts3, y=_camp_pt[_camp].tolist(),
                                            name=str(_camp), mode="lines+markers",
                                            line=dict(color=_col, width=2, shape="spline"),
                                            marker=dict(size=5, color=_col, line=dict(width=1, color="#fff")),
                                            hovertemplate=f"<b>%{{y:.1f}}%</b><extra>{_camp}</extra>",
                                        ))
                                    _lay3 = _plotly_layout("", "Avg Bot Score (%)", _dc2)
                                    _lay3["height"] = 260
                                    _lay3["margin"] = dict(l=10, r=10, t=18, b=10)
                                    _fig3.update_layout(**_lay3)
                                    st.plotly_chart(_fig3, use_container_width=True, config={"displayModeBar": False})
                            except Exception:
                                st.info("Not enough data for campaign trend.")

                    st.divider()

                    # ── 3. Status distribution (stacked bar) + Volume side by side
                    _c_st, _c_vol = st.columns(2)

                    with _c_st:
                        st.markdown('<div class="section-chip">📊 Status Distribution Over Time</div>', unsafe_allow_html=True)
                        try:
                            _status_pt = (_td2.groupby([pd.Grouper(key="_date", freq=_t_freq), "Status"])
                                          .size().unstack(fill_value=0))
                            _dts4 = _status_pt.index.strftime("%d %b" if _t_period in ("Daily","Weekly") else "%b %Y")
                            _STATUS_COLORS = {"Pass":"#059669","Needs Review":"#d97706","Fail":"#ef4444","Auto-Fail":"#dc2626"}
                            _fig4 = go.Figure()
                            for _stat in _status_pt.columns:
                                _sc = _STATUS_COLORS.get(str(_stat), "#94a3b8")
                                _fig4.add_trace(go.Bar(
                                    x=_dts4, y=_status_pt[_stat].tolist(),
                                    name=str(_stat), marker_color=_sc,
                                    hovertemplate=f"<b>%{{y}}</b> {_stat}<extra></extra>",
                                ))
                            _lay4 = dict(
                                barmode="stack",
                                plot_bgcolor="#fff", paper_bgcolor="#fff",
                                font=dict(family="Inter,sans-serif", size=11, color="#475569"),
                                hovermode="x unified",
                                hoverlabel=dict(bgcolor="#0B1F3A", font_color="#fff", font_size=12),
                                legend=dict(orientation="h", y=1.04, x=0, font=dict(size=10)),
                                xaxis=dict(showgrid=False, tickfont=dict(size=10, color="#94a3b8")),
                                yaxis=dict(showgrid=True, gridcolor="#F1F5F9", tickfont=dict(size=10, color="#94a3b8"), title="Count"),
                                margin=dict(l=10, r=10, t=36, b=10), height=260,
                            )
                            _fig4.update_layout(**_lay4)
                            if not _status_pt.empty:
                                st.plotly_chart(_fig4, use_container_width=True, config={"displayModeBar": False})
                        except Exception:
                            pass

                    with _c_vol:
                        st.markdown('<div class="section-chip">📋 Audit Volume Over Time</div>', unsafe_allow_html=True)
                        try:
                            _vol = _td2.resample(_t_freq, on="_date").size()
                            _dts5 = _vol.index.strftime("%d %b" if _t_period in ("Daily","Weekly") else "%b %Y")
                            _fig5 = go.Figure()
                            _fig5.add_trace(go.Bar(
                                x=_dts5, y=_vol.tolist(),
                                name="Audits",
                                marker=dict(
                                    color=_vol.tolist(),
                                    colorscale=[[0,"#DBEAFE"],[0.5,"#60A5FA"],[1,"#1D4ED8"]],
                                    showscale=False,
                                ),
                                hovertemplate="<b>%{y} audits</b><extra></extra>",
                            ))
                            _lay5 = dict(
                                plot_bgcolor="#fff", paper_bgcolor="#fff",
                                font=dict(family="Inter,sans-serif", size=11, color="#475569"),
                                hovermode="x",
                                hoverlabel=dict(bgcolor="#0B1F3A", font_color="#fff", font_size=12),
                                xaxis=dict(showgrid=False, tickfont=dict(size=10, color="#94a3b8")),
                                yaxis=dict(showgrid=True, gridcolor="#F1F5F9", tickfont=dict(size=10, color="#94a3b8"), title="# Audits"),
                                margin=dict(l=10, r=10, t=36, b=10), height=260,
                            )
                            _fig5.update_layout(**_lay5)
                            if not _vol.empty:
                                st.plotly_chart(_fig5, use_container_width=True, config={"displayModeBar": False})
                        except Exception:
                            pass

                except Exception:
                    st.info("Unable to compute trends — check date column format.")

    # Helper functions used by Tabs 4 and 5
    def _render_entity_kpi_band(df, label):
        if df is None or df.empty:
            return
        if "Bot Score" not in df.columns or "Status" not in df.columns:
            return
        _tot  = len(df)
        _bs   = pd.to_numeric(df["Bot Score"], errors="coerce")
        _st   = df["Status"].astype(str).str.strip()
        _avg  = round(_bs.dropna().mean(), 1) if _bs.dropna().notna().any() else None
        _pas  = int((_st == "Pass").sum())
        _rev  = int((_st == "Needs Review").sum())
        _fai  = int((_st == "Fail").sum())
        _fat  = int((_st == "Auto-Fail").sum())
        _pr   = round(_pas / _tot * 100, 1) if _tot else 0
        def _ekc(v, lbl, grad, shadow="rgba(37,99,235,0.18)"):
            return (f'<div style="background:#fff;border-radius:12px;overflow:hidden;'
                    f'box-shadow:0 2px 8px rgba(11,31,58,0.08);border:1px solid #E2EAF6;'
                    f'transition:box-shadow 0.2s,transform 0.2s;cursor:default;" '
                    f'onmouseover="this.style.boxShadow=\'0 6px 18px {shadow}\';this.style.transform=\'translateY(-2px)\'" '
                    f'onmouseout="this.style.boxShadow=\'0 2px 8px rgba(11,31,58,0.08)\';this.style.transform=\'translateY(0)\'">'
                    f'<div style="height:3px;background:{grad};"></div>'
                    f'<div style="padding:12px 10px;text-align:center;">'
                    f'<div style="font-size:1.6rem;font-weight:900;color:#0B1F3A;line-height:1.05;letter-spacing:-0.02em;">{v}</div>'
                    f'<div style="font-size:0.57rem;font-weight:700;color:#64748b;letter-spacing:0.10em;text-transform:uppercase;margin-top:4px;">{lbl}</div>'
                    f'</div></div>')
        _avg_g = "linear-gradient(135deg,#0891b2,#06b6d4)" if (_avg or 0)>=80 else "linear-gradient(135deg,#d97706,#f59e0b)" if (_avg or 0)>=60 else "linear-gradient(135deg,#dc2626,#ef4444)"
        _pr_g  = "linear-gradient(135deg,#059669,#10b981)" if _pr>=80 else "linear-gradient(135deg,#d97706,#f59e0b)" if _pr>=60 else "linear-gradient(135deg,#dc2626,#ef4444)"
        if label:
            st.markdown(f'<div style="font-size:0.61rem;font-weight:800;color:#1E40AF;letter-spacing:0.11em;text-transform:uppercase;margin-bottom:10px;background:#fff;border:1px solid #BFDBFE;border-left:3px solid #2563EB;padding:5px 14px 5px 12px;border-radius:6px;display:inline-block;box-shadow:0 1px 4px rgba(37,99,235,0.08);">{label}</div>', unsafe_allow_html=True)
        _ec1,_ec2,_ec3,_ec4,_ec5,_ec6 = st.columns(6)
        _ec1.markdown(_ekc(_tot,  "Audits",       "linear-gradient(135deg,#0B1F3A,#2563EB)","rgba(37,99,235,0.28)"), unsafe_allow_html=True)
        _ec2.markdown(_ekc(f"{_avg or '—'}%","Avg Score",_avg_g,"rgba(8,145,178,0.22)"), unsafe_allow_html=True)
        _ec3.markdown(_ekc(f"{_pr}%","Pass Rate", _pr_g, "rgba(5,150,105,0.22)"), unsafe_allow_html=True)
        _ec4.markdown(_ekc(_pas,  "Passed",       "linear-gradient(135deg,#059669,#10b981)","rgba(5,150,105,0.28)"), unsafe_allow_html=True)
        _ec5.markdown(_ekc(_rev,  "Needs Review", "linear-gradient(135deg,#d97706,#f59e0b)","rgba(217,119,6,0.22)"), unsafe_allow_html=True)
        _ec6.markdown(_ekc(_fat,  "Auto-Fails",   "linear-gradient(135deg,#dc2626,#f43f5e)" if _fat else "linear-gradient(135deg,#6b7280,#9ca3af)","rgba(220,38,38,0.22)"), unsafe_allow_html=True)
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    def _render_param_weakness(df, key_pfx):
        _all_params = []
        _seen_cols = set()
        for _tier in _QA_SCHEMA["tiers"]:
            for _p in _tier["params"]:
                _pmax_vals = [int(o) for o in _p["options"] if o not in ("NA",) and str(o).lstrip("-").isdigit()]
                _pmax = max(_pmax_vals) if _pmax_vals else 2
                _all_params.append({"col": _p["col"], "max": _pmax, "weight": _p["weight"], "tier": _tier["label"], "color": _tier["color"]})
                _seen_cols.add(_p["col"].lower())
        # Add any Legend params not already in QA schema
        for _lp, _lopts in legend_map.items():
            if _lp.lower() in _seen_cols:
                continue
            # Skip metadata / identity columns
            if any(kw in _lp.lower() for kw in ("date","name","id","phone","link","status","score","qa","client","campaign","pm","csm","lead","disposition","conversation")):
                continue
            _lmax_vals = [int(o) for o in _lopts if str(o).lstrip("-").isdigit()]
            _lmax = max(_lmax_vals) if _lmax_vals else 1
            _all_params.append({"col": _lp, "max": _lmax, "weight": 1.0, "tier": "Legend", "color": "#2563EB"})
        _param_rows = []
        for _pp in _all_params:
            if _pp["col"] not in df.columns:
                continue
            _vals = df[_pp["col"]].astype(str).str.strip()
            _vals = _vals[~_vals.str.upper().isin(["NA", ""])]
            _nums = pd.to_numeric(_vals, errors="coerce").dropna()
            if len(_nums) == 0:
                continue
            _avg_pct = round(_nums.mean() / _pp["max"] * 100, 1)
            _param_rows.append({"param": _pp["col"], "avg_pct": _avg_pct, "n": len(_nums), "tier": _pp["tier"], "color": _pp["color"]})
        if not _param_rows:
            st.info("No parameter-level data found.")
            return
        _param_rows.sort(key=lambda x: x["avg_pct"])
        st.markdown('<div class="section-chip">🔍 Parameter Score Breakdown (weakest first)</div>', unsafe_allow_html=True)
        _pw_html = ""
        for _idx, _pr in enumerate(_param_rows):
            _bar_bg = _pr["color"] + "22"
            _tier_short = _pr["tier"].split("·")[-1].strip() if "·" in _pr["tier"] else _pr["tier"]
            _badge_color = _pr["color"]
            _bar_fill = _pr["color"]
            _pw_html += (
                f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">'
                f'<div style="width:180px;font-size:0.7rem;color:#0d1d3a;font-weight:600;flex-shrink:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">'
                f'{"⚠️ " if _pr["avg_pct"] < 60 else ""}{_pr["param"]}</div>'
                f'<div style="flex:1;height:16px;background:#f0f2f5;border-radius:3px;overflow:hidden;">'
                f'<div style="width:{_pr["avg_pct"]}%;height:100%;background:{_bar_fill};border-radius:3px;"></div></div>'
                f'<div style="width:48px;text-align:right;font-size:0.7rem;font-weight:700;color:{_badge_color};flex-shrink:0;">{_pr["avg_pct"]}%</div>'
                f'<div style="width:50px;font-size:0.6rem;color:#aabbcc;flex-shrink:0;text-align:right;">n={_pr["n"]}</div>'
                f'</div>'
            )
        st.markdown(f'<div style="background:#fff;border:1px solid #e4e7ec;border-radius:10px;padding:14px 18px;margin-bottom:1rem;">{_pw_html}</div>', unsafe_allow_html=True)

    def _render_entity_insights(df, entity_type, entity_name):
        insights, actions = [], []
        if df is None or df.empty:
            return
        _tot  = len(df)
        _bs   = pd.to_numeric(df["Bot Score"], errors="coerce")
        _st   = df["Status"].astype(str).str.strip()
        _avg  = round(_bs.dropna().mean(), 1) if _bs.dropna().notna().any() else None
        _pas  = int((_st == "Pass").sum())
        _fai  = int((_st == "Fail").sum())
        _fat  = int((_st == "Auto-Fail").sum())
        _rev  = int((_st == "Needs Review").sum())
        _pr   = round(_pas  / _tot * 100, 1) if _tot else 0
        _fr   = round((_fai + _fat) / _tot * 100, 1) if _tot else 0
        _tar  = 80.0
        _TCFG = {"critical":("#fff1f2","#e11d48","#9f1239","#fecdd3"),"warning":("#fffbf0","#d97706","#92400e","#fde68a"),"success":("#ecfdf5","#059669","#064e3b","#a7f3d0"),"info":("#eef2ff","#4f46e5","#312e81","#c7d2fe")}
        _PCFG = {"high":("#dc2626","🔴","#fef2f2","#fee2e2"),"medium":("#f59e0b","🟡","#fffbeb","#fde68a"),"low":("#16a34a","🟢","#f0fdf4","#bbf7d0")}

        if _fat > 0:
            insights.append({"type":"critical","title":f"🚨 {_fat} Auto-Fail(s)","detail":f"{round(_fat/_tot*100,1)}% auto-fail rate — immediate review of these calls required."})
            actions.append({"priority":"high","category":"Technical","action":f"Review all {_fat} auto-fail conversation(s) in {entity_name} for bot logic errors or CTI failures","impact":"Eliminating fatal drops protects conversion rate and client trust."})
        if _pr < _tar:
            _gap = round(_tar - _pr, 1)
            insights.append({"type":"warning" if _pr>=60 else "critical","title":f"⚠️ Pass Rate {_pr}% (−{_gap}pp from target)","detail":f"{_pas} passed, {_rev} need review, {_fai} failed of {_tot} total."})
            actions.append({"priority":"high" if _pr<60 else "medium","category":"Coaching","action":f"Focus coaching on {_rev} 'Needs Review' audits — closest to pass threshold","impact":f"Pushing review cases to Pass adds +{round(_rev/_tot*100,1)}pp pass rate."})
        else:
            insights.append({"type":"success","title":f"✅ Pass Rate {_pr}% — above {int(_tar)}% target","detail":f"{_pas} of {_tot} audits passed (+{round(_pr-_tar,1)}pp above target). Performance is strong."})

        # Weakest parameter
        _all_params = []
        for _tier in _QA_SCHEMA["tiers"]:
            for _p in _tier["params"]:
                _pmax_vals = [int(o) for o in _p["options"] if o not in ("NA",) and str(o).lstrip("-").isdigit()]
                _pmax = max(_pmax_vals) if _pmax_vals else 2
                if _p["col"] in df.columns:
                    _vals = df[_p["col"]].astype(str).str.strip()
                    _vals = _vals[~_vals.str.upper().isin(["NA",""])]
                    _nums = pd.to_numeric(_vals, errors="coerce").dropna()
                    if len(_nums):
                        _all_params.append({"col":_p["col"],"pct":round(_nums.mean()/_pmax*100,1)})
        if _all_params:
            _all_params.sort(key=lambda x: x["pct"])
            _wp = _all_params[0]
            if _wp["pct"] < 75:
                insights.append({"type":"warning","title":f"📉 Weakest Parameter: {_wp['col']}","detail":f"Avg score {_wp['pct']}% — consistently underperforming. Bot logic for this area needs improvement."})
                actions.append({"priority":"medium","category":"Bot Tuning","action":f"Improve bot logic for '{_wp['col']}' — retrain or reconfigure this module","impact":"Fixing the weakest parameter has outsized impact on overall bot score."})

        # Trend
        _DATE_KW = ("audit date","date","created","submitted","month","week","day","period","time")
        _dc = next((c for c in df.columns if any(k in str(c).lower() for k in _DATE_KW)), None)
        if _dc:
            try:
                _td = df.copy()
                _td["_d"] = pd.to_datetime(_td[_dc], errors="coerce")
                _td["_b"] = _bs
                _td = _td.dropna(subset=["_d","_b"]).sort_values("_d")
                if len(_td) >= 6:
                    _first_h = _td.iloc[:len(_td)//2]["_b"].mean()
                    _last_h  = _td.iloc[len(_td)//2:]["_b"].mean()
                    _diff    = round(_last_h - _first_h, 1)
                    if _diff >= 3:
                        insights.append({"type":"success","title":f"📈 Improving Trend (+{_diff}%)","detail":f"Second half avg {round(_last_h,1)}% vs first half {round(_first_h,1)}%. Performance trajectory is positive."})
                    elif _diff <= -3:
                        insights.append({"type":"warning","title":f"📉 Declining Trend ({_diff}%)","detail":f"Second half avg {round(_last_h,1)}% vs first half {round(_first_h,1)}%. Investigate recent process changes."})
                        actions.append({"priority":"medium","category":"Process","action":f"Investigate root cause of score decline in recent audits for {entity_name}","impact":"Early identification of decline prevents further KPI deterioration."})
            except Exception:
                pass

        if insights:
            st.markdown('<div class="section-chip">💡 Key Insights</div>', unsafe_allow_html=True)
            _ic1, _ic2 = st.columns(2)
            for _ii, _ins in enumerate(insights):
                _tcfg = _TCFG.get(_ins["type"], _TCFG["info"])
                with (_ic1 if _ii%2==0 else _ic2):
                    st.markdown(f'<div style="background:{_tcfg[0]};border:1px solid {_tcfg[3]};border-left:4px solid {_tcfg[1]};border-radius:10px;padding:12px 16px;margin-bottom:8px;"><div style="font-size:0.78rem;font-weight:700;color:{_tcfg[2]};margin-bottom:4px;">{_ins["title"]}</div><div style="font-size:0.71rem;color:{_tcfg[2]};opacity:0.85;line-height:1.5;">{_ins["detail"]}</div></div>', unsafe_allow_html=True)
        if actions:
            st.markdown('<div class="section-chip">🎯 Actionable Suggestions</div>', unsafe_allow_html=True)
            _ac1, _ac2 = st.columns(2)
            for _ai, _act in enumerate(actions):
                _pcfg = _PCFG.get(_act["priority"], _PCFG["low"])
                with (_ac1 if _ai%2==0 else _ac2):
                    st.markdown(f'<div style="background:{_pcfg[2]};border:1px solid {_pcfg[3]};border-left:4px solid {_pcfg[0]};border-radius:10px;padding:12px 15px;margin-bottom:8px;"><div style="display:flex;align-items:center;gap:6px;margin-bottom:5px;"><span>{_pcfg[1]}</span><span style="font-size:0.63rem;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:{_pcfg[0]};">{_act["priority"].upper()} · {_act["category"]}</span></div><div style="font-size:0.73rem;font-weight:600;color:#0d1d3a;margin-bottom:5px;line-height:1.4;">{_act["action"]}</div><div style="font-size:0.65rem;color:#5588bb;line-height:1.4;border-top:1px solid {_pcfg[0]}22;padding-top:5px;">Impact: {_act["impact"]}</div></div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # Tab 4 — Parameter Analysis
    # ══════════════════════════════════════════════════════════════════════════
    with _i4:
        if not _has_qa_ins:
            st.info("No QA schema data found.")
        else:
            _pa_l, _pa_r = st.columns([3, 2])
            with _pa_l:
                _render_param_weakness(_audit_df_ins, "tab4_pw")

            with _pa_r:
                # Intelligence params breakdown
                st.markdown('<div class="section-chip">🧠 Intelligence Parameters</div>', unsafe_allow_html=True)
                _ip_html = ""
                for _ip in _QA_SCHEMA["intelligence"]:
                    if _ip["col"] not in _audit_df_ins.columns:
                        continue
                    _ip_vals = _audit_df_ins[_ip["col"]].astype(str).str.strip()
                    _ip_vc = _ip_vals[~_ip_vals.isin(["", "nan", "None"])].value_counts()
                    if _ip_vc.empty:
                        continue
                    _ip_total = _ip_vc.sum()
                    _ip_html += f'<div style="font-size:0.7rem;font-weight:700;color:#0d1d3a;margin:10px 0 5px;">{_ip["icon"]} {_ip["col"]}</div>'
                    for _ov, _oc in _ip_vc.items():
                        _op = round(_oc / _ip_total * 100, 1)
                        _score = _ip["score_map"].get(str(_ov), 0)
                        _oc2 = "#0ebc6e" if _score >= 2 else "#f59e0b" if _score >= 1 else "#dc2626"
                        _ip_html += (
                            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">'
                            f'<div style="width:80px;font-size:0.67rem;color:#0d1d3a;font-weight:600;flex-shrink:0;">{_ov}</div>'
                            f'<div style="flex:1;height:12px;background:#f0f2f5;border-radius:3px;overflow:hidden;">'
                            f'<div style="width:{_op}%;height:100%;background:{_oc2};border-radius:3px;"></div></div>'
                            f'<div style="width:44px;text-align:right;font-size:0.67rem;font-weight:700;color:{_oc2};flex-shrink:0;">{_op}%</div>'
                            f'</div>'
                        )
                if _ip_html:
                    st.markdown(f'<div style="background:#fff;border:1px solid #e4e7ec;border-radius:10px;padding:12px 16px;">{_ip_html}</div>', unsafe_allow_html=True)

            # Score bucket distribution
            st.markdown('<div class="section-chip">📊 Score Distribution</div>', unsafe_allow_html=True)
            _pa_bs = pd.to_numeric(_audit_df_ins.get("Bot Score", pd.Series(dtype=float)), errors="coerce").dropna()
            if len(_pa_bs):
                _buckets4 = [("90–100 (Excellent)","#0ebc6e",90,101),("80–89 (Pass)","#16a34a",80,90),
                             ("70–79 (Borderline)","#84cc16",70,80),("60–69 (Needs Review)","#f59e0b",60,70),
                             ("50–59 (Fail)","#ef4444",50,60),("< 50 (Critical Fail)","#dc2626",0,50)]
                _bk4_html = ""
                for _bl4, _bc4, _lo4, _hi4 in _buckets4:
                    _cnt4 = int(((_pa_bs >= _lo4) & (_pa_bs < _hi4)).sum())
                    _pct4 = round(_cnt4 / len(_pa_bs) * 100, 1)
                    _bk4_html += (
                        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:5px;">'
                        f'<div style="width:160px;font-size:0.7rem;color:#0d1d3a;font-weight:600;flex-shrink:0;">{_bl4}</div>'
                        f'<div style="flex:1;height:14px;background:#f0f2f5;border-radius:3px;overflow:hidden;">'
                        f'<div style="width:{_pct4}%;height:100%;background:{_bc4};border-radius:3px;"></div></div>'
                        f'<div style="width:80px;text-align:right;font-size:0.7rem;font-weight:700;color:{_bc4};flex-shrink:0;">{_cnt4:,} ({_pct4}%)</div>'
                        f'</div>'
                    )
                st.markdown(f'<div style="background:#fff;border:1px solid #e4e7ec;border-radius:10px;padding:14px 18px;">{_bk4_html}</div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # Tab 5 — Reports (Client · Campaign · Full Log · AI)
    # ══════════════════════════════════════════════════════════════════════════
    with _i5:
        if not _has_qa_ins:
            st.info("No QA schema data found.")
        else:
            _rep_view = st.radio("View by", ["🏢 Client", "🎯 Campaign", "📋 Full Log", "🤖 AI Deep Dive"],
                                 horizontal=True, key="rep_view_toggle")

            if _rep_view == "🏢 Client":
                if "Client" not in _audit_df_ins.columns:
                    st.info("No 'Client' column in audit data.")
                else:
                    _cli_opts_r = ["All Clients"] + sorted(_audit_df_ins["Client"].dropna().astype(str).unique().tolist())
                    _rc1, _rc2 = st.columns([2, 2])
                    with _rc1:
                        _sel_cli_r = st.selectbox("Client", _cli_opts_r, key="rep_client_sel")
                    with _rc2:
                        _camp_f_opts = ["All Campaigns"]
                        if "Campaign Name" in _audit_df_ins.columns and _sel_cli_r != "All Clients":
                            _camp_f_opts += sorted(_audit_df_ins[_audit_df_ins["Client"].astype(str)==_sel_cli_r]["Campaign Name"].dropna().astype(str).unique().tolist())
                        _camp_f = st.selectbox("Campaign", _camp_f_opts, key="rep_cli_camp_f")
                    _cr_df = _audit_df_ins.copy()
                    if _sel_cli_r != "All Clients":
                        _cr_df = _cr_df[_cr_df["Client"].astype(str) == _sel_cli_r]
                    if _camp_f != "All Campaigns" and "Campaign Name" in _cr_df.columns:
                        _cr_df = _cr_df[_cr_df["Campaign Name"].astype(str) == _camp_f]
                    if _cr_df.empty:
                        st.warning("No audits for this selection.")
                    else:
                        _render_entity_kpi_band(_cr_df, f"{_sel_cli_r}" + (f" · {_camp_f}" if _camp_f != "All Campaigns" else ""))
                        if _sel_cli_r != "All Clients" and _camp_f == "All Campaigns" and "Campaign Name" in _cr_df.columns:
                            st.markdown('<div class="section-chip">📋 Campaign Breakdown</div>', unsafe_allow_html=True)
                            _cb2 = []
                            for _cn, _cg in _cr_df.groupby("Campaign Name"):
                                _c_bs2 = pd.to_numeric(_cg["Bot Score"], errors="coerce")
                                _c_st2 = _cg["Status"].astype(str).str.strip()
                                _c_avg2 = round(_c_bs2.dropna().mean(),1) if _c_bs2.dropna().notna().any() else None
                                _c_pr2 = round(int((_c_st2=="Pass").sum())/len(_cg)*100,1) if len(_cg) else 0
                                _c_fat2 = int((_c_st2=="Auto-Fail").sum())
                                _hlth2 = "🟢 Good" if (_c_avg2 or 0)>=80 else "🟡 Review" if (_c_avg2 or 0)>=65 else "🔴 Critical"
                                _cb2.append({"Campaign":str(_cn),"Audits":len(_cg),"Avg Score":f"{_c_avg2}%" if _c_avg2 else "—","Pass Rate":f"{_c_pr2}%","Auto-Fails":_c_fat2,"Health":_hlth2})
                            _cb2.sort(key=lambda x:float(x["Avg Score"].rstrip("%")) if x["Avg Score"]!="—" else 0, reverse=True)
                            st.dataframe(pd.DataFrame(_cb2), use_container_width=True, hide_index=True)
                        if "QA" in _cr_df.columns:
                            st.markdown('<div class="section-chip">👤 QA Breakdown</div>', unsafe_allow_html=True)
                            _qa2 = []
                            for _aud2, _ag2 in _cr_df.groupby("QA"):
                                _a_bs2 = pd.to_numeric(_ag2["Bot Score"], errors="coerce")
                                _a_st2 = _ag2["Status"].astype(str).str.strip()
                                _a_avg2 = round(_a_bs2.dropna().mean(),1) if _a_bs2.dropna().notna().any() else None
                                _a_pr2 = round(int((_a_st2=="Pass").sum())/len(_ag2)*100,1) if len(_ag2) else 0
                                _qa2.append({"QA":str(_aud2),"Audits":len(_ag2),"Avg Score":f"{_a_avg2}%" if _a_avg2 else "—","Pass Rate":f"{_a_pr2}%","Auto-Fails":int((_a_st2=="Auto-Fail").sum())})
                            _qa2.sort(key=lambda x:float(x["Avg Score"].rstrip("%")) if x["Avg Score"]!="—" else 0, reverse=True)
                            st.dataframe(pd.DataFrame(_qa2), use_container_width=True, hide_index=True)
                        _render_param_weakness(_cr_df, "rep_cli_pw")
                        _render_entity_insights(_cr_df, "client", _sel_cli_r)
                        _dl2, _ = st.columns([1,4])
                        with _dl2:
                            st.download_button("⬇ Download", data=_cr_df.to_csv(index=False).encode("utf-8"),
                                               file_name=f"client_{_sel_cli_r.replace(' ','_')}.csv", mime="text/csv", key="dl_cli_rep")

            elif _rep_view == "🎯 Campaign":
                if "Campaign Name" not in _audit_df_ins.columns:
                    st.info("No 'Campaign Name' column in audit data.")
                else:
                    _camp_opts_r = ["All Campaigns"] + sorted(_audit_df_ins["Campaign Name"].dropna().astype(str).unique().tolist())
                    _rca1, _rca2 = st.columns([2, 2])
                    with _rca1:
                        _sel_camp_r = st.selectbox("Campaign", _camp_opts_r, key="rep_camp_sel")
                    with _rca2:
                        _aud_f_opts = ["All QA"]
                        if "QA" in _audit_df_ins.columns:
                            _aud_f_opts += sorted(_audit_df_ins["QA"].dropna().astype(str).unique().tolist())
                        _aud_f = st.selectbox("QA", _aud_f_opts, key="rep_camp_aud_f")
                    _crp_df = _audit_df_ins.copy()
                    if _sel_camp_r != "All Campaigns":
                        _crp_df = _crp_df[_crp_df["Campaign Name"].astype(str) == _sel_camp_r]
                    if _aud_f != "All QA" and "QA" in _crp_df.columns:
                        _crp_df = _crp_df[_crp_df["QA"].astype(str) == _aud_f]
                    if _crp_df.empty:
                        st.warning("No audits for this selection.")
                    else:
                        if "Client" in _crp_df.columns:
                            _meta_c = ", ".join(_crp_df["Client"].dropna().astype(str).unique())
                            _meta_pm = ", ".join(_crp_df["PM / CSM"].dropna().astype(str).unique()) if "PM / CSM" in _crp_df.columns else "—"
                            st.markdown(f'<div style="background:#f0f7ff;border:1px solid #ddeeff;border-radius:8px;padding:8px 14px;margin-bottom:10px;font-size:0.72rem;color:#2a5080;"><strong>Client:</strong> {_meta_c} &nbsp;|&nbsp; <strong>PM:</strong> {_meta_pm}</div>', unsafe_allow_html=True)
                        _render_entity_kpi_band(_crp_df, f"{_sel_camp_r}" + (f" · {_aud_f}" if _aud_f != "All QA" else ""))
                        if "QA" in _crp_df.columns and _aud_f == "All QA":
                            st.markdown('<div class="section-chip">👤 QA Breakdown</div>', unsafe_allow_html=True)
                            _cqa = []
                            for _a3, _ag3 in _crp_df.groupby("QA"):
                                _bs3 = pd.to_numeric(_ag3["Bot Score"], errors="coerce")
                                _st3 = _ag3["Status"].astype(str).str.strip()
                                _avg3 = round(_bs3.dropna().mean(),1) if _bs3.dropna().notna().any() else None
                                _pr3 = round(int((_st3=="Pass").sum())/len(_ag3)*100,1) if len(_ag3) else 0
                                _cqa.append({"QA":str(_a3),"Audits":len(_ag3),"Avg Score":f"{_avg3}%" if _avg3 else "—","Pass Rate":f"{_pr3}%","Auto-Fails":int((_st3=="Auto-Fail").sum()),"Needs Review":int((_st3=="Needs Review").sum())})
                            _cqa.sort(key=lambda x:float(x["Avg Score"].rstrip("%")) if x["Avg Score"]!="—" else 0, reverse=True)
                            st.dataframe(pd.DataFrame(_cqa), use_container_width=True, hide_index=True)
                        _render_param_weakness(_crp_df, "rep_camp_pw")
                        _render_entity_insights(_crp_df, "campaign", _sel_camp_r)
                        _dl3, _ = st.columns([1,4])
                        with _dl3:
                            st.download_button("⬇ Download", data=_crp_df.to_csv(index=False).encode("utf-8"),
                                               file_name=f"campaign_{_sel_camp_r.replace(' ','_')}.csv", mime="text/csv", key="dl_camp_rep")

            elif _rep_view == "📋 Full Log":
                _log_fc1, _log_fc2, _log_fc3 = st.columns(3)
                with _log_fc1:
                    _lg_aud = st.selectbox("QA", ["All"] + (sorted(_audit_df_ins["QA"].dropna().astype(str).unique().tolist()) if "QA" in _audit_df_ins.columns else []), key="log_aud_f")
                with _log_fc2:
                    _lg_camp = st.selectbox("Campaign", ["All"] + (sorted(_audit_df_ins["Campaign Name"].dropna().astype(str).unique().tolist()) if "Campaign Name" in _audit_df_ins.columns else []), key="log_camp_f")
                with _log_fc3:
                    _lg_st = st.selectbox("Status", ["All", "Pass", "Needs Review", "Fail", "Auto-Fail"], key="log_st_f")
                _lg_df = _audit_df_ins.copy()
                if _lg_aud  != "All" and "QA"            in _lg_df.columns: _lg_df = _lg_df[_lg_df["QA"].astype(str) == _lg_aud]
                if _lg_camp != "All" and "Campaign Name" in _lg_df.columns: _lg_df = _lg_df[_lg_df["Campaign Name"].astype(str) == _lg_camp]
                if _lg_st   != "All" and "Status"        in _lg_df.columns: _lg_df = _lg_df[_lg_df["Status"].astype(str).str.strip() == _lg_st]
                st.markdown(f'<div style="font-size:0.72rem;color:#5588bb;margin-bottom:6px;">Showing <strong>{len(_lg_df):,}</strong> of {len(_audit_df_ins):,} audits</div>', unsafe_allow_html=True)
                _disp_cols = ["Audit Date","QA","Client","Campaign Name","Disposition","Bot Score","Status","Notes","Improvement Suggestion"]
                _sc5 = [c for c in _disp_cols if c in _lg_df.columns]
                if _sc5:
                    st.dataframe(_lg_df[_sc5].reset_index(drop=True), use_container_width=True, height=360)
                    _dl5, _ = st.columns([1,4])
                    with _dl5:
                        st.download_button("⬇ Download filtered log", data=_lg_df[_sc5].to_csv(index=False).encode("utf-8"),
                                           file_name="audit_log_filtered.csv", mime="text/csv", key="ins_dl_filtered")

            else:  # AI Deep Dive
                ss_key  = "sense_ai_insights"
                err_key = "sense_ai_insights_err"
                _ai_sheet_names = list(_all_sheets.keys()) or ["Audit"]
                if not list(_all_sheets.keys()):
                    _all_sheets = {"Audit": _audit_df_ins} if _audit_df_ins is not None else {}
                _sel = _ai_sheet_names[0]
                if len(_ai_sheet_names) > 1:
                    _sel = st.selectbox("Analyse sheet", _ai_sheet_names, key="sense_ai_sheet_pick")
                _ai_df = _all_sheets.get(_sel, _audit_df_ins if _audit_df_ins is not None else pd.DataFrame())

                if st.session_state.get(ss_key):
                    s = st.session_state[ss_key]
                    def _card(title, items, bg, border, tc, dot):
                        bullets = "".join(f'<div style="display:flex;gap:8px;margin-bottom:6px;"><span style="color:{dot};font-size:0.85rem;flex-shrink:0;">●</span><span style="font-size:0.8rem;color:{tc};line-height:1.5;">{item}</span></div>' for item in items)
                        return f'<div style="background:{bg};border:1px solid {border};border-radius:8px;padding:14px 16px;margin-bottom:12px;"><div style="font-size:0.68rem;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:{dot};margin-bottom:10px;">{title}</div>{bullets}</div>'
                    st.markdown(
                        f'<div style="background:#f0f7ff;border:1px solid #e2e8f0;border-radius:8px;padding:14px 16px;margin-bottom:12px;"><div style="font-size:0.68rem;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#0284c7;margin-bottom:8px;">Dataset Summary</div><div style="font-size:0.84rem;color:#0f172a;line-height:1.6;">{s.get("summary","—")}</div></div>'
                        + _card("Key Trends", s.get("trends",[]), "#f0fdf4","#bbf7d0","#166534","#16a34a")
                        + _card("Anomalies / Red Flags", s.get("anomalies",[]), "#fff7ed","#fed7aa","#9a3412","#ea580c")
                        + _card("Recommended Actions", s.get("recommendations",[]), "#fdf8ff","#f0e8f8","#7a1558","#d22c84"),
                        unsafe_allow_html=True,
                    )
                    col_r, _ = st.columns([1,4])
                    with col_r:
                        if st.button("↺ Regenerate", key="sense_ai_regen", use_container_width=True):
                            st.session_state.pop(ss_key, None); st.session_state.pop(err_key, None); st.rerun()
                else:
                    if st.session_state.get(err_key):
                        st.error(st.session_state[err_key])
                    if st.button(f'✨ Generate AI Insights — "{_sel}"', key="sense_ai_gen", type="primary"):
                        api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
                        if not api_key:
                            st.session_state[err_key] = "ANTHROPIC_API_KEY not found in secrets."; st.rerun()
                        else:
                            num_cols = _ai_df.select_dtypes(include="number").columns.tolist()
                            cat_cols = _ai_df.select_dtypes(exclude="number").columns.tolist()
                            null_pct = round(_ai_df.isnull().sum().sum() / _ai_df.size * 100, 1) if _ai_df.size else 0
                            stats_text = _ai_df[num_cols].describe().round(2).to_string() if num_cols else "No numeric columns."
                            all_sheets_info = "\n".join(f"  - {k}: {len(v)} rows × {len(v.columns)} cols" for k, v in _all_sheets.items())
                            _qa_ctx = ""
                            if _has_qa_ins and _audit_df_ins is not None:
                                _qi3 = _gen_qa_insights(_audit_df_ins)
                                _qa_ctx = "\n\nQA Summary:\n" + "\n".join(f"- {i['title']}: {i['detail']}" for i in _qi3.get("insights",[]))
                            prompt = (
                                f"You are a senior QA analyst for a voice-bot team.\n"
                                f"Analyse the dataset below and return structured insights.\n\n"
                                f"File: {fname}\nSheets:\n{all_sheets_info}\n"
                                f"Analysing: {_sel} ({len(_ai_df)} rows × {len(_ai_df.columns)} cols)\n"
                                f"Columns: {', '.join(_ai_df.columns.tolist())}\n"
                                f"Numeric stats:\n{stats_text}\n\n"
                                f"Sample (first 10 rows):\n{_ai_df.head(10).to_csv(index=False)}"
                                f"{_qa_ctx}\n\n"
                                f'Return ONLY valid JSON: {{"summary":"2-3 sentences","trends":["...","...","..."],"anomalies":["...","...","..."],"recommendations":["...","...","..."]}}'
                            )
                            try:
                                import anthropic as _anthropic, json as _json
                                _client = _anthropic.Anthropic(api_key=api_key)
                                with st.spinner("Analysing with Claude AI…"):
                                    _msg = _client.messages.create(model="claude-haiku-4-5-20251001", max_tokens=900,
                                                                    messages=[{"role":"user","content":prompt}])
                                raw = _msg.content[0].text.strip()
                                if raw.startswith("```"):
                                    raw = raw.split("```")[1]
                                    if raw.startswith("json"): raw = raw[4:]
                                st.session_state[ss_key] = _json.loads(raw)
                                st.session_state.pop(err_key, None)
                            except Exception as e:
                                st.session_state[err_key] = f"AI error: {e}"
                            st.rerun()



def _render_registry():
    """Registry management — add/edit/delete PMs, CMs, QA, and Clients."""
    _registry_init()
    st.markdown('<div class="section-chip">🗂️ Registry Management</div>', unsafe_allow_html=True)
    _reg_tabs = st.tabs(["👤 PM", "👥 CM", "🎯 QA", "🏢 Clients"])

    # ── PM Registry ────────────────────────────────────────────────────────────
    with _reg_tabs[0]:
        _pms = st.session_state.get("sense_registry_pms", [])
        st.markdown(f'<div style="font-size:0.72rem;color:#5588bb;margin-bottom:8px;">{len(_pms)} PMs registered</div>', unsafe_allow_html=True)
        if _pms:
            _pm_html = ""
            for _i, _pm in enumerate(_pms):
                _pm_html += (f'<div style="display:flex;align-items:center;gap:8px;padding:5px 10px;'
                             f'border-bottom:1px solid #edf2fb;">'
                             f'<span style="font-size:0.75rem;font-weight:600;color:#0d1d3a;flex:1;">{_pm}</span>'
                             f'</div>')
            st.markdown(f'<div style="background:#fff;border:1px solid #e4e7ec;border-radius:8px;margin-bottom:10px;">{_pm_html}</div>', unsafe_allow_html=True)
        with st.expander("➕ Add / Remove PM", expanded=False):
            _pc1, _pc2 = st.columns([3,1])
            with _pc1:
                _new_pm = st.text_input("New PM name", placeholder="e.g. Rahul", key="reg_new_pm")
            with _pc2:
                st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
                if st.button("Add PM", key="reg_add_pm", use_container_width=True):
                    _n = _new_pm.strip()
                    if _n and _n not in _pms:
                        _pms.append(_n)
                        _pms.sort()
                        st.session_state["sense_registry_pms"] = _pms
                        _registry_persist()
                        st.rerun()
            if _pms:
                _del_pm = st.selectbox("Remove PM", ["— select —"] + _pms, key="reg_del_pm")
                if st.button("🗑️ Delete PM", key="reg_del_pm_btn", type="secondary"):
                    if _del_pm != "— select —":
                        st.session_state["sense_registry_pms"] = [p for p in _pms if p != _del_pm]
                        _registry_persist()
                        st.rerun()

    # ── CM Registry ────────────────────────────────────────────────────────────
    with _reg_tabs[1]:
        _cms = st.session_state.get("sense_registry_cms", [])
        st.markdown(f'<div style="font-size:0.72rem;color:#5588bb;margin-bottom:8px;">{len(_cms)} CMs registered</div>', unsafe_allow_html=True)
        if _cms:
            _cm_html = ""
            for _cm in _cms:
                _cm_html += (f'<div style="display:flex;align-items:center;padding:5px 10px;'
                             f'border-bottom:1px solid #edf2fb;">'
                             f'<span style="font-size:0.75rem;font-weight:600;color:#0d1d3a;flex:1;">{_cm}</span></div>')
            st.markdown(f'<div style="background:#fff;border:1px solid #e4e7ec;border-radius:8px;margin-bottom:10px;">{_cm_html}</div>', unsafe_allow_html=True)
        with st.expander("➕ Add / Remove CM", expanded=False):
            _cc1, _cc2 = st.columns([3,1])
            with _cc1:
                _new_cm = st.text_input("New CM name", placeholder="e.g. Priya", key="reg_new_cm")
            with _cc2:
                st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
                if st.button("Add CM", key="reg_add_cm", use_container_width=True):
                    _n = _new_cm.strip()
                    if _n and _n not in _cms:
                        _cms.append(_n)
                        _cms.sort()
                        st.session_state["sense_registry_cms"] = _cms
                        _registry_persist()
                        st.rerun()
            if _cms:
                _del_cm = st.selectbox("Remove CM", ["— select —"] + _cms, key="reg_del_cm")
                if st.button("🗑️ Delete CM", key="reg_del_cm_btn", type="secondary"):
                    if _del_cm != "— select —":
                        st.session_state["sense_registry_cms"] = [c for c in _cms if c != _del_cm]
                        _registry_persist()
                        st.rerun()

    # ── QA Registry ────────────────────────────────────────────────────────────
    with _reg_tabs[2]:
        _qas = st.session_state.get("sense_registry_qas", [])
        st.markdown(f'<div style="font-size:0.72rem;color:#5588bb;margin-bottom:8px;">{len(_qas)} QA reviewers registered</div>', unsafe_allow_html=True)
        if _qas:
            _qa_html = ""
            for _qa in _qas:
                _qa_html += (f'<div style="padding:5px 10px;border-bottom:1px solid #edf2fb;">'
                             f'<span style="font-size:0.75rem;font-weight:600;color:#0d1d3a;">{_qa}</span></div>')
            st.markdown(f'<div style="background:#fff;border:1px solid #e4e7ec;border-radius:8px;margin-bottom:10px;">{_qa_html}</div>', unsafe_allow_html=True)
        with st.expander("➕ Add / Remove QA", expanded=False):
            _qc1, _qc2 = st.columns([3,1])
            with _qc1:
                _new_qa = st.text_input("New QA name", placeholder="e.g. Rohit", key="reg_new_qa")
            with _qc2:
                st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
                if st.button("Add QA", key="reg_add_qa", use_container_width=True):
                    _n = _new_qa.strip()
                    if _n and _n not in _qas:
                        _qas.append(_n)
                        st.session_state["sense_registry_qas"] = _qas
                        _registry_persist()
                        st.rerun()
            if _qas:
                _del_qa = st.selectbox("Remove QA", ["— select —"] + _qas, key="reg_del_qa")
                if st.button("🗑️ Delete QA", key="reg_del_qa_btn", type="secondary"):
                    if _del_qa != "— select —":
                        st.session_state["sense_registry_qas"] = [q for q in _qas if q != _del_qa]
                        _registry_persist()
                        st.rerun()

    # ── Client Registry ────────────────────────────────────────────────────────
    with _reg_tabs[3]:
        _clients_reg = st.session_state.get("sense_registry_clients", [])
        _pms_reg     = st.session_state.get("sense_registry_pms", [])
        _cms_reg     = st.session_state.get("sense_registry_cms", [])
        _status_opts = ["Active", "Hold", "Live", "Self-Serve Live", "Onboarding", "Campaigns Over", "Sales Negotiation"]
        st.markdown(f'<div style="font-size:0.72rem;color:#5588bb;margin-bottom:8px;">{len(_clients_reg)} clients registered</div>', unsafe_allow_html=True)
        if _clients_reg:
            _cli_df_show = pd.DataFrame([{"Client": c["client"], "PM": c.get("pm",""), "CM": c.get("cm",""), "Status": c.get("status","")} for c in _clients_reg])
            st.dataframe(_cli_df_show, use_container_width=True, hide_index=True, height=220)
        with st.expander("➕ Add Client", expanded=False):
            _clc1, _clc2, _clc3, _clc4 = st.columns(4)
            with _clc1:
                _new_cli_name = st.text_input("Client Name *", placeholder="e.g. HDFC Bank", key="reg_new_cli_name")
            with _clc2:
                _new_cli_pm = st.selectbox("PM", [""] + _pms_reg, key="reg_new_cli_pm")
            with _clc3:
                _new_cli_cm = st.selectbox("CM", [""] + _cms_reg, key="reg_new_cli_cm") if _cms_reg else st.text_input("CM", key="reg_new_cli_cm_txt")
            with _clc4:
                _new_cli_status = st.selectbox("Status", _status_opts, key="reg_new_cli_status")
            if st.button("➕ Add Client", key="reg_add_cli", type="primary"):
                _n = _new_cli_name.strip()
                _existing_names = [c["client"] for c in _clients_reg]
                if _n and _n not in _existing_names:
                    _clients_reg.append({"client": _n, "pm": _new_cli_pm, "cm": _new_cli_cm if isinstance(_new_cli_cm, str) else "", "status": _new_cli_status})
                    st.session_state["sense_registry_clients"] = _clients_reg
                    _registry_persist()
                    st.rerun()
                elif _n in _existing_names:
                    st.warning(f"Client '{_n}' already exists.")
        with st.expander("✏️ Edit Client", expanded=False):
            _cli_names_reg = [c["client"] for c in _clients_reg]
            _edit_cli_sel = st.selectbox("Select client to edit", ["— select —"] + _cli_names_reg, key="reg_edit_cli_sel")
            if _edit_cli_sel != "— select —":
                _edit_idx = next((i for i, c in enumerate(_clients_reg) if c["client"] == _edit_cli_sel), None)
                if _edit_idx is not None:
                    _ec = _clients_reg[_edit_idx]
                    _ec1, _ec2, _ec3, _ec4 = st.columns(4)
                    with _ec1:
                        _edit_cli_name = st.text_input("Client Name", value=_ec["client"], key="reg_edit_cli_name")
                    with _ec2:
                        _edit_pm_opts = [""] + _pms_reg
                        _edit_pm_idx  = _edit_pm_opts.index(_ec.get("pm","")) if _ec.get("pm","") in _edit_pm_opts else 0
                        _edit_cli_pm  = st.selectbox("PM", _edit_pm_opts, index=_edit_pm_idx, key="reg_edit_cli_pm")
                    with _ec3:
                        _edit_cm_opts = [""] + _cms_reg
                        _edit_cm_idx  = _edit_cm_opts.index(_ec.get("cm","")) if _ec.get("cm","") in _edit_cm_opts else 0
                        _edit_cli_cm  = st.selectbox("CM", _edit_cm_opts, index=_edit_cm_idx, key="reg_edit_cli_cm") if _cms_reg else st.text_input("CM", value=_ec.get("cm",""), key="reg_edit_cli_cm_txt")
                    with _ec4:
                        _edit_st_idx  = _status_opts.index(_ec.get("status","Active")) if _ec.get("status","Active") in _status_opts else 0
                        _edit_cli_st  = st.selectbox("Status", _status_opts, index=_edit_st_idx, key="reg_edit_cli_st")
                    if st.button("💾 Save Changes", key="reg_edit_cli_save", type="primary"):
                        _clients_reg[_edit_idx] = {"client": _edit_cli_name.strip() or _edit_cli_sel, "pm": _edit_cli_pm, "cm": _edit_cli_cm if isinstance(_edit_cli_cm, str) else "", "status": _edit_cli_st}
                        st.session_state["sense_registry_clients"] = _clients_reg
                        _registry_persist()
                        st.rerun()
        with st.expander("🗑️ Delete Client", expanded=False):
            _del_cli_sel = st.selectbox("Select client to delete", ["— select —"] + [c["client"] for c in _clients_reg], key="reg_del_cli_sel")
            if st.button("🗑️ Delete Client", key="reg_del_cli_btn", type="secondary"):
                if _del_cli_sel != "— select —":
                    st.session_state["sense_registry_clients"] = [c for c in _clients_reg if c["client"] != _del_cli_sel]
                    _registry_persist()
                    st.rerun()



_TYPE_LABELS = {
    "dropdown": "📋 Dropdown",
    "scoring":  "⭐ Scoring (1–5)",
    "number":   "🔢 Number",
    "text":     "✏️ Text",
}
_TYPE_KEYS = list(_TYPE_LABELS.keys())


def _render_param_manager(key_sfx=""):
    """Custom parameter manager — add/edit/delete persisted custom audit params with input types."""
    if "sense_custom_audit_params" not in st.session_state:
        st.session_state["sense_custom_audit_params"] = param_store.load()
    _ks  = key_sfx
    _cps = st.session_state["sense_custom_audit_params"]

    st.markdown('<div class="section-chip">⭐ Custom Parameters</div>', unsafe_allow_html=True)

    # ── Existing params ────────────────────────────────────────────────────────
    if _cps:
        for _cpi, _cp in enumerate(_cps):
            _itype   = _cp.get("input_type", "dropdown")
            _lbl     = _TYPE_LABELS.get(_itype, _itype)
            _editing = st.session_state.get(f"pm_editing_{_cpi}{_ks}", False)

            _ca, _cb, _cc = st.columns([5, 1, 1])
            with _ca:
                _guide_txt = f' <span style="color:#94a3b8;font-size:0.7rem;">— {_cp["guide"]}</span>' if _cp.get("guide") else ""
                _badge_col = {"dropdown": "#dbeafe", "scoring": "#fef9c3", "number": "#f0fdf4", "text": "#f3e8ff"}.get(_itype, "#f1f5f9")
                _badge_txt = {"dropdown": "#1d4ed8", "scoring": "#854d0e", "number": "#166534", "text": "#6b21a8"}.get(_itype, "#475569")
                st.markdown(
                    f'<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;'
                    f'padding:8px 14px;font-size:0.82rem;font-weight:600;color:#166534;display:flex;align-items:center;gap:8px;">'
                    f'⭐ {_cp["name"]}{_guide_txt}'
                    f'<span style="margin-left:auto;background:{_badge_col};color:{_badge_txt};'
                    f'font-size:0.65rem;font-weight:700;padding:2px 7px;border-radius:99px;">{_lbl}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with _cb:
                if st.button("✏️", key=f"pm_edit_{_cpi}{_ks}", help="Edit", use_container_width=True):
                    st.session_state[f"pm_editing_{_cpi}{_ks}"] = not _editing
                    st.rerun()
            with _cc:
                if st.button("🗑", key=f"pm_del_{_cpi}{_ks}", help=f"Delete '{_cp['name']}'", use_container_width=True):
                    _del_err = param_store.remove(_cp["name"])
                    if _del_err:
                        st.error(f"Delete failed: {_del_err}")
                    else:
                        st.session_state["sense_custom_audit_params"] = [
                            p for p in _cps if p["name"] != _cp["name"]
                        ]
                        st.session_state.pop(f"pm_editing_{_cpi}{_ks}", None)
                        st.rerun()

            if st.session_state.get(f"pm_editing_{_cpi}{_ks}", False):
                with st.container():
                    st.markdown('<div style="background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:10px 14px;margin:4px 0 8px 0;">', unsafe_allow_html=True)
                    _e1, _e2 = st.columns([2, 3])
                    with _e1:
                        _e_type = st.selectbox(
                            "Input Type",
                            _TYPE_KEYS,
                            index=_TYPE_KEYS.index(_itype) if _itype in _TYPE_KEYS else 0,
                            format_func=lambda k: _TYPE_LABELS[k],
                            key=f"pm_e_type_{_cpi}{_ks}",
                        )
                    with _e2:
                        _e_guide = st.text_input("Remarks", value=_cp.get("guide", ""), key=f"pm_e_guide_{_cpi}{_ks}", placeholder="Auditor guidance")
                    if _e_type == "dropdown":
                        _e_opts_raw = st.text_input(
                            "Options (comma-separated)",
                            value=", ".join(_cp.get("options", ["Yes", "No"])),
                            key=f"pm_e_opts_{_cpi}{_ks}",
                            placeholder="Yes, No, NA",
                        )
                        _e_opts = [o.strip() for o in _e_opts_raw.split(",") if o.strip()] or ["Yes", "No"]
                    else:
                        _e_opts = _cp.get("options", ["Yes", "No"])

                    _save_col, _cancel_col = st.columns([1, 1])
                    with _save_col:
                        if st.button("💾 Save Changes", key=f"pm_e_save_{_cpi}{_ks}", use_container_width=True, type="primary"):
                            _upd_err = param_store.update(_cp["name"], _e_opts, _e_guide, _e_type)
                            if _upd_err:
                                st.error(f"Save failed: {_upd_err}")
                            else:
                                st.session_state["sense_custom_audit_params"][_cpi] = {
                                    **_cp,
                                    "options":    _e_opts,
                                    "guide":      _e_guide,
                                    "input_type": _e_type,
                                }
                                st.session_state[f"pm_editing_{_cpi}{_ks}"] = False
                                st.rerun()
                    with _cancel_col:
                        if st.button("✕ Cancel", key=f"pm_e_cancel_{_cpi}{_ks}", use_container_width=True):
                            st.session_state[f"pm_editing_{_cpi}{_ks}"] = False
                            st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.caption("No custom parameters yet. Add one below.")

    # ── Add form ──────────────────────────────────────────────────────────────
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    st.markdown('<div style="font-size:0.7rem;font-weight:700;color:#64748b;letter-spacing:0.07em;text-transform:uppercase;margin-bottom:6px;">Add New Parameter</div>', unsafe_allow_html=True)

    _pa, _pb, _pc = st.columns([2.5, 2, 1.5])
    with _pa:
        _new_name = st.text_input("Parameter Name", placeholder="e.g. Empathy Check", key=f"pm_new_name{_ks}", label_visibility="collapsed")
    with _pb:
        _new_remarks = st.text_input("Remarks (optional)", placeholder="Auditor guidance", key=f"pm_new_remarks{_ks}", label_visibility="collapsed")
    with _pc:
        _new_type = st.selectbox(
            "Type",
            _TYPE_KEYS,
            format_func=lambda k: _TYPE_LABELS[k],
            key=f"pm_new_type{_ks}",
            label_visibility="collapsed",
        )

    if _new_type == "dropdown":
        _new_opts_raw = st.text_input(
            "Dropdown Options",
            placeholder="Yes, No, NA",
            key=f"pm_new_opts{_ks}",
            help="Comma-separated values",
        )
        _new_opts = [o.strip() for o in _new_opts_raw.split(",") if o.strip()] or ["Yes", "No"]
    else:
        _new_opts = ["Yes", "No"]

    _add_btn = st.button("➕ Add Parameter", key=f"pm_add_param{_ks}", use_container_width=True, type="primary")

    if _add_btn:
        if not _new_name.strip():
            st.warning("Enter a parameter name.")
        elif _new_name.strip().lower() in [p["name"].lower() for p in _cps]:
            st.warning("A parameter with that name already exists.")
        else:
            _err = param_store.add(_new_name.strip(), _new_opts, _new_remarks.strip(), _new_type)
            if _err:
                st.error(f"Could not save: {_err}")
            else:
                st.session_state["sense_custom_audit_params"].append({
                    "name":       _new_name.strip(),
                    "options":    _new_opts,
                    "guide":      _new_remarks.strip(),
                    "input_type": _new_type,
                })
                st.rerun()


def _render_audit_form(legend_map, fname):
    """Convin Sense QA audit form — exact Convin.ai schema, all fields mandatory, auto-scoring."""
    # Always reload from Supabase on each render so data is never stale
    st.session_state["sense_audit_log"] = _audit_log_load()
    audit_log = st.session_state["sense_audit_log"]

    # ── "What's new" banner ────────────────────────────────────────────────────
    st.markdown("""
<div style="background:linear-gradient(120deg,#0d1d3a 0%,#1e3a5f 50%,#1a2d50 100%);
  border-radius:14px;padding:20px 24px;margin-bottom:1.4rem;position:relative;overflow:hidden;">
  <div style="position:absolute;top:-20px;right:-20px;width:120px;height:120px;
    background:rgba(61,142,245,0.12);border-radius:50%;"></div>
  <div style="position:absolute;bottom:-30px;left:40%;width:180px;height:180px;
    background:rgba(37,99,235,0.07);border-radius:50%;"></div>
  <div style="display:flex;align-items:flex-start;gap:16px;position:relative;">
    <div style="background:linear-gradient(135deg,#0B1F3A,#2563EB);border-radius:10px;
      padding:10px;flex-shrink:0;font-size:1.3rem;">🚀</div>
    <div>
      <div style="font-size:1rem;font-weight:900;color:#fff;letter-spacing:-0.01em;margin-bottom:4px;">
        Audit &amp; QA Intelligence Engine</div>
      <div style="font-size:0.74rem;color:#93c5fd;margin-bottom:12px;">
        Fully automated · Zero manual dependency · Real-time scoring</div>
      <div style="display:flex;flex-wrap:wrap;gap:8px;">
        <span style="background:rgba(14,188,110,0.15);border:1px solid rgba(14,188,110,0.3);
          border-radius:6px;padding:4px 10px;font-size:0.66rem;font-weight:700;color:#6ee7b7;">
          ✓ Flow Issue · Bot Restart · Bot Repetition</span>
        <span style="background:rgba(220,38,38,0.15);border:1px solid rgba(220,38,38,0.3);
          border-radius:6px;padding:4px 10px;font-size:0.66rem;font-weight:700;color:#fca5a5;">
          ⚠️ Auto-Fail for Fatal triggers</span>
        <span style="background:rgba(61,142,245,0.15);border:1px solid rgba(61,142,245,0.3);
          border-radius:6px;padding:4px 10px;font-size:0.66rem;font-weight:700;color:#93c5fd;">
          📊 Critical 61% · Important 28% · Quality 11%</span>
        <span style="background:rgba(124,58,237,0.15);border:1px solid rgba(124,58,237,0.3);
          border-radius:6px;padding:4px 10px;font-size:0.66rem;font-weight:700;color:#c4b5fd;">
          🎯 Pass ≥80 · Review 60-79 · Fail &lt;60</span>
      </div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

    # ── Schema overview: tiers with embedded intelligence params ──────────────
    st.markdown('<div class="section-chip">⚖️ Scoring Schema</div>', unsafe_allow_html=True)
    _tier_html = '<div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:1.2rem;">'
    for _ti, _tier in enumerate(_QA_SCHEMA["tiers"]):
        _tc = _tier["color"]
        _params_list = "  ·  ".join(p["col"] for p in _tier["params"])
        _ip = _QA_SCHEMA["intelligence"][_ti] if _ti < len(_QA_SCHEMA["intelligence"]) else None
        _ip_badge = ""
        if _ip:
            _ip_badge = (
                f'<div style="margin-top:7px;padding-top:7px;border-top:1px dashed rgba(37,99,235,0.25);">'
                f'<span style="display:inline-flex;align-items:center;gap:4px;background:rgba(37,99,235,0.08);'
                f'border:1px solid rgba(37,99,235,0.22);border-radius:5px;padding:2px 8px;">'
                f'<span style="font-size:0.68rem;">🧠</span>'
                f'<span style="font-size:0.62rem;font-weight:700;color:#2563EB;">{_ip["icon"]} {_ip["col"]}</span>'
                f'</span>'
                f'<span style="font-size:0.58rem;color:#aabbcc;margin-left:5px;">{" · ".join(_ip["options"])}</span>'
                f'</div>'
            )
        _tier_html += (
            f'<div style="flex:1;min-width:210px;background:#fff;border:1px solid {_tc}33;'
            f'border-top:3px solid {_tc};border-radius:10px;padding:10px 14px;">'
            f'<div style="font-size:0.68rem;font-weight:800;letter-spacing:0.08em;color:{_tc};'
            f'text-transform:uppercase;margin-bottom:4px;">{_tier["label"]} ({_tier["weight_pct"]}%)</div>'
            f'<div style="font-size:0.63rem;color:#5588bb;line-height:1.7;">{_params_list}</div>'
            f'{_ip_badge}'
            f'</div>'
        )
    _tier_html += '</div>'
    st.markdown(_tier_html, unsafe_allow_html=True)

    # ── Bulk Lead Import ─────────────────────────────────────────────────────
    with st.expander("📥 Bulk Import Leads (Client · Campaign · Lead No · Phone · Links)", expanded=False):
        st.markdown(
            '<div style="font-size:0.72rem;color:#5588bb;margin-bottom:8px;">'
            'Upload a CSV/Excel or paste data with columns: '
            '<strong>Client, Campaign Name, Lead Number, Phone Number, Lead Link, Conversation Link</strong> '
            '(all columns are optional except Client &amp; Campaign Name)</div>',
            unsafe_allow_html=True,
        )
        _bulk_tab1, _bulk_tab2 = st.tabs(["📤 Upload File", "📋 Paste CSV"])
        with _bulk_tab1:
            _bulk_file = st.file_uploader("Upload CSV or Excel", type=["csv","xlsx","xls"], key="bulk_lead_upload")
            if _bulk_file:
                try:
                    if _bulk_file.name.endswith((".xlsx",".xls")):
                        _bulk_df = pd.read_excel(_bulk_file)
                    else:
                        _bulk_df = pd.read_csv(_bulk_file)
                    _bulk_df.columns = [str(c).strip() for c in _bulk_df.columns]
                    st.dataframe(_bulk_df.head(10), use_container_width=True, hide_index=True)
                    if st.button("➕ Add to Lead Queue", key="bulk_add_file_btn", type="primary"):
                        _existing_q = st.session_state.get("sense_lead_queue", [])
                        _new_q = _bulk_df.to_dict("records")
                        st.session_state["sense_lead_queue"] = _existing_q + _new_q
                        st.success(f"✅ {len(_new_q)} leads added to queue.")
                        st.rerun()
                except Exception as _be:
                    st.error(f"Error reading file: {_be}")
        with _bulk_tab2:
            _paste_help = "Client,Campaign Name,Lead Number,Phone Number,Lead Link,Conversation Link\nHDFC,Q2 Campaign,LD-001,9876543210,https://...,https://..."
            _pasted = st.text_area("Paste CSV data (with header row)", placeholder=_paste_help, height=120, key="bulk_paste_csv")
            if st.button("➕ Add Pasted Leads", key="bulk_add_paste_btn", type="primary"):
                try:
                    import io as _io
                    _pasted_df = pd.read_csv(_io.StringIO(_pasted.strip()))
                    _pasted_df.columns = [str(c).strip() for c in _pasted_df.columns]
                    _existing_q = st.session_state.get("sense_lead_queue", [])
                    _new_q = _pasted_df.to_dict("records")
                    st.session_state["sense_lead_queue"] = _existing_q + _new_q
                    st.success(f"✅ {len(_new_q)} leads added to queue.")
                    st.rerun()
                except Exception as _pe:
                    st.error(f"Parse error: {_pe}")

        # Show queue
        _lead_q = st.session_state.get("sense_lead_queue", [])
        if _lead_q:
            st.markdown(f'<div style="font-size:0.72rem;color:#2563EB;margin-top:8px;font-weight:700;">{len(_lead_q)} leads in queue</div>', unsafe_allow_html=True)
            _q_df_show = pd.DataFrame(_lead_q)
            _q_cols_show = [c for c in ["Client","Campaign Name","Lead Number","Phone Number","Lead Link","Conversation Link"] if c in _q_df_show.columns]
            if _q_cols_show:
                st.dataframe(_q_df_show[_q_cols_show].head(20), use_container_width=True, hide_index=True, height=180)
            _qcl1, _qcl2 = st.columns([1,4])
            with _qcl1:
                if st.button("🗑️ Clear Queue", key="bulk_clear_queue", type="secondary", use_container_width=True):
                    st.session_state["sense_lead_queue"] = []
                    st.rerun()

    # ── AI Suggestion Builder (outside form — AI calls need rerun) ───────────
    with st.expander("✨ AI Suggestion Builder — draft & improve before submitting", expanded=False):
        st.markdown(
            '<div style="font-size:0.72rem;color:#5588bb;margin-bottom:8px;">'
            'Type an improvement suggestion (bot script, coaching note, fix idea). '
            'Click <strong>🤖 AI Improve</strong> to have Claude rewrite it as a crisp, actionable recommendation — '
            'then it auto-fills the Improvement Suggestion field in the audit form below.</div>',
            unsafe_allow_html=True,
        )
        _sug_draft = st.text_area(
            "Draft suggestion",
            value=st.session_state.get("_audit_suggestion_draft", ""),
            placeholder="e.g. 'bot misses DM confirmation — it should ask clearly if the decision maker is available before continuing'",
            height=80,
            key="sug_draft_input",
        )
        _sug_c1, _sug_c2, _sug_c3 = st.columns([2, 2, 3])
        with _sug_c1:
            if st.button("🤖 AI Verify & Improve", key="sug_ai_improve_btn", use_container_width=True, type="primary"):
                _raw_draft = _sug_draft.strip()
                if not _raw_draft:
                    st.warning("Type a suggestion first.")
                else:
                    _api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
                    if not _api_key:
                        st.error("ANTHROPIC_API_KEY not found in secrets.")
                    else:
                        try:
                            import anthropic as _anth
                            _anth_client = _anth.Anthropic(api_key=_api_key)
                            with st.spinner("Improving with Claude…"):
                                _sug_msg = _anth_client.messages.create(
                                    model="claude-haiku-4-5-20251001",
                                    max_tokens=300,
                                    messages=[{"role": "user", "content": (
                                        "You are a QA lead for a voice-bot team. "
                                        "Rewrite the following raw suggestion as a single, crisp, actionable improvement recommendation (2-3 sentences max). "
                                        "Keep it concrete — name the bot behaviour to fix, the desired behaviour, and the expected outcome. "
                                        "Do NOT add greetings or preamble.\n\n"
                                        f"Raw suggestion: {_raw_draft}"
                                    )}],
                                )
                            _improved = _sug_msg.content[0].text.strip()
                            st.session_state["_audit_suggestion_draft"]    = _improved
                            st.session_state["_audit_suggestion_improved"] = True
                            st.rerun()
                        except Exception as _sug_e:
                            st.error(f"AI error: {_sug_e}")
        with _sug_c2:
            if st.button("✕ Clear", key="sug_clear_btn", use_container_width=True):
                st.session_state.pop("_audit_suggestion_draft", None)
                st.session_state.pop("_audit_suggestion_improved", None)
                st.rerun()
        if st.session_state.get("_audit_suggestion_improved") and st.session_state.get("_audit_suggestion_draft"):
            st.markdown(
                f'<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-left:4px solid #0ebc6e;'
                f'border-radius:8px;padding:10px 14px;margin-top:8px;">'
                f'<div style="font-size:0.65rem;font-weight:700;color:#14532d;margin-bottom:4px;">✅ AI-Improved — will auto-fill below</div>'
                f'<div style="font-size:0.78rem;color:#166534;line-height:1.6;">{st.session_state["_audit_suggestion_draft"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ── Audit form ────────────────────────────────────────────────────────────
    st.markdown("""
<style>
/* Tick-mark style for QA scoring radio buttons */
div[data-testid="stRadio"] > div[role="radiogroup"] {
    display: flex !important;
    flex-wrap: wrap !important;
    gap: 6px !important;
    margin-top: 4px !important;
}
div[data-testid="stRadio"] > div[role="radiogroup"] > label {
    background: rgba(61,130,245,0.06) !important;
    border: 1.5px solid rgba(61,130,245,0.22) !important;
    border-radius: 8px !important;
    padding: 5px 14px !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    color: #1e3a5f !important;
    cursor: pointer !important;
    transition: background 0.15s, border-color 0.15s !important;
    min-width: 44px !important;
    text-align: center !important;
}
div[data-testid="stRadio"] > div[role="radiogroup"] > label > div:last-child {
    color: inherit !important;
}
div[data-testid="stRadio"] > div[role="radiogroup"] > label:hover {
    background: rgba(61,130,245,0.13) !important;
    border-color: rgba(61,130,245,0.5) !important;
}
div[data-testid="stRadio"] > div[role="radiogroup"] > label:has(input:checked) {
    background: linear-gradient(135deg,#0B1F3A,#2563EB) !important;
    border-color: transparent !important;
    color: #fff !important;
}
div[data-testid="stRadio"] > div[role="radiogroup"] > label > div:first-child {
    display: none !important;
}
/* NA option (3rd label) in Correct Disposition radio — visually muted */
div[data-testid="stRadio"][aria-label="Correct Disposition? *"] > div[role="radiogroup"] > label:nth-child(3),
div[data-testid="stForm"] div[data-testid="stRadio"]:has(label[data-testid]) > div[role="radiogroup"] > label:nth-child(3) {
    background: rgba(148,163,184,0.08) !important;
    border-color: rgba(148,163,184,0.25) !important;
    color: #94a3b8 !important;
}
div[data-testid="stRadio"] > div[role="radiogroup"] > label:nth-child(3):has(input:checked) {
    background: rgba(148,163,184,0.2) !important;
    border-color: rgba(148,163,184,0.4) !important;
    color: #64748b !important;
}
/* Submit audit button — blue bg white text */
div[data-testid="stForm"] div[data-testid="stFormSubmitButton"] > button[kind="primaryFormSubmit"],
div[data-testid="stForm"] div[data-testid="stFormSubmitButton"] > button {
    background: linear-gradient(135deg,#1a62f2,#2563EB) !important;
    color: #ffffff !important;
    border: none !important;
    font-weight: 700 !important;
    letter-spacing: 0.02em !important;
}
div[data-testid="stForm"] div[data-testid="stFormSubmitButton"] > button:hover {
    background: linear-gradient(135deg,#1550d4,#1d4ed8) !important;
    color: #ffffff !important;
}
</style>""", unsafe_allow_html=True)
    st.markdown('<div class="section-chip">✍️ New QA Audit — Convin.ai Standard Sheet</div>', unsafe_allow_html=True)

    with st.form("qa_audit_form_v2", clear_on_submit=False):
        # ── Queue selector ────────────────────────────────────────────────────
        def _qv(rec, key):
            v = rec.get(key, "")
            return "" if (v is None or (isinstance(v, float) and v != v) or str(v).strip() in ("nan","None","")) else str(v).strip()
        _lead_q_form = st.session_state.get("sense_lead_queue", [])
        if _lead_q_form:
            _q_labels = ["— type manually —"] + [
                f"{r.get('Client','?')} · {r.get('Campaign Name','?')} · {r.get('Lead Number', r.get('Phone Number','#'+str(i+1)))}"
                for i, r in enumerate(_lead_q_form)
            ]
            _q_sel = st.selectbox("📋 Pick lead from queue (auto-fills fields)", _q_labels, key="f_queue_sel")
            _q_idx = _q_labels.index(_q_sel) - 1 if _q_sel != "— type manually —" else -1
            _q_rec = _lead_q_form[_q_idx] if _q_idx >= 0 else {}
            if _q_idx >= 0:
                st.markdown(f'<div style="font-size:0.65rem;color:#0ebc6e;margin-bottom:6px;">✅ Pre-filling from queue record {_q_idx+1}</div>', unsafe_allow_html=True)
        else:
            _q_rec = {}
            _q_idx = -1

        # ── Audit & Lead details ──────────────────────────────────────────────
        st.markdown(
            '<div style="font-size:0.68rem;font-weight:700;color:#2a5080;letter-spacing:0.08em;'
            'text-transform:uppercase;margin-bottom:6px;">Audit Details</div>',
            unsafe_allow_html=True,
        )
        _ad1, _ad2, _ad3, _ad4 = st.columns(4)
        with _ad1:
            _f_audit_date = st.date_input("Audit Date *", value=pd.Timestamp.now().date())
        with _ad2:
            _registry_init()
            _reg_qas_form = [""] + st.session_state.get("sense_registry_qas", ["Animesh", "Shubham", "Aman", "Navya", "Alan"])
            _f_auditor = st.selectbox("QA *", _reg_qas_form, key="f_auditor_sel")
        with _ad3:
            _registry_init()
            _reg_clients_form = [""] + [c["client"] for c in st.session_state.get("sense_registry_clients", _SENSE_CLIENTS)]
            _q_client_val = _qv(_q_rec, "Client")
            _q_client_idx = _reg_clients_form.index(_q_client_val) if _q_client_val in _reg_clients_form else 0
            _f_client = st.selectbox("Client *", _reg_clients_form, index=_q_client_idx, key="f_client_sel")
        with _ad4:
            _f_campaign   = st.text_input("Campaign Name *", value=_qv(_q_rec,"Campaign Name"), placeholder="e.g. Q2 Outreach")

        _ld1, _ld2, _ld3 = st.columns(3)
        with _ld1:
            _reg_client_map_form = {c["client"]: c for c in st.session_state.get("sense_registry_clients", _SENSE_CLIENTS)}
            _auto_pm  = _reg_client_map_form.get(_f_client, {}).get("pm", "") or _SENSE_CLIENT_MAP.get(_f_client, {}).get("pm", "")
            _pm_opts  = [""] + st.session_state.get("sense_registry_pms", sorted(set(r["pm"] for r in _SENSE_CLIENTS)))
            _pm_idx   = _pm_opts.index(_auto_pm) if _auto_pm in _pm_opts else 0
            _f_pm_csm = st.selectbox("PM / CSM *", _pm_opts, index=_pm_idx, key="f_pm_csm_sel")
        with _ld2:
            _f_lead_no    = st.text_input("Lead Number", value=_qv(_q_rec,"Lead Number"), placeholder="e.g. LD-20250422")
        with _ld3:
            _f_conv_link  = st.text_input("Conversation Link", value=_qv(_q_rec,"Conversation Link"), placeholder="https://...")

        _ll1, _ll2, _ll3, _ll4 = st.columns(4)
        with _ll1:
            _f_lead_link  = st.text_input("Lead Link", value=_qv(_q_rec,"Lead Link"), placeholder="https://...")
        with _ll2:
            _disp_opts = ["— select —", "Hot", "Warm", "Cold", "Interested", "Warm Follow-up", "Not Interested", "Converted", "DNC", "Wrong Number", "Language Barrier", "Voicemail / No Answer", "Other"]
            _f_disposition = st.selectbox("Disposition *", _disp_opts, key="f_disposition_sel")
        with _ll3:
            _f_bot_name = st.text_input("Bot Name *", value=_qv(_q_rec, "Bot Name"), placeholder="e.g. Convin-LeadBot-v2")
        with _ll4:
            _f_correct_disp = st.radio(
                "Correct Disposition? *",
                ["Yes", "No", "NA"],
                index=2,
                horizontal=True,
                key="f_correct_disp",
            )

        _f_correct_disp_text = st.text_input(
            "Correct Disposition (leave blank if correct)",
            placeholder="e.g. Not Interested, Warm Follow-up…",
            key="f_correct_disp_text",
        )
        _f_call_drop_stage = ""

        st.markdown(
            '<hr style="border:none;border-top:1px solid rgba(61,130,245,0.1);margin:10px 0 4px;">',
            unsafe_allow_html=True,
        )

        # ── QA parameter scoring — tiers with embedded intelligence params ───────
        _pv = {}
        for _ti, _tier in enumerate(_QA_SCHEMA["tiers"]):
            _tc = _tier["color"]
            _ip = _QA_SCHEMA["intelligence"][_ti] if _ti < len(_QA_SCHEMA["intelligence"]) else None

            # Tier header
            _ip_badge_inline = (
                f' <span style="background:rgba(37,99,235,0.12);border:1px solid rgba(37,99,235,0.3);'
                f'border-radius:4px;padding:1px 7px;font-size:0.58rem;font-weight:700;color:#2563EB;">'
                f'🧠 +{_ip["icon"]} {_ip["col"]}</span>'
            ) if _ip else ""
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:8px;font-size:0.68rem;font-weight:700;'
                f'letter-spacing:0.08em;text-transform:uppercase;color:{_tc};margin:12px 0 6px;">'
                f'{_tier["label"]} ({_tier["weight_pct"]}%){_ip_badge_inline}</div>',
                unsafe_allow_html=True,
            )

            # Tier params (2 per row for tick-mark radio layout)
            _params = _tier["params"]
            for _ri in range(0, len(_params), 2):
                _batch = _params[_ri: _ri + 2]
                _wcols = st.columns(len(_batch))
                for _wc, _p in zip(_wcols, _batch):
                    with _wc:
                        _wt  = f" ({int(_p['weight']*100)}%)" if _p["weight"] > 0 else (" ⚠️ FATAL" if _p.get("fatal") else "")
                        _key = f"af_t_{_p['col'][:22].replace(' ','_').replace('/','_').replace('(','').replace(')','')}"
                        _tick_opts = _p["options"] + ["NA"]
                        _pv[_p["col"]] = st.radio(
                            f"{_p['col']}{_wt} *",
                            _tick_opts,
                            index=len(_tick_opts) - 1,
                            horizontal=True,
                            key=_key,
                            help=_p.get("guide", ""),
                        )

            # Intelligence param embedded at bottom of this tier
            if _ip:
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:6px;margin:6px 0 4px;">'
                    f'<div style="flex:1;height:1px;background:rgba(37,99,235,0.15);"></div>'
                    f'<span style="font-size:0.62rem;font-weight:700;color:#2563EB;white-space:nowrap;">'
                    f'🧠 Sense Intelligence</span>'
                    f'<div style="flex:1;height:1px;background:rgba(37,99,235,0.15);"></div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                _icol1, _icol2 = st.columns(2)
                with _icol1:
                    _ikey = f"af_i_{_ip['col'][:20].replace(' ','_')}"
                    _itick_opts = _ip["options"] + ["NA"]
                    _pv[_ip["col"]] = st.radio(
                        f"{_ip['icon']} {_ip['col']} *",
                        _itick_opts,
                        index=len(_itick_opts) - 1,
                        horizontal=True,
                        key=_ikey,
                        help=_ip.get("guide", _ip["desc"]),
                    )

        # ── Custom parameters (Yes / No + comment) ───────────────────────────
        if "sense_custom_audit_params" not in st.session_state:
            st.session_state["sense_custom_audit_params"] = param_store.load()
        _custom_params = st.session_state["sense_custom_audit_params"]
        if _custom_params:
            st.markdown(
                '<hr style="border:none;border-top:1px solid rgba(61,130,245,0.1);margin:10px 0 4px;">',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.08em;'
                'text-transform:uppercase;color:#0ebc6e;margin-bottom:6px;">⭐ Custom Parameters</div>',
                unsafe_allow_html=True,
            )
            for _cp in _custom_params:
                _cp_key = f"af_cp_{_cp['name'][:22].replace(' ','_').replace('/','_')}"
                _cp_cmt_key = f"af_cp_cmt_{_cp['name'][:22].replace(' ','_').replace('/','_')}"
                _cp_stage_key = f"af_cp_stage_{_cp['name'][:22].replace(' ','_').replace('/','_')}"
                _cpa, _cpb, _cpb2, _cpc = st.columns([3, 1, 1, 3])
                with _cpa:
                    _guide = _cp.get("guide", "")
                    _guide_html = f'<div style="font-size:0.65rem;color:#94a3b8;margin-top:2px;">{_guide}</div>' if _guide else ""
                    st.markdown(
                        f'<div style="padding:8px 0 4px;">'
                        f'<div style="font-size:0.82rem;font-weight:700;color:#0d1d3a;">⭐ {_cp["name"]} *</div>'
                        f'{_guide_html}</div>',
                        unsafe_allow_html=True,
                    )
                with _cpb:
                    _pv[_cp["name"]] = st.selectbox(
                        _cp["name"],
                        ["—", "Yes", "No", "NA"],
                        key=_cp_key,
                        label_visibility="collapsed",
                    )
                with _cpb2:
                    _pv[f"{_cp['name']} Stage"] = st.selectbox(
                        f"{_cp['name']} Stage",
                        ["—", "1st", "2nd", "3rd"],
                        key=_cp_stage_key,
                        label_visibility="collapsed",
                    )
                with _cpc:
                    _pv[f"{_cp['name']} Comment"] = st.text_input(
                        "Comment",
                        placeholder="Remark…",
                        key=_cp_cmt_key,
                        label_visibility="collapsed",
                    )

        _f_notes = st.text_area("Reviewer Notes", placeholder="Optional observations…", height=56)
        _f_suggestion = st.text_area(
            "💡 Improvement Suggestion",
            value=st.session_state.get("_audit_suggestion_draft", ""),
            placeholder="Describe what the bot could improve — use the ✨ AI Suggestion Builder above to draft & refine this automatically.",
            height=72,
            key="f_suggestion_field",
        )
        _sub     = st.form_submit_button("✅ Submit Audit  — Auto-Score", use_container_width=True, type="primary")

        if _sub:
            # Mandatory validation
            _errs = []
            if not _f_auditor.strip():
                _errs.append("QA name is required")
            if not _f_client.strip():
                _errs.append("Client is required")
            if not _f_campaign.strip():
                _errs.append("Campaign Name is required")
            if not _f_bot_name.strip():
                _errs.append("Bot Name is required")
            if not _f_pm_csm.strip():
                _errs.append("PM / CSM is required")
            for _col, _val in _pv.items():
                if _col.endswith(" Comment"):
                    continue  # comments are optional
                if not _val or str(_val).strip() in ("— select —", "—"):
                    _errs.append(f"'{_col}' must be selected")
                # NA is accepted as "not applicable" — no error
            if _f_disposition == "— select —":
                _errs.append("Disposition must be selected")

            if _errs:
                for _e in _errs:
                    st.error(_e)
            else:
                # Build full param dict including lead fields
                _full_pv = dict(_pv)
                _full_pv["Correct Disposition"]           = _f_correct_disp
                _full_pv["Correct Disposition (Expected)"] = _f_correct_disp_text

                # Auto-compute all scores
                _computed = _compute_qa_score(_full_pv)

                _rec = {
                    "Audit Date":         str(_f_audit_date),
                    "QA":                 _f_auditor.strip(),
                    "Client":             _f_client.strip(),
                    "Campaign Name":      _f_campaign.strip(),
                    "PM / CSM":           _f_pm_csm.strip(),
                    "Bot Name":           _f_bot_name.strip(),
                    "Lead Number":        _f_lead_no.strip(),
                    "Lead Link":          _f_lead_link.strip(),
                    "Disposition":        _f_disposition if _f_disposition != "— select —" else "",
                    "Conversation Link":  _f_conv_link.strip(),
                    **_full_pv,
                    "Lead Score":          _computed["Lead Score"],
                    "Lead Composite":      _computed["Lead Composite"],
                    "Bot Score":           _computed["Bot Score"],
                    "Intelligence Score":  _computed["Intelligence Score"],
                    "Status":              _computed["Status"],
                    "Fatal?":              _computed["Fatal?"],
                    "Notes":               _f_notes,
                    "Improvement Suggestion": _f_suggestion,
                    "Call Drop Stage":     _f_call_drop_stage if _f_call_drop_stage != "NA" else "",
                }
                _save_err = audit_store.append(_rec)
                if _save_err:
                    st.error(f"⚠️ Failed to save audit to database: {_save_err}")
                    st.stop()

                st.session_state["qa_last_result"] = {
                    **_computed,
                    "_disposition":        _f_disposition if _f_disposition != "— select —" else "—",
                    "_correct_disp":       _f_correct_disp,
                    "_correct_disp_text":  _f_correct_disp_text,
                    "_call_drop_stage":    _f_call_drop_stage if _f_call_drop_stage != "NA" else "",
                }

                st.session_state.pop("_audit_suggestion_draft", None)
                st.session_state.pop("_audit_suggestion_improved", None)

                if _q_idx >= 0 and _lead_q_form:
                    _lead_q_form.pop(_q_idx)
                    st.session_state["sense_lead_queue"] = _lead_q_form

                st.rerun()

    # ── Last submission result ─────────────────────────────────────────────────
    if st.session_state.get("qa_last_result"):
        _lr  = st.session_state["qa_last_result"]
        _sc  = _lr["Bot Score"]
        _sgc = _qa_status_color(_lr["Status"])
        _isc = _lr.get("Intelligence Score", "—")
        st.markdown(
            f'<div style="background:{_sgc}0d;border:1px solid {_sgc}44;border-left:4px solid {_sgc};'
            f'border-radius:10px;padding:14px 18px;margin-bottom:1rem;">'
            f'<div style="font-size:0.7rem;font-weight:700;color:{_sgc};text-transform:uppercase;'
            f'letter-spacing:0.08em;margin-bottom:8px;">✅ Last Audit Result</div>'
            f'<div style="display:flex;gap:28px;flex-wrap:wrap;">'
            f'<div><div style="font-size:1.8rem;font-weight:900;color:{_sgc};">{_sc}%</div>'
            f'<div style="font-size:0.62rem;color:#5588bb;">Bot Score</div></div>'
            f'<div><div style="font-size:1.4rem;font-weight:800;color:{_sgc};">{_lr["Status"]}</div>'
            f'<div style="font-size:0.62rem;color:#5588bb;">Status</div></div>'
            f'<div><div style="font-size:1.4rem;font-weight:800;color:#7c3aed;">'
            f'{"—" if _isc == "" else f"{_isc}%"}</div>'
            f'<div style="font-size:0.62rem;color:#5588bb;">Intelligence Score</div></div>'
            f'<div><div style="font-size:1.4rem;font-weight:800;color:#2563EB;">{_lr.get("Lead Composite","—")}</div>'
            f'<div style="font-size:0.62rem;color:#5588bb;">Lead Composite</div></div>'
            f'<div><div style="font-size:1.4rem;font-weight:800;color:{"#dc2626" if _lr["Fatal?"]=="YES" else "#0ebc6e"};">{_lr["Fatal?"]}</div>'
            f'<div style="font-size:0.62rem;color:#5588bb;">Fatal?</div></div>'
            + f'<div><div style="font-size:1.1rem;font-weight:800;color:{"#dc2626" if _lr.get("_disposition")=="Hot" else "#f59e0b" if _lr.get("_disposition")=="Warm" else "#2563EB" if _lr.get("_disposition")=="Cold" else "#0B1F3A"};">{_lr.get("_disposition","—")}</div>'
            f'<div style="font-size:0.62rem;color:#5588bb;">Disposition</div></div>'
            f'<div><div style="font-size:1rem;font-weight:800;color:{"#0ebc6e" if _lr.get("_correct_disp")=="Yes" else "#dc2626" if _lr.get("_correct_disp")=="No" else "#94a3b8"};">{_lr.get("_correct_disp","—")}</div>'
            f'<div style="font-size:0.62rem;color:#5588bb;">Correct Disposition</div></div>'
            + (f'<div><div style="font-size:1rem;font-weight:800;color:#dc2626;">{_lr.get("_correct_disp_text","—")}</div>'
               f'<div style="font-size:0.62rem;color:#5588bb;">Expected Disposition</div></div>'
               if _lr.get("_correct_disp_text") else "")
            + (f'<div><div style="font-size:1rem;font-weight:800;color:#f59e0b;">{_lr.get("_call_drop_stage","—")}</div>'
               f'<div style="font-size:0.62rem;color:#5588bb;">Call Drop Stage</div></div>'
               if _lr.get("_call_drop_stage") else "")
            + f'</div></div>',
            unsafe_allow_html=True,
        )

    # ── Audit log table ────────────────────────────────────────────────────────
    if audit_log:
        st.markdown('<div class="section-chip">📋 Audit Log</div>', unsafe_allow_html=True)

        _scores_v   = [r.get("Bot Score", 0) for r in audit_log if r.get("Bot Score") is not None]
        _avg_s      = round(sum(_scores_v) / len(_scores_v), 1) if _scores_v else 0
        _pass_ct    = sum(1 for r in audit_log if str(r.get("Status","")) == "Pass")
        _review_ct  = sum(1 for r in audit_log if str(r.get("Status","")) == "Needs Review")
        _fatal_ct   = sum(1 for r in audit_log if str(r.get("Fatal?","")) == "YES")
        _n          = len(audit_log)

        _lc1, _lc2, _lc3, _lc4, _lc5, _lc6 = st.columns(6)
        _lc1.metric("Total Audits",   _n)
        _lc2.metric("Avg Bot Score",  f"{_avg_s}%")
        _lc3.metric("Pass ≥80%",      f"{_pass_ct}  ({round(_pass_ct/_n*100,1)}%)")
        _lc4.metric("Needs Review",   f"{_review_ct}  ({round(_review_ct/_n*100,1)}%)")
        _lc5.metric("Auto-Fail",      f"{_fatal_ct}  ({round(_fatal_ct/_n*100,1)}%)")
        _lc6.metric("QA Count",        len(set(r.get("QA","") for r in audit_log)))

        # ── Export strip (uses clean df — no _row_id column) ──────────────────
        _log_df = pd.DataFrame([{k: v for k, v in r.items() if k != "_row_id"} for r in audit_log])
        import io as _io
        _exp_csv, _exp_xl = st.columns(2)
        with _exp_csv:
            st.download_button(
                "⬇ Export as CSV",
                data=_log_df.to_csv(index=False).encode("utf-8"),
                file_name="convin_qa_audit_log.csv",
                mime="text/csv",
                key="sense_dl_auditlog_csv",
            )
        with _exp_xl:
            _xl_buf = _io.BytesIO()
            with pd.ExcelWriter(_xl_buf, engine="openpyxl") as _xw:
                _log_df.to_excel(_xw, index=False, sheet_name="Audit Log")
            st.download_button(
                "⬇ Export as Excel",
                data=_xl_buf.getvalue(),
                file_name="convin_qa_audit_log.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="sense_dl_auditlog_xl",
            )

        # ── Per-record list with Edit / Delete ────────────────────────────────
        st.markdown(
            '<div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr 80px 90px 88px 88px;'
            'gap:6px;padding:6px 10px;background:#f0f4ff;border-radius:8px;'
            'font-size:0.66rem;font-weight:700;color:#2563EB;text-transform:uppercase;'
            'letter-spacing:0.04em;margin-top:0.8rem;">'
            '<span>Date</span><span>QA</span><span>Client</span><span>Bot Name</span>'
            '<span style="text-align:center">Score</span><span style="text-align:center">Status</span>'
            '<span></span><span></span></div>',
            unsafe_allow_html=True,
        )

        _editing_id  = st.session_state.get("_audit_edit_id")
        _deleting_id = st.session_state.get("_audit_del_id")

        for _aidx, _ar in enumerate(audit_log):
            _rid    = _ar.get("_row_id") or f"idx{_aidx}"
            _status = str(_ar.get("Status", ""))
            _score  = _ar.get("Bot Score", "—")
            _sc_str = f"{_score}%" if isinstance(_score, (int, float)) else str(_score)
            _sc_col = "#16a34a" if _status == "Pass" else ("#f59e0b" if _status == "Needs Review" else "#dc2626")

            # ── record row ────────────────────────────────────────────────────
            st.markdown(
                f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr 80px 90px 88px 88px;'
                f'gap:6px;padding:7px 10px;border-bottom:1px solid #e9edf5;'
                f'background:{"#f0f9ff" if _rid == _editing_id else "#fff"};">'
                f'<span style="font-size:0.72rem;color:#334155;">{_ar.get("Audit Date","")}</span>'
                f'<span style="font-size:0.72rem;color:#334155;">{_ar.get("QA","")}</span>'
                f'<span style="font-size:0.72rem;color:#334155;">{_ar.get("Client","")}</span>'
                f'<span style="font-size:0.72rem;color:#334155;">{_ar.get("Bot Name","")}</span>'
                f'<span style="font-size:0.72rem;font-weight:700;color:{_sc_col};text-align:center">{_sc_str}</span>'
                f'<span style="font-size:0.7rem;color:{_sc_col};text-align:center">{_status}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

            _btn_edit, _btn_del = st.columns([1, 1])
            with _btn_edit:
                if st.button("✏️ Edit", key=f"_aed_{_rid}", use_container_width=True):
                    if st.session_state.get("_audit_edit_id") == _rid:
                        st.session_state.pop("_audit_edit_id", None)
                    else:
                        st.session_state["_audit_edit_id"] = _rid
                        st.session_state.pop("_audit_del_id", None)
                    st.rerun()
            with _btn_del:
                if st.button("🗑 Delete", key=f"_add_{_rid}", use_container_width=True):
                    if st.session_state.get("_audit_del_id") == _rid:
                        st.session_state.pop("_audit_del_id", None)
                    else:
                        st.session_state["_audit_del_id"] = _rid
                        st.session_state.pop("_audit_edit_id", None)
                    st.rerun()

            # ── Delete confirmation ───────────────────────────────────────────
            if _deleting_id == _rid:
                st.warning(f"Delete audit for **{_ar.get('Client','')} / {_ar.get('Bot Name','')}** on {_ar.get('Audit Date','')}? This cannot be undone.")
                _dc1, _dc2 = st.columns(2)
                with _dc1:
                    if st.button("Yes, delete", key=f"_adconf_{_rid}", type="primary", use_container_width=True):
                        _derr = audit_store.delete(_ar.get("_row_id"))
                        if _derr:
                            st.error(f"Delete failed: {_derr}")
                        else:
                            st.session_state.pop("_audit_del_id", None)
                            st.session_state["sense_audit_log"] = _audit_log_load()
                            st.rerun()
                with _dc2:
                    if st.button("Cancel", key=f"_adcancel_{_rid}", use_container_width=True):
                        st.session_state.pop("_audit_del_id", None)
                        st.rerun()

            # ── Inline edit form ──────────────────────────────────────────────
            if _editing_id == _rid:
                with st.container():
                    st.markdown(
                        '<div style="background:#f0f9ff;border:1px solid #bfdbfe;border-radius:10px;'
                        'padding:14px 16px;margin:6px 0 10px;">',
                        unsafe_allow_html=True,
                    )
                    st.markdown("**✏️ Edit Audit Record**", unsafe_allow_html=False)
                    _ea1, _ea2, _ea3 = st.columns(3)
                    _e_client    = _ea1.text_input("Client",       value=_ar.get("Client",""),       key=f"_ec_{_rid}")
                    _e_campaign  = _ea2.text_input("Campaign Name",value=_ar.get("Campaign Name",""),key=f"_ecam_{_rid}")
                    _e_bot       = _ea3.text_input("Bot Name",     value=_ar.get("Bot Name",""),     key=f"_ebot_{_rid}")
                    _eb1, _eb2, _eb3 = st.columns(3)
                    _e_qa        = _eb1.text_input("QA",           value=_ar.get("QA",""),           key=f"_eqa_{_rid}")
                    _e_pm        = _eb2.text_input("PM / CSM",     value=_ar.get("PM / CSM",""),     key=f"_epm_{_rid}")
                    _e_lead      = _eb3.text_input("Lead Number",  value=_ar.get("Lead Number",""),  key=f"_eld_{_rid}")
                    _ec1, _ec2 = st.columns(2)
                    _e_conv_link = _ec1.text_input("Conversation Link", value=_ar.get("Conversation Link",""), key=f"_ecl_{_rid}")
                    _e_lead_link = _ec2.text_input("Lead Link",         value=_ar.get("Lead Link",""),         key=f"_ell_{_rid}")
                    _e_notes     = st.text_area("Reviewer Notes",        value=_ar.get("Notes",""),             key=f"_en_{_rid}", height=72)
                    _e_suggest   = st.text_area("Improvement Suggestion",value=_ar.get("Improvement Suggestion",""), key=f"_es_{_rid}", height=72)
                    _esv1, _esv2 = st.columns(2)
                    with _esv1:
                        if st.button("💾 Save Changes", key=f"_esave_{_rid}", type="primary", use_container_width=True):
                            _updated = dict(_ar)
                            _updated["Client"]               = _e_client.strip()
                            _updated["Campaign Name"]        = _e_campaign.strip()
                            _updated["Bot Name"]             = _e_bot.strip()
                            _updated["QA"]                   = _e_qa.strip()
                            _updated["PM / CSM"]             = _e_pm.strip()
                            _updated["Lead Number"]          = _e_lead.strip()
                            _updated["Conversation Link"]    = _e_conv_link.strip()
                            _updated["Lead Link"]            = _e_lead_link.strip()
                            _updated["Notes"]                = _e_notes.strip()
                            _updated["Improvement Suggestion"] = _e_suggest.strip()
                            _uerr = audit_store.update(_ar.get("_row_id"), _updated)
                            if _uerr:
                                st.error(f"Save failed: {_uerr}")
                            else:
                                st.session_state.pop("_audit_edit_id", None)
                                st.session_state["sense_audit_log"] = _audit_log_load()
                                st.rerun()
                    with _esv2:
                        if st.button("✕ Cancel", key=f"_ecancel_{_rid}", use_container_width=True):
                            st.session_state.pop("_audit_edit_id", None)
                            st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)


def _render_legend_page():
    """Full parameter legend & scoring guide — mirrors the Convin Sense audit spec."""

    # ── Page header ───────────────────────────────────────────────────────────
    st.markdown(
        '<div style="display:flex;align-items:center;justify-content:space-between;'
        'margin-bottom:1.2rem;flex-wrap:wrap;gap:8px;">'
        '<div>'
        '<div style="font-size:1.05rem;font-weight:800;color:#0d1d3a;letter-spacing:-0.01em;">'
        '📖 Sense Audit — Parameter Legend & Scoring Guide</div>'
        '<div style="font-size:0.72rem;color:#5588bb;margin-top:2px;">'
        'Complete reference for all QA parameters, weights, scoring options and definitions</div>'
        '</div>'
        f'<div style="font-size:0.65rem;color:#aabbcc;background:#fff;'
        f'border:1px solid #e4e7ec;border-radius:8px;padding:4px 10px;">'
        f'Last updated · {pd.Timestamp.now().strftime("%d %b %Y")}</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Quick-stats strip ─────────────────────────────────────────────────────
    _all_params = [p for tier in _QA_SCHEMA["tiers"] for p in tier["params"]]
    _scored_w   = sum(p["weight"] for p in _all_params if p["weight"] > 0)
    _t1_params  = len(_QA_SCHEMA["tiers"][0]["params"])
    _t2_params  = len(_QA_SCHEMA["tiers"][1]["params"])
    _t3_params  = len(_QA_SCHEMA["tiers"][2]["params"])
    st.markdown(
        f'<div class="stats-grid" style="grid-template-columns:repeat(5,1fr);margin-bottom:1.4rem;">'
        f'<div class="stat-card" style="border-top:2px solid #0B1F3A;">'
        f'<div style="color:#2a5080;font-size:0.58rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:4px;">Total Parameters</div>'
        f'<div style="color:#0B1F3A;font-size:1.6rem;font-weight:800;">{len(_all_params)}</div>'
        f'</div>'
        f'<div class="stat-card" style="border-top:2px solid #dc2626;">'
        f'<div style="color:#2a5080;font-size:0.58rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:4px;">Tier 1 · Critical</div>'
        f'<div style="color:#dc2626;font-size:1.6rem;font-weight:800;">{_t1_params} <span style="font-size:0.9rem;font-weight:600;">({_QA_SCHEMA["tiers"][0]["weight_pct"]}%)</span></div>'
        f'</div>'
        f'<div class="stat-card" style="border-top:2px solid #f59e0b;">'
        f'<div style="color:#2a5080;font-size:0.58rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:4px;">Tier 2 · Important</div>'
        f'<div style="color:#f59e0b;font-size:1.6rem;font-weight:800;">{_t2_params} <span style="font-size:0.9rem;font-weight:600;">({_QA_SCHEMA["tiers"][1]["weight_pct"]}%)</span></div>'
        f'</div>'
        f'<div class="stat-card" style="border-top:2px solid #2563EB;">'
        f'<div style="color:#2a5080;font-size:0.58rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:4px;">Tier 3 · Quality</div>'
        f'<div style="color:#2563EB;font-size:1.6rem;font-weight:800;">{_t3_params} <span style="font-size:0.9rem;font-weight:600;">({_QA_SCHEMA["tiers"][2]["weight_pct"]}%)</span></div>'
        f'</div>'
        f'<div class="stat-card" style="border-top:2px solid #059669;">'
        f'<div style="color:#2a5080;font-size:0.58rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:4px;">Pass Threshold</div>'
        f'<div style="color:#059669;font-size:1.6rem;font-weight:800;">≥ 80%</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Tier parameter tables ─────────────────────────────────────────────────
    _ROW_COLORS = {"0/1/2": "#2563EB", "0/2": "#f59e0b", "0/Fatal": "#dc2626", "Fatal": "#7f1d1d"}

    for _tier_idx, _tier in enumerate(_QA_SCHEMA["tiers"], 1):
        _ip = None  # intelligence params are now standard tier params
        _tc = _tier["color"]
        _tier_params = _tier["params"]
        _ip_hdr = ""
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:12px;margin:1.2rem 0 0.6rem;flex-wrap:wrap;">'
            f'<div style="background:{_tc};color:#fff;font-size:0.62rem;font-weight:800;'
            f'letter-spacing:0.12em;text-transform:uppercase;border-radius:6px;padding:4px 12px;">'
            f'{_tier["label"]}</div>'
            f'<div style="font-size:0.7rem;color:#5588bb;">'
            f'Weight: <strong style="color:{_tc};">{_tier["weight_pct"]}%</strong>'
            f' &nbsp;·&nbsp; {len(_tier_params)} param{"s" if len(_tier_params)!=1 else ""}'
            f'{_ip_hdr}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Table — shared columns for tier params + intelligence row
        _tbl = (
            '<div style="background:#fff;border:1px solid #e4e7ec;border-radius:12px;overflow:hidden;margin-bottom:0.8rem;">'
            '<div style="display:grid;grid-template-columns:2rem 1fr 0.55fr 0.55fr 2.8fr;'
            'gap:0;padding:8px 16px;background:rgba(61,130,245,0.06);'
            'font-size:0.62rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#5588bb;">'
            '<div>#</div><div>Parameter</div><div>Weight</div><div>Scoring</div><div>Definition &amp; Guide</div>'
            '</div>'
        )

        for _pi, _p in enumerate(_tier_params, 1):
            _opts_str = "/".join(_p["options"])
            _opts_c   = _ROW_COLORS.get(_opts_str, "#2563EB")
            _w_pct    = f'{int(_p["weight"]*100)}%' if _p["weight"] > 0 else ("FATAL" if _p.get("fatal") else "—")
            _w_c      = "#dc2626" if _p.get("fatal") else "#0d1d3a"
            _bg       = "#fff" if _pi % 2 == 1 else "#f9fbff"
            _guide    = _p.get("guide", "")
            _guide_html = _guide
            for _opt in _p["options"]:
                _guide_html = _guide_html.replace(
                    f"{_opt} =",
                    f'<span style="background:{_opts_c}18;border:1px solid {_opts_c}55;'
                    f'border-radius:4px;padding:0 5px;font-weight:700;color:{_opts_c};">{_opt}</span> =',
                )
            _fatal_badge = (
                '  <span style="background:#dc262618;color:#dc2626;border-radius:4px;'
                'padding:1px 6px;font-size:0.58rem;font-weight:700;">FATAL</span>'
                if _p.get("fatal") else ""
            )
            _tbl += (
                f'<div style="display:grid;grid-template-columns:2rem 1fr 0.55fr 0.55fr 2.8fr;'
                f'gap:0;padding:10px 16px;background:{_bg};'
                f'border-top:1px solid rgba(61,130,245,0.06);align-items:start;">'
                f'<div style="font-size:0.68rem;color:#aabbcc;font-weight:600;">{_pi}</div>'
                f'<div style="font-size:0.78rem;font-weight:700;color:#0d1d3a;">{_p["col"]}{_fatal_badge}</div>'
                f'<div style="font-size:0.75rem;font-weight:800;color:{_w_c};">{_w_pct}</div>'
                f'<div><span style="background:{_opts_c}18;border:1px solid {_opts_c}55;'
                f'border-radius:6px;padding:2px 9px;font-size:0.68rem;font-weight:700;color:{_opts_c};">'
                f'{_opts_str}</span></div>'
                f'<div style="font-size:0.7rem;color:#5588bb;line-height:1.55;">{_guide_html}</div>'
                f'</div>'
            )


        _tbl += '</div>'
        st.markdown(_tbl, unsafe_allow_html=True)

    # ── Status bands ─────────────────────────────────────────────────────────
    st.markdown('<div class="section-chip">🎨 Status Bands</div>', unsafe_allow_html=True)
    _bands_html = '<div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:1.2rem;">'
    _band_defs = [
        {"label": "Pass",         "range": "Bot Score ≥ 80",  "color": "#0ebc6e", "desc": "All critical parameters met; high-quality interaction"},
        {"label": "Needs Review", "range": "Bot Score 60–79", "color": "#f59e0b", "desc": "Acceptable but improvement areas exist; flag for coaching"},
        {"label": "Fail",         "range": "Bot Score < 60",  "color": "#dc2626", "desc": "Significant issues present; requires immediate action"},
        {"label": "Auto-Fail",    "range": "Fatal Error",     "color": "#7f1d1d", "desc": "Abrupt disconnection detected — score zeroed regardless of other params"},
    ]
    for _bd in _band_defs:
        _c = _bd["color"]
        _bands_html += (
            f'<div style="flex:1;min-width:180px;background:#fff;border:1px solid {_c}33;'
            f'border-top:4px solid {_c};border-radius:10px;padding:14px 16px;">'
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">'
            f'<div style="width:12px;height:12px;border-radius:50%;background:{_c};flex-shrink:0;"></div>'
            f'<div style="font-size:0.78rem;font-weight:800;color:{_c};">{_bd["label"]}</div>'
            f'</div>'
            f'<div style="font-size:0.68rem;font-weight:700;color:#0d1d3a;margin-bottom:4px;">{_bd["range"]}</div>'
            f'<div style="font-size:0.65rem;color:#5588bb;line-height:1.5;">{_bd["desc"]}</div>'
            f'</div>'
        )
    _bands_html += '</div>'
    st.markdown(_bands_html, unsafe_allow_html=True)

    # ── Lead stage colour key ─────────────────────────────────────────────────
    st.markdown('<div class="section-chip">🏷️ Lead Stage Reference</div>', unsafe_allow_html=True)
    _lead_colors = {"Hot": "#dc2626", "Warm": "#f59e0b", "Cold": "#2563EB", "Not Interested": "#6b7280", "RNR": "#9ca3af"}
    _lead_html = '<div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:1.2rem;">'
    for _stage, _lc in _lead_colors.items():
        _ls = _QA_SCHEMA["lead_stage_scores"].get(_stage, 0)
        _lead_html += (
            f'<div style="background:#fff;border:1px solid {_lc}33;border-left:4px solid {_lc};'
            f'border-radius:8px;padding:8px 14px;min-width:120px;">'
            f'<div style="font-size:0.75rem;font-weight:700;color:{_lc};">{_stage}</div>'
            f'<div style="font-size:0.65rem;color:#5588bb;margin-top:2px;">Lead Score = {_ls}</div>'
            f'</div>'
        )
    _lead_html += '</div>'
    st.markdown(_lead_html, unsafe_allow_html=True)

    # ── Scoring formula ───────────────────────────────────────────────────────
    st.markdown('<div class="section-chip">🔢 Scoring Formulas</div>', unsafe_allow_html=True)
    st.markdown(
        '<div style="background:#fff;border:1px solid #e4e7ec;border-radius:12px;padding:20px 24px;margin-bottom:1rem;">'
        '<div style="display:flex;flex-direction:column;gap:14px;">'

        '<div><div style="font-size:0.68rem;font-weight:700;color:#2563EB;text-transform:uppercase;'
        'letter-spacing:0.08em;margin-bottom:4px;">Bot Score</div>'
        '<div style="font-family:monospace;font-size:0.82rem;color:#0d1d3a;background:#fff;'
        'border:1px solid rgba(61,130,245,0.15);border-radius:6px;padding:8px 14px;">'
        'Bot Score = Σ (param_score × weight) / (Σ weight × 2) × 100</div>'
        '<div style="font-size:0.65rem;color:#5588bb;margin-top:4px;">'
        'Each param scored 0–2. Max possible per param = weight × 2. '
        'If Abrupt Disconnection = Fatal → Bot Score forced to 0.</div></div>'

        '<div><div style="font-size:0.68rem;font-weight:700;color:#7c3aed;text-transform:uppercase;'
        'letter-spacing:0.08em;margin-bottom:4px;">Intelligence Score</div>'
        '<div style="font-family:monospace;font-size:0.82rem;color:#0d1d3a;background:#fff;'
        'border:1px solid rgba(124,58,237,0.15);border-radius:6px;padding:8px 14px;">'
        'Intelligence Score = Σ (mapped_score × weight) / (Σ weight × 2) × 100</div>'
        '<div style="font-size:0.65rem;color:#5588bb;margin-top:4px;">'
        'Separate metric — does not affect Bot Score. Weights are relative multipliers (1.5×, 1.2×, 1.0×).</div></div>'

        '<div><div style="font-size:0.68rem;font-weight:700;color:#0ebc6e;text-transform:uppercase;'
        'letter-spacing:0.08em;margin-bottom:4px;">Lead Composite</div>'
        '<div style="font-family:monospace;font-size:0.82rem;color:#0d1d3a;background:#fff;'
        'border:1px solid rgba(14,188,110,0.15);border-radius:6px;padding:8px 14px;">'
        'Lead Composite = (Lead Score + (PI + FR + DM) / 6 × 100) / 2</div>'
        '<div style="font-size:0.65rem;color:#5588bb;margin-top:4px;">'
        'PI = Product Interest · FR = Follow-up Readiness · DM = DM Confirmed (each 0–2). '
        'Lead Score from stage mapping.</div></div>'

        '</div></div>',
        unsafe_allow_html=True,
    )


def render_convin_sense():
    _has_data = bool(st.session_state.get("sense_sheets"))
    _registry_init()

    # ── Convin premium brand UI ────────────────────────────────────────────────
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

@keyframes fadeUp {
  from { opacity:0; transform:translateY(10px); }
  to   { opacity:1; transform:translateY(0); }
}
@keyframes shimmer {
  0%   { background-position: -400px 0; }
  100% { background-position: 400px 0; }
}
@keyframes pulseBlue {
  0%,100% { box-shadow: 0 0 0 0 rgba(37,99,235,0.25); }
  50%      { box-shadow: 0 0 0 6px rgba(37,99,235,0); }
}

/* ── Base ── */
.stApp, .stApp > div, section.main > div { background: #F0F4F9 !important; font-family: 'Inter', sans-serif !important; }
.block-container { background: #F0F4F9 !important; padding-top: 1.5rem !important; }

/* ── Section chip: Convin branded pill ── */
.section-chip {
    display: inline-flex !important;
    align-items: center !important;
    gap: 6px !important;
    font-size: 0.61rem !important;
    font-weight: 800 !important;
    letter-spacing: 0.11em !important;
    text-transform: uppercase !important;
    color: #ffffff !important;
    background: linear-gradient(135deg,#0B1F3A,#2563EB) !important;
    border: none !important;
    border-radius: 6px !important;
    padding: 5px 14px !important;
    margin-bottom: 16px !important;
    box-shadow: 0 2px 8px rgba(37,99,235,0.28) !important;
    transition: box-shadow 0.2s, transform 0.15s !important;
}
.section-chip:hover {
    box-shadow: 0 4px 14px rgba(37,99,235,0.38) !important;
    transform: translateY(-1px) !important;
}

/* ── Tabs: premium glass pill bar ── */
.stTabs [data-baseweb="tab-list"] {
    background: #fff !important;
    border-radius: 14px !important;
    padding: 5px !important;
    border-bottom: none !important;
    gap: 3px !important;
    box-shadow: 0 2px 10px rgba(11,31,58,0.08), inset 0 1px 0 rgba(255,255,255,0.8) !important;
}
.stTabs [data-baseweb="tab"] {
    font-size: 0.75rem !important;
    font-weight: 600 !important;
    color: #64748b !important;
    background: transparent !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 9px 18px !important;
    transition: all 0.2s ease !important;
    letter-spacing: 0.01em !important;
}
.stTabs [data-baseweb="tab"]:hover {
    background: #F0F4F9 !important;
    color: #0B1F3A !important;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg,#0B1F3A,#2563EB) !important;
    color: #fff !important;
    box-shadow: 0 3px 10px rgba(37,99,235,0.32) !important;
    font-weight: 700 !important;
}
.stTabs [data-baseweb="tab-panel"] { padding-top: 20px !important; }

/* ── Expanders: elevated card ── */
.streamlit-expanderHeader {
    font-size: 0.79rem !important;
    font-weight: 700 !important;
    color: #0B1F3A !important;
    background: #fff !important;
    border-radius: 12px 12px 0 0 !important;
    padding: 14px 18px !important;
    border-left: 3px solid #2563EB !important;
    transition: background 0.15s !important;
}
.streamlit-expanderHeader:hover { background: #F8FAFF !important; }
.streamlit-expanderContent {
    background: #fff !important;
    border: 1px solid #E2EAF6 !important;
    border-top: none !important;
    border-radius: 0 0 12px 12px !important;
    padding: 16px 18px !important;
    animation: fadeUp 0.2s ease !important;
}

/* ── Dataframe: premium header + hover rows ── */
.stDataFrame table { border-collapse: separate !important; border-spacing: 0 !important; border-radius: 10px !important; overflow: hidden !important; box-shadow: 0 2px 8px rgba(11,31,58,0.08) !important; }
.stDataFrame table thead th {
    background: linear-gradient(135deg,#0B1F3A 0%,#1D4ED8 100%) !important;
    color: #fff !important;
    font-size: 0.66rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    border: none !important;
    padding: 10px 14px !important;
}
.stDataFrame table tbody tr:nth-child(even) td { background: #F8FBFF !important; }
.stDataFrame table tbody tr:nth-child(odd) td  { background: #fff !important; }
.stDataFrame table tbody td {
    font-size: 0.77rem !important;
    color: #1E293B !important;
    border-color: #E8F0FB !important;
    padding: 9px 14px !important;
    transition: background 0.15s !important;
}
.stDataFrame table tbody tr:hover td {
    background: #EFF6FF !important;
    color: #0B1F3A !important;
}

/* ── Inputs: refined ── */
.stSelectbox > div > div, .stTextInput > div > div, .stDateInput > div > div {
    border: 1.5px solid #CBD5E8 !important;
    border-radius: 10px !important;
    background: #fff !important;
    transition: border-color 0.18s, box-shadow 0.18s !important;
    box-shadow: 0 1px 3px rgba(11,31,58,0.06) !important;
}
.stSelectbox > div > div:focus-within,
.stTextInput > div > div:focus-within {
    border-color: #2563EB !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.12) !important;
}
.stSelectbox label, .stTextInput label, .stDateInput label,
.stRadio label, .stNumberInput label, .stTextArea label {
    font-size: 0.71rem !important;
    font-weight: 600 !important;
    color: #475569 !important;
    letter-spacing: 0.02em !important;
}

/* ── All buttons ── */
.stButton > button {
    border-radius: 10px !important;
    font-size: 0.77rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.03em !important;
    transition: all 0.2s ease !important;
    padding: 9px 22px !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg,#0B1F3A 0%,#2563EB 100%) !important;
    border: none !important;
    color: #fff !important;
    box-shadow: 0 4px 14px rgba(37,99,235,0.35) !important;
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 8px 22px rgba(37,99,235,0.48) !important;
    transform: translateY(-2px) !important;
}
.stButton > button[kind="primary"]:active { transform: translateY(0) !important; }
.stButton > button[kind="secondary"] {
    background: #fff !important;
    border: 1.5px solid #BFDBFE !important;
    color: #2563EB !important;
    box-shadow: 0 1px 4px rgba(37,99,235,0.10) !important;
}
.stButton > button[kind="secondary"]:hover {
    background: #EFF6FF !important;
    border-color: #2563EB !important;
    box-shadow: 0 3px 10px rgba(37,99,235,0.18) !important;
    transform: translateY(-1px) !important;
}
.stButton > button:not([kind]) {
    background: #fff !important;
    border: 1.5px solid #CBD5E8 !important;
    color: #374151 !important;
}
.stButton > button:not([kind]):hover {
    border-color: #2563EB !important;
    color: #2563EB !important;
    background: #EFF6FF !important;
    transform: translateY(-1px) !important;
}

/* ── Radio: elevated pill toggle ── */
.stRadio > div[role="radiogroup"] {
    gap: 8px !important;
    flex-wrap: wrap !important;
}
.stRadio > div[role="radiogroup"] > label {
    background: #fff !important;
    border: 1.5px solid #CBD5E8 !important;
    border-radius: 24px !important;
    padding: 6px 18px !important;
    font-size: 0.75rem !important;
    font-weight: 600 !important;
    color: #475569 !important;
    cursor: pointer !important;
    transition: all 0.18s ease !important;
    box-shadow: 0 1px 3px rgba(11,31,58,0.06) !important;
}
.stRadio > div[role="radiogroup"] > label:hover {
    border-color: #93C5FD !important;
    color: #1D4ED8 !important;
    background: #F0F7FF !important;
}
.stRadio > div[role="radiogroup"] > label:has(input:checked) {
    background: linear-gradient(135deg,#0B1F3A,#2563EB) !important;
    border-color: transparent !important;
    color: #fff !important;
    box-shadow: 0 4px 12px rgba(37,99,235,0.32) !important;
    animation: pulseBlue 1.8s ease-in-out !important;
}

/* ── Metric widgets ── */
[data-testid="metric-container"] {
    background: #fff !important;
    border: 1px solid #E2EAF6 !important;
    border-radius: 14px !important;
    padding: 16px 20px !important;
    box-shadow: 0 2px 8px rgba(11,31,58,0.07) !important;
    transition: box-shadow 0.2s, transform 0.2s !important;
    border-left: 3px solid #2563EB !important;
}
[data-testid="metric-container"]:hover {
    box-shadow: 0 6px 20px rgba(37,99,235,0.14) !important;
    transform: translateY(-2px) !important;
}
[data-testid="metric-container"] label {
    font-size: 0.68rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    color: #64748b !important;
}
[data-testid="stMetricValue"] {
    font-size: 1.85rem !important;
    font-weight: 900 !important;
    color: #0B1F3A !important;
    letter-spacing: -0.03em !important;
}

/* ── Dividers ── */
hr { border: none !important; border-top: 1px solid #E2EAF6 !important; margin: 18px 0 !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #F0F4F9; border-radius: 3px; }
::-webkit-scrollbar-thumb { background: #BFDBFE; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #2563EB; }
</style>""", unsafe_allow_html=True)

    st.markdown("""
<style>
@keyframes heroFloat {
  0%,100% { transform: translateY(0px) scale(1); }
  50%      { transform: translateY(-18px) scale(1.04); }
}
@keyframes heroFloatB {
  0%,100% { transform: translateY(0px) scale(1); }
  50%      { transform: translateY(14px) scale(0.97); }
}
@keyframes gradientShift {
  0%   { background-position: 0% 50%; }
  50%  { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}
@keyframes fadeSlideUp {
  from { opacity:0; transform:translateY(22px); }
  to   { opacity:1; transform:translateY(0); }
}
@keyframes badgePulse {
  0%,100% { box-shadow: 0 0 0 0 rgba(96,165,250,0.4); }
  50%      { box-shadow: 0 0 0 7px rgba(96,165,250,0); }
}
@keyframes gridFade {
  from { opacity:0; }
  to   { opacity:0.06; }
}

/* ════════════════════════════════════════
   FULL HERO  (empty state / landing)
════════════════════════════════════════ */
.sense-hero-full {
    background: linear-gradient(145deg, #061224 0%, #0B1F3A 45%, #0D2960 100%);
    border-radius: 24px;
    padding: 64px 56px 52px;
    margin-bottom: 28px;
    position: relative;
    overflow: hidden;
    border: 1px solid rgba(37,99,235,0.22);
    box-shadow: 0 24px 80px rgba(11,31,58,0.55), inset 0 1px 0 rgba(255,255,255,0.06);
    animation: fadeSlideUp 0.6s ease both;
}
/* Animated grid overlay */
.sense-hero-full::before {
    content: "";
    position: absolute; inset: 0;
    background-image:
        linear-gradient(rgba(37,99,235,0.07) 1px, transparent 1px),
        linear-gradient(90deg, rgba(37,99,235,0.07) 1px, transparent 1px);
    background-size: 40px 40px;
    pointer-events: none;
    animation: gridFade 1.2s ease forwards;
}
/* Glow orb — top right */
.sense-hero-full::after {
    content: "";
    position: absolute;
    top: -100px; right: -80px;
    width: 420px; height: 420px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(37,99,235,0.22) 0%, rgba(96,165,250,0.08) 45%, transparent 70%);
    pointer-events: none;
    animation: heroFloat 7s ease-in-out infinite;
}
/* Second orb — bottom left */
.sense-hero-orb2 {
    position: absolute;
    bottom: -110px; left: -60px;
    width: 380px; height: 380px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(56,189,248,0.12) 0%, transparent 65%);
    pointer-events: none;
    animation: heroFloatB 9s ease-in-out infinite;
}

/* Badge */
.sense-badge {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    background: rgba(37,99,235,0.15);
    border: 1px solid rgba(96,165,250,0.40);
    border-radius: 99px;
    padding: 5px 16px;
    font-size: 0.63rem;
    font-weight: 800;
    letter-spacing: 0.13em;
    text-transform: uppercase;
    color: #93C5FD;
    margin-bottom: 22px;
    animation: badgePulse 2.5s ease-in-out infinite, fadeSlideUp 0.5s ease both;
}
.sense-badge .dot {
    width: 6px; height: 6px;
    border-radius: 50%;
    background: #60A5FA;
    box-shadow: 0 0 8px #60A5FA;
}

/* Headline */
.sense-headline {
    font-size: 2.4rem;
    font-weight: 900;
    line-height: 1.12;
    color: #F0F8FF;
    margin-bottom: 14px;
    letter-spacing: -0.03em;
    animation: fadeSlideUp 0.6s 0.1s ease both;
}
.sense-headline .grad {
    background: linear-gradient(110deg, #60A5FA 0%, #38BDF8 40%, #818CF8 80%);
    background-size: 200% auto;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: gradientShift 4s ease infinite;
}

/* Body */
.sense-body {
    font-size: 0.9rem;
    color: rgba(186,210,240,0.70);
    line-height: 1.75;
    max-width: 600px;
    margin-bottom: 30px;
    animation: fadeSlideUp 0.6s 0.2s ease both;
}
.sense-body strong { color: rgba(224,240,255,0.92); font-weight: 700; }

/* Feature cards row */
.sense-features {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-bottom: 32px;
    animation: fadeSlideUp 0.6s 0.3s ease both;
}
.sense-feat {
    display: flex;
    align-items: center;
    gap: 8px;
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(96,165,250,0.20);
    border-radius: 12px;
    padding: 9px 16px;
    font-size: 0.75rem;
    font-weight: 600;
    color: rgba(186,210,240,0.85);
    transition: all 0.2s ease;
    cursor: default;
    backdrop-filter: blur(4px);
}
.sense-feat:hover {
    background: rgba(37,99,235,0.14);
    border-color: rgba(96,165,250,0.45);
    color: #DBEAFE;
    transform: translateY(-2px);
    box-shadow: 0 4px 14px rgba(37,99,235,0.18);
}
.sense-feat .fi { font-size: 1rem; }

/* Divider */
.sense-divider {
    height: 1px;
    background: linear-gradient(90deg, rgba(37,99,235,0.5), rgba(56,189,248,0.3), transparent 80%);
    margin-bottom: 22px;
    animation: fadeSlideUp 0.6s 0.35s ease both;
}

/* Tagline CTA */
.sense-tagline {
    font-size: 0.8rem;
    color: rgba(186,210,240,0.45);
    letter-spacing: 0.04em;
    animation: fadeSlideUp 0.6s 0.4s ease both;
}
.sense-tagline strong { color: rgba(186,210,240,0.80); }
.sense-tagline .arrow {
    display: inline-block;
    color: #60A5FA;
    font-size: 1rem;
    margin-right: 4px;
    animation: gradientShift 1.5s ease-in-out infinite alternate;
}

/* ════════════════════════════════════════
   COMPACT HERO  (data loaded)
════════════════════════════════════════ */
.sense-hero-compact {
    background: linear-gradient(135deg, #061224 0%, #0B1F3A 60%, #0D2960 100%);
    border: 1px solid rgba(37,99,235,0.25);
    border-radius: 16px;
    padding: 20px 30px;
    margin-bottom: 22px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 14px;
    position: relative;
    overflow: hidden;
    box-shadow: 0 8px 32px rgba(11,31,58,0.4);
}
.sense-hero-compact::before {
    content: "";
    position: absolute; inset: 0;
    background-image:
        linear-gradient(rgba(37,99,235,0.05) 1px, transparent 1px),
        linear-gradient(90deg, rgba(37,99,235,0.05) 1px, transparent 1px);
    background-size: 32px 32px;
    pointer-events: none;
}
.sense-hero-compact::after {
    content: "";
    position: absolute;
    top: -60px; right: -40px;
    width: 200px; height: 200px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(37,99,235,0.18) 0%, transparent 65%);
    pointer-events: none;
}
.sense-compact-left { position: relative; z-index: 1; }
.sense-compact-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(37,99,235,0.15);
    border: 1px solid rgba(96,165,250,0.35);
    border-radius: 99px;
    padding: 3px 12px;
    font-size: 0.6rem;
    font-weight: 800;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #93C5FD;
    margin-bottom: 7px;
}
.sense-compact-badge .live-dot {
    width: 5px; height: 5px;
    border-radius: 50%;
    background: #34D399;
    box-shadow: 0 0 6px #34D399;
    animation: badgePulse 1.8s ease-in-out infinite;
}
.sense-compact-title {
    font-size: 1.05rem;
    font-weight: 800;
    letter-spacing: -0.015em;
    color: #EFF6FF;
}
.sense-compact-title .grad {
    background: linear-gradient(110deg, #60A5FA, #38BDF8 50%, #818CF8);
    background-size: 200% auto;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: gradientShift 4s ease infinite;
}
.sense-compact-pills {
    display: flex;
    flex-wrap: wrap;
    gap: 7px;
    position: relative;
    z-index: 1;
}
.sense-compact-pill {
    font-size: 0.68rem;
    font-weight: 600;
    color: rgba(186,210,240,0.75);
    background: rgba(37,99,235,0.10);
    border: 1px solid rgba(96,165,250,0.22);
    border-radius: 99px;
    padding: 4px 12px;
    white-space: nowrap;
    transition: all 0.18s ease;
}
.sense-compact-pill:hover {
    background: rgba(37,99,235,0.20);
    border-color: rgba(96,165,250,0.45);
    color: #DBEAFE;
}
</style>
""", unsafe_allow_html=True)

    if not _has_data:
        # ── Full hero (empty state) ──────────────────────────────────────────
        st.markdown("""
<div class="sense-hero-full">
  <div class="sense-hero-orb2"></div>
  <div class="sense-badge"><span class="dot"></span>Convin Sense Audit &nbsp;·&nbsp; Auto QA Data Insights</div>
  <div class="sense-headline">
    Automated QA scoring.<br>Deep bot intelligence.<br>
    <span class="grad">Convin Sense Audit.</span>
  </div>
  <div class="sense-body">
    <strong>Auto QA Data Insights — powered by Convin Sense.</strong><br>
    Upload your audit data and instantly unlock automated QA scores, bot failure patterns,
    agent leaderboards, score trends, and prioritised action plans —
    all in one beautifully crafted dashboard built for conversation intelligence teams.
  </div>
  <div class="sense-features">
    <div class="sense-feat"><span class="fi">🤖</span> Auto QA scoring &amp; bot intelligence</div>
    <div class="sense-feat"><span class="fi">🔍</span> Instant flow-issue detection</div>
    <div class="sense-feat"><span class="fi">🏆</span> Agent &amp; campaign leaderboards</div>
    <div class="sense-feat"><span class="fi">📈</span> Score trends &amp; pass-rate tracking</div>
    <div class="sense-feat"><span class="fi">⚡</span> Auto-prioritised action plans</div>
    <div class="sense-feat"><span class="fi">📋</span> One-click PDF reports</div>
  </div>
  <div class="sense-divider"></div>
  <div class="sense-tagline">
    <span class="arrow">↓</span>
    <strong>Drop your audit file below to begin.</strong>
    &nbsp; Supports CSV, Excel, JSON — insights in seconds.
  </div>
</div>
""", unsafe_allow_html=True)
    else:
        # ── Compact hero bar (data loaded) ───────────────────────────────────
        st.markdown("""
<div class="sense-hero-compact">
  <div class="sense-compact-left">
    <div class="sense-compact-badge"><span class="live-dot"></span> Live &nbsp;·&nbsp; Convin Sense Audit</div>
    <div class="sense-compact-title">
      <span class="grad">Real-time conversation intelligence</span>
      &nbsp;— thinks, not just reports.
    </div>
  </div>
  <div class="sense-compact-pills">
    <span class="sense-compact-pill">🔍 Flow issues</span>
    <span class="sense-compact-pill">🤖 Bot failures</span>
    <span class="sense-compact-pill">🏆 Leaderboards</span>
    <span class="sense-compact-pill">📈 Score trends</span>
    <span class="sense-compact-pill">⚡ Action plans</span>
  </div>
</div>
""", unsafe_allow_html=True)

    # ── Restore from disk if session was wiped (hot-reload / refresh) ────────
    if "sense_sheets" not in st.session_state:
        _cached = _sense_load()
        if _cached:
            st.session_state["sense_sheets"] = _cached["sheets"]
            st.session_state["sense_filename"] = _cached["fname"]
        else:
            # Even without the main cache, restore protected sheets
            _prot = _sense_load_protected()
            if _prot:
                st.session_state["sense_sheets"] = _prot["sheets"]
                st.session_state["sense_filename"] = _prot["fname"]

    st.markdown('<div class="section-chip">📂 Upload Data</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader(
        "Upload a file to analyse",
        key="sense_csv_upload",
        help="Supported: CSV, Excel (.xlsx/.xls), JSON, TSV, Parquet, TXT",
    )
    if uploaded is not None:
        _raw = uploaded.read()
        _name = uploaded.name.lower()
        try:
            if _name.endswith((".xlsx", ".xls")):
                _all = pd.read_excel(io.BytesIO(_raw), sheet_name=None)
                sheets = {k: v for k, v in _all.items()}
            elif _name.endswith(".json"):
                sheets = {"Data": pd.read_json(io.BytesIO(_raw))}
            elif _name.endswith((".tsv", ".txt")):
                sheets = {"Data": pd.read_csv(io.BytesIO(_raw), sep="\t")}
            elif _name.endswith(".parquet"):
                sheets = {"Data": pd.read_parquet(io.BytesIO(_raw))}
            else:
                sheets = {"Data": pd.read_csv(io.BytesIO(_raw))}
            st.session_state["sense_sheets"] = sheets
            st.session_state["sense_filename"] = uploaded.name
            st.session_state.pop("sense_ai_insights", None)
            st.session_state.pop("sense_ai_insights_err", None)
            _sense_save(sheets, uploaded.name)
            _sense_save_protected(sheets, uploaded.name)  # lock Legend + Audit
            st.rerun()
        except Exception as _e:
            st.error(f"Could not read file: {_e}")

    sheets = st.session_state.get("sense_sheets") or {}
    fname  = st.session_state.get("sense_filename", "data")

    # ── Build legend map (needed for New Audit tab even with no sheets) ───────
    _legend_map_pre = {}
    for _k, _v in sheets.items():
        if "legend" in _k.lower():
            _legend_map_pre = _parse_legend(_v)
            break

    if not sheets:
        # No file yet — still allow all tabs; Insights uses seed data
        _tabs_empty = st.tabs(["📊  Scorecard", "✍️  New Audit", "📖  Legend", "🤖  Insights"])
        with _tabs_empty[0]:
            _render_sense_scorecard({}, {})
        with _tabs_empty[1]:
            _render_audit_form(_legend_map_pre, "")
        with _tabs_empty[2]:
            _render_legend_page()
        with _tabs_empty[3]:
            _render_sense_insights(pd.DataFrame(), "Seed Data", {}, legend_map=_legend_map_pre)
        return

    # ── File info bar ─────────────────────────────────────────────────────────
    _total_rows = sum(len(v) for v in sheets.values())
    col_info, col_clear = st.columns([6, 1])
    with col_info:
        _sheet_names = ", ".join(sheets.keys())
        st.markdown(
            f'<div style="font-size:0.78rem;color:#5588bb;padding:6px 0;">'
            f'📄 <strong>{fname}</strong> &nbsp;·&nbsp; {len(sheets)} sheet{"s" if len(sheets)>1 else ""}'
            f' &nbsp;·&nbsp; {_total_rows:,} total rows &nbsp;·&nbsp; <span style="color:#2563EB;">{_sheet_names}</span></div>',
            unsafe_allow_html=True,
        )
    with col_clear:
        if st.button("✕ Clear other sheets", key="sense_clear", use_container_width=True):
            # Save protected sheets before wiping session
            _cur_sheets = st.session_state.get("sense_sheets", {})
            _cur_fname  = st.session_state.get("sense_filename", "data")
            _prot_sheets = {k: v for k, v in _cur_sheets.items() if _is_protected_sheet(k)}
            # Wipe session state
            _stale = [k for k in st.session_state if any(k.startswith(p) for p in
                ("sense_sheets", "sense_filename", "sense_ai_insights", "sense_audit_edits", "sense_editor_"))]
            for _k in _stale:
                st.session_state.pop(_k, None)
            _sense_clear_cache()
            # Restore protected sheets immediately
            if _prot_sheets:
                st.session_state["sense_sheets"] = _prot_sheets
                st.session_state["sense_filename"] = _cur_fname
            st.rerun()

    # ── Sheet icon mapping ────────────────────────────────────────────────────
    _SHEET_ICONS = {
        "dashboard":   "📈",
        "audit":       "📋",
        "trend":       "📉",
        "legend":      "📖",
        "formula":     "🧮",
        "data":        "🗂️",
        "summary":     "📊",
        "overview":    "🔍",
        "insight":     "💡",
        "report":      "📝",
        "metric":      "📐",
    }
    def _sheet_icon(name):
        _low = name.lower()
        for key, icon in _SHEET_ICONS.items():
            if key in _low:
                return icon
        return "📄"

    # Legend map already built above (_legend_map_pre); reuse it
    _legend_map = _legend_map_pre

    # ── Dynamic tabs: Scorecard, New Audit, one per sheet, AI Insights ───────
    def _tab_label(name):
        icon = _sheet_icon(name)
        lock = " 🔒" if _is_protected_sheet(name) else ""
        return f"{icon}  {name}{lock}"

    _tab_labels = ["📊  Scorecard", "✍️  New Audit", "📖  Legend"] + [_tab_label(s) for s in sheets] + ["🗂️  Registry", "🤖  Insights"]
    _tabs = st.tabs(_tab_labels)

    with _tabs[0]:
        _render_sense_scorecard(sheets, _legend_map)

    with _tabs[1]:
        _render_audit_form(_legend_map, fname)

    with _tabs[2]:
        _render_legend_page()

    for i, (sheet_name, df) in enumerate(sheets.items()):
        with _tabs[i + 3]:
            _render_sense_sheet(df, sheet_name, fname, sheets=sheets)

    with _tabs[-2]:
        _render_registry()

    with _tabs[-1]:
        # Prefer the Audit sheet as the primary df; fall back to first sheet
        _primary_df = next(
            (v for k, v in sheets.items() if any(kw in k.lower() for kw in ("audit","qa","review","score"))),
            next(iter(sheets.values()))
        )
        _render_sense_insights(_primary_df, fname, sheets, legend_map=_legend_map)


if not st.session_state["show_sidebar"]:
    st.markdown("""
    <style>
    section[data-testid="stSidebar"]       { display:none !important; }
    [data-testid="collapsedControl"]        { display:none !important; }
    [data-testid="stSidebarCollapseButton"] { display:none !important; }
    </style>""", unsafe_allow_html=True)

# ─── Top navigation bar ───────────────────────────────────────────────────────

_app_mode = st.session_state["app_mode"]
_current_page = st.session_state["current_page"]

st.markdown("""<style>.stApp > header { display: none !important; }</style>""", unsafe_allow_html=True)

if _app_mode == "Home":
    render_home()

elif _app_mode == "CDL":
    # ── CDL header ────────────────────────────────────────────────────────────
    st.markdown(f"""
<style>
@keyframes navGradient {{
    0%   {{ background-position: 0% 50%; }}
    50%  {{ background-position: 100% 50%; }}
    100% {{ background-position: 0% 50%; }}
}}
.cdl-navbar {{
    background: linear-gradient(135deg, #0B1F3A, #2563EB);
    background-size: 300% 300%;
    animation: navGradient 8s ease infinite;
    padding: 0 28px;
    height: 62px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: -1rem -1rem 0 -1rem;
    box-shadow: 0 4px 30px rgba(61,130,245,0.55), 0 1px 0 rgba(255,255,255,0.08);
    position: sticky;
    top: 0;
    z-index: 1000;
}}
</style>
<div class="cdl-navbar">
    <div style="display:flex;align-items:center;gap:12px;">
        <div style="filter:drop-shadow(0 2px 8px rgba(0,0,0,0.4));flex-shrink:0;">{_logo_img(38, 10)}</div>
        <div>
            <div style="color:#fff;font-weight:800;font-size:0.96rem;letter-spacing:-0.01em;line-height:1.1;text-shadow:0 1px 8px rgba(0,0,0,0.3);">Convin Data Labs</div>
            <div style="color:rgba(255,255,255,0.55);font-size:0.58rem;font-weight:500;letter-spacing:0.1em;text-transform:uppercase;">Insights Dashboard</div>
        </div>
    </div>
    <div style="background:rgba(0,0,0,0.22);border:1px solid rgba(255,255,255,0.25);border-radius:99px;padding:5px 14px 5px 8px;display:flex;align-items:center;gap:8px;box-shadow:0 2px 12px rgba(0,0,0,0.3);">
        <div style="width:26px;height:26px;border-radius:50%;background:rgba(255,255,255,0.2);display:flex;align-items:center;justify-content:center;font-size:0.68rem;font-weight:800;color:#fff;border:1px solid rgba(255,255,255,0.3);">
            {(st.session_state.get("user_email","?")[0]).upper()}
        </div>
        <div style="color:rgba(255,255,255,0.9);font-size:0.72rem;font-weight:600;max-width:140px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
            {st.session_state.get("user_email","—")}
        </div>
    </div>
</div>""", unsafe_allow_html=True)

    st.markdown("""
<style>
div[data-testid="stHorizontalBlock"]:has(button[key="nav_settings"]) {
    background: #ffffff !important;
    border-bottom: 1px solid #e8edf8 !important;
    padding: 4px 0 6px !important;
    margin-bottom: 1.4rem !important;
    box-shadow: 0 1px 6px rgba(210,44,132,0.06) !important;
}
div[data-testid="stHorizontalBlock"]:has(button[key="nav_settings"]) button[kind="primary"] {
    background: linear-gradient(135deg, #0B1F3A, #2563EB) !important;
    color: #ffffff !important; border: none !important;
    box-shadow: 0 2px 14px rgba(61,130,245,0.55) !important;
    font-weight: 700 !important; border-radius: 7px !important;
}
div[data-testid="stHorizontalBlock"]:has(button[key="nav_settings"]) button[kind="secondary"] {
    background: transparent !important;
    border: 1px solid rgba(61,130,245,0.22) !important;
    color: #6699cc !important; border-radius: 7px !important;
}
div[data-testid="stHorizontalBlock"]:has(button[key="nav_settings"]) button[kind="secondary"]:hover {
    background: rgba(61,130,245,0.07) !important;
    border-color: rgba(61,130,245,0.4) !important;
    color: #2563EB !important;
}
</style>""", unsafe_allow_html=True)

    _n0, _n_home, _n1, _n2, _n3, _n4, _n_switch = st.columns([1.0, 1.0, 1.4, 1.3, 1.7, 1.5, 1.8])
    with _n0:
        _sb_label = "✕ Close" if st.session_state["show_sidebar"] else "⚙️ Settings"
        if st.button(_sb_label, key="nav_settings", use_container_width=True):
            st.session_state["show_sidebar"] = not st.session_state["show_sidebar"]
            st.rerun()
    with _n_home:
        if st.button("⌂ Home", key="nav_home_cdl", use_container_width=True, type="secondary"):
            st.session_state["app_mode"] = "Home"
            st.rerun()
    for _key, _label, _col in [
        ("Overview",      "📊 Overview",      _n1),
        ("Clients",       "🏢 Clients",       _n2),
        ("Client Emails", "📋 Client Emails", _n3),
        ("Email Maker",   "📧 Email Maker",   _n4),
    ]:
        with _col:
            if st.button(_label, key=f"nav_{_key}", use_container_width=True,
                         type="primary" if _current_page == _key else "secondary"):
                st.session_state["current_page"] = _key
                st.rerun()
    with _n_switch:
        if st.button("🎯 Audit →", key="nav_switch_to_sense", use_container_width=True, type="secondary"):
            st.session_state["app_mode"] = "Audit"
            st.session_state["current_page"] = "Audit"
            st.rerun()

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # ── CDL page routing ──────────────────────────────────────────────────────
    _page = st.session_state["current_page"]
    if _page == "Overview":
        render_overview()
    elif _page == "Clients":
        render_clients()
    elif _page == "Client Emails":
        render_client_emails()
    elif _page == "Email Maker":
        render_email_maker()
    else:
        render_overview()

else:
    # ── Sense Audit header ────────────────────────────────────────────────────
    st.markdown(f"""
<style>
@keyframes navGradientSenseTop {{
    0%   {{ background-position: 0% 50%; }}
    50%  {{ background-position: 100% 50%; }}
    100% {{ background-position: 0% 50%; }}
}}
.sense-navbar {{
    background: linear-gradient(108deg, #040d1e, #0d1230 40%, #1a0d30 70%, #040d1e);
    background-size: 300% 300%;
    animation: navGradientSenseTop 10s ease infinite;
    padding: 0 28px;
    height: 62px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: -1rem -1rem 0 -1rem;
    border-bottom: 1px solid rgba(37,99,235,0.3);
    box-shadow: 0 4px 30px rgba(37,99,235,0.2), 0 1px 0 rgba(255,255,255,0.04);
    position: sticky;
    top: 0;
    z-index: 1000;
}}
</style>
<div class="sense-navbar">
    <div style="display:flex;align-items:center;gap:12px;">
        <div style="filter:drop-shadow(0 2px 8px rgba(0,0,0,0.4));flex-shrink:0;">{_logo_img(38, 10)}</div>
        <div>
            <div style="color:#fff;font-weight:800;font-size:0.96rem;letter-spacing:-0.01em;line-height:1.1;text-shadow:0 1px 8px rgba(0,0,0,0.3);">Audit</div>
            <div style="color:rgba(37,99,235,0.7);font-size:0.58rem;font-weight:600;letter-spacing:0.12em;text-transform:uppercase;">QA &amp; Bot Intelligence</div>
        </div>
    </div>
    <div style="background:rgba(0,0,0,0.3);border:1px solid rgba(37,99,235,0.25);border-radius:99px;padding:5px 14px 5px 8px;display:flex;align-items:center;gap:8px;">
        <div style="width:26px;height:26px;border-radius:50%;background:rgba(37,99,235,0.2);display:flex;align-items:center;justify-content:center;font-size:0.68rem;font-weight:800;color:#2563EB;border:1px solid rgba(37,99,235,0.3);">
            {(st.session_state.get("user_email","?")[0]).upper()}
        </div>
        <div style="color:rgba(255,255,255,0.85);font-size:0.72rem;font-weight:600;max-width:140px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
            {st.session_state.get("user_email","—")}
        </div>
    </div>
</div>""", unsafe_allow_html=True)

    st.markdown("""
<style>
div[data-testid="stHorizontalBlock"]:has(button[key="nav_back_to_cdl"]) {
    background: #06101f !important;
    border-bottom: 1px solid rgba(37,99,235,0.15) !important;
    padding: 4px 0 6px !important;
    margin-bottom: 1.4rem !important;
}
div[data-testid="stHorizontalBlock"]:has(button[key="nav_back_to_cdl"]) button[kind="secondary"] {
    background: transparent !important;
    border: 1px solid rgba(37,99,235,0.3) !important;
    color: rgba(37,99,235,0.8) !important;
    border-radius: 7px !important;
}
div[data-testid="stHorizontalBlock"]:has(button[key="nav_back_to_cdl"]) button[kind="secondary"]:hover {
    background: rgba(37,99,235,0.08) !important;
    color: #2563EB !important;
}
</style>""", unsafe_allow_html=True)

    _sb_col, _home_col, _back_col, _spacer_col = st.columns([1.0, 1.0, 2.0, 6.0])
    with _sb_col:
        _sb_label = "✕ Close" if st.session_state["show_sidebar"] else "⚙️ Settings"
        if st.button(_sb_label, key="nav_settings_sense", use_container_width=True, type="secondary"):
            st.session_state["show_sidebar"] = not st.session_state["show_sidebar"]
            st.rerun()
    with _home_col:
        if st.button("⌂ Home", key="nav_home_sense", use_container_width=True, type="secondary"):
            st.session_state["app_mode"] = "Home"
            st.rerun()
    with _back_col:
        if st.button("← CDL Dashboard", key="nav_back_to_cdl", use_container_width=True, type="secondary"):
            st.session_state["app_mode"] = "CDL"
            st.session_state["current_page"] = "Overview"
            st.rerun()

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # ── Sense Audit page routing ──────────────────────────────────────────────
    render_convin_sense()
