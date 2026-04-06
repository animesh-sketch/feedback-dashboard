"""
Sent email log — GitHub CSV storage.

Reads and writes data/sent_items.csv in the GitHub repo via the GitHub Contents API.
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
_SS_KEY       = "sent_store_data"

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


# ── CSV conversion ────────────────────────────────────────────────────────────

def _to_dict(row: dict) -> dict:
    """CSV row → record dict."""
    failed_raw = row.get("failed", "[]")
    try:
        failed = json.loads(failed_raw) if failed_raw else []
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

def _to_csv(records: list) -> str:
    """Record dicts → CSV string."""
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
    """Fetch data/sent_items.csv from GitHub. Returns list or None on error."""
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
            reader = csv.DictReader(io.StringIO(raw))
            return [_to_dict(row) for row in reader]
        if r.status_code == 404:
            return []          # file doesn't exist yet
    except Exception:
        pass
    return None


def _gh_save(records: list) -> bool:
    """Write data/sent_items.csv back to GitHub. Returns True on success."""
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
            "content": _b64.b64encode(_to_csv(records).encode()).decode(),
        }
        if sha:
            payload["sha"] = sha
        resp = _req.put(url, headers=hdrs, json=payload, timeout=15)
        return resp.status_code in (200, 201)
    except Exception:
        return False


# ── Public API ────────────────────────────────────────────────────────────────

def _init() -> None:
    if _SS_KEY in st.session_state:
        return
    data = _gh_load()
    st.session_state[_SS_KEY] = data if data is not None else []


def load() -> list:
    _init()
    return st.session_state[_SS_KEY]


def _persist(records: list) -> None:
    st.session_state[_SS_KEY] = records
    _gh_save(records)


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
    normalised_failed = []
    for item in failed:
        if isinstance(item, dict):
            normalised_failed.append({"email": item.get("email", ""), "error": item.get("error", "")})
        else:
            normalised_failed.append({"email": str(item), "error": ""})
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
