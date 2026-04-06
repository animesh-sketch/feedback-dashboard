"""
Tracks email open/click/rating events.
Storage: GitHub JSON (same pattern as sent_store.py), session state, local file.
"""

import base64 as _b64
import json
import os
from datetime import datetime, timezone

import streamlit as st

_FILE         = os.path.join(os.path.dirname(__file__), "tracking_events.json")
_SS_KEY       = "tracking_store_data"
_DEFAULT_REPO = "animesh-sketch/feedback-dashboard"
_GH_PATH      = "streamlit/tracking_events.json"


def _gh_headers():
    token = st.secrets.get("GITHUB_TOKEN", "")
    if not token:
        return None
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _gh_load():
    try:
        import requests as _req
        hdrs = _gh_headers()
        if not hdrs:
            return None
        repo = st.secrets.get("GITHUB_REPO", _DEFAULT_REPO)
        url  = f"https://api.github.com/repos/{repo}/contents/{_GH_PATH}"
        r = _req.get(url, headers=hdrs, timeout=8)
        if r.status_code == 200:
            raw = _b64.b64decode(r.json()["content"]).decode("utf-8")
            return json.loads(raw)
    except Exception:
        pass
    return None


def _gh_save(events: list) -> bool:
    try:
        import requests as _req
        hdrs = _gh_headers()
        if not hdrs:
            return False
        repo = st.secrets.get("GITHUB_REPO", _DEFAULT_REPO)
        url  = f"https://api.github.com/repos/{repo}/contents/{_GH_PATH}"
        sha  = None
        r    = _req.get(url, headers=hdrs, timeout=5)
        if r.status_code == 200:
            sha = r.json().get("sha")
        content = _b64.b64encode(
            json.dumps(events, indent=2, ensure_ascii=False).encode()
        ).decode()
        payload = {"message": "chore: update tracking events", "content": content}
        if sha:
            payload["sha"] = sha
        resp = _req.put(url, headers=hdrs, json=payload, timeout=10)
        return resp.status_code in (200, 201)
    except Exception:
        return False


def _init() -> None:
    if _SS_KEY in st.session_state:
        return
    data = _gh_load()
    if data is not None:
        st.session_state[_SS_KEY] = data
        return
    if os.path.exists(_FILE):
        try:
            with open(_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                st.session_state[_SS_KEY] = data
                return
        except (json.JSONDecodeError, OSError):
            pass
    st.session_state[_SS_KEY] = []


def load() -> list:
    _init()
    return list(st.session_state[_SS_KEY])


def _persist(events: list) -> None:
    st.session_state[_SS_KEY] = events
    _gh_save(events)
    try:
        with open(_FILE, "w", encoding="utf-8") as f:
            json.dump(events, f, indent=2, ensure_ascii=False)
    except OSError:
        pass


def log_event(record_id: str, email: str, event_type: str) -> None:
    """Log an open or click event. Opens are deduplicated per email per record."""
    now = datetime.now(timezone.utc)
    events = load()
    if event_type == "open":
        already = any(
            e["record_id"] == record_id and e["email"] == email and e["type"] == "open"
            for e in events
        )
        if already:
            return
    event = {
        "record_id": record_id,
        "email":     email,
        "type":      event_type,
        "timestamp": now.isoformat(),
        "date":      now.strftime("%b %d, %Y"),
        "time":      now.strftime("%H:%M"),
    }
    events.insert(0, event)
    events = events[:5000]
    _persist(events)


def log_rating(record_id: str, email: str, rating: int) -> None:
    """Log a star rating. Updates existing rating for same email+record."""
    now = datetime.now(timezone.utc)
    events = load()
    events = [e for e in events if not (
        e["record_id"] == record_id and e["email"] == email and e["type"] == "rating"
    )]
    event = {
        "record_id": record_id,
        "email":     email,
        "type":      "rating",
        "rating":    rating,
        "timestamp": now.isoformat(),
        "date":      now.strftime("%b %d, %Y"),
        "time":      now.strftime("%H:%M"),
    }
    events.insert(0, event)
    events = events[:5000]
    _persist(events)


def get_stats_for_send(record_id: str) -> dict:
    """Return open/click/rating counts for a single sent record."""
    events  = [e for e in load() if e.get("record_id") == record_id]
    opens   = len({e["email"] for e in events if e["type"] in ("open", "click")})
    clicks  = len({e["email"] for e in events if e["type"] == "click"})
    ratings = [e for e in events if e["type"] == "rating"]
    return {"opens": opens, "clicks": clicks, "ratings": ratings}


def get_stats_for_period(hours: int = None) -> dict:
    """
    Compute stats for the given time window (hours=24 → daily, 168 → weekly, None → all).
    Returns dict with opens, clicks, ratings, respondents list, dist, avg_rating.
    """
    from datetime import timedelta
    events = load()

    if hours is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        events = [
            e for e in events
            if datetime.fromisoformat(e["timestamp"]) >= cutoff
        ]

    opens   = [e for e in events if e["type"] == "open"]
    clicks  = [e for e in events if e["type"] == "click"]
    ratings = [e for e in events if e["type"] == "rating"]

    # Unique openers (open OR click OR rating counts as engagement)
    engaged_emails = list({e["email"] for e in opens + clicks + ratings})
    opened_emails  = list({e["email"] for e in opens + clicks})

    dist_counts = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
    for e in ratings:
        dist_counts[e.get("rating", 1)] = dist_counts.get(e.get("rating", 1), 0) + 1
    total_ratings = len(ratings)
    avg = sum(e.get("rating", 0) for e in ratings) / total_ratings if total_ratings else 0

    dist = []
    for star in [5, 4, 3, 2, 1]:
        cnt = dist_counts.get(star, 0)
        dist.append({
            "star":  star,
            "pct":   round(cnt / total_ratings * 100) if total_ratings else 0,
            "count": cnt,
        })

    respondents = [
        {
            "name":   e["email"].split("@")[0].replace(".", " ").title(),
            "email":  e["email"],
            "rating": e["rating"],
            "date":   e["date"],
        }
        for e in sorted(ratings, key=lambda x: x["timestamp"], reverse=True)
    ]

    return {
        "opens":       opens,
        "clicks":      clicks,
        "ratings":     ratings,
        "opened_emails":  [{"email": em, "campaign": "—", "date": "—"} for em in opened_emails],
        "clicked_emails": [{"email": e["email"], "campaign": "—", "date": e["date"]} for e in clicks],
        "respondents": respondents,
        "avg_rating":  round(avg, 1),
        "total_ratings": total_ratings,
        "dist":        dist,
    }
