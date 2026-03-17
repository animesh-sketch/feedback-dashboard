"""
Sends report emails via Resend API.
No App Password or SMTP needed.

Set RESEND_API_KEY in .streamlit/secrets.toml or enter it in the sidebar.
Get a free API key at resend.com (3000 emails/month free).
"""

import resend
import streamlit as st


def send_report_email(
    credentials_dict,   # kept for API compatibility, unused
    to_emails: list,
    subject: str,
    html_body: str,
    from_email: str,
) -> dict:
    """
    Sends html_body to each address in to_emails via Resend API.
    Returns {"sent": [...], "failed": [{"email": ..., "error": ...}]}.
    """
    api_key    = st.session_state.get("resend_api_key") or st.secrets.get("RESEND_API_KEY", "")
    sender     = st.session_state.get("user_email") or from_email

    if not api_key:
        return {"sent": [], "failed": [{"email": "config", "error": "Resend API key not set. Add it in the sidebar."}]}

    resend.api_key = api_key
    sent, failed   = [], []

    for addr in to_emails:
        try:
            resend.Emails.send({
                "from": f"Convin Data Labs <{sender}>",
                "to":   [addr],
                "subject": subject,
                "html": html_body,
            })
            sent.append(addr)
        except Exception as exc:
            msg = str(exc)
            if "domain" in msg.lower() or "verify" in msg.lower() or "not allowed" in msg.lower():
                err = f"Sender domain not verified in Resend. Go to resend.com/domains and add {sender.split('@')[-1]}."
            elif "invalid_api_key" in msg.lower() or "unauthorized" in msg.lower():
                err = "Invalid Resend API key. Check the key in the sidebar."
            else:
                err = msg
            failed.append({"email": addr, "error": err})

    return {"sent": sent, "failed": failed}
