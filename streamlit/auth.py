"""
Google OAuth 2.0 helpers for the LivePure Streamlit app.

Usage in app.py:
  1. Call render_login_sidebar() inside `with st.sidebar:`.
  2. On load, check st.query_params for "code" and call exchange_code_for_token().
  3. Store result in st.session_state["credentials"] and st.session_state["user_email"].
"""

import streamlit as st
import requests
from google_auth_oauthlib.flow import Flow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]


def _client_config(redirect_uri: str) -> dict:
    s = st.secrets
    return {
        "web": {
            "client_id": s["GOOGLE_CLIENT_ID"],
            "client_secret": s["GOOGLE_CLIENT_SECRET"],
            "redirect_uris": [redirect_uri],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }


def get_auth_url(redirect_uri: str) -> str:
    """Returns the Google OAuth authorization URL (cached per session)."""
    if "pending_auth_url" not in st.session_state:
        flow = Flow.from_client_config(
            _client_config(redirect_uri),
            scopes=SCOPES,
            redirect_uri=redirect_uri,
        )
        auth_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        st.session_state["pending_auth_url"] = auth_url
        st.session_state["oauth_state"] = state
    return st.session_state["pending_auth_url"]


def exchange_code_for_token(code: str, redirect_uri: str) -> dict:
    """Exchanges the authorization code for credentials. Returns a serializable dict."""
    flow = Flow.from_client_config(
        _client_config(redirect_uri),
        scopes=SCOPES,
        redirect_uri=redirect_uri,
    )
    flow.fetch_token(code=code)
    creds = flow.credentials
    return {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes) if creds.scopes else SCOPES,
    }


def get_user_email(credentials_dict: dict) -> str:
    """Fetches the authenticated user's email address via the userinfo endpoint."""
    resp = requests.get(
        "https://www.googleapis.com/oauth2/v1/userinfo",
        headers={"Authorization": f"Bearer {credentials_dict['token']}"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("email", "")


def render_login_sidebar() -> None:
    """
    Renders Google sign-in button or signed-in state in the sidebar.
    Must be called from within a `with st.sidebar:` block.
    """
    redirect_uri = st.secrets.get("REDIRECT_URI", "http://localhost:8501")

    if st.session_state.get("credentials"):
        email = st.session_state.get("user_email", "")
        st.markdown(
            f'<div style="color:#86efac;font-size:0.78rem;font-weight:600;margin-bottom:2px;">✓ Signed in</div>'
            f'<div style="color:#64748b;font-size:0.75rem;word-break:break-all;margin-bottom:8px;">{email}</div>',
            unsafe_allow_html=True,
        )
        if st.button("Sign out", key="signout_btn", use_container_width=True):
            for key in ["credentials", "user_email", "oauth_state", "pending_auth_url"]:
                st.session_state.pop(key, None)
            st.rerun()
    else:
        try:
            auth_url = get_auth_url(redirect_uri)
            st.markdown(
                f'<a href="{auth_url}" target="_self" style="display:block;background:#4285f4;'
                f'color:#fff;text-align:center;padding:9px 12px;border-radius:8px;'
                f'text-decoration:none;font-size:0.82rem;font-weight:600;">🔑 Sign in with Google</a>',
                unsafe_allow_html=True,
            )
        except Exception:
            st.caption("⚠️ Add credentials to .streamlit/secrets.toml")
