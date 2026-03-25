"""
Persistent client repository.

Storage priority:
  1. st.session_state — fast intra-session access (no API calls)
  2. GitHub API       — cross-deploy persistence on Streamlit Cloud
  3. Local file       — fallback / local dev
  4. Sample data      — absolute last resort

To enable GitHub persistence, add to .streamlit/secrets.toml:
    GITHUB_TOKEN = "ghp_xxxxxxxxxxxx"   # PAT with repo write access
    GITHUB_REPO  = "animesh-sketch/feedback-dashboard"  # optional override
"""

import base64 as _b64
import json
import os
import uuid
from datetime import datetime, timezone

import streamlit as st

_FILE    = os.path.join(os.path.dirname(__file__), "clients.json")
_SS_KEY  = "client_store_data"
_DEFAULT_REPO = "animesh-sketch/feedback-dashboard"
_GH_PATH = "streamlit/clients.json"

STATUSES = ["Active", "At Risk", "Inactive"]

SAMPLE_CLIENTS = [
    {
        "id": "demo0001",
        "company": "Acme Corp",
        "contact": "Sarah Johnson",
        "emails": ["sarah@acmecorp.com", "reports@acmecorp.com"],
        "status": "Active",
        "tags": ["Enterprise", "Q1"],
        "notes": "Quarterly review scheduled for March.",
        "added_at": "Jan 10, 2026",
    },
    {
        "id": "demo0002",
        "company": "Stellar Dynamics",
        "contact": "Raj Patel",
        "emails": ["raj.patel@stellardyn.com"],
        "status": "Active",
        "tags": ["SaaS", "High Priority"],
        "notes": "Interested in expanding to 3 more teams.",
        "added_at": "Jan 22, 2026",
    },
    {
        "id": "demo0003",
        "company": "Nova Retail",
        "contact": "Emma Clarke",
        "emails": ["emma@novaretail.io", "analytics@novaretail.io"],
        "status": "At Risk",
        "tags": ["Retail", "Renewal Due"],
        "notes": "Renewal due in April — needs check-in call.",
        "added_at": "Feb 01, 2026",
    },
]


# ── GitHub API helpers ────────────────────────────────────────────────────────

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
    """Read clients.json from GitHub repo. Returns list or None."""
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


def _gh_save(clients: list) -> bool:
    """Write clients.json back to GitHub repo. Returns True on success."""
    try:
        import requests as _req
        hdrs = _gh_headers()
        if not hdrs:
            return False
        repo = st.secrets.get("GITHUB_REPO", _DEFAULT_REPO)
        url  = f"https://api.github.com/repos/{repo}/contents/{_GH_PATH}"
        # Get current SHA (required to update an existing file)
        sha = None
        r = _req.get(url, headers=hdrs, timeout=5)
        if r.status_code == 200:
            sha = r.json().get("sha")
        content = _b64.b64encode(
            json.dumps(clients, indent=2, ensure_ascii=False).encode()
        ).decode()
        payload = {
            "message": "chore: update client repository",
            "content": content,
        }
        if sha:
            payload["sha"] = sha
        resp = _req.put(url, headers=hdrs, json=payload, timeout=10)
        return resp.status_code in (200, 201)
    except Exception:
        return False


# ── Public API ────────────────────────────────────────────────────────────────

def _init() -> None:
    """Load clients into session_state on first call this session."""
    if _SS_KEY in st.session_state:
        return

    # 1. Try GitHub API (persistent across all deploys)
    data = _gh_load()
    if data is not None:
        st.session_state[_SS_KEY] = data
        return

    # 2. Try local file (works locally + first-boot on Cloud)
    if os.path.exists(_FILE):
        try:
            with open(_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data:
                st.session_state[_SS_KEY] = data
                return
        except (json.JSONDecodeError, OSError):
            pass

    # 3. Absolute fallback
    st.session_state[_SS_KEY] = list(SAMPLE_CLIENTS)


def load() -> list:
    _init()
    return st.session_state[_SS_KEY]


def save(clients: list) -> None:
    """Persist clients to session_state, GitHub, and local file."""
    st.session_state[_SS_KEY] = clients
    # Write to GitHub (survives container restarts and redeploys)
    _gh_save(clients)
    # Best-effort local file write (local dev / first-boot baseline)
    try:
        with open(_FILE, "w", encoding="utf-8") as f:
            json.dump(clients, f, indent=2, ensure_ascii=False)
    except OSError:
        pass


def add(company: str, contact: str, emails: list,
        status: str = "Active", tags: list = None, notes: str = "") -> dict:
    client = {
        "id":       str(uuid.uuid4())[:8],
        "company":  company,
        "contact":  contact,
        "emails":   emails,
        "status":   status,
        "tags":     tags or [],
        "notes":    notes,
        "added_at": datetime.now(timezone.utc).strftime("%b %d, %Y"),
    }
    clients = load()
    clients.append(client)
    save(clients)
    return client


def update(client_id: str, updates: dict) -> None:
    clients = load()
    for c in clients:
        if c["id"] == client_id:
            c.update(updates)
            break
    save(clients)


def delete(client_id: str) -> None:
    save([c for c in load() if c["id"] != client_id])
