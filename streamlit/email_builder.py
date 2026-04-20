"""
12 email template designs for Convin Data Labs report emails.
Fields used: client, headline, body, screenshot_url, screenshot_caption,
             report_link, survey_question, template (1-12)
"""

# Template registry: (name, description, swatch_bg)
TEMPLATE_NAMES = [
    ("Convin Dark",  "Dark · Convin brand blue",    "#151515"),
    ("Convin Light", "Clean white · Convin blue",   "#eef0ff"),
    ("Convin Bold",  "Bold blue · Convin primary",  "#4d65ff"),
    ("Convin Pro",   "Dark gradient · Convin glow", "#0e0e1e"),
    ("Classic",      "Warm cream · Serif elegant",  "#f4ede0"),
    ("Neon",         "Dark · Cyan glow tech",       "#040d18"),
    ("Sunrise",      "Warm orange · Light airy",    "#fff3e8"),
    ("Forest",       "Deep green · Mint fresh",     "#0b1f14"),
    ("Carbon",       "Charcoal · Bold orange",      "#1a1a1a"),
    ("Convin Signature", "Pink·Coral·Blue brand gradient", "#d22c84"),
    ("Convin Slate",     "Slate grey · Blue accent clean",  "#3d4f6b"),
    ("Convin Premium",  "White · Gradient border premium",  "#1a62f2"),
]

import base64 as _b64e
import urllib.parse as _up

_BASE_URL  = "https://feedback-dashboard-4mqlwnnzntsjdhjhy9a6br.streamlit.app"
_LOGO_URL  = "https://static-asset.inc42.com/logo/convin.png"


def _logo(dark: bool = True, h: int = 28) -> str:
    """Convin brand logo img tag for email headers.
    dark=True wraps in a white pill (for dark/coloured backgrounds).
    """
    img = (f'<img src="{_LOGO_URL}" alt="Convin" height="{h}" '
           f'style="height:{h}px;width:auto;display:block;border:0;"/>')
    if dark:
        return (f'<div style="background:rgba(255,255,255,0.92);border-radius:6px;'
                f'padding:4px 10px;display:inline-block;line-height:0;">{img}</div>')
    return img


def _track_click_url(send_id, em_b64, original_url):
    if not send_id or not original_url or original_url == "#":
        return original_url
    return f"{_BASE_URL}/?track=click&id={send_id}&em={em_b64}&url={_up.quote(original_url, safe='')}"


def _rating_url(star, send_id, em_b64):
    base = f"{_BASE_URL}/?rating={star}"
    if send_id:
        base += f"&id={send_id}&em={em_b64}"
    return base


def _tracking_pixel(send_id, em_b64):
    if not send_id:
        return ""
    return (
        f'<img src="{_BASE_URL}/?track=open&id={send_id}&em={em_b64}" '
        f'width="1" height="1" style="display:none;border:0;" alt="" />'
    )


def build_email_html(draft: dict, template_id: int = 1, send_id: str = None, recipient_email: str = None, font_size: str = None, font_family: str = None) -> str:
    c  = draft.get("client")              or "—"
    h  = draft.get("headline")            or "—"
    b  = (draft.get("body") or draft.get("intro") or "").replace("\n", "<br>")
    if font_size or font_family:
        _b_style = ""
        if font_size:   _b_style += f"font-size:{font_size};"
        if font_family: _b_style += f"font-family:{font_family};"
        b = f'<span style="{_b_style}">{b}</span>'
    ss = draft.get("screenshot_url")      or ""
    sc = draft.get("screenshot_caption")  or ""
    rl = draft.get("report_link")         or "#"
    sq = draft.get("survey_question")     or "Was this report useful to you?"
    em_b64 = _b64e.b64encode((recipient_email or "").encode()).decode() if recipient_email else ""

    # Build extra images block (img2, img3) rendered after the main screenshot
    extra_parts = []
    for i in (2, 3):
        url = draft.get(f"img{i}_url") or ""
        cap = draft.get(f"img{i}_caption") or ""
        if url:
            cap_html = (f'<p style="font-size:11px;font-style:italic;margin-top:8px;'
                        f'color:#9c8e80;text-align:center;">{cap}</p>') if cap else ""
            extra_parts.append(
                f'<div style="padding:0 44px 24px;">'
                f'<img src="{url}" alt="Image {i}" '
                f'style="width:100%;display:block;border-radius:8px;"/>'
                f'{cap_html}</div>'
            )

    # Build attachment block — shown when a URL or uploaded file name is present
    att_url  = draft.get("attachment_url")  or ""
    att_name = draft.get("attachment_name") or "Attachment"
    att_data = draft.get("attachment_data") or ""   # base64 — file was uploaded
    if att_url or att_data:
        dl_btn = (
            f'<a href="{att_url}" style="background:#1a62f2;color:#fff;text-decoration:none;'
            f'font-size:11px;font-weight:700;padding:8px 16px;border-radius:6px;white-space:nowrap;'
            f'letter-spacing:0.03em;">Download ↓</a>'
            if att_url else
            f'<span style="background:#e1e1e1;color:#667085;font-size:11px;font-weight:600;'
            f'padding:8px 14px;border-radius:6px;white-space:nowrap;">File attached</span>'
        )
        extra_parts.append(
            f'<div style="padding:0 44px 24px;">'
            f'<div style="border:1px solid #e1e1e1;border-radius:10px;padding:14px 18px;'
            f'background:#ffffff;display:flex;align-items:center;gap:14px;">'
            f'<div style="width:38px;height:38px;background:#f1f6fe;border-radius:8px;border:1px solid #c3e4fd;'
            f'display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0;">📎</div>'
            f'<div style="flex:1;min-width:0;">'
            f'<div style="font-size:10px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;'
            f'color:#667085;margin-bottom:3px;">Attachment</div>'
            f'<div style="font-size:13px;font-weight:600;color:#151515;white-space:nowrap;'
            f'overflow:hidden;text-overflow:ellipsis;">{att_name}</div>'
            f'</div>{dl_btn}</div></div>'
        )

    extra_imgs_html = "".join(extra_parts)

    builders = {1: _tpl_executive, 2: _tpl_minimal,
                3: _tpl_bold_blue, 4: _tpl_modern, 5: _tpl_classic,
                6: _tpl_neon, 7: _tpl_sunrise, 8: _tpl_forest, 9: _tpl_carbon,
                10: _tpl_signature, 11: _tpl_slate, 12: _tpl_premium}
    _track_rl = _track_click_url(send_id, em_b64, rl)
    _pixel    = _tracking_pixel(send_id, em_b64)
    _stars    = [_rating_url(i, send_id, em_b64) for i in range(1, 6)]
    return builders.get(template_id, _tpl_executive)(c, h, b, ss, sc, _track_rl, sq, extra_imgs_html, _pixel, _stars)


# ─── Shared helpers ───────────────────────────────────────────────────────────

def _screenshot(url, caption, wrap_css="", img_css=""):
    if not url:
        return ""
    cap = f'<p style="font-size:11px;font-style:italic;margin-top:10px;color:#9c8e80;">{caption}</p>' if caption else ""
    return f'<div style="{wrap_css}"><img src="{url}" alt="Screenshot" style="width:100%;display:block;{img_css}"/>{cap}</div>'


# ─── Template 1: Convin Dark ──────────────────────────────────────────────────

def _tpl_executive(c, h, b, ss, sc, rl, sq, extra_imgs_html="", pixel="", stars=None):
    if stars is None: stars = [f"{_BASE_URL}/?rating={i}" for i in range(1, 6)]
    css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #08080f; font-family: 'Inter', sans-serif; padding: 32px 16px 48px; }
.wrap { max-width: 600px; margin: 0 auto; background: #111111; box-shadow: 0 20px 80px rgba(0,0,0,0.7); border: 1px solid #1e1e1e; }
</style>"""
    ss_html = _screenshot(ss, sc,
        wrap_css="padding:0 44px 32px;",
        img_css="border:1px solid #2a2a2a;border-radius:6px;")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>{css}</head><body>
<div class="wrap">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#151515;border-top:3px solid #4d65ff;"><tr><td style="padding:24px 44px;font-size:16px;font-weight:700;color:#ffffff;letter-spacing:-0.01em;font-family:Arial,Helvetica,sans-serif;">Convin Data Labs</td><td align="right" style="padding:18px 44px;">{_logo(dark=True)}</td></tr></table>
  <div style="background:#0e0e0e;border-bottom:1px solid #1e1e1e;padding:10px 44px;">
    <span style="font-size:11px;color:#666;">Prepared for <strong style="color:#d2d2d2;">{c}</strong></span>
  </div>
  <div style="padding:44px 44px 36px;border-bottom:1px solid #1e1e1e;">
    <div style="font-size:10px;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;color:#4d65ff;margin-bottom:14px;">Executive Summary</div>
    <p style="font-size:14px;line-height:1.85;color:#c8c8c8;">{b}</p>
  </div>
  {ss_html}{extra_imgs_html}
  <div style="padding:40px 44px;background:#0e0e0e;border-bottom:1px solid #1e1e1e;text-align:center;">
    <div style="font-size:18px;font-weight:600;color:#ffffff;margin-bottom:24px;">Access the complete analysis</div>
    <a href="{rl}" style="display:inline-block;background:#4d65ff;color:#fff;text-decoration:none;font-size:12px;font-weight:700;letter-spacing:0.04em;text-transform:uppercase;padding:14px 40px;border-radius:6px;">Open Full Report →</a>
  </div>
  <div style="padding:28px 44px 24px;background:#151515;border-top:1px solid #1e1e1e;border-bottom:1px solid #1e1e1e;">
    <p style="font-size:13px;color:#555;margin-bottom:8px;">Warm regards,</p>
    <p style="font-size:16px;font-weight:700;color:#ffffff;margin-bottom:3px;">Convin Data Labs</p>
    <div style="width:36px;height:2px;background:#4d65ff;margin-top:12px;border-radius:2px;"></div>
  </div>
  <div style="background:#0a0a10;padding:40px 44px 44px;">
    <div style="text-align:center;padding-bottom:24px;border-bottom:1px solid #1a1a2a;margin-bottom:28px;">
      <div style="font-size:10px;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;color:#4d65ff;margin-bottom:10px;">Quick Feedback</div>
      <div style="font-size:19px;font-weight:600;color:#ffffff;margin-bottom:6px;">{sq}</div>
      <div style="font-size:12px;color:#444;">Takes 15 seconds · Helps us improve future reports.</div>
    </div>
    <div style="text-align:center;margin-bottom:10px;">
      <a href="{stars[0]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="{stars[1]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="{stars[2]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="{stars[3]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="{stars[4]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a>
    </div>
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px;"><tr><td style="font-size:10px;letter-spacing:1px;text-transform:uppercase;color:#2a2a3a;">Not useful</td><td align="right" style="font-size:10px;letter-spacing:1px;text-transform:uppercase;color:#2a2a3a;">Very useful</td></tr></table>
    <div style="text-align:center;font-size:11px;color:#444;letter-spacing:0.5px;margin-top:6px;">Click a star above to rate — opens in your browser</div>
  </div>
  <div style="padding:20px 44px;background:#0e0e0e;border-top:1px solid #1e1e1e;text-align:center;">
    <div><a href="#" style="font-size:11px;color:#444;text-decoration:none;margin:0 10px;">Unsubscribe</a><a href="#" style="font-size:11px;color:#444;text-decoration:none;margin:0 10px;">Preferences</a><a href="#" style="font-size:11px;color:#444;text-decoration:none;margin:0 10px;">Privacy</a></div>
    <div style="font-size:11px;color:#333;line-height:1.8;margin-top:8px;">Convin Data Labs · You are receiving this as a registered client.</div>
  </div>
{pixel}</div></body></html>"""


# ─── Template 2: Convin Light ─────────────────────────────────────────────────

def _tpl_minimal(c, h, b, ss, sc, rl, sq, extra_imgs_html="", pixel="", stars=None):
    if stars is None: stars = [f"{_BASE_URL}/?rating={i}" for i in range(1, 6)]
    css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #eef0ff; font-family: 'Inter', sans-serif; color: #151515; padding: 32px 16px 48px; }
.wrap { max-width: 600px; margin: 0 auto; background: #fff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 32px rgba(77,101,255,0.12); border: 1px solid #dde0ff; }
</style>"""
    ss_html = _screenshot(ss, sc,
        wrap_css="padding:0 40px 32px;",
        img_css="border-radius:10px;border:1px solid #dde0ff;")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>{css}</head><body>
<div class="wrap">
  <table width="100%" cellpadding="0" cellspacing="0" style="border-bottom:1px solid #f0f1ff;"><tr><td style="padding:20px 40px;">
    <table cellpadding="0" cellspacing="0"><tr>
      <td style="width:4px;background:#4d65ff;border-radius:4px;padding:14px 0;">&nbsp;</td>
      <td style="padding-left:10px;font-size:15px;font-weight:700;color:#151515;letter-spacing:-0.01em;font-family:Arial,Helvetica,sans-serif;">Convin Data Labs</td>
    </tr></table>
  </td><td align="right" style="padding:16px 40px;">{_logo(dark=False)}</td></tr></table>
  <div style="padding:8px 40px;background:#f7f8ff;border-bottom:1px solid #eef0ff;">
    <span style="font-size:11px;color:#888;">Prepared for <strong style="color:#151515;">{c}</strong></span>
  </div>
  <div style="padding:48px 40px 40px;border-bottom:1px solid #f0f1ff;">
    <p style="font-size:14px;line-height:1.85;color:#444;">{b}</p>
  </div>
  {ss_html}{extra_imgs_html}
  <div style="padding:36px 40px;background:#f7f8ff;border-bottom:1px solid #eef0ff;text-align:center;">
    <a href="{rl}" style="display:inline-block;background:#4d65ff;color:#fff;text-decoration:none;font-size:12px;font-weight:600;padding:14px 42px;border-radius:10px;letter-spacing:0.01em;">Open Full Report →</a>
  </div>
  <div style="padding:28px 40px 24px;border-bottom:1px solid #f0f1ff;">
    <p style="font-size:13px;color:#aaa;margin-bottom:8px;">Best regards,</p>
    <p style="font-size:16px;font-weight:700;color:#151515;letter-spacing:-0.01em;margin-bottom:3px;">Convin Data Labs</p>
  </div>
  <div style="padding:36px 40px;border-bottom:1px solid #f0f1ff;">
    <div style="text-align:center;margin-bottom:20px;">
      <div style="font-size:10px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#4d65ff;margin-bottom:10px;">Quick Feedback</div>
      <div style="font-size:19px;font-weight:600;color:#151515;margin-bottom:6px;">{sq}</div>
      <div style="font-size:12px;color:#aaa;">Takes 15 seconds · Helps us improve.</div>
    </div>
    <div style="text-align:center;margin-bottom:8px;">
      <a href="{stars[0]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="{stars[1]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="{stars[2]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="{stars[3]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="{stars[4]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a>
    </div>
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;"><tr><td style="font-size:11px;color:#d2d2d2;">Not useful</td><td align="right" style="font-size:11px;color:#d2d2d2;">Very useful</td></tr></table>
    <div style="text-align:center;font-size:11px;color:#aaa;margin-top:6px;">Click a star above to rate — opens in your browser</div>
  </div>
  <div style="padding:20px 40px;text-align:center;background:#f7f8ff;">
    <div><a href="#" style="font-size:11px;color:#aaa;text-decoration:none;margin:0 10px;">Unsubscribe</a><a href="#" style="font-size:11px;color:#aaa;text-decoration:none;margin:0 10px;">Preferences</a><a href="#" style="font-size:11px;color:#aaa;text-decoration:none;margin:0 10px;">Privacy</a></div>
    <div style="font-size:11px;color:#ccc;margin-top:8px;">Convin Data Labs · Registered client communication.</div>
  </div>
{pixel}</div></body></html>"""


# ─── Template 3: Convin Bold ──────────────────────────────────────────────────

def _tpl_bold_blue(c, h, b, ss, sc, rl, sq, extra_imgs_html="", pixel="", stars=None):
    if stars is None: stars = [f"{_BASE_URL}/?rating={i}" for i in range(1, 6)]
    css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap');
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #4d65ff; font-family: 'Inter', sans-serif; color: #151515; padding: 32px 16px 48px; }
.wrap { max-width: 600px; margin: 0 auto; background: #fff; box-shadow: 0 24px 80px rgba(77,101,255,0.4); }
</style>"""
    ss_html = _screenshot(ss, sc,
        wrap_css="padding:0 44px 36px;",
        img_css="border:2px solid #dde0ff;border-radius:6px;")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>{css}</head><body>
<div class="wrap">
  <div style="background:#4d65ff;padding:20px 44px;">
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
      <td valign="middle">
        <div style="font-size:18px;font-weight:800;color:#fff;letter-spacing:-0.01em;margin-bottom:3px;">Convin Data Labs</div>
        <div style="font-size:11px;color:rgba(255,255,255,0.55);font-weight:500;">Analytics · Report Delivery</div>
      </td>
      <td align="right" valign="middle" style="padding-left:16px;">{_logo(dark=True)}</td>
    </tr></table>
  </div>
  <div style="background:#f7f8ff;padding:10px 44px;border-bottom:2px solid #dde0ff;">
    <span style="font-size:11px;color:#4d65ff;font-weight:600;">FOR: <span style="color:#151515;">{c}</span></span>
  </div>
  <div style="padding:52px 44px 44px;border-bottom:1px solid #f0f1ff;">
    <div style="font-size:11px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:#4d65ff;margin-bottom:16px;">Executive Summary</div>
    <p style="font-size:15px;line-height:1.8;color:#444;">{b}</p>
  </div>
  {ss_html}{extra_imgs_html}
  <div style="padding:40px 44px;text-align:center;border-bottom:1px solid #f0f1ff;background:#f7f8ff;">
    <div style="font-size:20px;font-weight:700;color:#151515;margin-bottom:24px;">Access the complete report</div>
    <a href="{rl}" style="display:inline-block;background:#151515;color:#fff;text-decoration:none;font-size:13px;font-weight:700;padding:16px 48px;border-radius:6px;letter-spacing:0.03em;">Open Full Report →</a>
  </div>
  <div style="padding:28px 44px 24px;background:#f7f8ff;border-bottom:2px solid #dde0ff;">
    <p style="font-size:13px;color:#888;margin-bottom:8px;">Best regards,</p>
    <p style="font-size:17px;font-weight:800;color:#151515;letter-spacing:-0.02em;margin-bottom:3px;">Convin Data Labs</p>
  </div>
  <div style="background:#4d65ff;padding:40px 44px 44px;">
    <div style="text-align:center;padding-bottom:24px;border-bottom:1px solid rgba(255,255,255,0.15);margin-bottom:28px;">
      <div style="font-size:10px;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;color:rgba(255,255,255,0.6);margin-bottom:10px;">Quick Feedback</div>
      <div style="font-size:20px;font-weight:700;color:#fff;margin-bottom:6px;">{sq}</div>
      <div style="font-size:12px;color:rgba(255,255,255,0.45);">Takes 15 seconds · Helps us improve.</div>
    </div>
    <div style="text-align:center;margin-bottom:8px;">
      <a href="{stars[0]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="{stars[1]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="{stars[2]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="{stars[3]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="{stars[4]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a>
    </div>
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;"><tr><td style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:rgba(255,255,255,0.25);">Not useful</td><td align="right" style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:rgba(255,255,255,0.25);">Very useful</td></tr></table>
    <div style="text-align:center;font-size:11px;color:rgba(255,255,255,0.4);margin-top:6px;">Click a star above to rate — opens in your browser</div>
  </div>
  <div style="padding:22px 44px;background:#f7f8ff;text-align:center;border-top:2px solid #dde0ff;">
    <div><a href="#" style="font-size:11px;color:#4d65ff;text-decoration:none;margin:0 10px;">Unsubscribe</a><a href="#" style="font-size:11px;color:#4d65ff;text-decoration:none;margin:0 10px;">Preferences</a><a href="#" style="font-size:11px;color:#4d65ff;text-decoration:none;margin:0 10px;">Privacy</a></div>
    <div style="font-size:11px;color:#bbb;margin-top:8px;">Convin Data Labs · Registered client communication.</div>
  </div>
{pixel}</div></body></html>"""


# ─── Template 4: Convin Pro ───────────────────────────────────────────────────

def _tpl_modern(c, h, b, ss, sc, rl, sq, extra_imgs_html="", pixel="", stars=None):
    if stars is None: stars = [f"{_BASE_URL}/?rating={i}" for i in range(1, 6)]
    css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #05050f; font-family: 'Inter', sans-serif; padding: 32px 16px 48px; }
.wrap { max-width: 600px; margin: 0 auto; background: #0e0e1e; border-radius: 20px; overflow: hidden; box-shadow: 0 24px 80px rgba(77,101,255,0.2); border: 1px solid #1a1a30; }
</style>"""
    ss_html = _screenshot(ss, sc,
        wrap_css="padding:0 40px 32px;",
        img_css="border-radius:10px;border:1px solid #1a1a30;")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>{css}</head><body>
<div class="wrap">
  <div style="background:linear-gradient(135deg,#151528 0%,#1a1a3a 60%,#1e1e48 100%);padding:24px 40px;border-bottom:2px solid #4d65ff;">
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
      <td valign="middle">
        <div style="font-size:13px;font-weight:700;color:#4d65ff;letter-spacing:2.5px;text-transform:uppercase;margin-bottom:4px;">Convin Data Labs</div>
        <div style="font-size:11px;color:rgba(77,101,255,0.4);font-weight:400;">Analytics Intelligence · Report</div>
      </td>
      <td align="right" valign="middle" style="padding-left:16px;">{_logo(dark=True)}</td>
    </tr></table>
  </div>
  <div style="padding:10px 40px;background:#0a0a18;border-bottom:1px solid #1a1a30;">
    <span style="font-size:11px;color:#444;">For <span style="color:#4d65ff;font-weight:600;">{c}</span></span>
  </div>
  <div style="padding:44px 40px 36px;border-bottom:1px solid #1a1a30;background:#0e0e1e;">
    <div style="display:inline-block;font-size:9px;font-weight:700;letter-spacing:0.15em;text-transform:uppercase;color:#4d65ff;background:rgba(77,101,255,0.08);border:1px solid rgba(77,101,255,0.2);padding:4px 12px;border-radius:99px;margin-bottom:20px;">Executive Summary</div>
    <p style="font-size:14px;line-height:1.85;color:#888;">{b}</p>
  </div>
  {ss_html}{extra_imgs_html}
  <div style="padding:36px 40px;background:#0a0a18;border-bottom:1px solid #1a1a30;text-align:center;">
    <a href="{rl}" style="display:inline-block;background:#4d65ff;color:#fff;text-decoration:none;font-size:12px;font-weight:600;padding:14px 44px;border-radius:10px;letter-spacing:0.03em;box-shadow:0 4px 24px rgba(77,101,255,0.4);">Open Full Report →</a>
  </div>
  <div style="padding:28px 40px 24px;background:#0a0a18;border-top:1px solid #1a1a30;border-bottom:1px solid #1a1a30;">
    <p style="font-size:13px;color:#444;margin-bottom:8px;">Warm regards,</p>
    <p style="font-size:16px;font-weight:700;color:#ffffff;letter-spacing:-0.01em;margin-bottom:3px;">Convin Data Labs</p>
  </div>
  <div style="background:#07071a;padding:40px 40px 44px;border-top:1px solid #1a1a30;">
    <div style="text-align:center;padding-bottom:24px;border-bottom:1px solid #1a1a30;margin-bottom:28px;">
      <div style="font-size:9px;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;color:#4d65ff;margin-bottom:10px;">Quick Feedback</div>
      <div style="font-size:19px;font-weight:600;color:#d2d2d2;margin-bottom:6px;">{sq}</div>
      <div style="font-size:12px;color:#333;">Takes 15 seconds · Helps us improve.</div>
    </div>
    <div style="text-align:center;margin-bottom:8px;">
      <a href="{stars[0]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="{stars[1]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="{stars[2]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="{stars[3]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="{stars[4]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a>
    </div>
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;"><tr><td style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:#1a1a30;">Not useful</td><td align="right" style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:#1a1a30;">Very useful</td></tr></table>
    <div style="text-align:center;font-size:11px;color:#333;margin-top:6px;">Click a star above to rate — opens in your browser</div>
  </div>
  <div style="padding:20px 40px;background:#07071a;text-align:center;border-top:1px solid #1a1a30;">
    <div><a href="#" style="font-size:11px;color:#333;text-decoration:none;margin:0 10px;">Unsubscribe</a><a href="#" style="font-size:11px;color:#333;text-decoration:none;margin:0 10px;">Preferences</a><a href="#" style="font-size:11px;color:#333;text-decoration:none;margin:0 10px;">Privacy</a></div>
    <div style="font-size:11px;color:#222;margin-top:6px;">Convin Data Labs · Registered client communication.</div>
  </div>
{pixel}</div></body></html>"""


# ─── Template 5: Classic ──────────────────────────────────────────────────────

def _tpl_classic(c, h, b, ss, sc, rl, sq, extra_imgs_html="", pixel="", stars=None):
    if stars is None: stars = [f"{_BASE_URL}/?rating={i}" for i in range(1, 6)]
    css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=Lora:wght@400;500;600&display=swap');
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #f0e6d3; font-family: 'Lora', Georgia, serif; color: #1a0a00; padding: 32px 16px 48px; }
.wrap { max-width: 600px; margin: 0 auto; background: #fffef9; border: 1px solid #d5c4a8; box-shadow: 0 4px 24px rgba(100,60,0,0.1); }
.star { font-size: 28px; cursor: pointer; color: #d5c4a8; margin: 0 4px; display: inline-block; transition: color 0.12s; user-select: none; }
.orn { color: #c9a96e; text-align: center; letter-spacing: 8px; font-size: 14px; }
</style>"""
    ss_html = _screenshot(ss, sc,
        wrap_css="padding:0 48px 36px;",
        img_css="border:1px solid #d5c4a8;",
    )
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>{css}</head><body>
<div class="wrap">
  <div style="background:#2c1a0e;padding:18px 48px;">
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
      <td width="1">&nbsp;</td>
      <td valign="middle" style="text-align:center;">
        <div style="font-family:'Playfair Display',serif;font-size:13px;color:#c9a96e;letter-spacing:5px;text-transform:uppercase;margin-bottom:4px;">Convin Data Labs</div>
        <div class="orn">· · ·</div>
        <div style="font-size:10px;color:rgba(201,169,110,0.5);letter-spacing:3px;text-transform:uppercase;margin-top:4px;">Analytics &amp; Reports</div>
      </td>
      <td align="right" valign="middle" width="80" style="padding-left:16px;">{_logo(dark=True)}</td>
    </tr></table>
  </div>
  <div style="background:#faf5ed;border-bottom:1px solid #d5c4a8;padding:10px 48px;text-align:center;">
    <span style="font-size:11px;color:#8b7355;font-style:italic;">Prepared for <strong style="color:#2c1a0e;font-style:normal;">{c}</strong></span>
  </div>
  <div style="padding:48px 48px 40px;border-bottom:1px solid #d5c4a8;">
    <div style="font-size:11px;color:#c9a96e;font-style:italic;letter-spacing:0.05em;margin-bottom:14px;text-align:center;">Executive Summary</div>
    <p style="font-size:14px;line-height:1.95;color:#3d2b1f;text-align:justify;">{b}</p>
  </div>
  {ss_html}{extra_imgs_html}
  <div style="padding:36px 48px;background:#faf5ed;border-bottom:1px solid #d5c4a8;text-align:center;">
    <a href="{rl}" style="display:inline-block;border:1.5px solid #2c1a0e;color:#2c1a0e;text-decoration:none;font-family:'Playfair Display',serif;font-size:13px;padding:12px 40px;letter-spacing:0.04em;">Open Full Report</a>
  </div>
  <div style="padding:32px 48px 28px;border-bottom:1px solid #d5c4a8;">
    <p style="font-size:14px;color:#8b7355;font-style:italic;margin-bottom:10px;">Warm regards,</p>
    <p style="font-family:'Playfair Display',serif;font-size:18px;color:#2c1a0e;margin-bottom:4px;">Convin Data Labs</p>
    <div style="width:48px;height:1px;background:#c9a96e;margin-top:16px;"></div>
  </div>
  <div style="padding:36px 48px;border-bottom:1px solid #d5c4a8;">
    <div style="text-align:center;margin-bottom:22px;">
      <div style="font-size:10px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:#c9a96e;margin-bottom:10px;">Quick Feedback</div>
      <div style="font-family:'Playfair Display',serif;font-size:19px;color:#1a0a00;margin-bottom:6px;font-style:italic;">{sq}</div>
      <div style="font-size:12px;color:#8b7355;">Takes 15 seconds · Helps us improve.</div>
    </div>
    <div style="text-align:center;margin-bottom:8px;">
      <a href="{stars[0]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="{stars[1]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="{stars[2]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="{stars[3]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="{stars[4]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a>
    </div>
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;"><tr><td style="font-size:11px;color:#d5c4a8;">Not useful</td><td align="right" style="font-size:11px;color:#d5c4a8;">Very useful</td></tr></table>
    <div style="text-align:center;font-size:11px;color:#9c8e80;font-style:italic;font-family:'Lora',serif;margin-top:6px;">Click a star above to rate — opens in your browser</div>
  </div>
  <div style="padding:20px 48px;background:#faf5ed;text-align:center;">
    <div class="orn" style="font-size:12px;margin-bottom:10px;">· · ·</div>
    <div><a href="#" style="font-size:11px;color:#8b7355;text-decoration:none;margin:0 10px;">Unsubscribe</a><a href="#" style="font-size:11px;color:#8b7355;text-decoration:none;margin:0 10px;">Preferences</a><a href="#" style="font-size:11px;color:#8b7355;text-decoration:none;margin:0 10px;">Privacy</a></div>
    <div style="font-size:11px;color:#c9a96e;margin-top:8px;">Convin Data Labs · Registered client communication.</div>
  </div>
{pixel}</div></body></html>"""


# ─── Template 6: Neon ─────────────────────────────────────────────────────────

def _tpl_neon(c, h, b, ss, sc, rl, sq, extra_imgs_html="", pixel="", stars=None):
    if stars is None: stars = [f"{_BASE_URL}/?rating={i}" for i in range(1, 6)]
    css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #020a12; font-family: 'Inter', sans-serif; padding: 32px 16px 48px; }
.wrap { max-width: 600px; margin: 0 auto; background: #040d18; border: 1px solid #0c2a3a; border-radius: 16px; overflow: hidden; box-shadow: 0 0 60px rgba(6,182,212,0.08), 0 24px 80px rgba(0,0,0,0.7); }
.star { font-size: 28px; cursor: pointer; color: #0c2a3a; margin: 0 4px; display: inline-block; transition: color 0.12s, text-shadow 0.12s; user-select: none; }
</style>"""
    ss_html = _screenshot(ss, sc,
        wrap_css="padding:0 40px 32px;",
        img_css="border-radius:10px;border:1px solid #0c2a3a;")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>{css}</head><body>
<div class="wrap">
  <div style="background:linear-gradient(135deg,#040d18 0%,#061a28 100%);padding:28px 40px;border-bottom:1px solid #06b6d4;position:relative;overflow:hidden;">
    <div style="position:absolute;top:-40px;right:-40px;width:180px;height:180px;background:radial-gradient(circle,rgba(6,182,212,0.12) 0%,transparent 70%);pointer-events:none;"></div>
    <div style="position:absolute;top:20px;right:24px;z-index:2;">{_logo(dark=True, h=24)}</div>
    <div style="font-size:15px;font-weight:800;color:#06b6d4;letter-spacing:3px;text-transform:uppercase;text-shadow:0 0 20px rgba(6,182,212,0.5);margin-bottom:3px;">Convin Data Labs</div>
    <div style="font-size:11px;color:rgba(6,182,212,0.35);font-weight:400;letter-spacing:1.5px;text-transform:uppercase;">Analytics · Report Delivery</div>
  </div>
  <div style="padding:8px 40px;background:#030b14;border-bottom:1px solid #0c2a3a;">
    <span style="font-size:11px;color:#164e63;">For <span style="color:#06b6d4;font-weight:600;">{c}</span></span>
  </div>
  <div style="padding:44px 40px 36px;border-bottom:1px solid #0c2a3a;">
    <div style="display:inline-block;font-size:9px;font-weight:700;letter-spacing:0.15em;text-transform:uppercase;color:#06b6d4;background:rgba(6,182,212,0.06);border:1px solid rgba(6,182,212,0.2);padding:4px 12px;border-radius:99px;margin-bottom:20px;">Executive Summary</div>
    <p style="font-size:14px;line-height:1.85;color:#475569;">{b}</p>
  </div>
  {ss_html}{extra_imgs_html}
  <div style="padding:36px 40px;background:#030b14;border-bottom:1px solid #0c2a3a;text-align:center;">
    <a href="{rl}" style="display:inline-block;background:transparent;border:1.5px solid #06b6d4;color:#06b6d4;text-decoration:none;font-size:12px;font-weight:700;padding:13px 44px;border-radius:8px;letter-spacing:0.06em;text-transform:uppercase;box-shadow:0 0 16px rgba(6,182,212,0.2);">Open Full Report →</a>
  </div>
  <div style="padding:26px 40px 22px;background:#030b14;border-bottom:1px solid #0c2a3a;">
    <p style="font-size:13px;color:#164e63;margin-bottom:8px;">Best regards,</p>
    <p style="font-size:16px;font-weight:700;color:#e0f7fa;letter-spacing:-0.01em;margin-bottom:3px;">Convin Data Labs</p>
  </div>
  <div style="background:#020a12;padding:38px 40px 42px;border-top:1px solid #0c2a3a;">
    <div style="text-align:center;padding-bottom:22px;border-bottom:1px solid #0c2a3a;margin-bottom:26px;">
      <div style="font-size:9px;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;color:#06b6d4;margin-bottom:10px;">Quick Feedback</div>
      <div style="font-size:19px;font-weight:600;color:#e0f7fa;margin-bottom:6px;">{sq}</div>
      <div style="font-size:12px;color:#164e63;">Takes 15 seconds · Helps us improve.</div>
    </div>
    <div style="text-align:center;margin-bottom:8px;">
      <a href="{stars[0]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="{stars[1]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="{stars[2]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="{stars[3]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="{stars[4]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a>
    </div>
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;"><tr><td style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:#0c2a3a;">Not useful</td><td align="right" style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:#0c2a3a;">Very useful</td></tr></table>
    <div style="text-align:center;font-size:11px;color:rgba(6,182,212,0.4);letter-spacing:0.5px;margin-top:6px;">Click a star above to rate — opens in your browser</div>
  </div>
  <div style="padding:18px 40px;background:#020a12;text-align:center;border-top:1px solid #0c2a3a;">
    <div><a href="#" style="font-size:11px;color:#164e63;text-decoration:none;margin:0 10px;">Unsubscribe</a><a href="#" style="font-size:11px;color:#164e63;text-decoration:none;margin:0 10px;">Preferences</a><a href="#" style="font-size:11px;color:#164e63;text-decoration:none;margin:0 10px;">Privacy</a></div>
    <div style="font-size:11px;color:#0c2a3a;margin-top:6px;">Convin Data Labs · Registered client communication.</div>
  </div>
{pixel}</div></body></html>"""


# ─── Template 7: Sunrise ──────────────────────────────────────────────────────

def _tpl_sunrise(c, h, b, ss, sc, rl, sq, extra_imgs_html="", pixel="", stars=None):
    if stars is None: stars = [f"{_BASE_URL}/?rating={i}" for i in range(1, 6)]
    css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Poppins:wght@600;700;800&display=swap');
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #fde8d0; font-family: 'Inter', sans-serif; padding: 32px 16px 48px; }
.wrap { max-width: 600px; margin: 0 auto; background: #fff; border-radius: 20px; overflow: hidden; box-shadow: 0 8px 40px rgba(234,88,12,0.12); }
.star { font-size: 28px; cursor: pointer; color: #fde8d0; margin: 0 4px; display: inline-block; transition: color 0.12s; user-select: none; }
</style>"""
    ss_html = _screenshot(ss, sc,
        wrap_css="padding:0 44px 32px;",
        img_css="border-radius:12px;border:1px solid #fed7aa;")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>{css}</head><body>
<div class="wrap">
  <div style="background:linear-gradient(135deg,#ea580c 0%,#f97316 50%,#fb923c 100%);padding:30px 44px;position:relative;overflow:hidden;">
    <div style="position:absolute;top:-30px;right:-30px;width:160px;height:160px;background:rgba(255,255,255,0.1);border-radius:50%;pointer-events:none;"></div>
    <div style="position:absolute;bottom:-50px;left:-20px;width:200px;height:200px;background:rgba(255,255,255,0.06);border-radius:50%;pointer-events:none;"></div>
    <div style="position:absolute;top:20px;right:24px;z-index:2;">{_logo(dark=True, h=24)}</div>
    <div style="font-family:'Poppins',sans-serif;font-size:16px;font-weight:800;color:#fff;letter-spacing:1px;margin-bottom:3px;position:relative;">Convin Data Labs</div>
    <div style="font-size:11px;color:rgba(255,255,255,0.65);position:relative;">Analytics · Report Delivery</div>
  </div>
  <div style="padding:10px 44px;background:#fff8f3;border-bottom:1px solid #fed7aa;">
    <span style="font-size:11px;color:#c2410c;">Report for <strong style="color:#ea580c;">{c}</strong></span>
  </div>
  <div style="padding:48px 44px 40px;border-bottom:1px solid #fde8d0;">
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:18px;">
      <div style="width:4px;height:32px;background:linear-gradient(180deg,#f97316,#fb923c);border-radius:4px;"></div>
      <div style="font-size:10px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:#c2410c;">Executive Summary</div>
    </div>
    <p style="font-size:14px;line-height:1.85;color:#57534e;">{b}</p>
  </div>
  {ss_html}{extra_imgs_html}
  <div style="padding:36px 44px;background:#fff8f3;border-bottom:1px solid #fde8d0;text-align:center;">
    <a href="{rl}" style="display:inline-block;background:linear-gradient(135deg,#ea580c,#f97316);color:#fff;text-decoration:none;font-size:13px;font-weight:700;padding:14px 44px;border-radius:12px;letter-spacing:0.02em;box-shadow:0 4px 20px rgba(234,88,12,0.3);">Open Full Report →</a>
  </div>
  <div style="padding:28px 44px 24px;border-bottom:1px solid #fde8d0;">
    <p style="font-size:13px;color:#a8a29e;margin-bottom:8px;">Warm regards,</p>
    <p style="font-family:'Poppins',sans-serif;font-size:17px;font-weight:700;color:#1c0a00;margin-bottom:3px;">Convin Data Labs</p>
  </div>
  <div style="background:linear-gradient(135deg,#ea580c 0%,#f97316 100%);padding:38px 44px 42px;">
    <div style="text-align:center;padding-bottom:22px;border-bottom:1px solid rgba(255,255,255,0.15);margin-bottom:26px;">
      <div style="font-size:9px;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;color:rgba(255,255,255,0.7);margin-bottom:10px;">Quick Feedback</div>
      <div style="font-size:20px;font-weight:700;color:#fff;margin-bottom:6px;">{sq}</div>
      <div style="font-size:12px;color:rgba(255,255,255,0.5);">Takes 15 seconds · Helps us improve.</div>
    </div>
    <div style="text-align:center;margin-bottom:8px;">
      <a href="{stars[0]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="{stars[1]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="{stars[2]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="{stars[3]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="{stars[4]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a>
    </div>
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;"><tr><td style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:rgba(255,255,255,0.3);">Not useful</td><td align="right" style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:rgba(255,255,255,0.3);">Very useful</td></tr></table>
    <div style="text-align:center;font-size:11px;color:rgba(255,255,255,0.5);margin-top:6px;">Click a star above to rate — opens in your browser</div>
  </div>
  <div style="padding:18px 44px;background:#fff8f3;text-align:center;border-top:1px solid #fde8d0;">
    <div><a href="#" style="font-size:11px;color:#c2410c;text-decoration:none;margin:0 10px;">Unsubscribe</a><a href="#" style="font-size:11px;color:#c2410c;text-decoration:none;margin:0 10px;">Preferences</a><a href="#" style="font-size:11px;color:#c2410c;text-decoration:none;margin:0 10px;">Privacy</a></div>
    <div style="font-size:11px;color:#fed7aa;margin-top:8px;">Convin Data Labs · Registered client communication.</div>
  </div>
{pixel}</div></body></html>"""


# ─── Template 8: Forest ───────────────────────────────────────────────────────

def _tpl_forest(c, h, b, ss, sc, rl, sq, extra_imgs_html="", pixel="", stars=None):
    if stars is None: stars = [f"{_BASE_URL}/?rating={i}" for i in range(1, 6)]
    css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #071a0e; font-family: 'Inter', sans-serif; padding: 32px 16px 48px; }
.wrap { max-width: 600px; margin: 0 auto; background: #0b1f14; border: 1px solid #132e1c; border-radius: 18px; overflow: hidden; box-shadow: 0 24px 80px rgba(0,0,0,0.6); }
.star { font-size: 28px; cursor: pointer; color: #132e1c; margin: 0 4px; display: inline-block; transition: color 0.12s; user-select: none; }
</style>"""
    ss_html = _screenshot(ss, sc,
        wrap_css="padding:0 44px 32px;",
        img_css="border-radius:10px;border:1px solid #132e1c;")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>{css}</head><body>
<div class="wrap">
  <div style="background:linear-gradient(135deg,#052e16 0%,#064e23 60%,#065f2c 100%);padding:28px 44px;border-bottom:1px solid #10b981;position:relative;overflow:hidden;">
    <div style="position:absolute;top:-40px;right:-30px;width:160px;height:160px;background:radial-gradient(circle,rgba(16,185,129,0.1) 0%,transparent 70%);pointer-events:none;"></div>
    <div style="position:absolute;top:20px;right:24px;z-index:2;">{_logo(dark=True, h=24)}</div>
    <div style="font-size:15px;font-weight:800;color:#6ee7b7;letter-spacing:2px;text-transform:uppercase;margin-bottom:3px;">Convin Data Labs</div>
    <div style="font-size:11px;color:rgba(110,231,183,0.35);letter-spacing:1px;text-transform:uppercase;">Analytics · Report</div>
  </div>
  <div style="padding:8px 44px;background:#071a0e;border-bottom:1px solid #132e1c;">
    <span style="font-size:11px;color:#166534;">For <span style="color:#10b981;font-weight:600;">{c}</span></span>
  </div>
  <div style="padding:44px 44px 36px;border-bottom:1px solid #132e1c;">
    <div style="display:inline-block;font-size:9px;font-weight:700;letter-spacing:0.15em;text-transform:uppercase;color:#10b981;background:rgba(16,185,129,0.06);border:1px solid rgba(16,185,129,0.18);padding:4px 12px;border-radius:99px;margin-bottom:20px;">Executive Summary</div>
    <p style="font-size:14px;line-height:1.85;color:#4b7a5e;">{b}</p>
  </div>
  {ss_html}{extra_imgs_html}
  <div style="padding:36px 44px;background:#071a0e;border-bottom:1px solid #132e1c;text-align:center;">
    <a href="{rl}" style="display:inline-block;background:linear-gradient(135deg,#059669,#10b981);color:#fff;text-decoration:none;font-size:12px;font-weight:700;padding:14px 44px;border-radius:10px;letter-spacing:0.04em;box-shadow:0 4px 20px rgba(16,185,129,0.25);">Open Full Report →</a>
  </div>
  <div style="padding:26px 44px 22px;background:#071a0e;border-bottom:1px solid #132e1c;">
    <p style="font-size:13px;color:#166534;margin-bottom:8px;">Warm regards,</p>
    <p style="font-size:16px;font-weight:700;color:#ecfdf5;letter-spacing:-0.01em;margin-bottom:3px;">Convin Data Labs</p>
  </div>
  <div style="background:#040f08;padding:38px 44px 42px;border-top:1px solid #132e1c;">
    <div style="text-align:center;padding-bottom:22px;border-bottom:1px solid #132e1c;margin-bottom:26px;">
      <div style="font-size:9px;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;color:#10b981;margin-bottom:10px;">Quick Feedback</div>
      <div style="font-size:19px;font-weight:600;color:#d1fae5;margin-bottom:6px;">{sq}</div>
      <div style="font-size:12px;color:#1a3a24;">Takes 15 seconds · Helps us improve.</div>
    </div>
    <div style="text-align:center;margin-bottom:8px;">
      <a href="{stars[0]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="{stars[1]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="{stars[2]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="{stars[3]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="{stars[4]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a>
    </div>
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;"><tr><td style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:#132e1c;">Not useful</td><td align="right" style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:#132e1c;">Very useful</td></tr></table>
    <div style="text-align:center;font-size:11px;color:rgba(16,185,129,0.4);margin-top:6px;">Click a star above to rate — opens in your browser</div>
  </div>
  <div style="padding:18px 44px;background:#040f08;text-align:center;border-top:1px solid #132e1c;">
    <div><a href="#" style="font-size:11px;color:#166534;text-decoration:none;margin:0 10px;">Unsubscribe</a><a href="#" style="font-size:11px;color:#166534;text-decoration:none;margin:0 10px;">Preferences</a><a href="#" style="font-size:11px;color:#166534;text-decoration:none;margin:0 10px;">Privacy</a></div>
    <div style="font-size:11px;color:#132e1c;margin-top:6px;">Convin Data Labs · Registered client communication.</div>
  </div>
{pixel}</div></body></html>"""


# ─── Template 9: Carbon ───────────────────────────────────────────────────────

def _tpl_carbon(c, h, b, ss, sc, rl, sq, extra_imgs_html="", pixel="", stars=None):
    if stars is None: stars = [f"{_BASE_URL}/?rating={i}" for i in range(1, 6)]
    css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #111; font-family: 'Inter', sans-serif; padding: 32px 16px 48px; }
.wrap { max-width: 600px; margin: 0 auto; background: #1a1a1a; overflow: hidden; box-shadow: 0 24px 80px rgba(0,0,0,0.7); }
.star { font-size: 28px; cursor: pointer; color: #333; margin: 0 4px; display: inline-block; transition: color 0.12s; user-select: none; }
</style>"""
    ss_html = _screenshot(ss, sc,
        wrap_css="padding:0 44px 32px;",
        img_css="border:2px solid #2a2a2a;")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>{css}</head><body>
<div class="wrap">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#111;border-bottom:3px solid #f97316;"><tr><td style="padding:24px 44px;">
    <div style="font-size:16px;font-weight:800;color:#fff;letter-spacing:2px;text-transform:uppercase;margin-bottom:2px;font-family:Arial,Helvetica,sans-serif;">Convin Data Labs</div>
    <div style="font-size:10px;color:#444;letter-spacing:2px;text-transform:uppercase;font-family:Arial,Helvetica,sans-serif;">Analytics · Report</div>
  </td><td align="right" style="padding:18px 44px;">{_logo(dark=True)}</td></tr></table>
  <div style="padding:8px 44px;background:#141414;border-bottom:1px solid #222;">
    <span style="font-size:11px;color:#555;">Prepared for <span style="color:#f97316;font-weight:600;">{c}</span></span>
  </div>
  <div style="padding:48px 44px 40px;border-bottom:1px solid #222;">
    <div style="font-size:10px;font-weight:700;letter-spacing:0.15em;text-transform:uppercase;color:#f97316;margin-bottom:16px;">Executive Summary</div>
    <p style="font-size:14px;line-height:1.85;color:#888;">{b}</p>
  </div>
  {ss_html}{extra_imgs_html}
  <div style="padding:38px 44px;background:#141414;border-bottom:1px solid #222;text-align:center;">
    <a href="{rl}" style="display:inline-block;background:#f97316;color:#fff;text-decoration:none;font-size:13px;font-weight:700;padding:15px 48px;letter-spacing:0.04em;text-transform:uppercase;">Open Report →</a>
  </div>
  <div style="padding:28px 44px 24px;background:#141414;border-bottom:1px solid #222;">
    <p style="font-size:13px;color:#444;margin-bottom:8px;">Best regards,</p>
    <p style="font-size:17px;font-weight:800;color:#fff;letter-spacing:-0.02em;margin-bottom:3px;">Convin Data Labs</p>
  </div>
  <div style="background:#111;padding:38px 44px 42px;border-top:1px solid #222;">
    <div style="text-align:center;padding-bottom:22px;border-bottom:1px solid #222;margin-bottom:26px;">
      <div style="font-size:9px;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;color:#f97316;margin-bottom:10px;">Quick Feedback</div>
      <div style="font-size:20px;font-weight:700;color:#fff;margin-bottom:6px;">{sq}</div>
      <div style="font-size:12px;color:#333;">Takes 15 seconds · Helps us improve.</div>
    </div>
    <div style="text-align:center;margin-bottom:8px;">
      <a href="{stars[0]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="{stars[1]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="{stars[2]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="{stars[3]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="{stars[4]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a>
    </div>
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;"><tr><td style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:#2a2a2a;">Not useful</td><td align="right" style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:#2a2a2a;">Very useful</td></tr></table>
    <div style="text-align:center;font-size:11px;color:#555;margin-top:6px;">Click a star above to rate — opens in your browser</div>
  </div>
  <div style="padding:18px 44px;background:#141414;text-align:center;border-top:1px solid #222;">
    <div><a href="#" style="font-size:11px;color:#444;text-decoration:none;margin:0 10px;">Unsubscribe</a><a href="#" style="font-size:11px;color:#444;text-decoration:none;margin:0 10px;">Preferences</a><a href="#" style="font-size:11px;color:#444;text-decoration:none;margin:0 10px;">Privacy</a></div>
    <div style="font-size:11px;color:#2a2a2a;margin-top:6px;">Convin Data Labs · Registered client communication.</div>
  </div>
{pixel}</div></body></html>"""


# ── Template 10 · Convin Signature ──────────────────────────────────────────
def _tpl_signature(c, h, b, ss, sc, rl, sq, extra_imgs_html="", pixel="", stars=None):
    if stars is None: stars = [f"{_BASE_URL}/?rating={i}" for i in range(1, 6)]
    css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #f9f9f9; font-family: 'Inter', sans-serif; padding: 32px 16px 48px; }
.wrap { max-width: 600px; margin: 0 auto; background: #fff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 32px rgba(210,44,132,0.1); border: 1px solid #f0e8f8; }
</style>"""
    ss_html = _screenshot(ss, sc,
        wrap_css="padding:0 44px 32px;",
        img_css="border-radius:8px;border:1px solid #f0e8f8;")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>{css}</head><body>
<div class="wrap">
  <div style="background:linear-gradient(108deg,#d22c84,#fb6069 52%,#2d84f1);padding:20px 44px;">
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
      <td valign="middle">
        <div style="font-size:16px;font-weight:700;color:#fff;letter-spacing:-0.01em;margin-bottom:3px;">Convin Data Labs</div>
        <div style="font-size:11px;color:rgba(255,255,255,0.65);font-weight:400;">Analytics · Report Delivery</div>
      </td>
      <td align="right" valign="middle" style="padding-left:16px;">{_logo(dark=True)}</td>
    </tr></table>
  </div>
  <div style="background:#fdf8ff;padding:10px 44px;border-bottom:1px solid #f0e8f8;">
    <span style="font-size:11px;color:#888;">Prepared for <strong style="color:#151515;">{c}</strong></span>
  </div>
  <div style="padding:48px 44px 40px;border-bottom:1px solid #f5f0fc;">
    <div style="font-size:10px;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;margin-bottom:14px;color:#d22c84;background:linear-gradient(90deg,#d22c84,#fb6069 52%,#2d84f1);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">Executive Summary</div>
    <p style="font-size:14px;line-height:1.85;color:#444;">{b}</p>
  </div>
  {ss_html}{extra_imgs_html}
  <div style="padding:36px 44px;background:#fdf8ff;border-bottom:1px solid #f0e8f8;text-align:center;">
    <a href="{rl}" style="display:inline-block;background:linear-gradient(108deg,#d22c84,#fb6069 52%,#2d84f1);color:#fff;text-decoration:none;font-size:12px;font-weight:700;padding:14px 44px;border-radius:8px;letter-spacing:0.03em;">Open Full Report →</a>
  </div>
  <div style="padding:28px 44px 24px;border-bottom:1px solid #f5f0fc;">
    <p style="font-size:13px;color:#aaa;margin-bottom:8px;">Warm regards,</p>
    <p style="font-size:16px;font-weight:700;color:#151515;margin-bottom:3px;">Convin Data Labs</p>
    <div style="width:36px;height:2px;background:linear-gradient(90deg,#d22c84,#2d84f1);margin-top:12px;border-radius:2px;"></div>
  </div>
  <div style="background:#fdf8ff;padding:36px 44px 40px;">
    <div style="text-align:center;padding-bottom:22px;border-bottom:1px solid #f0e8f8;margin-bottom:26px;">
      <div style="font-size:10px;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;margin-bottom:10px;color:#d22c84;background:linear-gradient(90deg,#d22c84,#2d84f1);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">Quick Feedback</div>
      <div style="font-size:19px;font-weight:600;color:#151515;margin-bottom:6px;">{sq}</div>
      <div style="font-size:12px;color:#aaa;">Takes 15 seconds · Helps us improve.</div>
    </div>
    <div style="text-align:center;margin-bottom:8px;">
      <a href="{stars[0]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="{stars[1]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="{stars[2]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="{stars[3]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="{stars[4]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a>
    </div>
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;"><tr><td style="font-size:11px;color:#ddd;">Not useful</td><td align="right" style="font-size:11px;color:#ddd;">Very useful</td></tr></table>
    <div style="text-align:center;font-size:11px;color:#aaa;margin-top:6px;">Click a star above to rate — opens in your browser</div>
  </div>
  <div style="padding:18px 44px;background:#fff;border-top:1px solid #f0e8f8;text-align:center;">
    <div><a href="#" style="font-size:11px;color:#ccc;text-decoration:none;margin:0 10px;">Unsubscribe</a><a href="#" style="font-size:11px;color:#ccc;text-decoration:none;margin:0 10px;">Preferences</a><a href="#" style="font-size:11px;color:#ccc;text-decoration:none;margin:0 10px;">Privacy</a></div>
    <div style="font-size:11px;color:#ddd;margin-top:8px;">Convin Data Labs · Registered client communication.</div>
  </div>
{pixel}</div></body></html>"""


# ── Template 11 · Convin Slate ───────────────────────────────────────────────
def _tpl_slate(c, h, b, ss, sc, rl, sq, extra_imgs_html="", pixel="", stars=None):
    if stars is None: stars = [f"{_BASE_URL}/?rating={i}" for i in range(1, 6)]
    css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #e8ecf0; font-family: 'Inter', sans-serif; padding: 32px 16px 48px; }
.wrap { max-width: 600px; margin: 0 auto; background: #fff; box-shadow: 0 4px 24px rgba(0,0,0,0.12); }
</style>"""
    ss_html = _screenshot(ss, sc,
        wrap_css="padding:0 44px 32px;",
        img_css="border-radius:6px;border:1px solid #e2e8f0;")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>{css}</head><body>
<div class="wrap">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#2d3748;"><tr><td style="padding:24px 44px;">
    <div style="font-size:15px;font-weight:700;color:#fff;letter-spacing:-0.01em;font-family:Arial,Helvetica,sans-serif;">Convin Data Labs</div>
    <div style="font-size:11px;color:#94a3b8;margin-top:2px;font-family:Arial,Helvetica,sans-serif;">Analytics Intelligence</div>
  </td><td align="right" style="padding:18px 44px;">{_logo(dark=True)}</td></tr></table>
  <div style="background:#f8fafc;border-bottom:1px solid #e2e8f0;padding:10px 44px;">
    <span style="font-size:11px;color:#64748b;">For <strong style="color:#1e293b;">{c}</strong></span>
  </div>
  <div style="padding:48px 44px 40px;border-bottom:1px solid #e2e8f0;">
    <div style="display:inline-block;font-size:10px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#1a62f2;background:#f1f6fe;padding:4px 12px;border-radius:4px;margin-bottom:18px;">Executive Summary</div>
    <p style="font-size:14px;line-height:1.85;color:#475569;">{b}</p>
  </div>
  {ss_html}{extra_imgs_html}
  <div style="padding:36px 44px;background:#f8fafc;border-bottom:1px solid #e2e8f0;text-align:center;">
    <a href="{rl}" style="display:inline-block;background:#2d3748;color:#fff;text-decoration:none;font-size:12px;font-weight:700;padding:14px 44px;border-radius:6px;letter-spacing:0.04em;text-transform:uppercase;">Open Full Report →</a>
  </div>
  <div style="padding:28px 44px 24px;border-bottom:1px solid #e2e8f0;">
    <p style="font-size:13px;color:#94a3b8;margin-bottom:8px;">Best regards,</p>
    <p style="font-size:16px;font-weight:700;color:#0f172a;margin-bottom:3px;">Convin Data Labs</p>
    <div style="width:36px;height:2px;background:#1a62f2;margin-top:12px;border-radius:2px;"></div>
  </div>
  <div style="background:#f8fafc;padding:36px 44px 40px;">
    <div style="text-align:center;padding-bottom:22px;border-bottom:1px solid #e2e8f0;margin-bottom:26px;">
      <div style="font-size:10px;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;color:#1a62f2;margin-bottom:10px;">Quick Feedback</div>
      <div style="font-size:19px;font-weight:600;color:#0f172a;margin-bottom:6px;">{sq}</div>
      <div style="font-size:12px;color:#94a3b8;">Takes 15 seconds · Helps us improve.</div>
    </div>
    <div style="text-align:center;margin-bottom:8px;">
      <a href="{stars[0]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="{stars[1]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="{stars[2]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="{stars[3]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="{stars[4]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a>
    </div>
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;"><tr><td style="font-size:11px;color:#cbd5e1;">Not useful</td><td align="right" style="font-size:11px;color:#cbd5e1;">Very useful</td></tr></table>
    <div style="text-align:center;font-size:11px;color:#94a3b8;margin-top:6px;">Click a star above to rate — opens in your browser</div>
  </div>
  <div style="padding:18px 44px;background:#2d3748;text-align:center;">
    <div><a href="#" style="font-size:11px;color:#64748b;text-decoration:none;margin:0 10px;">Unsubscribe</a><a href="#" style="font-size:11px;color:#64748b;text-decoration:none;margin:0 10px;">Preferences</a><a href="#" style="font-size:11px;color:#64748b;text-decoration:none;margin:0 10px;">Privacy</a></div>
    <div style="font-size:11px;color:#475569;margin-top:8px;">Convin Data Labs · Registered client communication.</div>
  </div>
{pixel}</div></body></html>"""


# ── Template 12 · Convin Premium ────────────────────────────────────────────
def _tpl_premium(c, h, b, ss, sc, rl, sq, extra_imgs_html="", pixel="", stars=None):
    if stars is None: stars = [f"{_BASE_URL}/?rating={i}" for i in range(1, 6)]
    css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #f1f6fe; font-family: 'Inter', sans-serif; padding: 32px 16px 48px; }
.wrap { max-width: 600px; margin: 0 auto; background: #fff; border-top: 3px solid transparent; border-image: linear-gradient(90deg,#d22c84,#fb6069 52%,#2d84f1) 1; box-shadow: 0 4px 40px rgba(26,98,242,0.08); }
</style>"""
    ss_html = _screenshot(ss, sc,
        wrap_css="padding:0 44px 32px;",
        img_css="border-radius:8px;border:1px solid #e8effe;")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>{css}</head><body>
<div class="wrap">
  <table width="100%" cellpadding="0" cellspacing="0" style="border-bottom:1px solid #f0f1ff;"><tr><td style="padding:24px 44px;font-size:15px;font-weight:700;color:#151515;letter-spacing:-0.01em;font-family:Arial,Helvetica,sans-serif;">Convin Data Labs</td><td align="right" style="padding:18px 44px;">{_logo(dark=False)}</td></tr></table>
  <div style="background:#f7f8ff;border-bottom:1px solid #eef0ff;padding:9px 44px;">
    <span style="font-size:11px;color:#888;">Prepared for <strong style="color:#151515;">{c}</strong></span>
  </div>
  <div style="padding:48px 44px 40px;border-bottom:1px solid #f0f1ff;">
    <div style="font-size:10px;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;color:#1a62f2;margin-bottom:14px;">Executive Summary</div>
    <p style="font-size:14px;line-height:1.85;color:#4a5568;">{b}</p>
  </div>
  {ss_html}{extra_imgs_html}
  <div style="padding:36px 44px;background:#f7f8ff;border-bottom:1px solid #eef0ff;text-align:center;">
    <a href="{rl}" style="display:inline-block;background:#1a62f2;color:#fff;text-decoration:none;font-size:12px;font-weight:700;padding:14px 44px;border-radius:8px;letter-spacing:0.04em;">Open Full Report →</a>
  </div>
  <div style="padding:28px 44px 24px;border-bottom:1px solid #f0f1ff;">
    <p style="font-size:13px;color:#aaa;margin-bottom:8px;">Warm regards,</p>
    <p style="font-size:16px;font-weight:700;color:#151515;margin-bottom:3px;">Convin Data Labs</p>
    <div style="width:36px;height:2px;background:linear-gradient(90deg,#d22c84,#2d84f1);margin-top:12px;border-radius:2px;"></div>
  </div>
  <div style="padding:36px 44px 40px;background:#f7f8ff;">
    <div style="text-align:center;padding-bottom:22px;border-bottom:1px solid #eef0ff;margin-bottom:26px;">
      <div style="font-size:10px;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;color:#1a62f2;margin-bottom:10px;">Quick Feedback</div>
      <div style="font-size:19px;font-weight:600;color:#151515;margin-bottom:6px;">{sq}</div>
      <div style="font-size:12px;color:#aaa;">Takes 15 seconds · Helps us improve.</div>
    </div>
    <div style="text-align:center;margin-bottom:8px;">
      <a href="{stars[0]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="{stars[1]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="{stars[2]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="{stars[3]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="{stars[4]}" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a>
    </div>
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;"><tr><td style="font-size:11px;color:#dde0ff;">Not useful</td><td align="right" style="font-size:11px;color:#dde0ff;">Very useful</td></tr></table>
    <div style="text-align:center;font-size:11px;color:#aaa;margin-top:6px;">Click a star above to rate — opens in your browser</div>
  </div>
  <div style="padding:18px 44px;background:#fff;border-top:1px solid #f0f1ff;text-align:center;">
    <div><a href="#" style="font-size:11px;color:#ccc;text-decoration:none;margin:0 10px;">Unsubscribe</a><a href="#" style="font-size:11px;color:#ccc;text-decoration:none;margin:0 10px;">Preferences</a><a href="#" style="font-size:11px;color:#ccc;text-decoration:none;margin:0 10px;">Privacy</a></div>
    <div style="font-size:11px;color:#ddd;margin-top:8px;">Convin Data Labs · Registered client communication.</div>
  </div>
{pixel}</div></body></html>"""
