"""
Sent email log — GitHub CSV storage with shared cache.

All users share a single @st.cache_data cache (TTL 15 s).
When any user sends an email, the shared cache is cleared so every
other user sees the new record on their next interaction.

Requires st.secrets: GITHUB_TOKEN, GITHUB_REPO.
"""

import base64 as _b64
import csv
import io
import json
import uuid
from datetime import datetime, timezone

import streamlit as st

_DEFAULT_REPO = "animesh-sketch/feedback-dashboard"
_GH_PATH      = "data/sent_items.csv"

_FIELDS = [
    "id", "timestamp", "date", "time", "sender",
    "draft_name", "subject", "template_num", "template_name",
    "client", "attachment_name", "is_test",
    "sent_to", "failed", "body_preview",
]


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

def _row_to_record(row: dict) -> dict:
    try:
        failed = json.loads(row.get("failed", "[]") or "[]")
    except Exception:
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
        "is_test":         row.get("is_test", "").lower() == "true",
        "sent_to":         [e for e in row.get("sent_to", "").split("|") if e.strip()],
        "failed":          failed,
        "body_preview":    row.get("body_preview", ""),
    }

def _records_to_csv(records: list) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=_FIELDS, lineterminator="\n")
    w.writeheader()
    for r in records:
        w.writerow({
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
            "is_test":         "true" if r.get("is_test") else "false",
            "sent_to":         "|".join(r.get("sent_to", [])),
            "failed":          json.dumps(r.get("failed", []), ensure_ascii=False),
            "body_preview":    r.get("body_preview", "")[:300].replace("\n", " "),
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
            return [_row_to_record(row) for row in csv.DictReader(io.StringIO(raw))]
        if r.status_code == 404:
            return []
    except Exception:
        pass
    return None


def _gh_save(records: list) -> bool:
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
            "message": "chore: update sent items",
            "content": _b64.b64encode(_records_to_csv(records).encode()).decode(),
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
    """Return current sent records (shared cache, max 15 s stale)."""
    return list(_cached_load())


def _persist(records: list) -> None:
    _gh_save(records)
    _cached_load.clear()                 # all users see update on next interaction


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
) -> dict:
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
    records = load()
    records.insert(0, record)
    records = records[:500]
    _persist(records)
    return record


def clear() -> None:
    _persist([])
