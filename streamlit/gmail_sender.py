"""
Sends report emails via Brevo (formerly Sendinblue) API.
Free tier: 300 emails/day. No domain DNS setup needed —
just verify your sender email by clicking a link in your inbox.

Get a free API key at brevo.com
"""

import json
import urllib.request
import streamlit as st


def send_report_email(
    credentials_dict,
    to_emails: list,
    subject: str,
    html_body: str,
    from_email: str,
) -> dict:
    api_key = st.session_state.get("resend_api_key") or st.secrets.get("RESEND_API_KEY", "")
    sender  = st.session_state.get("user_email") or from_email

    if not api_key:
        return {"sent": [], "failed": [{"email": "config", "error": "Brevo API key not set. Add it in the sidebar."}]}

    sent, failed = [], []

    for addr in to_emails:
        try:
            payload = json.dumps({
                "sender":      {"email": sender},
                "to":          [{"email": addr}],
                "subject":     subject,
                "htmlContent": html_body,
            }).encode()

            req = urllib.request.Request(
                "https://api.brevo.com/v3/smtp/email",
                data=payload,
                headers={
                    "accept":       "application/json",
                    "content-type": "application/json",
                    "api-key":      api_key,
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                resp.read()
            sent.append(addr)

        except urllib.error.HTTPError as exc:
            body = exc.read().decode()
            if "not verified" in body.lower() or "unauthorized sender" in body.lower():
                err = f"Sender {sender} not verified. Go to brevo.com → Senders & Domains → Add & verify your email."
            elif "invalid" in body.lower() and "key" in body.lower():
                err = "Invalid Brevo API key."
            else:
                err = body
            failed.append({"email": addr, "error": err})
        except Exception as exc:
            failed.append({"email": addr, "error": str(exc)})

    return {"sent": sent, "failed": failed}
