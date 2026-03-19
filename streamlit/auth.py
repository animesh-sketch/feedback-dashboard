"""
Email + password authentication for the Streamlit app.
Credentials are read from .streamlit/secrets.toml:
  USER_EMAIL = "you@example.com"
  USER_HASH  = "<sha256 of your password>"

To generate a hash for a new password, run in Python:
  import hashlib; print(hashlib.sha256("yourpassword".encode()).hexdigest())

If neither key is set, any valid email can log in (open access).
"""

import hashlib
import streamlit as st


def check_login(email: str, password: str = "") -> tuple[bool, str]:
    """
    Returns (True, "") on success, or (False, error_message) on failure.
    Checks email against USER_EMAIL and password against USER_HASH from secrets.
    """
    email = email.strip().lower()
    if not email or "@" not in email:
        return False, "Enter a valid email address."

    # Restrict to the configured email address (if set)
    allowed_email = st.secrets.get("USER_EMAIL", "").strip().lower()
    if allowed_email and email != allowed_email:
        return False, "This email is not authorised to access this dashboard."

    # Require password if USER_HASH is configured
    user_hash = st.secrets.get("USER_HASH", "").strip()
    if user_hash:
        if not password:
            return False, "Password is required."
        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        if pw_hash != user_hash:
            return False, "Incorrect password."

    return True, ""


def needs_password() -> bool:
    """True when a password hash is configured in secrets."""
    return bool(st.secrets.get("USER_HASH", "").strip())


def render_login_sidebar() -> None:
    """Renders signed-in state + sign-out button in the sidebar."""
    if st.session_state.get("logged_in"):
        email = st.session_state.get("user_email", "")
        st.markdown(
            f'<div style="color:#16a34a;font-size:0.78rem;font-weight:600;margin-bottom:2px;">✓ Signed in</div>'
            f'<div style="color:#475569;font-size:0.75rem;word-break:break-all;margin-bottom:8px;">{email}</div>',
            unsafe_allow_html=True,
        )
        if st.button("Sign out", key="signout_btn", use_container_width=True):
            st.session_state.pop("logged_in", None)
            st.session_state.pop("user_email", None)
            st.session_state.pop("gmail_app_password", None)
            st.rerun()
    else:
        st.caption("Not signed in")
