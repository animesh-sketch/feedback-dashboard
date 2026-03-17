"""
Simple email-based authentication for the Streamlit app.
Any valid email address can log in — no password required at login.
Gmail credentials for sending are entered separately in the Send tab.
"""

import streamlit as st


def check_login(email: str) -> tuple:
    """Returns (True, "") if email looks valid, else (False, error)."""
    email = email.strip().lower()
    if not email or "@" not in email:
        return False, "Enter a valid email address."
    return True, ""


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
