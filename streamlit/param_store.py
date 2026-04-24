"""
Custom audit parameters — Supabase PostgreSQL storage (permanent).
Requires st.secrets: SUPABASE_URL, SUPABASE_KEY.
"""

import sys
import streamlit as st

_TABLE = "custom_params"

_VALID_TYPES = ("dropdown", "scoring", "number", "text")


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
                "name":       row["name"],
                "options":    row.get("options", "Yes|No").split("|"),
                "guide":      row.get("guide", ""),
                "input_type": row.get("input_type", "dropdown"),
            }
            for row in (res.data or [])
        ]
    except Exception as e:
        _log_err("load", e)
        return []


def add(name: str, options: list, guide: str, input_type: str = "dropdown") -> str | None:
    """Insert a custom param. Returns error string or None."""
    if input_type not in _VALID_TYPES:
        input_type = "dropdown"
    try:
        _sb().table(_TABLE).insert({
            "id":         name.strip().lower().replace(" ", "_"),
            "name":       name.strip(),
            "options":    "|".join(options),
            "guide":      guide.strip(),
            "input_type": input_type,
        }).execute()
        return None
    except Exception as e:
        _log_err("add", e)
        return str(e)


def update(name: str, options: list, guide: str, input_type: str = "dropdown") -> str | None:
    """Update an existing param by name. Returns error string or None."""
    if input_type not in _VALID_TYPES:
        input_type = "dropdown"
    try:
        _id = name.strip().lower().replace(" ", "_")
        _sb().table(_TABLE).update({
            "options":    "|".join(options),
            "guide":      guide.strip(),
            "input_type": input_type,
        }).eq("id", _id).execute()
        return None
    except Exception as e:
        _log_err("update", e)
        return str(e)


def remove(name: str) -> str | None:
    """Delete a custom param by name. Returns error string or None."""
    try:
        _sb().table(_TABLE).delete().eq("id", name.strip().lower().replace(" ", "_")).execute()
        return None
    except Exception as e:
        _log_err("remove", e)
        return str(e)
