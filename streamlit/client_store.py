"""
Client repository — Supabase PostgreSQL storage.

Requires st.secrets: SUPABASE_URL, SUPABASE_KEY.
All users share the same database — changes are immediately visible to everyone.
"""

import sys
import uuid
from datetime import datetime, timezone

import streamlit as st

_TABLE = "clients"
STATUSES = ["Active", "At Risk", "Inactive"]


# ── Supabase client (cached — one connection per app process) ─────────────────

@st.cache_resource
def _sb():
    from supabase import create_client
    url = st.secrets.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set in st.secrets")
    return create_client(url, key)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _log_err(fn: str, exc: Exception) -> None:
    print(f"[client_store.{fn}] ERROR: {exc}", file=sys.stderr)


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
    except Exception as e:
        _log_err("load", e)
        return []


def save(clients: list) -> str | None:
    """
    Full replace — upsert all rows then delete ones not in the new list.
    Safer than delete-all-then-insert (avoids data loss on network failure).
    Returns an error string on failure, None on success.
    """
    try:
        sb = _sb()
        rows = [_client_to_row(c) for c in clients]
        if rows:
            sb.table(_TABLE).upsert(rows).execute()
        # Delete rows whose IDs are no longer in the list
        keep_ids = [c.get("id", "") for c in clients if c.get("id")]
        if keep_ids:
            sb.table(_TABLE).delete().not_.in_("id", keep_ids).execute()
        else:
            # No clients at all — wipe the table
            sb.table(_TABLE).delete().neq("id", "").execute()
        return None
    except Exception as e:
        _log_err("save", e)
        return str(e)


def add(company: str, contact: str, emails: list,
        status: str = "Active", tags: list = None, notes: str = "") -> tuple:
    """Returns (client_dict, error_string_or_None)."""
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
        return client, None
    except Exception as e:
        _log_err("add", e)
        return client, str(e)


def update(client_id: str, updates: dict) -> str | None:
    """Returns error string on failure, None on success."""
    try:
        res = _sb().table(_TABLE).select("*").eq("id", client_id).execute()
        if not res.data:
            return f"Client {client_id} not found"
        current = _row_to_client(res.data[0])
        current.update(updates)
        _sb().table(_TABLE).update(_client_to_row(current)).eq("id", client_id).execute()
        return None
    except Exception as e:
        _log_err("update", e)
        return str(e)


def delete(client_id: str) -> str | None:
    """Returns error string on failure, None on success."""
    try:
        _sb().table(_TABLE).delete().eq("id", client_id).execute()
        return None
    except Exception as e:
        _log_err("delete", e)
        return str(e)
