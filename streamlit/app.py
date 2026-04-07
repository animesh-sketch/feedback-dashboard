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
        return f'<div style="width:{size}px;height:{size}px;border-radius:{br}px;background:linear-gradient(135deg,#e0368e,#3d8ef5);display:flex;align-items:center;justify-content:center;font-size:0.6rem;font-weight:900;color:#fff;">CDL</div>'

import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import base64
import io
from PIL import Image
from data import format_kpi, format_delta, delta_is_positive, CAMPAIGNS, ACTION_QUEUE, HEALTH_KPIS, CSAT_RESPONDENTS
from email_builder import build_email_html, TEMPLATE_NAMES
import client_store
import sent_store
import client_emails_store
import auth
import gmail_sender
import tracking_store

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

if "show_sidebar" not in st.session_state:
    st.session_state["show_sidebar"] = False

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
              text-align:center;box-shadow:0 0 60px rgba(224,54,142,0.3),0 4px 32px rgba(0,0,0,0.6);border:1px solid rgba(224,54,142,0.2);">
    <div style="font-size:52px;margin-bottom:20px;">✅</div>
    <div style="font-size:12px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;
                background:linear-gradient(108deg,#e0368e,#ff6b78 52%,#3d8ef5);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;margin-bottom:12px;">Feedback received</div>
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
    --brand-primary:   #e0368e;
    --brand-dark:      #c4267a;
    --brand-deep:      #b5206f;
    --brand-navy:      #8a1855;
    --brand-bright:    #3d8ef5;
    --brand-pink:      #e0368e;
    --brand-coral:     #ff6b78;
    --neutral-black:   #0d1d3a;
    --neutral-body:    #1e3a5f;
    --neutral-secondary: #3a6699;
    --neutral-outline: rgba(61,130,245,0.25);
    --neutral-smoke:   rgba(61,130,245,0.06);
    --bg-page:         #e8f4ff;
    --bg-card:         #ffffff;
    --bg-card-2:       #f0f7ff;
    --bg-blue-xl:      rgba(61,130,245,0.06);
    --bg-blue-shade:   rgba(61,130,245,0.18);
    --gradient-blue:   linear-gradient(108deg, #e0368e, #ff6b78 52%, #3d8ef5);
    --gradient-brand:  linear-gradient(108deg, #e0368e, #ff6b78 52%, #3d8ef5);
    --glow-pink:       0 0 24px rgba(61,130,245,0.3);
    --glow-strong:     0 0 40px rgba(61,130,245,0.35), 0 0 80px rgba(61,142,245,0.15);
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
section[data-testid="stSidebar"] { background: #cde4ff !important; border-right: 1px solid rgba(61,130,245,0.25) !important; }
section[data-testid="stSidebar"] > div { background: #cde4ff !important; }
section[data-testid="stSidebar"] label { color: #1e3a5f !important; font-size: 0.86rem !important; font-weight: 500 !important; }
section[data-testid="stSidebar"] p { color: #1e3a5f !important; }
section[data-testid="stSidebar"] span { color: #1e3a5f !important; }
section[data-testid="stSidebar"] .stRadio > div { gap: 2px !important; }
section[data-testid="stSidebar"] .stRadio label {
    padding: 8px 10px !important;
    border-radius: 8px !important;
    transition: background 0.15s !important;
}
section[data-testid="stSidebar"] .stRadio label:has(input:checked) {
    background: rgba(61,130,245,0.15) !important;
    color: var(--brand-primary) !important;
    border-left: 3px solid var(--brand-primary) !important;
}
section[data-testid="stSidebar"] hr { border-color: rgba(61,130,245,0.15) !important; }

/* ── Inputs & textareas ── */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {
    background: #f0f8ff !important;
    border: 1.5px solid rgba(61,130,245,0.25) !important;
    border-radius: 10px !important;
    color: #0d1d3a !important;
    font-size: 0.84rem !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}
[data-testid="stTextInput"] input::placeholder,
[data-testid="stTextArea"] textarea::placeholder { color: #8aabcc !important; }
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
    border-color: var(--brand-primary) !important;
    box-shadow: 0 0 0 3px rgba(61,130,245,0.18), var(--glow-pink) !important;
    outline: none !important;
}
[data-testid="stSelectbox"] > div > div {
    background: #f0f8ff !important;
    border: 1.5px solid rgba(61,130,245,0.25) !important;
    border-radius: 10px !important;
    color: #0d1d3a !important;
}
[data-testid="stMultiSelect"] > div > div {
    background: #f0f8ff !important;
    border: 1.5px solid rgba(61,130,245,0.25) !important;
    border-radius: 10px !important;
    color: #0d1d3a !important;
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
    background: linear-gradient(108deg, #e0368e, #ff6b78 52%, #3d8ef5) !important;
    color: #fff !important;
    box-shadow: 0 2px 14px rgba(61,130,245,0.5) !important;
}
.stButton > button[kind="primary"]:hover {
    filter: brightness(1.1) !important;
    box-shadow: 0 4px 24px rgba(61,130,245,0.7), 0 0 40px rgba(224,54,142,0.2) !important;
    transform: translateY(-2px) !important;
}
.stButton > button[kind="secondary"] {
    background: rgba(61,130,245,0.06) !important;
    border: 1px solid rgba(61,130,245,0.25) !important;
    color: #3a6699 !important;
}
.stButton > button[kind="secondary"]:hover {
    background: rgba(61,130,245,0.07) !important;
    border-color: rgba(224,54,142,0.4) !important;
    color: #e0368e !important;
    transform: translateY(-1px) !important;
}

/* ── Download button ── */
[data-testid="stDownloadButton"] button {
    background: rgba(61,130,245,0.07) !important;
    border: 1px solid rgba(61,130,245,0.3) !important;
    border-radius: 8px !important;
    color: #e0368e !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    transition: all 0.2s ease !important;
}
[data-testid="stDownloadButton"] button:hover {
    background: rgba(61,130,245,0.18) !important;
    border-color: rgba(61,130,245,0.55) !important;
    box-shadow: 0 0 16px rgba(224,54,142,0.3) !important;
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
.metric-card.accent-blue::before   { background: var(--gradient-blue); box-shadow: 0 2px 12px rgba(224,54,142,0.6); }
.metric-card.accent-green::before  { background: linear-gradient(90deg, #0ebc6e, #42ba78); box-shadow: 0 2px 12px rgba(14,188,110,0.5); }
.metric-card.accent-red::before    { background: linear-gradient(90deg, #e72b3b, #ff6b78); box-shadow: 0 2px 12px rgba(231,43,59,0.5); }
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
.csat-number { font-size: 3.2rem; font-weight: 800; background: var(--gradient-brand); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; letter-spacing: -0.05em; line-height: 1; filter: drop-shadow(0 0 12px rgba(224,54,142,0.4)); }
.csat-stars { color: #ffaa00; font-size: 1.1rem; margin: 10px 0 6px; letter-spacing: 3px; text-shadow: 0 0 10px rgba(255,170,0,0.5); }
.csat-count { font-size: 0.7rem; color: #7a99bb; }
.bar-row { display: flex; align-items: center; gap: 12px; margin-bottom: 11px; }
.bar-row:last-child { margin-bottom: 0; }
.bar-star  { font-size: 0.67rem; color: #7a99bb; width: 18px; text-align: right; flex-shrink: 0; }
.bar-track { flex: 1; height: 6px; background: rgba(61,130,245,0.12); border-radius: 99px; overflow: hidden; }
.bar-fill  { height: 100%; border-radius: 99px; background: var(--gradient-blue); box-shadow: 0 0 8px rgba(224,54,142,0.4); animation: barSlide 1s ease both; }
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
    background: rgba(224,54,142,0.1);
    display: flex; align-items: center; justify-content: center;
    font-size: 1.2rem;
    flex-shrink: 0;
    border: 1px solid rgba(61,130,245,0.3);
    box-shadow: 0 0 16px rgba(224,54,142,0.2);
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
    box-shadow: 0 8px 40px rgba(61,130,245,0.26), 0 0 60px rgba(61,142,245,0.08);
    border-color: rgba(224,54,142,0.4);
    transform: translateY(-3px);
}
.tag-chip {
    display: inline-block;
    background: rgba(224,54,142,0.1);
    color: #e0368e;
    font-size: 0.61rem;
    font-weight: 700;
    padding: 3px 10px;
    border-radius: 99px;
    margin: 2px 3px 0 0;
    border: 1px solid rgba(224,54,142,0.2);
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
    box-shadow: 0 8px 36px rgba(224,54,142,0.2);
    border-color: rgba(61,130,245,0.4);
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
    background: rgba(224,54,142,0.1);
    color: var(--brand-primary);
    font-size: 0.7rem;
    font-weight: 500;
    padding: 3px 10px;
    border-radius: 6px;
    margin: 3px 3px 0 0;
    border: 1px solid rgba(61,130,245,0.26);
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
    color: var(--brand-primary);
    background: rgba(224,54,142,0.1);
    border: 1px solid rgba(61,130,245,0.3);
    border-radius: 6px;
    padding: 3px 10px;
    margin-bottom: 14px;
    box-shadow: 0 0 12px rgba(61,130,245,0.18);
}

/* ── Client avatar ── */
.client-avatar {
    width: 46px; height: 46px;
    border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.82rem; font-weight: 800;
    flex-shrink: 0;
    box-shadow: 0 4px 16px rgba(61,130,245,0.12), 0 0 20px rgba(224,54,142,0.15);
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
    background: #daeeff !important;
    border-bottom: 1px solid rgba(61,130,245,0.2) !important;
    box-shadow: 0 1px 20px rgba(61,130,245,0.08) !important;
}

/* ── Tab overrides ── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    border-bottom-color: rgba(61,130,245,0.18) !important;
}
[data-baseweb="tab"] { color: #3a6699 !important; }
[aria-selected="true"][data-baseweb="tab"] {
    color: #e0368e !important;
    border-bottom-color: #e0368e !important;
}

/* ── Streamlit overrides ── */
p, .stMarkdown p { color: #1e3a5f !important; }
h1, h2, h3 { color: #0d1d3a !important; }
[data-testid="stMetricValue"] { color: #0d1d3a !important; }

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
    .login-brand {{ font-size: 0.58rem; font-weight: 700; letter-spacing: 0.15em; text-transform: uppercase; color: #e0368e; margin-bottom: 6px; }}
    .login-title {{ font-size: 1.5rem; font-weight: 800; color: #0d1d3a; margin-bottom: 0.3rem; letter-spacing: -0.03em; line-height: 1.2; }}
    .login-divider {{ width: 40px; height: 3px; background: linear-gradient(90deg, #e0368e, #ff6b78 52%, #3d8ef5); border-radius: 2px; margin: 12px auto 20px; box-shadow: 0 0 10px rgba(61,130,245,0.3); }}
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
                <div style="color:#e0368e;font-size:0.6rem;margin-top:2px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;">Settings</div>
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
        f"""<tr style="transition:background 0.15s;" onmouseover="this.style.background='rgba(224,54,142,0.05)'" onmouseout="this.style.background='transparent'">
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
            f'<div style="width:8px;height:8px;border-radius:50%;background:linear-gradient(135deg,#e0368e,#3d8ef5);flex-shrink:0;box-shadow:0 0 6px rgba(61,130,245,0.55);"></div>'
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


# ─── Overview ─────────────────────────────────────────────────────────────────

def render_overview():
    st.markdown("""<div class="page-header">
        <div class="page-header-icon">📊</div>
        <div class="page-header-text">
            <div class="page-title">Overview</div>
            <div class="page-sub">Convin Data Labs · Insights Report Feedback Dashboard</div>
        </div>
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
    cid   = c["id"]
    emails = c.get("emails", [])
    tags   = c.get("tags", [])
    notes  = str(c.get("notes") or "")
    confirm_key   = f"confirm_del_{cid}"
    is_confirming = st.session_state.get(confirm_key, False)
    is_editing    = st.session_state.get(f"editing_{cid}", False)

    # ── Card container
    with st.container(border=True):
        # Company + contact
        col_av, col_info = st.columns([1, 8])
        with col_av:
            st.markdown(_avatar(c.get("company", "")), unsafe_allow_html=True)
        with col_info:
            st.markdown(f"**{c.get('company', '')}**")
            if c.get("contact"):
                st.caption(f"👤 {c['contact']}")

        # Emails — always visible, each on its own line
        st.markdown("**📧 Email Addresses**")
        if emails:
            for e in emails:
                st.markdown(
                    f'<div style="background:#eef5ff;border:1px solid #b3d0ff;border-radius:8px;'
                    f'padding:8px 14px;margin-bottom:5px;font-size:0.85rem;color:#0d1d3a;font-weight:500;">'
                    f'✉&nbsp;&nbsp;{e}</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No email addresses saved yet.")

        # Tags
        if tags:
            st.markdown(" ".join(f'<span class="tag-chip">{t}</span>' for t in tags),
                        unsafe_allow_html=True)

        # Notes
        if notes:
            st.caption(f"📝 {notes[:120]}{'…' if len(notes) > 120 else ''}")

    btn1, btn2, btn3, btn4 = st.columns([2, 2, 2, 6])
    with btn1:
        lbl = "✕ Close" if is_editing else "✏️ Edit"
        if st.button(lbl, key=f"edit_c_{cid}", use_container_width=True):
            st.session_state[f"editing_{cid}"] = not is_editing
            st.session_state.pop(confirm_key, None)
            st.session_state.pop(f"hist_{cid}", None)
            st.rerun()
    with btn2:
        hist_open = st.session_state.get(f"hist_{cid}", False)
        hist_lbl = "✕ History" if hist_open else "📧 History"
        if st.button(hist_lbl, key=f"hist_btn_{cid}", use_container_width=True):
            st.session_state[f"hist_{cid}"] = not hist_open
            st.session_state.pop(f"editing_{cid}", None)
            st.session_state.pop(confirm_key, None)
            st.rerun()
    with btn3:
        if not is_confirming:
            if st.button("🗑 Remove", key=f"del_c_{cid}", use_container_width=True):
                st.session_state[confirm_key] = True
                st.rerun()
        else:
            cc1, cc2 = st.columns(2)
            with cc1:
                if st.button("⚠️ Yes, delete", key=f"conf_del_{cid}", use_container_width=True, type="primary"):
                    client_store.delete(cid)
                    for _k in [k for k in st.session_state if cid in k]:
                        del st.session_state[_k]
                    st.toast(f"Removed {c.get('company','client')}", icon="🗑")
                    st.rerun()
            with cc2:
                if st.button("Cancel", key=f"cancel_del_{cid}", use_container_width=True):
                    st.session_state.pop(confirm_key, None)
                    st.rerun()

    # ── Email History panel ───────────────────────────────────────────────────
    if st.session_state.get(f"hist_{cid}"):
        history = client_emails_store.get_for_client(c.get("company", ""))
        st.markdown(
            '<div style="background:#f5f9ff;border:1px solid rgba(61,130,245,0.18);'
            'border-radius:12px;padding:16px 20px;margin-top:8px;">',
            unsafe_allow_html=True,
        )
        if not history:
            st.markdown(
                '<div style="text-align:center;padding:20px;color:#7a99bb;font-size:0.84rem;">'
                '📭 No emails sent to this client yet.</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div style="color:#2a5080;font-size:0.72rem;font-weight:700;'
                f'text-transform:uppercase;letter-spacing:0.06em;margin-bottom:12px;">'
                f'📧 Email History — {len(history)} email{"s" if len(history)!=1 else ""} (permanent)</div>',
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
                    f'<div style="background:#ffffff;border:1px solid rgba(61,130,245,0.15);'
                    f'border-radius:10px;padding:12px 14px;margin-bottom:8px;">'
                    f'<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;margin-bottom:6px;">'
                    f'<div style="font-size:0.84rem;font-weight:700;color:#0d1d3a;flex:1;">{h["subject"] or "(no subject)"}</div>'
                    f'<span style="font-size:0.65rem;color:#7a99bb;white-space:nowrap;flex-shrink:0;">{h["date"]}</span>'
                    f'</div>'
                    f'<div style="display:flex;flex-wrap:wrap;gap:5px;margin-bottom:6px;">{sent_pills}</div>'
                    + (f'<div style="color:#3a6699;font-size:0.69rem;margin-bottom:4px;">🎨 {h["template_name"]}</div>' if h.get("template_name") else '')
                    + (attach_html + '<br>' if attach_html else '')
                    + (f'<div style="color:#2a5080;font-size:0.71rem;line-height:1.5;margin-top:4px;'
                       f'padding:6px 10px;background:rgba(61,130,245,0.04);border-radius:6px;">'
                       f'{h["body_preview"][:150]}{"…" if len(h["body_preview"])>150 else ""}</div>'
                       if h.get("body_preview") else '') +
                    f'</div>',
                    unsafe_allow_html=True,
                )
        st.markdown('</div>', unsafe_allow_html=True)

    if is_editing:
        st.markdown(
            '<div style="background:rgba(61,130,245,0.04);border:1px solid rgba(61,130,245,0.15);'
            'border-radius:12px;padding:16px;margin-top:8px;">',
            unsafe_allow_html=True,
        )
        # ── Email management ──────────────────────────────────────────────────
        st.markdown('<div style="color:#3a6699;font-size:0.72rem;font-weight:700;'
                    'text-transform:uppercase;letter-spacing:0.06em;margin-bottom:8px;">Email Addresses</div>',
                    unsafe_allow_html=True)
        current_emails = list(c.get("emails", []))
        for idx, em in enumerate(current_emails):
            ec1, ec2 = st.columns([6, 1])
            with ec1:
                st.markdown(
                    f'<div style="background:#f0f8ff;border:1px solid rgba(61,130,245,0.2);border-radius:6px;'
                    f'padding:7px 12px;font-size:0.78rem;color:#1e3a5f;">✉ {em}</div>',
                    unsafe_allow_html=True,
                )
            with ec2:
                if st.button("✕", key=f"del_em_{cid}_{idx}", use_container_width=True, help="Remove"):
                    client_store.update(cid, {"emails": [e for j, e in enumerate(current_emails) if j != idx]})
                    st.toast(f"Removed {em}", icon="🗑")
                    st.rerun()
        ae1, ae2 = st.columns([6, 1])
        with ae1:
            new_em = st.text_input("new_email", key=f"add_em_{cid}",
                                   placeholder="Add email address…", label_visibility="collapsed")
        with ae2:
            if st.button("＋", key=f"add_em_btn_{cid}", use_container_width=True, help="Add"):
                if new_em.strip():
                    client_store.update(cid, {"emails": current_emails + [new_em.strip()]})
                    st.toast(f"Added {new_em.strip()}", icon="✅")
                    st.rerun()

        # ── Other fields ──────────────────────────────────────────────────────
        with st.form(f"edit_f_{cid}"):
            ef1, ef2 = st.columns(2)
            with ef1:
                new_company = st.text_input("Company Name", value=c.get("company", ""))
            with ef2:
                new_contact = st.text_input("Contact Person", value=c.get("contact", ""))
            new_tags  = st.text_input("Tags", value=", ".join(c.get("tags", [])),
                                      placeholder="Enterprise, Q1, High Priority")
            new_notes = st.text_area("Notes", value=c.get("notes", ""), height=68)
            fs1, fs2 = st.columns(2)
            with fs1:
                save_clicked = st.form_submit_button("Save Changes", type="primary", use_container_width=True)
            with fs2:
                cancel_clicked = st.form_submit_button("Cancel", use_container_width=True)
            if save_clicked:
                client_store.update(cid, {
                    "company": new_company.strip(),
                    "contact": new_contact.strip(),
                    "tags":    [t.strip() for t in new_tags.split(",") if t.strip()],
                    "notes":   new_notes.strip(),
                })
                for _k in [k for k in st.session_state if k.startswith("editing_") or k.startswith("confirm_del_")]:
                    del st.session_state[_k]
                st.toast("Client updated.", icon="✅")
                st.rerun()
            if cancel_clicked:
                for _k in [k for k in st.session_state if k.startswith("editing_") or k.startswith("confirm_del_")]:
                    del st.session_state[_k]
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)


def render_clients():
    all_clients = client_store.load()

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown("""<div class="page-header">
        <div class="page-header-icon">🏢</div>
        <div class="page-header-text">
            <div class="page-title">Client Repository</div>
            <div class="page-sub">All your stakeholders, contacts and email addresses in one place.</div>
        </div>
    </div>""", unsafe_allow_html=True)

    # ── Stats ─────────────────────────────────────────────────────────────────
    total_em   = sum(len(c.get("emails", [])) for c in all_clients)
    total_tags = len({t for c in all_clients for t in c.get("tags", [])})
    with_notes = sum(1 for c in all_clients if c.get("notes", "").strip())

    st.markdown(f"""<div class="stats-grid" style="grid-template-columns:repeat(4,1fr);">
        <div class="stat-card" style="border-top:2px solid #3d8ef5;">
            <div style="color:#2a5080;font-size:0.6rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">Total Clients</div>
            <div style="background:var(--gradient-brand);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;font-size:1.8rem;font-weight:800;letter-spacing:-0.03em;">{len(all_clients)}</div>
        </div>
        <div class="stat-card" style="border-top:2px solid #3d8ef5;">
            <div style="color:#2a5080;font-size:0.6rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">Email Addresses</div>
            <div style="color:#3d8ef5;font-size:1.8rem;font-weight:800;">{total_em}</div>
        </div>
        <div class="stat-card" style="border-top:2px solid #e0368e;">
            <div style="color:#2a5080;font-size:0.6rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">Unique Tags</div>
            <div style="color:#e0368e;font-size:1.8rem;font-weight:800;">{total_tags}</div>
        </div>
        <div class="stat-card" style="border-top:2px solid #0ebc6e;">
            <div style="color:#2a5080;font-size:0.6rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">With Notes</div>
            <div style="color:#0ebc6e;font-size:1.8rem;font-weight:800;">{with_notes}</div>
        </div>
    </div>""", unsafe_allow_html=True)

    # ── Add New Client ────────────────────────────────────────────────────────
    _show_add = st.session_state.get("show_add_client", False)
    _btn_label = "✕ Cancel" if _show_add else "➕ Add New Client"
    if st.button(_btn_label, key="toggle_add_client", type="primary" if not _show_add else "secondary"):
        st.session_state["show_add_client"] = not _show_add
        st.rerun()

    if st.session_state.get("show_add_client", False):
        st.markdown(
            '<div style="background:#ffffff;border:2px solid rgba(61,130,245,0.25);'
            'border-radius:16px;padding:24px;margin:12px 0 20px;">',
            unsafe_allow_html=True,
        )
        fc1, fc2 = st.columns(2)
        with fc1:
            company = st.text_input("Company Name *", placeholder="e.g. Acme Corp", key="add_company")
        with fc2:
            contact = st.text_input("Contact Person", placeholder="e.g. John Smith", key="add_contact")

        tags_raw = st.text_input("Tags (comma-separated)", placeholder="Enterprise, Q1, High Priority", key="add_tags")

        st.markdown("**Email Addresses**")
        ec1, ec2, ec3 = st.columns(3)
        with ec1:
            e1 = st.text_input("Primary Email *", placeholder="primary@company.com", key="add_e1")
        with ec2:
            e2 = st.text_input("Email 2", placeholder="cc@company.com", key="add_e2")
        with ec3:
            e3 = st.text_input("Email 3", placeholder="optional@company.com", key="add_e3")

        notes = st.text_area("Notes", placeholder="Client context, renewal dates, preferences…", height=72, key="add_notes")

        sa1, sa2 = st.columns([2, 5])
        with sa1:
            if st.button("Save Client", type="primary", use_container_width=True, key="add_client_save"):
                if not company.strip():
                    st.warning("Company name is required.")
                elif not any([e1.strip(), e2.strip(), e3.strip()]):
                    st.warning("At least one email address is required.")
                else:
                    emails = [e for e in [e1, e2, e3] if e.strip()]
                    tags   = [t.strip() for t in tags_raw.split(",") if t.strip()]
                    client_store.add(company.strip(), contact.strip(), emails, "Active", tags, notes.strip())
                    st.session_state["show_add_client"] = False
                    st.toast(f"✓ {company} added!", icon="🏢")
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")

    # ── Search ────────────────────────────────────────────────────────────────
    search = st.text_input("", placeholder="🔍  Search by company, contact, email or tag…",
                           label_visibility="collapsed", key="client_search")

    filtered = all_clients
    if search:
        q = search.lower()
        filtered = [c for c in filtered if
                    q in c.get("company","").lower() or
                    q in c.get("contact","").lower() or
                    any(q in e.lower() for e in c.get("emails",[])) or
                    any(q in t.lower() for t in c.get("tags",[]))]

    if not filtered:
        st.markdown('<div style="text-align:center;padding:60px 20px;color:#7a99bb;font-size:0.84rem;">No clients found. Add one above.</div>', unsafe_allow_html=True)
        return

    st.markdown(f'<div style="color:#2a5080;font-size:0.75rem;font-weight:600;margin-bottom:12px;">'
                f'{len(filtered)} client{"s" if len(filtered)!=1 else ""}</div>', unsafe_allow_html=True)

    # ── Client List ───────────────────────────────────────────────────────────
    for c in filtered:
        _render_client_card(c)

    # ── Export ────────────────────────────────────────────────────────────────
    if all_clients:
        st.markdown("---")
        rows = [{"Company": c.get("company",""), "Contact": c.get("contact",""),
                 "Email": e, "Tags": ", ".join(c.get("tags",[])),
                 "Notes": c.get("notes",""), "Added": c.get("added_at","")}
                for c in all_clients for e in c.get("emails",[])]
        csv = pd.DataFrame(rows).to_csv(index=False)
        exp_col, bak_col, res_col = st.columns([2, 1, 2])
        with exp_col:
            st.download_button("⬇️  Export CSV", data=csv,
                               file_name="convin_clients.csv", mime="text/csv")
        with bak_col:
            import json as _json
            _bak = _json.dumps(all_clients, indent=2, ensure_ascii=False)
            st.download_button("⬇️  Backup JSON", data=_bak,
                               file_name="clients_backup.json", mime="application/json")
        with res_col:
            _uploaded = st.file_uploader("📥 Restore from JSON backup", type=["json"],
                                         key="client_restore_upload",
                                         label_visibility="collapsed")
            if _uploaded:
                try:
                    _restored = _json.loads(_uploaded.read())
                    if isinstance(_restored, list):
                        client_store.save(_restored)
                        st.toast(f"Restored {len(_restored)} clients.", icon="✅")
                        st.rerun()
                    else:
                        st.error("Invalid backup file format.")
                except Exception as _e:
                    st.error(f"Restore failed: {_e}")


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
                html_content = build_email_html(draft, draft.get("template", 1))
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

        with st.expander("🖼  Images, Attachment & Survey (optional)", expanded=True):
            _screenshot_input(d, f"c{ci}")
            st.markdown("")
            _attachment_slot(d, f"c{ci}")
            st.markdown("")
            d["survey_question"] = st.text_input("Survey Question", value=d["survey_question"], key=f"cc_sq_{ci}")

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
                _dl_html = build_email_html(d, d.get("template", 1))
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
                components.html(build_email_html(d, d.get("template", 1)), height=2000, scrolling=True)
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
                    def _html_builder_test(addr):
                        return build_email_html(d, d.get("template", 1), send_id=_send_id, recipient_email=addr)
                    with st.spinner("Sending test…"):
                        _res = gmail_sender.send_report_email(
                            None, [_test_addr], _subj[:80],
                            build_email_html(d, d.get("template", 1)),
                            _test_addr,
                            attachment_name=_att_name,
                            attachment_data=_att_bytes,
                            attachment_mime=_att_mime,
                            html_builder=_html_builder_test,
                        )
                    if _res["sent"]:
                        st.success(f"Test sent to {_test_addr}")
                        sent_store.log_send(
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
                    def _html_builder_prod(addr):
                        return build_email_html(d, d.get("template", 1), send_id=_send_id, recipient_email=addr)
                    with st.spinner(f"Sending to {len(all_emails)} recipient(s)…"):
                        result = gmail_sender.send_report_email(
                            None, all_emails, _subject,
                            build_email_html(d, d.get("template", 1)),
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
                        sent_store.log_send(
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
                        if d.get("client", "").strip():
                            from datetime import datetime as _dt2, timezone as _tz2
                            client_emails_store.log(
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
        <div class="stat-card" style="border-top:2px solid #3d8ef5;">
            <div style="color:#2a5080;font-size:0.6rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">Total Sends</div>
            <div style="background:var(--gradient-brand);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;font-size:1.8rem;font-weight:800;letter-spacing:-0.03em;">{len(records)}</div>
        </div>
        <div class="stat-card" style="border-top:2px solid #0ebc6e;">
            <div style="color:#2a5080;font-size:0.6rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">Emails Delivered</div>
            <div style="color:#0ebc6e;font-size:1.8rem;font-weight:800;">{total_sent}</div>
        </div>
        <div class="stat-card" style="border-top:2px solid #3d8ef5;">
            <div style="color:#2a5080;font-size:0.6rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">Unique Recipients</div>
            <div style="color:#3d8ef5;font-size:1.8rem;font-weight:800;">{unique_emails}</div>
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

        top_color = "#e72b3b" if _has_f else "#3d8ef5"

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
            + _stat_pill("👁", "Opens",   _opens,    "#3d8ef5")
            + _stat_pill("👆", "Clicks",  _clicks,   "#3d8ef5")
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

    sla_breached   = [i for i in ACTION_QUEUE if i.get("sla_breached")]
    critical_rpts  = [c for c in CAMPAIGNS if "Critical" in c["status"]]
    needs_action   = [c for c in CAMPAIGNS if "Needs Action" in c["status"]]
    low_csat       = [r for r in CSAT_RESPONDENTS if r["rating"] <= 2]
    declining_kpis = [m for m in HEALTH_KPIS if not delta_is_positive(m)]

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


if not st.session_state["show_sidebar"]:
    st.markdown("""
    <style>
    section[data-testid="stSidebar"]       { display:none !important; }
    [data-testid="collapsedControl"]        { display:none !important; }
    [data-testid="stSidebarCollapseButton"] { display:none !important; }
    </style>""", unsafe_allow_html=True)

# ─── Top navigation bar ───────────────────────────────────────────────────────

# Full-width branded header — rendered as HTML above the button row
_current_page = st.session_state["current_page"]
st.markdown(f"""
<style>
@keyframes navGradient {{
    0%   {{ background-position: 0% 50%; }}
    50%  {{ background-position: 100% 50%; }}
    100% {{ background-position: 0% 50%; }}
}}
.cdl-navbar {{
    background: linear-gradient(108deg, #e0368e, #ff6b78 35%, #3d8ef5 65%, #e0368e);
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
    <!-- Logo + brand -->
    <div style="display:flex;align-items:center;gap:12px;">
        <div style="filter:drop-shadow(0 2px 8px rgba(0,0,0,0.4));flex-shrink:0;">{_logo_img(38, 10)}</div>
        <div>
            <div style="color:#fff;font-weight:800;font-size:0.96rem;letter-spacing:-0.01em;line-height:1.1;text-shadow:0 1px 8px rgba(0,0,0,0.3);">Convin Data Labs</div>
            <div style="color:rgba(255,255,255,0.55);font-size:0.58rem;font-weight:500;letter-spacing:0.1em;text-transform:uppercase;">Insights Dashboard</div>
        </div>
    </div>
    <!-- Nav links -->
    <div style="display:flex;align-items:center;gap:4px;">
        {"".join(
            f'<div style="padding:7px 16px;border-radius:8px;font-size:0.78rem;font-weight:{"700" if page == _current_page else "500"};color:#fff;background:{"rgba(0,0,0,0.28)" if page == _current_page else "transparent"};border:{"1px solid rgba(255,255,255,0.35)" if page == _current_page else "1px solid transparent"};box-shadow:{"0 2px 10px rgba(0,0,0,0.25)" if page == _current_page else "none"};letter-spacing:0.01em;">{icon} {page}</div>'
            for icon, page in [("📊","Overview"),("🏢","Clients"),("📧","Email Maker"),("📤","Sent")]
        )}
    </div>
    <!-- User pill -->
    <div style="
        background:rgba(0,0,0,0.22);border:1px solid rgba(255,255,255,0.25);
        border-radius:99px;padding:5px 14px 5px 8px;
        display:flex;align-items:center;gap:8px;
        box-shadow:0 2px 12px rgba(0,0,0,0.3);
    ">
        <div style="width:26px;height:26px;border-radius:50%;background:rgba(255,255,255,0.2);display:flex;align-items:center;justify-content:center;font-size:0.68rem;font-weight:800;color:#fff;border:1px solid rgba(255,255,255,0.3);">
            {(st.session_state.get("user_email","?")[0]).upper()}
        </div>
        <div style="color:rgba(255,255,255,0.9);font-size:0.72rem;font-weight:600;max-width:140px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
            {st.session_state.get("user_email","—")}
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* Hide default Streamlit header bar */
.stApp > header { display: none !important; }
/* Compact utility nav strip (⚙️ Settings + page buttons) */
div[data-testid="stHorizontalBlock"]:has(button[key="nav_settings"]) {
    background: #ffffff !important;
    border-bottom: 1px solid #e8edf8 !important;
    padding: 4px 0 6px !important;
    margin-bottom: 1.4rem !important;
    box-shadow: 0 1px 6px rgba(210,44,132,0.06) !important;
}
/* Active nav button */
div[data-testid="stHorizontalBlock"]:has(button[key="nav_settings"]) button[kind="primary"] {
    background: linear-gradient(108deg, #e0368e, #ff6b78 52%, #3d8ef5) !important;
    color: #ffffff !important;
    border: none !important;
    box-shadow: 0 2px 14px rgba(61,130,245,0.55) !important;
    font-weight: 700 !important;
    border-radius: 7px !important;
}
div[data-testid="stHorizontalBlock"]:has(button[key="nav_settings"]) button[kind="primary"]:hover {
    filter: brightness(1.1) !important;
    box-shadow: 0 4px 20px rgba(224,54,142,0.7) !important;
    transform: translateY(-1px) !important;
}
/* Inactive nav button */
div[data-testid="stHorizontalBlock"]:has(button[key="nav_settings"]) button[kind="secondary"] {
    background: transparent !important;
    border: 1px solid rgba(61,130,245,0.22) !important;
    color: #6699cc !important;
    border-radius: 7px !important;
}
div[data-testid="stHorizontalBlock"]:has(button[key="nav_settings"]) button[kind="secondary"]:hover {
    background: rgba(61,130,245,0.07) !important;
    border-color: rgba(61,130,245,0.4) !important;
    color: #e0368e !important;
    transform: none !important;
}
</style>
""", unsafe_allow_html=True)

_n0, _n1, _n2, _n3, _n4, _n_spacer = st.columns([1.2, 2, 2, 2, 2, 2])

with _n0:
    _sb_label = "✕ Close" if st.session_state["show_sidebar"] else "⚙️ Settings"
    if st.button(_sb_label, key="nav_settings", use_container_width=True):
        st.session_state["show_sidebar"] = not st.session_state["show_sidebar"]
        st.rerun()

_sent_count = len(sent_store.load())
_page_btns = {
    "Overview":    ("📊 Overview",    _n1),
    "Clients":     ("🏢 Clients",     _n2),
    "Email Maker": ("📧 Email Maker", _n3),
    "Sent":        (f"📤 Sent  {_sent_count}" if _sent_count else "📤 Sent", _n4),
}
for _key, (_label, _col) in _page_btns.items():
    with _col:
        _active = st.session_state["current_page"] == _key
        if st.button(
            _label,
            key=f"nav_{_key}",
            use_container_width=True,
            type="primary" if _active else "secondary",
        ):
            st.session_state["current_page"] = _key
            st.rerun()

st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

# ─── Route pages ──────────────────────────────────────────────────────────────

_page = st.session_state["current_page"]
if _page == "Overview":
    render_overview()
elif _page == "Clients":
    render_clients()
elif _page == "Email Maker":
    render_email_maker()
elif _page == "Sent":
    render_sent()
