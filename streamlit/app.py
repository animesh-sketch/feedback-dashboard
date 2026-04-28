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
import param_store
import pending_store

# ─── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Convin Data Labs",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── Type definitions ────────────────────────────────────────────────────────
_TYPE_LABELS = {
    "dropdown": "📋 Dropdown",
    "scoring":  "⭐ Scoring (1–5)",
    "number":   "🔢 Number",
    "text":     "✏️ Text",
}
_TYPE_KEYS = list(_TYPE_LABELS.keys())

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
        pin = st.text_input(
            "Access Code",
            placeholder="Enter your 4-digit code",
            type="password",
            key="login_pin",
            max_chars=6,
        )
        if st.button("Sign in", type="primary", use_container_width=True, key="login_btn"):
            ok, user, err = auth.check_login(pin)
            if ok:
                st.session_state["logged_in"]  = True
                st.session_state["auth_user"]  = user
                st.session_state["user_email"] = user["name"]
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
    _total_failed    = sum(len(r.get("failed",  [])) for r in _sent_recs)
    _total_attempted = _total_delivered + _total_failed
    _total_opens     = len(_ts["opens"]) + len(_ts["clicks"])   # clicks imply open
    _total_clicks    = len(_ts["clicks"])
    _total_ratings   = _ts["total_ratings"]

    _open_rate_pct   = round(_total_opens  / _total_delivered * 100, 1) if _total_delivered else 0
    _click_rate_pct  = round(_total_clicks / _total_delivered * 100, 1) if _total_delivered else 0
    _cto_pct         = round(_total_clicks / _total_opens * 100, 1) if _total_opens else 0
    _delivered_pct   = round(_total_delivered / _total_attempted * 100, 1) if _total_attempted else 100.0
    _bounce_pct      = round(_total_failed    / _total_attempted * 100, 1) if _total_attempted else 0.0

    _period_labels   = {"Daily": "Today", "Weekly": "This Week", "Monthly": "All Time"}
    _real_data = {
        "label":   _period_labels.get(period, period),
        "updated": "Live",
        "metrics": [
            {"label": "Total Sent",     "value": str(_total_delivered),                      "sub": None,                                "change": None, "up_good": True},
            {"label": "Open Rate",      "value": f"{_open_rate_pct}%",                       "sub": f"{_total_opens} opens",             "change": None, "up_good": True},
            {"label": "Click to Open",  "value": f"{_cto_pct}%",                             "sub": f"{_total_clicks} clicks",           "change": None, "up_good": True},
            {"label": "Delivered Rate", "value": f"{_delivered_pct}%",                       "sub": f"{_total_delivered} emails",        "change": None, "up_good": True},
            {"label": "Bounce Rate",    "value": f"{_bounce_pct}%",                          "sub": f"{_total_failed} failed" if _total_failed else None, "change": None, "up_good": False},
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

    _render_ai_summary(period, csat, respondents)

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
/* glow orb top-right of each card */
.h-card::before {{
    content: ""; position: absolute; top: -60px; right: -60px;
    width: 220px; height: 220px; border-radius: 50%; pointer-events: none;
    animation: hFloat 6s ease-in-out infinite;
}}
.h-card-cdl::before  {{ background: radial-gradient(circle, rgba(147,197,253,0.25) 0%, transparent 65%); }}

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

    _col_cdl, = st.columns([1])

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
        st.markdown("---")
        _sb_hdr_col, _sb_tog_col = st.columns([6, 2])
        with _sb_hdr_col:
            st.markdown('<div class="section-chip">📊 Performance Scoreboard</div>', unsafe_allow_html=True)
        with _sb_tog_col:
            _sb_enabled = st.toggle("Include in email", value=d.get("scoreboard_enabled", False), key=f"cc_sb_on_{ci}")
        d["scoreboard_enabled"] = _sb_enabled

        if _sb_enabled:
            # Load params
            if "sense_custom_audit_params" not in st.session_state:
                st.session_state["sense_custom_audit_params"] = param_store.load()
            _param_names = [p["name"] for p in st.session_state["sense_custom_audit_params"]]
            _param_map   = {p["name"]: p for p in st.session_state["sense_custom_audit_params"]}

            if "sb_rows" not in d or not isinstance(d.get("sb_rows"), list):
                d["sb_rows"] = []

            _sb_left, _sb_right = st.columns([3, 2])

            with _sb_left:
                d["scoreboard_title"] = st.text_input(
                    "Title",
                    value=d.get("scoreboard_title", "Performance Scoreboard"),
                    key=f"cc_sb_title_{ci}",
                    placeholder="e.g. Bot Performance — April",
                )

                _STATUS_OPTS  = ["good", "warning", "bad", "neutral"]
                _STATUS_ICONS = {"good": "🟢", "warning": "🟡", "bad": "🔴", "neutral": "⚪"}

                _rows_updated = []
                for _ri, _row in enumerate(d["sb_rows"]):
                    st.markdown(f'<div style="font-size:0.68rem;font-weight:700;color:#64748b;'
                                f'letter-spacing:0.07em;text-transform:uppercase;margin:10px 0 4px;">'
                                f'Metric {_ri + 1}</div>', unsafe_allow_html=True)

                    _mc1, _mc2, _mc_del = st.columns([4, 1, 0.6])
                    with _mc1:
                        _use_custom = _row.get("label", "") not in _param_names
                        if _param_names:
                            _label_opts = _param_names + ["✏️ Custom…"]
                            _sel_idx    = _param_names.index(_row["label"]) if _row["label"] in _param_names else len(_param_names)
                            _sel        = st.selectbox("Label", _label_opts, index=min(_sel_idx, len(_label_opts)-1), key=f"sb_lbl_{ci}_{_ri}", label_visibility="collapsed")
                            _label      = st.text_input("Custom", value=_row.get("label",""), key=f"sb_cust_{ci}_{_ri}", label_visibility="collapsed", placeholder="Custom label…") if _sel == "✏️ Custom…" else _sel
                        else:
                            _label = st.text_input("Label", value=_row.get("label",""), key=f"sb_lbl_t_{ci}_{_ri}", label_visibility="collapsed", placeholder="Metric name")
                    with _mc2:
                        _rtype_src = _param_map.get(_label, {}).get("input_type", _row.get("type", "text"))
                        _rtype_idx = _TYPE_KEYS.index(_rtype_src) if _rtype_src in _TYPE_KEYS else 3
                        _rtype     = st.selectbox("Type", _TYPE_KEYS, index=_rtype_idx, format_func=lambda k: _TYPE_LABELS[k], key=f"sb_type_{ci}_{_ri}", label_visibility="collapsed")
                    with _mc_del:
                        if st.button("✕", key=f"sb_rm_{ci}_{_ri}", use_container_width=True, help="Remove"):
                            continue

                    _mv1, _mv2 = st.columns([3, 1])
                    with _mv1:
                        if _rtype == "scoring":
                            _raw_v = _row.get("value", "3")
                            _int_v = int(_raw_v) if str(_raw_v).isdigit() and 1 <= int(_raw_v) <= 5 else 3
                            _val   = str(st.slider("Score 1–5", 1, 5, _int_v, key=f"sb_val_{ci}_{_ri}", label_visibility="collapsed"))
                        elif _rtype == "dropdown" and _label in _param_map:
                            _opts = _param_map[_label].get("options", ["Yes", "No"])
                            _cur  = _row.get("value", _opts[0]) if _row.get("value") in _opts else _opts[0]
                            _val  = st.selectbox("Value", _opts, index=_opts.index(_cur), key=f"sb_val_{ci}_{_ri}", label_visibility="collapsed")
                        elif _rtype == "number":
                            _val = str(st.number_input("Value", value=float(_row.get("value") or 0), key=f"sb_val_{ci}_{_ri}", label_visibility="collapsed"))
                        else:
                            _val = st.text_input("Value", value=str(_row.get("value","")), key=f"sb_val_{ci}_{_ri}", label_visibility="collapsed", placeholder="e.g. 87%")
                    with _mv2:
                        _cur_status = _row.get("status", "neutral")
                        _stat_idx   = _STATUS_OPTS.index(_cur_status) if _cur_status in _STATUS_OPTS else 3
                        _status     = st.selectbox(
                            "Status", _STATUS_OPTS, index=_stat_idx,
                            format_func=lambda s: f"{_STATUS_ICONS[s]} {s.capitalize()}",
                            key=f"sb_status_{ci}_{_ri}", label_visibility="collapsed",
                        )

                    _rows_updated.append({"label": _label, "value": _val, "type": _rtype, "status": _status})

                d["sb_rows"] = _rows_updated
                d["scoreboard_rows"] = d["sb_rows"]

                _qadd1, _qadd2, _qadd3, _qadd4 = st.columns(4)
                with _qadd1:
                    if st.button("➕ Metric", key=f"sb_add_{ci}", use_container_width=True):
                        d["sb_rows"].append({"label": "", "value": "", "type": "text", "status": "neutral"})
                        d["scoreboard_rows"] = d["sb_rows"]
                        st.rerun()
                with _qadd2:
                    if st.button("⭐ Scoring", key=f"sb_qadd_score_{ci}", use_container_width=True, help="Add a 1–5 scoring row"):
                        d["sb_rows"].append({"label": "Score", "value": "4", "type": "scoring", "status": "good"})
                        d["scoreboard_rows"] = d["sb_rows"]
                        st.rerun()
                with _qadd3:
                    if st.button("📈 Number", key=f"sb_qadd_num_{ci}", use_container_width=True, help="Add a numeric metric"):
                        d["sb_rows"].append({"label": "Metric", "value": "85", "type": "number", "status": "neutral"})
                        d["scoreboard_rows"] = d["sb_rows"]
                        st.rerun()
                with _qadd4:
                    if st.button("✅ Yes/No", key=f"sb_qadd_drop_{ci}", use_container_width=True, help="Add a Yes/No metric"):
                        d["sb_rows"].append({"label": "Check", "value": "Yes", "type": "dropdown", "status": "good"})
                        d["scoreboard_rows"] = d["sb_rows"]
                        st.rerun()

                if not d["sb_rows"]:
                    st.caption("No metrics yet — use the buttons above to add one.")

            with _sb_right:
                st.markdown('<div style="font-size:0.68rem;font-weight:700;color:#64748b;letter-spacing:0.07em;text-transform:uppercase;margin-bottom:8px;">Live Preview</div>', unsafe_allow_html=True)
                if d["sb_rows"]:
                    from email_builder import _build_scoreboard_html as _sbprev
                    _prev_html = _sbprev(d.get("scoreboard_title","Performance Scoreboard"), d["sb_rows"])
                    _prev_html_wrap = f'<div style="transform:scale(0.78);transform-origin:top left;width:128%;pointer-events:none;">{_prev_html}</div>'
                    st.markdown(_prev_html_wrap, unsafe_allow_html=True)
                else:
                    st.markdown('<div style="border:2px dashed #e2e8f0;border-radius:10px;padding:32px 16px;text-align:center;color:#94a3b8;font-size:0.8rem;">Add metrics to see preview</div>', unsafe_allow_html=True)

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


_app_mode = st.session_state["app_mode"]
_current_page = st.session_state["current_page"]

st.markdown("""<style>.stApp > header { display: none !important; }</style>""", unsafe_allow_html=True)

_auth_role = auth.current_user().get("role", "admin")

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
            {auth.current_name()[:1].upper() or "?"}
        </div>
        <div style="color:rgba(255,255,255,0.9);font-size:0.72rem;font-weight:600;max-width:140px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
            {auth.current_name() or "—"} {auth.role_icon()}
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

    _n0, _n_home, _n1, _n2, _n3, _n4 = st.columns([1.0, 1.0, 1.5, 1.4, 1.8, 1.6])
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

