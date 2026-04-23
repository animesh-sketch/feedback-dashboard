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
    """Return all audit records newest-first."""
    try:
        res = (
            _sb().table(_TABLE)
            .select("record")
            .order("id", desc=True)
            .execute()
        )
        return [row["record"] for row in (res.data or [])]
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
