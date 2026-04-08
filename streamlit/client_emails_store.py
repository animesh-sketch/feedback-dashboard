"""
Client email history — permanent storage, never purged.
Requires st.secrets: SUPABASE_URL, SUPABASE_KEY.
"""
import sys
import streamlit as st

_TABLE = "client_emails"


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
    print(f"[client_emails_store.{fn}] ERROR: {exc}", file=sys.stderr)


# ── Public API ────────────────────────────────────────────────────────────────

def log(
    record_id: str,
    client_company: str,
    date: str,
    subject: str,
    template_name: str,
    sent_to: list,
    body_preview: str,
    sender: str,
    attachment_name: str,
) -> str | None:
    """
    Permanently store an email send under the client's history.
    Returns error string on failure, None on success.
    """
    try:
        _sb().table(_TABLE).insert({
            "id":              record_id,
            "client_company":  client_company,
            "date":            date,
            "subject":         subject,
            "template_name":   template_name,
            "sent_to":         "|".join(sent_to),
            "body_preview":    body_preview[:300],
            "sender":          sender,
            "attachment_name": attachment_name or "",
        }).execute()
        return None
    except Exception as e:
        _log_err("log", e)
        return str(e)


def get_for_client(client_company: str) -> list:
    """Return all emails ever sent to this client, newest first."""
    try:
        res = (
            _sb().table(_TABLE)
            .select("*")
            .eq("client_company", client_company)
            .order("id", desc=True)
            .execute()
        )
        return [
            {
                "id":              r.get("id", ""),
                "date":            r.get("date", ""),
                "subject":         r.get("subject", ""),
                "template_name":   r.get("template_name", ""),
                "sent_to":         [e for e in (r.get("sent_to", "") or "").split("|") if e],
                "body_preview":    r.get("body_preview", ""),
                "sender":          r.get("sender", ""),
                "attachment_name": r.get("attachment_name", ""),
            }
            for r in (res.data or [])
        ]
    except Exception as e:
        _log_err("get_for_client", e)
        return []
