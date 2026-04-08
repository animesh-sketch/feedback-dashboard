"""
Sent email log — Supabase PostgreSQL storage.

Requires st.secrets: SUPABASE_URL, SUPABASE_KEY.
All users share the same database — writes are immediately visible to everyone.
"""

import sys
import uuid
from datetime import datetime, timezone

import streamlit as st

_TABLE = "sent_items"


# ── Supabase client (cached — one connection per app process) ─────────────────

@st.cache_resource
def _sb():
    from supabase import create_client
    url = st.secrets.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set in st.secrets")
    return create_client(url, key)


def _log_err(fn: str, exc: Exception) -> None:
    print(f"[sent_store.{fn}] ERROR: {exc}", file=sys.stderr)


# ── Row ↔ dict conversion ─────────────────────────────────────────────────────

def _row_to_record(row: dict) -> dict:
    failed = row.get("failed") or []
    if not isinstance(failed, list):
        failed = []
    return {
        "id":              row.get("id", ""),
        "timestamp":       row.get("timestamp", ""),
        "date":            row.get("date", ""),
        "time":            row.get("time", ""),
        "sender":          row.get("sender", ""),
        "draft_name":      row.get("draft_name", ""),
        "subject":         row.get("subject", ""),
        "template_num":    int(row.get("template_num", 1) or 1),
        "template_name":   row.get("template_name", ""),
        "client":          row.get("client", ""),
        "attachment_name": row.get("attachment_name", ""),
        "is_test":         bool(row.get("is_test", False)),
        "sent_to":         [e for e in (row.get("sent_to", "") or "").split("|") if e.strip()],
        "failed":          failed,
        "body_preview":    row.get("body_preview", ""),
    }

def _record_to_row(r: dict) -> dict:
    return {
        "id":              r.get("id", ""),
        "timestamp":       r.get("timestamp", ""),
        "date":            r.get("date", ""),
        "time":            r.get("time", ""),
        "sender":          r.get("sender", ""),
        "draft_name":      r.get("draft_name", ""),
        "subject":         r.get("subject", "").replace("\n", " "),
        "template_num":    r.get("template_num", 1),
        "template_name":   r.get("template_name", ""),
        "client":          r.get("client", ""),
        "attachment_name": r.get("attachment_name", ""),
        "is_test":         bool(r.get("is_test", False)),
        "sent_to":         "|".join(r.get("sent_to", [])),
        "failed":          r.get("failed", []),   # JSONB — pass as Python list
        "body_preview":    r.get("body_preview", "")[:300].replace("\n", " "),
    }


# ── Public API ────────────────────────────────────────────────────────────────

def _purge_old() -> None:
    """Delete sent_items older than 30 days to keep storage lean."""
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    try:
        _sb().table(_TABLE).delete().lt("timestamp", cutoff).execute()
    except Exception as e:
        _log_err("_purge_old", e)


def load() -> list:
    """Return sent records newest-first (max 500). Auto-purges >30 days."""
    _purge_old()
    try:
        res = (
            _sb().table(_TABLE)
            .select("*")
            .order("timestamp", desc=True)
            .limit(500)
            .execute()
        )
        return [_row_to_record(r) for r in (res.data or [])]
    except Exception as e:
        _log_err("load", e)
        return []


def log_send(
    draft_name: str,
    subject: str,
    template_num: int,
    template_name: str,
    client: str,
    sent_to: list,
    failed: list,
    body_preview: str = "",
    record_id: str = None,
    sender: str = "",
    attachment_name: str = "",
    is_test: bool = False,
) -> tuple:
    """
    Returns (record_dict, error_string_or_None).
    Caller should check the error and surface it to the user.
    """
    now = datetime.now(timezone.utc)
    normalised_failed = [
        {"email": f.get("email", ""), "error": f.get("error", "")}
        if isinstance(f, dict) else {"email": str(f), "error": ""}
        for f in failed
    ]
    record = {
        "id":              record_id or str(uuid.uuid4())[:8],
        "timestamp":       now.isoformat(),
        "date":            now.strftime("%b %d, %Y"),
        "time":            now.strftime("%H:%M UTC"),
        "draft_name":      draft_name,
        "subject":         subject,
        "template_num":    template_num,
        "template_name":   template_name,
        "client":          client,
        "sender":          sender,
        "sent_to":         sent_to,
        "failed":          normalised_failed,
        "body_preview":    body_preview[:300],
        "attachment_name": attachment_name or "",
        "is_test":         is_test,
    }
    try:
        _sb().table(_TABLE).insert(_record_to_row(record)).execute()
        return record, None
    except Exception as e:
        _log_err("log_send", e)
        return record, str(e)


def clear() -> str | None:
    """Returns error string on failure, None on success."""
    try:
        _sb().table(_TABLE).delete().neq("id", "").execute()
        return None
    except Exception as e:
        _log_err("clear", e)
        return str(e)
