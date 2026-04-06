"""
Client repository — GitHub CSV storage.

Reads and writes data/clients.csv in the GitHub repo via the GitHub Contents API.
Requires st.secrets: GITHUB_TOKEN, GITHUB_REPO.
Falls back to empty list when token is missing or the file doesn't exist yet.
"""

import base64 as _b64
import csv
import io
import uuid
from datetime import datetime, timezone

import streamlit as st

_DEFAULT_REPO = "animesh-sketch/feedback-dashboard"
_GH_PATH      = "data/clients.csv"
_SS_KEY       = "client_store_data"

STATUSES = ["Active", "At Risk", "Inactive"]

_FIELDS = ["id", "company", "contact", "emails", "status", "tags", "notes", "added_at"]


# ── GitHub helpers ────────────────────────────────────────────────────────────

def _headers():
    token = st.secrets.get("GITHUB_TOKEN", "")
    if not token:
        return None
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

def _repo():
    return st.secrets.get("GITHUB_REPO", _DEFAULT_REPO)


# ── CSV conversion ────────────────────────────────────────────────────────────

def _to_dict(row: dict) -> dict:
    """CSV row → client dict."""
    return {
        "id":       row.get("id", ""),
        "company":  row.get("company", ""),
        "contact":  row.get("contact", ""),
        "emails":   [e for e in row.get("emails", "").split("|") if e.strip()],
        "status":   row.get("status", "Active"),
        "tags":     [t for t in row.get("tags", "").split("|") if t.strip()],
        "notes":    row.get("notes", ""),
        "added_at": row.get("added_at", ""),
    }

def _to_csv(clients: list) -> str:
    """Client dicts → CSV string."""
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=_FIELDS, lineterminator="\n")
    w.writeheader()
    for c in clients:
        w.writerow({
            "id":       c.get("id", ""),
            "company":  c.get("company", ""),
            "contact":  c.get("contact", ""),
            "emails":   "|".join(c.get("emails", [])),
            "status":   c.get("status", "Active"),
            "tags":     "|".join(c.get("tags", [])),
            "notes":    c.get("notes", "").replace("\n", " "),
            "added_at": c.get("added_at", ""),
        })
    return buf.getvalue()


# ── GitHub read / write ───────────────────────────────────────────────────────

def _gh_load() -> list | None:
    """Fetch data/clients.csv from GitHub. Returns list or None on error."""
    try:
        import requests as _req
        hdrs = _headers()
        if not hdrs:
            return None
        r = _req.get(
            f"https://api.github.com/repos/{_repo()}/contents/{_GH_PATH}",
            headers=hdrs, timeout=8,
        )
        if r.status_code == 200:
            raw = _b64.b64decode(r.json()["content"]).decode("utf-8")
            reader = csv.DictReader(io.StringIO(raw))
            return [_to_dict(row) for row in reader]
        if r.status_code == 404:
            return []          # file doesn't exist yet — start empty
    except Exception:
        pass
    return None


def _gh_save(clients: list) -> bool:
    """Write data/clients.csv back to GitHub. Returns True on success."""
    try:
        import requests as _req
        hdrs = _headers()
        if not hdrs:
            return False
        url = f"https://api.github.com/repos/{_repo()}/contents/{_GH_PATH}"
        sha = None
        r = _req.get(url, headers=hdrs, timeout=5)
        if r.status_code == 200:
            sha = r.json().get("sha")
        payload = {
            "message": "chore: update clients",
            "content": _b64.b64encode(_to_csv(clients).encode()).decode(),
        }
        if sha:
            payload["sha"] = sha
        resp = _req.put(url, headers=hdrs, json=payload, timeout=15)
        return resp.status_code in (200, 201)
    except Exception:
        return False


# ── Cached loader (shared across reruns, TTL 30 s) ────────────────────────────

@st.cache_data(ttl=30, show_spinner=False)
def _cached_load() -> list | None:
    return _gh_load()


# ── Public API ────────────────────────────────────────────────────────────────

def _init() -> None:
    if _SS_KEY in st.session_state:
        return
    data = _cached_load()
    st.session_state[_SS_KEY] = data if data is not None else []


def load() -> list:
    _init()
    return st.session_state[_SS_KEY]


def save(clients: list) -> None:
    st.session_state[_SS_KEY] = clients
    _gh_save(clients)
    _cached_load.clear()


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
