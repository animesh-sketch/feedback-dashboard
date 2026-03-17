"""
Sends report emails via Gmail SMTP (App Password).

Set in .streamlit/secrets.toml:
  GMAIL_SENDER       = "you@gmail.com"
  GMAIL_APP_PASSWORD = "xxxx xxxx xxxx xxxx"   # Gmail → Security → App passwords
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import streamlit as st


def send_report_email(
    credentials_dict,   # kept for API compatibility, unused
    to_emails: list,
    subject: str,
    html_body: str,
    from_email: str,
) -> dict:
    """
    Sends html_body to each address in to_emails via Gmail SMTP.
    Returns {"sent": [...], "failed": [{"email": ..., "error": ...}]}.
    """
    sender       = st.session_state.get("user_email") or st.secrets.get("GMAIL_SENDER", from_email)
    app_password = st.session_state.get("gmail_app_password") or st.secrets.get("GMAIL_APP_PASSWORD", "")

    sent, failed = [], []

    def _friendly(exc: Exception) -> str:
        msg = str(exc)
        if "534" in msg or "InvalidSecondFactor" in msg or "Application-specific" in msg:
            return "Wrong password type — you need a Gmail App Password, not your regular password. Go to myaccount.google.com → Security → App passwords → Generate."
        if "535" in msg or "BadCredentials" in msg:
            return "Incorrect Gmail or App Password. Double-check and reconnect Gmail in the sidebar."
        if "getaddrinfo" in msg or "timeout" in msg.lower():
            return "Network error — check your internet connection."
        return msg

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
            server.login(sender, app_password)
            for addr in to_emails:
                try:
                    msg = MIMEMultipart("alternative")
                    msg["To"]      = addr
                    msg["From"]    = sender
                    msg["Subject"] = subject
                    msg.attach(MIMEText(html_body, "html", "utf-8"))
                    server.sendmail(sender, addr, msg.as_string())
                    sent.append(addr)
                except Exception as exc:
                    failed.append({"email": addr, "error": _friendly(exc)})
    except Exception as exc:
        return {"sent": [], "failed": [{"email": "login", "error": _friendly(exc)}]}

    return {"sent": sent, "failed": failed}
