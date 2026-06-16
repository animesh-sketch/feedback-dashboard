"""
PIN-based authentication with role support.

Users log in with a unique 4-digit number.
Roles: "admin" (full access) | "tl" (Team Lead — same as admin) | "qa" (Audit only).

USERS can be overridden via st.secrets["USERS"] (JSON string) for production.
"""

import json
import streamlit as st

# ── User table ────────────────────────────────────────────────────────────────
# Format: { "PIN": {"name": "...", "role": "admin"|"tl"|"qa"} }

_DEFAULT_USERS = {
    "1000": {"name": "Admin",           "role": "admin"},
    "1011": {"name": "Aman",            "role": "admin"},
    "1001": {"name": "Animesh",         "role": "admin"},
    "1002": {"name": "Left - Navya",    "role": "qa"},
    "1003": {"name": "Shubham Sharma",  "role": "qa"},
    "1004": {"name": "Left - Nora",     "role": "qa"},
    "1005": {"name": "Left - Alan",     "role": "qa"},
    "1006": {"name": "Left - Priya",    "role": "qa"},
    "1007": {"name": "Left - Raj",      "role": "qa"},
    "1008": {"name": "Left - Sara",     "role": "qa"},
    "1009": {"name": "Left - Mansi",    "role": "qa"},
    "1010": {"name": "Sakshi",          "role": "qa"},
    "1012": {"name": "Tabassum Arfeen", "role": "qa"},
    "1013": {"name": "Bhavya",          "role": "qa"},
    "1014": {"name": "Roshan",          "role": "qa"},
    "1015": {"name": "Siddhi",          "role": "qa"},
    "9999": {"name": "Test",            "role": "qa"},
}

_ROLE_LABELS = {
    "admin": "🔑 Admin",
    "tl":    "⭐ Team Lead",
    "qa":    "👤 QA",
}

_ROLE_ICONS = {
    "admin": "🔑",
    "tl":    "⭐",
    "qa":    "👤",
}


def _get_users() -> dict:
    """Return user table, preferring st.secrets override if present."""
    raw = st.secrets.get("USERS", "")
    if raw:
        try:
            return json.loads(raw)
        except Exception:
            pass
    return _DEFAULT_USERS


def check_login(pin: str) -> tuple[bool, dict, str]:
    """
    Returns (True, user_dict, "") on success.
    Returns (False, {}, error_message) on failure.
    user_dict has keys: name, role, pin
    """
    pin = str(pin).strip()
    if not pin.isdigit():
        return False, {}, "Enter your numeric access code."
    users = _get_users()
    user = users.get(pin)
    if not user:
        return False, {}, "Invalid access code. Please try again."
    return True, {"pin": pin, "name": user["name"], "role": user["role"]}, ""


def current_user() -> dict:
    """Return the logged-in user dict or {}."""
    return st.session_state.get("auth_user", {})


def is_admin() -> bool:
    """True for admin and TL — both have full access."""
    return current_user().get("role") in ("admin", "tl")


def is_tl() -> bool:
    return current_user().get("role") == "tl"


def is_qa() -> bool:
    return current_user().get("role") == "qa"


def current_name() -> str:
    return current_user().get("name", "")


def role_icon() -> str:
    return _ROLE_ICONS.get(current_user().get("role", ""), "👤")


def render_login_sidebar() -> None:
    """Renders signed-in state + sign-out button in the sidebar."""
    user = current_user()
    if user:
        badge = _ROLE_LABELS.get(user["role"], "👤 QA")
        st.markdown(
            f'<div style="color:#16a34a;font-size:0.78rem;font-weight:600;margin-bottom:2px;">✓ Signed in</div>'
            f'<div style="color:#334155;font-size:0.80rem;font-weight:700;margin-bottom:2px;">{user["name"]}</div>'
            f'<div style="color:#5588bb;font-size:0.68rem;margin-bottom:8px;">{badge}</div>',
            unsafe_allow_html=True,
        )
        if st.button("Sign out", key="signout_btn", use_container_width=True):
            st.session_state.pop("logged_in", None)
            st.session_state.pop("auth_user", None)
            st.session_state.pop("user_email", None)
            st.session_state.pop("gmail_app_password", None)
            st.rerun()
    else:
        st.caption("Not signed in")
