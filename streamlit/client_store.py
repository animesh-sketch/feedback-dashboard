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


SAMPLE_CLIENTS = [
    {
        "id": "demo0001",
        "company": "Acme Corp",
        "contact": "Sarah Johnson",
        "emails": ["sarah@acmecorp.com", "reports@acmecorp.com"],
        "status": "Active",
        "tags": ["Enterprise", "Q1"],
        "notes": "Quarterly review scheduled for March.",
        "added_at": "Jan 10, 2026",
    },
    {
        "id": "demo0002",
        "company": "Stellar Dynamics",
        "contact": "Raj Patel",
        "emails": ["raj.patel@stellardyn.com"],
        "status": "Active",
        "tags": ["SaaS", "High Priority"],
        "notes": "Interested in expanding to 3 more teams.",
        "added_at": "Jan 22, 2026",
    },
    {
        "id": "demo0003",
        "company": "Nova Retail",
        "contact": "Emma Clarke",
        "emails": ["emma@novaretail.io", "analytics@novaretail.io"],
        "status": "At Risk",
        "tags": ["Retail", "Renewal Due"],
        "notes": "Renewal due in April — needs check-in call.",
        "added_at": "Feb 01, 2026",
    },
    {
        "id": "demo0004",
        "company": "Bridgewater Finance",
        "contact": "Michael Torres",
        "emails": ["m.torres@bridgewaterfinance.com"],
        "status": "Active",
        "tags": ["Finance", "Enterprise"],
        "notes": "Prefers executive summary format.",
        "added_at": "Feb 10, 2026",
    },
    {
        "id": "demo0005",
        "company": "Greenleaf Solutions",
        "contact": "Priya Mehta",
        "emails": ["priya@greenleaf.co", "ops@greenleaf.co"],
        "status": "Inactive",
        "tags": ["SMB"],
        "notes": "On hold since Feb — follow up in Q2.",
        "added_at": "Feb 14, 2026",
    },
]


def load() -> list:
    """Return all clients from disk. Falls back to sample data if file missing."""
    if not os.path.exists(_FILE):
        return SAMPLE_CLIENTS
    try:
        with open(_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if data else SAMPLE_CLIENTS
    except (json.JSONDecodeError, OSError):
        return SAMPLE_CLIENTS


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
