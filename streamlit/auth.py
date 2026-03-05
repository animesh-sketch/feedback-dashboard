"""
Simple email + password authentication for the Streamlit app.

Credentials are stored in .streamlit/secrets.toml under [users]:
  [users]
  "you@example.com" = "<sha256 of password>"

Generate a hash:  python3 -c "import hashlib; print(hashlib.sha256(b'yourpassword').hexdigest())"
"""

import hashlib
import streamlit as st


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def check_credentials(email: str, password: str) -> bool:
    expected_email = st.secrets.get("USER_EMAIL", "")
    expected_hash  = st.secrets.get("USER_HASH", "")
    return (
        bool(expected_email)
        and email.strip().lower() == expected_email.strip().lower()
        and bool(expected_hash)
        and _hash(password) == expected_hash
    )


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
            st.rerun()
    else:
        st.caption("Not signed in")
