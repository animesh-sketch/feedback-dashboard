"""
Tracks email open/click/rating events — Supabase PostgreSQL storage.

Requires st.secrets: SUPABASE_URL, SUPABASE_KEY.
"""

from datetime import datetime, timezone

import streamlit as st

_TABLE = "tracking_events"


# ── Supabase client ────────────────────────────────────────────────────────────

@st.cache_resource
def _sb():
    from supabase import create_client
    url = st.secrets.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_KEY", "")
    return create_client(url, key)


# ── Public API ────────────────────────────────────────────────────────────────

def load() -> list:
    try:
        res = (
            _sb().table(_TABLE)
            .select("*")
            .order("timestamp", desc=True)
            .limit(5000)
            .execute()
        )
        return res.data or []
    except Exception:
        return []


def log_event(record_id: str, email: str, event_type: str) -> None:
    """Log an open or click event. Opens are deduplicated per email per record."""
    now = datetime.now(timezone.utc)
    try:
        if event_type == "open":
            existing = (
                _sb().table(_TABLE)
                .select("id")
                .eq("record_id", record_id)
                .eq("email", email)
                .eq("type", "open")
                .execute()
            )
            if existing.data:
                return
        _sb().table(_TABLE).insert({
            "record_id": record_id,
            "email":     email,
            "type":      event_type,
            "timestamp": now.isoformat(),
            "date":      now.strftime("%b %d, %Y"),
            "time":      now.strftime("%H:%M"),
        }).execute()
    except Exception:
        pass


def log_rating(record_id: str, email: str, rating: int) -> None:
    """Log a star rating. Updates existing rating for same email+record."""
    now = datetime.now(timezone.utc)
    try:
        existing = (
            _sb().table(_TABLE)
            .select("id")
            .eq("record_id", record_id)
            .eq("email", email)
            .eq("type", "rating")
            .execute()
        )
        if existing.data:
            _sb().table(_TABLE).update({
                "rating":    rating,
                "timestamp": now.isoformat(),
                "date":      now.strftime("%b %d, %Y"),
                "time":      now.strftime("%H:%M"),
            }).eq("id", existing.data[0]["id"]).execute()
        else:
            _sb().table(_TABLE).insert({
                "record_id": record_id,
                "email":     email,
                "type":      "rating",
                "rating":    rating,
                "timestamp": now.isoformat(),
                "date":      now.strftime("%b %d, %Y"),
                "time":      now.strftime("%H:%M"),
            }).execute()
    except Exception:
        pass


def get_stats_for_send(record_id: str) -> dict:
    """Return open/click/rating counts for a single sent record."""
    try:
        res = _sb().table(_TABLE).select("*").eq("record_id", record_id).execute()
        events = res.data or []
    except Exception:
        events = []
    opens   = len({e["email"] for e in events if e["type"] in ("open", "click")})
    clicks  = len({e["email"] for e in events if e["type"] == "click"})
    ratings = [e for e in events if e["type"] == "rating"]
    return {"opens": opens, "clicks": clicks, "ratings": ratings}


def get_stats_for_period(hours: int = None) -> dict:
    """
    Compute stats for a time window (hours=24 → daily, 168 → weekly, None → all).
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

    opened_emails  = list({e["email"] for e in opens + clicks})

    dist_counts = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
    for e in ratings:
        dist_counts[e.get("rating", 1)] = dist_counts.get(e.get("rating", 1), 0) + 1
    total_ratings = len(ratings)
    avg = sum(e.get("rating", 0) for e in ratings) / total_ratings if total_ratings else 0

    dist = [
        {
            "star":  star,
            "pct":   round(dist_counts.get(star, 0) / total_ratings * 100) if total_ratings else 0,
            "count": dist_counts.get(star, 0),
        }
        for star in [5, 4, 3, 2, 1]
    ]

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
        "opens":          opens,
        "clicks":         clicks,
        "ratings":        ratings,
        "opened_emails":  [{"email": em, "campaign": "—", "date": "—"} for em in opened_emails],
        "clicked_emails": [{"email": e["email"], "campaign": "—", "date": e["date"]} for e in clicks],
        "respondents":    respondents,
        "avg_rating":     round(avg, 1),
        "total_ratings":  total_ratings,
        "dist":           dist,
    }
