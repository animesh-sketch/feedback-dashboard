"""
Pending QA audit queue — Supabase PostgreSQL storage.
Records stored as JSONB. Status: 'Ready for Audit' | 'Completed'.

Requires st.secrets: SUPABASE_URL, SUPABASE_KEY.
"""

import sys
import streamlit as st

_TABLE = "pending_audits"


@st.cache_resource
def _sb():
    from supabase import create_client
    url = st.secrets.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set in st.secrets")
    return create_client(url, key)


def _log_err(fn: str, exc: Exception) -> None:
    print(f"[pending_store.{fn}] ERROR: {exc}", file=sys.stderr)


def load_all() -> list:
    """Return all 'Ready for Audit' pending records, oldest first."""
    try:
        res = (
            _sb().table(_TABLE)
            .select("id,assigned_qa,record,status")
            .eq("status", "Ready for Audit")
            .order("id")
            .execute()
        )
        rows = []
        for row in (res.data or []):
            rec = dict(row["record"])
            rec["_pending_id"]   = row["id"]
            rec["_assigned_qa"]  = row["assigned_qa"]
            rows.append(rec)
        return rows
    except Exception as e:
        _log_err("load_all", e)
        return []


def load_for_qa(assigned_qa: str) -> list:
    """Return 'Ready for Audit' pending records for a specific QA, oldest first."""
    try:
        res = (
            _sb().table(_TABLE)
            .select("id,assigned_qa,record,status")
            .eq("status", "Ready for Audit")
            .eq("assigned_qa", assigned_qa)
            .order("id")
            .execute()
        )
        rows = []
        for row in (res.data or []):
            rec = dict(row["record"])
            rec["_pending_id"]   = row["id"]
            rec["_assigned_qa"]  = row["assigned_qa"]
            rows.append(rec)
        return rows
    except Exception as e:
        _log_err("load_for_qa", e)
        return []


def add_batch(records: list, assigned_qa: str) -> tuple:
    """Insert multiple pending audit records. Returns (success_count, error_list)."""
    success = 0
    errors  = []
    for i, rec in enumerate(records):
        try:
            _sb().table(_TABLE).insert({
                "assigned_qa": assigned_qa,
                "status":      "Ready for Audit",
                "record":      rec,
            }).execute()
            success += 1
        except Exception as e:
            _log_err("add_batch", e)
            errors.append({"row": i + 1, "reason": str(e)})
    return success, errors


def mark_done(row_id: int) -> str | None:
    """Mark a pending audit as Completed. Returns error string or None."""
    try:
        _sb().table(_TABLE).update({"status": "Completed"}).eq("id", row_id).execute()
        return None
    except Exception as e:
        _log_err("mark_done", e)
        return str(e)


def remove(row_id: int) -> str | None:
    """Delete a pending audit by its Supabase row id. Returns error string or None."""
    try:
        _sb().table(_TABLE).delete().eq("id", row_id).execute()
        return None
    except Exception as e:
        _log_err("remove", e)
        return str(e)
