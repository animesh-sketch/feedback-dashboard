"""
Persistent client repository backed by a local JSON file.
Stored at: streamlit/clients.json  (gitignored — never commit real data)
"""

import json
import os
import uuid
from datetime import datetime, timezone

_FILE = os.path.join(os.path.dirname(__file__), "clients.json")

# Status options available throughout the app
STATUSES = ["Active", "At Risk", "Inactive"]


def load() -> list:
    """Return all clients from disk. Returns [] if file missing or corrupt."""
    if not os.path.exists(_FILE):
        return []
    try:
        with open(_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def save(clients: list) -> None:
    with open(_FILE, "w", encoding="utf-8") as f:
        json.dump(clients, f, indent=2, ensure_ascii=False)


def add(company: str, contact: str, emails: list,
        status: str = "Active", tags: list = None, notes: str = "") -> dict:
    client = {
        "id":       str(uuid.uuid4())[:8],
        "company":  company,
        "contact":  contact,
        "emails":   emails,
        "status":   status,
        "tags":     tags or [],
        "notes":    notes,
        "added_at": datetime.now(timezone.utc).strftime("%b %d, %Y"),
    }
    clients = load()
    clients.append(client)
    save(clients)
    return client


def update(client_id: str, updates: dict) -> None:
    clients = load()
    for c in clients:
        if c["id"] == client_id:
            c.update(updates)
            break
    save(clients)


def delete(client_id: str) -> None:
    save([c for c in load() if c["id"] != client_id])
