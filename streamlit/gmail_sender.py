"""
Sends report emails via Resend API (primary) or Gmail SMTP (fallback).

Primary: Resend API — uses RESEND_API_KEY from st.secrets, no App Password needed.
Fallback: Gmail SMTP — uses GMAIL_SENDER + GMAIL_APP_PASSWORD from st.secrets.
"""

import base64 as _b64
import re
import smtplib
import ssl
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import streamlit as st

# Domains that returned 403 (unverified) — skip on subsequent calls to avoid double round-trip
_UNVERIFIED_DOMAINS: set = set()


def _get_secret(key: str, default: str = "") -> str:
    try:
        return st.secrets.get(key, default) or default
    except Exception:
        return default


def _extract_inline_images(html: str):
    images = []

    def _replace(match):
        data_url = match.group(1)
        cid = f"img_{len(images)}"
        header, b64data = data_url.split(",", 1)
        subtype = header.split(":")[1].split(";")[0].split("/")[1]
        images.append((cid, subtype, _b64.b64decode(b64data)))
        return f'src="cid:{cid}"'

    modified = re.sub(r'src="(data:image/[^"]+)"', _replace, html)
    return modified, images


def _resend_post(resend_key: str, from_str: str, to_emails: list,
                 subject: str, html_body: str) -> dict:
    """Single Resend API call. Returns {sent, failed}."""
    import requests as _req
    sent, failed = [], []
    for addr in to_emails:
        try:
            resp = _req.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {resend_key}",
                         "Content-Type": "application/json"},
                json={"from": from_str, "to": [addr],
                      "subject": subject, "html": html_body},
                timeout=8,
            )
            if resp.status_code in (200, 201):
                sent.append(addr)
            else:
                failed.append({"email": addr,
                                "error": f"Resend {resp.status_code}: {resp.text[:300]}"})
        except Exception as exc:
            failed.append({"email": addr, "error": f"Resend request failed: {exc}"})
    return {"sent": sent, "failed": failed}


def _domain_of(addr: str) -> str:
    try:
        return addr.split("@")[1].lower()
    except Exception:
        return ""


def _send_via_resend(resend_key: str, from_addr: str, to_emails: list,
                     subject: str, html_body: str) -> dict:
    """Send via Resend. Skips custom domain if previously unverified; falls back to onboarding@resend.dev."""
    domain = _domain_of(from_addr)

    # If domain already known to be unverified, go straight to fallback
    if domain not in _UNVERIFIED_DOMAINS:
        result = _resend_post(resend_key,
                              f"Convin Data Labs <{from_addr}>",
                              to_emails, subject, html_body)
        if not result.get("failed"):
            return result

        errs = " ".join(f.get("error", "") for f in result["failed"])
        if "403" in errs or "422" in errs or "domain" in errs.lower() or "not verified" in errs.lower():
            _UNVERIFIED_DOMAINS.add(domain)  # remember — skip next time
        else:
            return result

    # Fallback: Resend's verified default sender
    return _resend_post(resend_key,
                        "Convin Data Labs <onboarding@resend.dev>",
                        to_emails, subject, html_body)


def _send_via_gmail(gmail_user: str, app_password: str, to_emails: list,
                    subject: str, html_body: str,
                    attachment_name=None, attachment_data=None) -> dict:
    """Send using Gmail SMTP. Returns {sent, failed}."""
    sent, failed = [], []
    try:
        context = ssl.create_default_context()
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context)
        server.login(gmail_user, app_password)
    except smtplib.SMTPAuthenticationError:
        return {"sent": [], "failed": [{"email": "config", "error": (
            "Gmail authentication failed — wrong email or App Password.\n"
            "Use an App Password (not your regular password):\n"
            "myaccount.google.com → Security → App Passwords"
        )}]}
    except Exception as exc:
        return {"sent": [], "failed": [{"email": "config",
                                        "error": f"Could not connect to Gmail: {exc}"}]}

    for addr in to_emails:
        try:
            modified_html, inline_images = _extract_inline_images(html_body)
            if attachment_data:
                outer = MIMEMultipart("mixed")
                related = MIMEMultipart("related")
                outer.attach(related)
            else:
                outer = related = MIMEMultipart("related")
            outer["Subject"] = subject
            outer["From"] = gmail_user
            outer["To"] = addr
            alt = MIMEMultipart("alternative")
            alt.attach(MIMEText(modified_html, "html"))
            related.attach(alt)
            for cid, subtype, img_bytes in inline_images:
                part = MIMEImage(img_bytes, _subtype=subtype)
                part.add_header("Content-ID", f"<{cid}>")
                part.add_header("Content-Disposition", "inline")
                related.attach(part)
            if attachment_data and attachment_name:
                app_part = MIMEApplication(attachment_data, Name=attachment_name)
                app_part.add_header("Content-Disposition", "attachment",
                                    filename=attachment_name)
                outer.attach(app_part)
            server.sendmail(gmail_user, addr, outer.as_string())
            sent.append(addr)
        except Exception as exc:
            failed.append({"email": addr, "error": str(exc)})

    server.quit()
    return {"sent": sent, "failed": failed}


def send_report_email(
    credentials_dict,
    to_emails: list,
    subject: str,
    html_body: str,
    from_email: str = "",
    attachment_name: str = None,
    attachment_data: bytes = None,
    attachment_mime: str = None,
    html_builder=None,
    sender: str = "",
) -> dict:
    from_addr = (st.session_state.get("user_email")
                 or from_email or sender
                 or _get_secret("GMAIL_SENDER")
                 or "convinlabs@convin.ai").strip()

    resend_key = (st.session_state.get("resend_api_key")
                  or _get_secret("RESEND_API_KEY"))

    app_password = (st.session_state.get("gmail_app_password", "")
                    or _get_secret("GMAIL_APP_PASSWORD")).replace(" ", "")

    # Build per-recipient html if builder provided
    if html_builder:
        results = {"sent": [], "failed": []}
        for addr in to_emails:
            body = html_builder(addr)
            r = send_report_email(
                credentials_dict={}, to_emails=[addr],
                subject=subject, html_body=body,
                from_email=from_addr,
            )
            results["sent"].extend(r.get("sent", []))
            results["failed"].extend(r.get("failed", []))
        return results

    # ── Try Gmail SMTP first (works for any recipient) ───────────────────────
    if app_password:
        return _send_via_gmail(from_addr, app_password, to_emails,
                               subject, html_body, attachment_name, attachment_data)

    # ── Fall back to Resend (requires verified domain for non-owner recipients) ──
    if resend_key:
        return _send_via_resend(resend_key, from_addr, to_emails,
                                subject, html_body)

    return {"sent": [], "failed": [{"email": "config", "error": (
        "No email provider configured. "
        "Add GMAIL_APP_PASSWORD or RESEND_API_KEY to Streamlit secrets."
    )}]}
