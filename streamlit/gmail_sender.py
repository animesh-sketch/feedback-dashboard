"""
Sends report emails via the Gmail API.

Usage:
  result = send_report_email(
      credentials_dict=st.session_state["credentials"],
      to_emails=["a@example.com", "b@example.com"],
      subject="Monthly Analytics Report — February 2026",
      html_body=build_email_html(draft),
      from_email=st.session_state["user_email"],
  )
  # result == {"sent": [...], "failed": [{"email": ..., "error": ...}]}
"""

import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


def _build_service(credentials_dict: dict):
    creds = Credentials(
        token=credentials_dict["token"],
        refresh_token=credentials_dict.get("refresh_token"),
        token_uri=credentials_dict["token_uri"],
        client_id=credentials_dict["client_id"],
        client_secret=credentials_dict["client_secret"],
        scopes=credentials_dict.get("scopes"),
    )
    return build("gmail", "v1", credentials=creds)


def _make_message(to: str, subject: str, html_body: str, from_email: str) -> dict:
    msg = MIMEMultipart("alternative")
    msg["to"] = to
    msg["from"] = from_email
    msg["subject"] = subject
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    return {"raw": raw}


def send_report_email(
    credentials_dict: dict,
    to_emails: list,
    subject: str,
    html_body: str,
    from_email: str,
) -> dict:
    """
    Sends html_body to each address in to_emails via the Gmail API.
    Returns {"sent": [...], "failed": [{"email": ..., "error": ...}]}.
    """
    service = _build_service(credentials_dict)
    sent, failed = [], []

    for addr in to_emails:
        try:
            message = _make_message(addr, subject, html_body, from_email)
            service.users().messages().send(userId="me", body=message).execute()
            sent.append(addr)
        except Exception as exc:
            failed.append({"email": addr, "error": str(exc)})

    return {"sent": sent, "failed": failed}
