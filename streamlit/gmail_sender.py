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

import base64 as _b64
import re
import smtplib
import ssl
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import streamlit as st


def _extract_inline_images(html: str):
    """
    Finds base64 data-URL images in HTML, replaces each with a cid: reference,
    and returns (modified_html, [(cid, subtype, bytes), ...]).
    Email clients block data: URLs — CID attachments are the correct approach.
    """
    images = []

    def _replace(match):
        data_url = match.group(1)          # data:image/jpeg;base64,<data>
        cid = f"img_{len(images)}"
        header, b64data = data_url.split(",", 1)
        subtype = header.split(":")[1].split(";")[0].split("/")[1]  # jpeg / png / gif
        images.append((cid, subtype, _b64.b64decode(b64data)))
        return f'src="cid:{cid}"'

    modified = re.sub(r'src="(data:image/[^"]+)"', _replace, html)
    return modified, images


def send_report_email(
    credentials_dict,
    to_emails: list,
    subject: str,
    html_body: str,
    from_email: str,
    attachment_name: str = None,
    attachment_data: bytes = None,
    attachment_mime: str = None,
    html_builder=None,
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
            body_html = html_builder(addr) if html_builder else html_body
            modified_html, inline_images = _extract_inline_images(body_html)

            # Outer container: "mixed" when file attachment present, else "related"
            if attachment_data:
                outer          = MIMEMultipart("mixed")
                outer["Subject"] = subject
                outer["From"]    = gmail_user
                outer["To"]      = addr
                related        = MIMEMultipart("related")
                outer.attach(related)
            else:
                outer = related = MIMEMultipart("related")
                outer["Subject"] = subject
                outer["From"]    = gmail_user
                outer["To"]      = addr

            alt = MIMEMultipart("alternative")
            alt.attach(MIMEText(modified_html, "html"))
            related.attach(alt)

            for cid, subtype, img_bytes in inline_images:
                part = MIMEImage(img_bytes, _subtype=subtype)
                part.add_header("Content-ID", f"<{cid}>")
                part.add_header("Content-Disposition", "inline")
                related.attach(part)

            if attachment_data and attachment_name:
                ext = attachment_name.rsplit(".", 1)[-1].lower() if "." in attachment_name else "bin"
                app_part = MIMEApplication(attachment_data, Name=attachment_name)
                app_part.add_header("Content-Disposition", "attachment", filename=attachment_name)
                outer.attach(app_part)

            server.sendmail(gmail_user, addr, outer.as_string())
            sent.append(addr)
        except Exception as exc:
            failed.append({"email": addr, "error": str(exc)})

    server.quit()
    return {"sent": sent, "failed": failed}
