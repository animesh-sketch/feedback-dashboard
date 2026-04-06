"""
Client repository — GitHub CSV storage with shared cache.

All users share a single @st.cache_data cache (TTL 15 s).
When any user writes, the shared cache is cleared so every other
user sees the update on their next interaction.

Requires st.secrets: GITHUB_TOKEN, GITHUB_REPO.
"""

import base64 as _b64
import csv
import io
import uuid
from datetime import datetime, timezone

import streamlit as st

_DEFAULT_REPO = "animesh-sketch/feedback-dashboard"
_GH_PATH      = "data/clients.csv"

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


# ── CSV ↔ dict conversion ─────────────────────────────────────────────────────

def _row_to_client(row: dict) -> dict:
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

def _clients_to_csv(clients: list) -> str:
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
            return [_row_to_client(row) for row in csv.DictReader(io.StringIO(raw))]
        if r.status_code == 404:
            return []
    except Exception:
        pass
    return None


def _gh_save(clients: list) -> bool:
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
            "content": _b64.b64encode(_clients_to_csv(clients).encode()).decode(),
        }
        if sha:
            payload["sha"] = sha
        return _req.put(url, headers=hdrs, json=payload, timeout=15).status_code in (200, 201)
    except Exception:
        return False


# ── Shared cache (all users, all sessions) ────────────────────────────────────

@st.cache_data(ttl=15, show_spinner=False)
def _cached_load() -> list:
    """Fetches from GitHub. Shared across all users — TTL 15 s."""
    data = _gh_load()
    return data if data is not None else []


# ── Public API ────────────────────────────────────────────────────────────────

def load() -> list:
    """Return current client list (shared cache, max 15 s stale)."""
    return list(_cached_load())          # copy so callers can't mutate the cache


def save(clients: list) -> None:
    """Write to GitHub and immediately invalidate shared cache for all users."""
    _gh_save(clients)
    _cached_load.clear()                 # all users get fresh data on next call


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
