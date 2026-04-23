"""
Custom audit parameters — Supabase PostgreSQL storage (permanent).
Requires st.secrets: SUPABASE_URL, SUPABASE_KEY.
"""

import sys
import streamlit as st

_TABLE = "custom_params"


@st.cache_resource
def _sb():
    from supabase import create_client
    url = st.secrets.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set in st.secrets")
    return create_client(url, key)


def _log_err(fn: str, exc: Exception) -> None:
    print(f"[param_store.{fn}] ERROR: {exc}", file=sys.stderr)


def load() -> list:
    """Return all custom params ordered by creation (oldest first)."""
    try:
        res = _sb().table(_TABLE).select("*").order("id").execute()
        return [
            {
                "name":    row["name"],
                "options": row.get("options", "Yes|No").split("|"),
                "guide":   row.get("guide", ""),
            }
            for row in (res.data or [])
        ]
    except Exception as e:
        _log_err("load", e)
        return []


def add(name: str, options: list, guide: str) -> str | None:
    """Insert a custom param. Returns error string or None."""
    try:
        _sb().table(_TABLE).insert({
            "id":      name.strip().lower().replace(" ", "_"),
            "name":    name.strip(),
            "options": "|".join(options),
            "guide":   guide.strip(),
        }).execute()
        return None
    except Exception as e:
        _log_err("add", e)
        return str(e)


def remove(name: str) -> str | None:
    """Delete a custom param by name. Returns error string or None."""
    try:
        _sb().table(_TABLE).delete().eq("id", name.strip().lower().replace(" ", "_")).execute()
        return None
    except Exception as e:
        _log_err("remove", e)
        return str(e)
