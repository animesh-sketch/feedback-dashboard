"""
Client repository — Supabase PostgreSQL storage.

Requires st.secrets: SUPABASE_URL, SUPABASE_KEY.
All users share the same database — changes are immediately visible to everyone.
"""

import uuid
from datetime import datetime, timezone

import streamlit as st

_TABLE = "clients"
STATUSES = ["Active", "At Risk", "Inactive"]


# ── Supabase client ────────────────────────────────────────────────────────────

@st.cache_resource
def _sb():
    from supabase import create_client
    url = st.secrets.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_KEY", "")
    return create_client(url, key)


# ── Row ↔ dict conversion ─────────────────────────────────────────────────────

def _row_to_client(row: dict) -> dict:
    return {
        "id":       row.get("id", ""),
        "company":  row.get("company", ""),
        "contact":  row.get("contact", ""),
        "emails":   [e for e in (row.get("emails", "") or "").split("|") if e.strip()],
        "status":   row.get("status", "Active"),
        "tags":     [t for t in (row.get("tags", "") or "").split("|") if t.strip()],
        "notes":    row.get("notes", ""),
        "added_at": row.get("added_at", ""),
    }

def _client_to_row(c: dict) -> dict:
    return {
        "id":       c.get("id", ""),
        "company":  c.get("company", ""),
        "contact":  c.get("contact", ""),
        "emails":   "|".join(c.get("emails", [])),
        "status":   c.get("status", "Active"),
        "tags":     "|".join(c.get("tags", [])),
        "notes":    c.get("notes", "").replace("\n", " "),
        "added_at": c.get("added_at", ""),
    }


# ── Public API ────────────────────────────────────────────────────────────────

def load() -> list:
    """Return all clients ordered by most recently added."""
    try:
        res = _sb().table(_TABLE).select("*").order("added_at", desc=True).execute()
        return [_row_to_client(r) for r in (res.data or [])]
    except Exception:
        return []


def save(clients: list) -> None:
    """Full replace — delete all rows then re-insert. Use for bulk operations."""
    try:
        sb = _sb()
        sb.table(_TABLE).delete().neq("id", "").execute()
        if clients:
            sb.table(_TABLE).insert([_client_to_row(c) for c in clients]).execute()
    except Exception:
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
    try:
        _sb().table(_TABLE).insert(_client_to_row(client)).execute()
    except Exception:
        pass
    return client


def update(client_id: str, updates: dict) -> None:
    try:
        res = _sb().table(_TABLE).select("*").eq("id", client_id).execute()
        if not res.data:
            return
        current = _row_to_client(res.data[0])
        current.update(updates)
        _sb().table(_TABLE).update(_client_to_row(current)).eq("id", client_id).execute()
    except Exception:
        pass


def delete(client_id: str) -> None:
    try:
        _sb().table(_TABLE).delete().eq("id", client_id).execute()
    except Exception:
        pass
