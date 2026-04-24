"""
QA Audit log — Supabase PostgreSQL storage (permanent, never purged).
Each record is stored as JSONB so schema changes don't require migrations.

Requires st.secrets: SUPABASE_URL, SUPABASE_KEY.
"""

import sys
import streamlit as st

_TABLE = "audit_log"


@st.cache_resource
def _sb():
    from supabase import create_client
    url = st.secrets.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set in st.secrets")
    return create_client(url, key)


def _log_err(fn: str, exc: Exception) -> None:
    print(f"[audit_store.{fn}] ERROR: {exc}", file=sys.stderr)


def load() -> list:
    """Return all audit records newest-first (record dicts only)."""
    try:
        res = (
            _sb().table(_TABLE)
            .select("id,record")
            .order("id", desc=True)
            .execute()
        )
        rows = []
        for row in (res.data or []):
            rec = dict(row["record"])
            rec["_row_id"] = row["id"]
            rows.append(rec)
        return rows
    except Exception as e:
        _log_err("load", e)
        return []


def append(record: dict) -> str | None:
    """Insert a single audit record. Returns error string or None."""
    try:
        _sb().table(_TABLE).insert({"record": record}).execute()
        return None
    except Exception as e:
        _log_err("append", e)
        return str(e)


def delete(row_id: int) -> str | None:
    """Delete an audit record by its Supabase row id. Returns error string or None."""
    try:
        _sb().table(_TABLE).delete().eq("id", row_id).execute()
        return None
    except Exception as e:
        _log_err("delete", e)
        return str(e)


def update(row_id: int, record: dict) -> str | None:
    """Overwrite the record JSONB for a given row id. Returns error string or None."""
    try:
        clean = {k: v for k, v in record.items() if k != "_row_id"}
        _sb().table(_TABLE).update({"record": clean}).eq("id", row_id).execute()
        return None
    except Exception as e:
        _log_err("update", e)
        return str(e)
