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
    sender       = st.secrets.get("GMAIL_SENDER", from_email)
    app_password = st.secrets.get("GMAIL_APP_PASSWORD", "")

    sent, failed = [], []

    for addr in to_emails:
        try:
            msg = MIMEMultipart("alternative")
            msg["To"]      = addr
            msg["From"]    = sender
            msg["Subject"] = subject
            msg.attach(MIMEText(html_body, "html", "utf-8"))

            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(sender, app_password)
                server.sendmail(sender, addr, msg.as_string())

            sent.append(addr)
        except Exception as exc:
            failed.append({"email": addr, "error": str(exc)})

    return {"sent": sent, "failed": failed}
