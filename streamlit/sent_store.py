"""
Persistent sent-email log.

Storage priority:
  1. st.session_state — fast intra-session access
  2. GitHub API       — cross-deploy persistence on Streamlit Cloud
  3. Local file       — fallback / local dev

To enable GitHub persistence add to .streamlit/secrets.toml:
    GITHUB_TOKEN = "ghp_xxxxxxxxxxxx"
    GITHUB_REPO  = "animesh-sketch/feedback-dashboard"  # optional
"""

import base64 as _b64
import json
import os
import uuid
from datetime import datetime, timezone

import streamlit as st

_FILE         = os.path.join(os.path.dirname(__file__), "sent_emails.json")
_SS_KEY       = "sent_store_data"
_DEFAULT_REPO = "animesh-sketch/feedback-dashboard"
_GH_PATH      = "streamlit/sent_emails.json"


# ── GitHub helpers ─────────────────────────────────────────────────────────────

def _gh_headers():
    token = st.secrets.get("GITHUB_TOKEN", "")
    if not token:
        return None
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _gh_load():
    try:
        import requests as _req
        hdrs = _gh_headers()
        if not hdrs:
            return None
        repo = st.secrets.get("GITHUB_REPO", _DEFAULT_REPO)
        url  = f"https://api.github.com/repos/{repo}/contents/{_GH_PATH}"
        r = _req.get(url, headers=hdrs, timeout=8)
        if r.status_code == 200:
            raw = _b64.b64decode(r.json()["content"]).decode("utf-8")
            return json.loads(raw)
    except Exception:
        pass
    return None


def _gh_save(records: list) -> bool:
    try:
        import requests as _req
        hdrs = _gh_headers()
        if not hdrs:
            return False
        repo = st.secrets.get("GITHUB_REPO", _DEFAULT_REPO)
        url  = f"https://api.github.com/repos/{repo}/contents/{_GH_PATH}"
        sha  = None
        r    = _req.get(url, headers=hdrs, timeout=5)
        if r.status_code == 200:
            sha = r.json().get("sha")
        content = _b64.b64encode(
            json.dumps(records, indent=2, ensure_ascii=False).encode()
        ).decode()
        payload = {"message": "chore: update sent email log", "content": content}
        if sha:
            payload["sha"] = sha
        resp = _req.put(url, headers=hdrs, json=payload, timeout=10)
        return resp.status_code in (200, 201)
    except Exception:
        return False


# ── Public API ─────────────────────────────────────────────────────────────────

def _init() -> None:
    if _SS_KEY in st.session_state:
        return
    data = _gh_load()
    if data is not None:
        st.session_state[_SS_KEY] = data
        return
    if os.path.exists(_FILE):
        try:
            with open(_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                st.session_state[_SS_KEY] = data
                return
        except (json.JSONDecodeError, OSError):
            pass
    st.session_state[_SS_KEY] = []


def load() -> list:
    _init()
    return st.session_state[_SS_KEY]


def _persist(records: list) -> None:
    st.session_state[_SS_KEY] = records
    _gh_save(records)
    try:
        with open(_FILE, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
    except OSError:
        pass


def log_send(
    draft_name: str,
    subject: str,
    template_num: int,
    template_name: str,
    client: str,
    sent_to: list,
    failed: list,
    body_preview: str = "",
) -> dict:
    """Prepend a new send record and persist."""
    now = datetime.now(timezone.utc)
    record = {
        "id":            str(uuid.uuid4())[:8],
        "timestamp":     now.isoformat(),
        "date":          now.strftime("%b %d, %Y"),
        "time":          now.strftime("%H:%M"),
        "draft_name":    draft_name,
        "subject":       subject,
        "template_num":  template_num,
        "template_name": template_name,
        "client":        client,
        "sent_to":       sent_to,
        "failed":        failed,
        "body_preview":  body_preview[:120],
    }
    records = load()
    records.insert(0, record)          # newest first
    records = records[:500]            # cap at 500 entries
    _persist(records)
    return record


def clear() -> None:
    _persist([])
