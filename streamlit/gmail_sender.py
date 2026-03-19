"""
Sends report emails via Gmail SMTP using a Google App Password.
No third-party service needed — uses your own Gmail account directly.

Setup (one-time):
1. Go to myaccount.google.com → Security
2. Enable 2-Step Verification (required)
3. Search "App Passwords" → Create one → select Mail
4. Copy the 16-character code (e.g. abcd efgh ijkl mnop)
5. Paste it in the sidebar "Gmail App Password" field
"""

import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import streamlit as st


def send_report_email(
    credentials_dict,
    to_emails: list,
    subject: str,
    html_body: str,
    from_email: str,
) -> dict:
    gmail_user   = st.session_state.get("user_email") or from_email
    app_password = st.session_state.get("gmail_app_password", "").replace(" ", "")

    if not app_password:
        return {"sent": [], "failed": [{"email": "config", "error": "Gmail App Password not set. Add it in the sidebar."}]}
    if not gmail_user or "@" not in gmail_user:
        return {"sent": [], "failed": [{"email": "config", "error": "Gmail address not set. Add it in the sidebar."}]}

    sent, failed = [], []

    # Open one SMTP connection and reuse it for all recipients
    try:
        context = ssl.create_default_context()
        server  = smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context)
        server.login(gmail_user, app_password)
    except smtplib.SMTPAuthenticationError:
        return {"sent": [], "failed": [{"email": "config", "error": (
            "Gmail authentication failed — wrong email or App Password.\n\n"
            "Make sure you're using an App Password, not your regular Gmail password.\n\n"
            "Steps to create one:\n"
            "1. myaccount.google.com → Security\n"
            "2. Enable 2-Step Verification\n"
            "3. Search 'App Passwords' → create one for Mail\n"
            "4. Copy the 16-character code and paste it in the sidebar"
        )}]}
    except Exception as exc:
        return {"sent": [], "failed": [{"email": "config", "error": f"Could not connect to Gmail: {exc}"}]}

    for addr in to_emails:
        try:
            msg             = MIMEMultipart("alternative")
            msg["Subject"]  = subject
            msg["From"]     = gmail_user
            msg["To"]       = addr
            msg.attach(MIMEText(html_body, "html"))
            server.sendmail(gmail_user, addr, msg.as_string())
            sent.append(addr)
        except Exception as exc:
            failed.append({"email": addr, "error": str(exc)})

    server.quit()
    return {"sent": sent, "failed": failed}
