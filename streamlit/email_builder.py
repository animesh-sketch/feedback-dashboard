"""
9 email template designs for Convin Data Labs report emails.
Fields used: client, headline, body, screenshot_url, screenshot_caption,
             report_link, survey_question, template (1-9)
"""

# Template registry: (name, description, swatch_bg)
TEMPLATE_NAMES = [
    ("Executive",  "Dark navy · Gold serif",      "#0d1b2a"),
    ("Minimal",    "Clean white · Blue accent",   "#f1f5f9"),
    ("Bold Blue",  "Royal blue · High contrast",  "#1e3a8a"),
    ("Modern",     "Dark gradient · Purple glow", "#13111f"),
    ("Classic",    "Warm cream · Serif elegant",  "#f4ede0"),
    ("Neon",       "Dark · Cyan glow tech",        "#040d18"),
    ("Sunrise",    "Warm orange · Light airy",    "#fff3e8"),
    ("Forest",     "Deep green · Mint fresh",     "#0b1f14"),
    ("Carbon",     "Charcoal · Bold orange",      "#1a1a1a"),
]


def build_email_html(draft: dict, template_id: int = 1) -> str:
    c  = draft.get("client")              or "—"
    h  = draft.get("headline")            or "—"
    b  = draft.get("body") or draft.get("intro") or ""
    ss = draft.get("screenshot_url")      or ""
    sc = draft.get("screenshot_caption")  or ""
    rl = draft.get("report_link")         or "#"
    sq = draft.get("survey_question")     or "Was this report useful to you?"

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
    extra_imgs_html = "".join(extra_parts)

    builders = {1: _tpl_executive, 2: _tpl_minimal,
                3: _tpl_bold_blue, 4: _tpl_modern, 5: _tpl_classic,
                6: _tpl_neon, 7: _tpl_sunrise, 8: _tpl_forest, 9: _tpl_carbon}
    return builders.get(template_id, _tpl_executive)(c, h, b, ss, sc, rl, sq, extra_imgs_html)


# ─── Shared helpers ───────────────────────────────────────────────────────────

def _screenshot(url, caption, wrap_css="", img_css=""):
    if not url:
        return ""
    cap = f'<p style="font-size:11px;font-style:italic;margin-top:10px;color:#9c8e80;">{caption}</p>' if caption else ""
    return f'<div style="{wrap_css}"><img src="{url}" alt="Screenshot" style="width:100%;display:block;{img_css}"/>{cap}</div>'


# ─── Template 1: Executive ────────────────────────────────────────────────────

def _tpl_executive(c, h, b, ss, sc, rl, sq, extra_imgs_html=""):
    css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600&family=Inter:wght@400;500;600&display=swap');
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #e8e3db; font-family: 'Inter', sans-serif; color: #1c1c1c; padding: 32px 16px 48px; }
.wrap { max-width: 600px; margin: 0 auto; background: #fff; box-shadow: 0 8px 48px rgba(0,0,0,0.15); }
.star { width: 52px; height: 52px; background: #0a1520; border: 1px solid #1e3050; color: #1e3050;
        font-size: 24px; display: inline-flex; align-items: center; justify-content: center;
        cursor: pointer; margin: 0 3px; user-select: none; transition: color 0.15s, border-color 0.15s; }
</style>"""
    ss_html = _screenshot(ss, sc,
        wrap_css="padding:0 44px 32px;border-bottom:1px solid #ede8e0;",
        img_css="border:1px solid #ddd8d0;")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>{css}</head><body>
<div class="wrap">
  <div style="background:#0d1b2a;padding:24px 44px;border-bottom:3px solid #b8962e;display:flex;align-items:center;justify-content:space-between;">
    <div style="font-family:'Playfair Display',serif;font-size:17px;color:#fff;letter-spacing:2px;text-transform:uppercase;">Convin Data Labs</div>
    <div style="font-size:11px;color:#4a6a8a;">Report · Convin Data Labs</div>
  </div>
  <div style="background:#faf9f7;border-bottom:1px solid #e4ded6;padding:10px 44px;">
    <span style="font-size:11px;color:#9c8e80;">Prepared for <strong style="color:#4a4a4a;">{c}</strong></span>
  </div>
  <div style="padding:44px 44px 36px;border-bottom:1px solid #ede8e0;">
    <div style="font-size:10px;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;color:#b8962e;margin-bottom:14px;">Executive Summary</div>
    <h1 style="font-family:'Playfair Display',serif;font-size:26px;font-weight:600;line-height:1.3;color:#0d1b2a;margin-bottom:18px;">{h}</h1>
    <div style="width:44px;height:2px;background:#b8962e;margin:0 0 20px;"></div>
    <p style="font-size:14px;line-height:1.85;color:#4a4a4a;">{b}</p>
  </div>
  {ss_html}{extra_imgs_html}
  <div style="padding:40px 44px;background:#faf9f7;border-bottom:1px solid #ede8e0;text-align:center;">
    <div style="font-size:10px;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;color:#9c8e80;margin-bottom:10px;">Full Report</div>
    <div style="font-family:'Playfair Display',serif;font-size:20px;color:#0d1b2a;margin-bottom:24px;">Access the complete analysis</div>
    <a href="{rl}" style="display:inline-block;background:#0d1b2a;color:#fff;text-decoration:none;font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;padding:14px 40px;">Open Full Report</a>
  </div>
  <div style="padding:30px 44px 26px;background:#faf9f7;border-top:1px solid #ede8e0;border-bottom:1px solid #ede8e0;">
    <p style="font-size:14px;line-height:1.8;color:#6a5c4e;font-style:italic;margin-bottom:10px;">Warm regards,</p>
    <p style="font-family:'Playfair Display',serif;font-size:17px;font-weight:600;color:#0d1b2a;margin-bottom:3px;">Convin Data Labs</p>
    <div style="width:40px;height:1px;background:#b8962e;margin-top:14px;"></div>
  </div>
  <div style="background:#0d1b2a;padding:40px 44px 44px;">
    <div style="text-align:center;padding-bottom:24px;border-bottom:1px solid #1e3050;margin-bottom:28px;">
      <div style="font-size:10px;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;color:#b8962e;margin-bottom:10px;">Quick Feedback</div>
      <div style="font-family:'Playfair Display',serif;font-size:20px;font-weight:400;color:#f0ede8;margin-bottom:6px;">{sq}</div>
      <div style="font-size:12px;color:#4a6a8a;">Takes 15 seconds · Helps us improve future reports.</div>
    </div>
    <div style="text-align:center;margin-bottom:10px;">
      <a href="https://feedback-dashboard-4mqlwnnzntsjdhjhy9a6br.streamlit.app/?rating=1" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="https://feedback-dashboard-4mqlwnnzntsjdhjhy9a6br.streamlit.app/?rating=2" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="https://feedback-dashboard-4mqlwnnzntsjdhjhy9a6br.streamlit.app/?rating=3" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="https://feedback-dashboard-4mqlwnnzntsjdhjhy9a6br.streamlit.app/?rating=4" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="https://feedback-dashboard-4mqlwnnzntsjdhjhy9a6br.streamlit.app/?rating=5" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a>
    </div>
    <div style="display:flex;justify-content:space-between;margin-bottom:24px;"><span style="font-size:10px;letter-spacing:1px;text-transform:uppercase;color:#2a4a6a;">Not useful</span><span style="font-size:10px;letter-spacing:1px;text-transform:uppercase;color:#2a4a6a;">Very useful</span></div>
    <div style="text-align:center;font-size:11px;color:#4a6a8a;letter-spacing:0.5px;margin-top:6px;">Click a star above to rate — opens in your browser</div>
  </div>
  <div style="padding:22px 44px;background:#faf9f7;border-top:1px solid #ede8e0;text-align:center;">
    <div><a href="#" style="font-size:11px;color:#9c8e80;text-decoration:none;margin:0 10px;">Unsubscribe</a><a href="#" style="font-size:11px;color:#9c8e80;text-decoration:none;margin:0 10px;">Preferences</a><a href="#" style="font-size:11px;color:#9c8e80;text-decoration:none;margin:0 10px;">Privacy</a></div>
    <div style="font-size:11px;color:#c0b8ae;line-height:1.8;margin-top:8px;">Convin Data Labs · You are receiving this as a registered client.</div>
  </div>
</div></body></html>"""


# ─── Template 2: Minimal ──────────────────────────────────────────────────────

def _tpl_minimal(c, h, b, ss, sc, rl, sq, extra_imgs_html=""):
    css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #f1f5f9; font-family: 'Inter', sans-serif; color: #111827; padding: 32px 16px 48px; }
.wrap { max-width: 600px; margin: 0 auto; background: #fff; border-radius: 16px; overflow: hidden; box-shadow: 0 1px 16px rgba(0,0,0,0.07); }
.star { font-size: 28px; cursor: pointer; color: #d1d5db; margin: 0 4px; display: inline-block; transition: color 0.12s; user-select: none; }
</style>"""
    ss_html = _screenshot(ss, sc,
        wrap_css="padding:0 40px 32px;",
        img_css="border-radius:10px;border:1px solid #e5e7eb;")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>{css}</head><body>
<div class="wrap">
  <div style="padding:20px 40px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #f3f4f6;">
    <div style="display:flex;align-items:center;gap:10px;">
      <div style="width:8px;height:28px;background:#2563eb;border-radius:4px;"></div>
      <div style="font-size:14px;font-weight:700;color:#111827;letter-spacing:-0.01em;">Convin Data Labs</div>
    </div>
    <div style="font-size:11px;color:#9ca3af;font-weight:500;">Report</div>
  </div>
  <div style="padding:8px 40px;background:#f9fafb;border-bottom:1px solid #f3f4f6;">
    <span style="font-size:11px;color:#6b7280;">Prepared for <strong style="color:#374151;">{c}</strong></span>
  </div>
  <div style="padding:48px 40px 40px;border-bottom:1px solid #f3f4f6;">
    <div style="width:32px;height:3px;background:#2563eb;border-radius:2px;margin-bottom:20px;"></div>
    <h1 style="font-size:28px;font-weight:700;color:#111827;line-height:1.3;margin-bottom:20px;letter-spacing:-0.02em;">{h}</h1>
    <p style="font-size:14px;line-height:1.85;color:#4b5563;">{b}</p>
  </div>
  {ss_html}{extra_imgs_html}
  <div style="padding:36px 40px;background:#f9fafb;border-bottom:1px solid #f3f4f6;text-align:center;">
    <div style="font-size:10px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#9ca3af;margin-bottom:14px;">Full Report Available</div>
    <a href="{rl}" style="display:inline-block;background:#2563eb;color:#fff;text-decoration:none;font-size:12px;font-weight:600;padding:14px 42px;border-radius:10px;letter-spacing:0.01em;">Open Full Report →</a>
  </div>
  <div style="padding:28px 40px 24px;border-bottom:1px solid #f3f4f6;">
    <p style="font-size:13px;color:#9ca3af;margin-bottom:8px;">Best regards,</p>
    <p style="font-size:16px;font-weight:700;color:#111827;letter-spacing:-0.01em;margin-bottom:3px;">Convin Data Labs</p>
  </div>
  <div style="padding:36px 40px;border-bottom:1px solid #f3f4f6;">
    <div style="text-align:center;margin-bottom:20px;">
      <div style="font-size:10px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#2563eb;margin-bottom:10px;">Quick Feedback</div>
      <div style="font-size:19px;font-weight:600;color:#111827;margin-bottom:6px;">{sq}</div>
      <div style="font-size:12px;color:#9ca3af;">Takes 15 seconds · Helps us improve.</div>
    </div>
    <div style="text-align:center;margin-bottom:8px;">
      <a href="https://feedback-dashboard-4mqlwnnzntsjdhjhy9a6br.streamlit.app/?rating=1" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="https://feedback-dashboard-4mqlwnnzntsjdhjhy9a6br.streamlit.app/?rating=2" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="https://feedback-dashboard-4mqlwnnzntsjdhjhy9a6br.streamlit.app/?rating=3" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="https://feedback-dashboard-4mqlwnnzntsjdhjhy9a6br.streamlit.app/?rating=4" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="https://feedback-dashboard-4mqlwnnzntsjdhjhy9a6br.streamlit.app/?rating=5" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a>
    </div>
    <div style="display:flex;justify-content:space-between;margin-bottom:20px;padding:0 4px;"><span style="font-size:11px;color:#d1d5db;">Not useful</span><span style="font-size:11px;color:#d1d5db;">Very useful</span></div>
    <div style="text-align:center;font-size:11px;color:#9ca3af;margin-top:6px;">Click a star above to rate — opens in your browser</div>
  </div>
  <div style="padding:20px 40px;text-align:center;background:#f9fafb;">
    <div><a href="#" style="font-size:11px;color:#9ca3af;text-decoration:none;margin:0 10px;">Unsubscribe</a><a href="#" style="font-size:11px;color:#9ca3af;text-decoration:none;margin:0 10px;">Preferences</a><a href="#" style="font-size:11px;color:#9ca3af;text-decoration:none;margin:0 10px;">Privacy</a></div>
    <div style="font-size:11px;color:#d1d5db;margin-top:8px;">Convin Data Labs · Registered client communication.</div>
  </div>
</div></body></html>"""


# ─── Template 3: Bold Blue ────────────────────────────────────────────────────

def _tpl_bold_blue(c, h, b, ss, sc, rl, sq, extra_imgs_html=""):
    css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap');
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #1e3a8a; font-family: 'Inter', sans-serif; color: #0f172a; padding: 32px 16px 48px; }
.wrap { max-width: 600px; margin: 0 auto; background: #fff; box-shadow: 0 20px 80px rgba(0,0,0,0.45); }
.star { font-size: 30px; cursor: pointer; color: rgba(255,255,255,0.2); margin: 0 4px; display: inline-block; transition: color 0.12s; user-select: none; }
</style>"""
    ss_html = _screenshot(ss, sc,
        wrap_css="padding:0 44px 36px;",
        img_css="border:2px solid #dbeafe;")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>{css}</head><body>
<div class="wrap">
  <div style="background:#1d4ed8;padding:28px 44px;">
    <div style="font-size:18px;font-weight:900;color:#fff;letter-spacing:2px;text-transform:uppercase;margin-bottom:3px;">Convin Data Labs</div>
    <div style="font-size:11px;color:rgba(255,255,255,0.5);font-weight:500;">Analytics · Report Delivery</div>
  </div>
  <div style="background:#eff6ff;padding:10px 44px;border-bottom:2px solid #dbeafe;">
    <span style="font-size:11px;color:#3b82f6;font-weight:600;">FOR: <span style="color:#1d4ed8;">{c}</span></span>
  </div>
  <div style="padding:52px 44px 44px;border-bottom:1px solid #e5e7eb;">
    <div style="font-size:11px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:#93c5fd;margin-bottom:16px;">Executive Summary</div>
    <h1 style="font-size:32px;font-weight:800;color:#0f172a;line-height:1.2;margin-bottom:20px;letter-spacing:-0.025em;">{h}</h1>
    <div style="width:60px;height:4px;background:#1d4ed8;border-radius:2px;margin-bottom:24px;"></div>
    <p style="font-size:15px;line-height:1.8;color:#374151;">{b}</p>
  </div>
  {ss_html}{extra_imgs_html}
  <div style="padding:40px 44px;text-align:center;border-bottom:1px solid #e5e7eb;background:#f8faff;">
    <div style="font-size:11px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#93c5fd;margin-bottom:12px;">Full Analysis Ready</div>
    <div style="font-size:20px;font-weight:700;color:#0f172a;margin-bottom:24px;">Access the complete report</div>
    <a href="{rl}" style="display:inline-block;background:#1d4ed8;color:#fff;text-decoration:none;font-size:13px;font-weight:700;padding:16px 48px;letter-spacing:0.03em;">Open Full Report →</a>
  </div>
  <div style="padding:28px 44px 24px;background:#f8faff;border-bottom:2px solid #dbeafe;">
    <p style="font-size:13px;color:#6b7280;margin-bottom:8px;">Best regards,</p>
    <p style="font-size:17px;font-weight:800;color:#0f172a;letter-spacing:-0.02em;margin-bottom:3px;">Convin Data Labs</p>
  </div>
  <div style="background:#1d4ed8;padding:40px 44px 44px;">
    <div style="text-align:center;padding-bottom:24px;border-bottom:1px solid rgba(255,255,255,0.12);margin-bottom:28px;">
      <div style="font-size:10px;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;color:#93c5fd;margin-bottom:10px;">Quick Feedback</div>
      <div style="font-size:20px;font-weight:700;color:#fff;margin-bottom:6px;">{sq}</div>
      <div style="font-size:12px;color:rgba(255,255,255,0.4);">Takes 15 seconds · Helps us improve.</div>
    </div>
    <div style="text-align:center;margin-bottom:8px;">
      <a href="https://feedback-dashboard-4mqlwnnzntsjdhjhy9a6br.streamlit.app/?rating=1" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="https://feedback-dashboard-4mqlwnnzntsjdhjhy9a6br.streamlit.app/?rating=2" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="https://feedback-dashboard-4mqlwnnzntsjdhjhy9a6br.streamlit.app/?rating=3" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="https://feedback-dashboard-4mqlwnnzntsjdhjhy9a6br.streamlit.app/?rating=4" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="https://feedback-dashboard-4mqlwnnzntsjdhjhy9a6br.streamlit.app/?rating=5" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a>
    </div>
    <div style="display:flex;justify-content:space-between;margin-bottom:20px;"><span style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:rgba(255,255,255,0.2);">Not useful</span><span style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:rgba(255,255,255,0.2);">Very useful</span></div>
    <div style="text-align:center;font-size:11px;color:rgba(255,255,255,0.35);margin-top:6px;">Click a star above to rate — opens in your browser</div>
  </div>
  <div style="padding:22px 44px;background:#eff6ff;text-align:center;border-top:2px solid #dbeafe;">
    <div><a href="#" style="font-size:11px;color:#3b82f6;text-decoration:none;margin:0 10px;">Unsubscribe</a><a href="#" style="font-size:11px;color:#3b82f6;text-decoration:none;margin:0 10px;">Preferences</a><a href="#" style="font-size:11px;color:#3b82f6;text-decoration:none;margin:0 10px;">Privacy</a></div>
    <div style="font-size:11px;color:#93c5fd;margin-top:8px;">Convin Data Labs · Registered client communication.</div>
  </div>
</div></body></html>"""


# ─── Template 4: Modern ───────────────────────────────────────────────────────

def _tpl_modern(c, h, b, ss, sc, rl, sq, extra_imgs_html=""):
    css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #0d0d1a; font-family: 'Inter', sans-serif; padding: 32px 16px 48px; }
.wrap { max-width: 600px; margin: 0 auto; background: #111827; border-radius: 24px; overflow: hidden; box-shadow: 0 24px 80px rgba(0,0,0,0.6); border: 1px solid #1e293b; }
.star { font-size: 28px; cursor: pointer; color: #1e293b; margin: 0 4px; display: inline-block; transition: color 0.12s; user-select: none; }
</style>"""
    ss_html = _screenshot(ss, sc,
        wrap_css="padding:0 40px 32px;",
        img_css="border-radius:12px;border:1px solid #1e293b;")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>{css}</head><body>
<div class="wrap">
  <div style="background:linear-gradient(135deg,#1e1b4b 0%,#312e81 60%,#4c1d95 100%);padding:32px 40px 28px;">
    <div style="font-size:13px;font-weight:700;color:#a78bfa;letter-spacing:2.5px;text-transform:uppercase;margin-bottom:4px;">Convin Data Labs</div>
    <div style="font-size:11px;color:rgba(167,139,250,0.45);font-weight:400;">Analytics Intelligence · Report</div>
  </div>
  <div style="padding:10px 40px;background:#0f172a;border-bottom:1px solid #1e293b;">
    <span style="font-size:11px;color:#475569;">For <span style="color:#a78bfa;font-weight:600;">{c}</span></span>
  </div>
  <div style="padding:44px 40px 36px;border-bottom:1px solid #1e293b;background:linear-gradient(180deg,#111827,#0f172a);">
    <div style="display:inline-block;font-size:9px;font-weight:700;letter-spacing:0.15em;text-transform:uppercase;color:#a78bfa;background:rgba(167,139,250,0.08);border:1px solid rgba(167,139,250,0.2);padding:4px 12px;border-radius:99px;margin-bottom:20px;">Executive Summary</div>
    <h1 style="font-size:28px;font-weight:700;color:#f8fafc;line-height:1.3;margin-bottom:20px;letter-spacing:-0.02em;">{h}</h1>
    <div style="width:40px;height:2px;background:linear-gradient(90deg,#7c3aed,#a78bfa);border-radius:2px;margin-bottom:20px;"></div>
    <p style="font-size:14px;line-height:1.85;color:#64748b;">{b}</p>
  </div>
  {ss_html}{extra_imgs_html}
  <div style="padding:36px 40px;background:#0f172a;border-bottom:1px solid #1e293b;text-align:center;">
    <div style="font-size:10px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:#475569;margin-bottom:14px;">Full Analysis</div>
    <a href="{rl}" style="display:inline-block;background:linear-gradient(135deg,#7c3aed,#a78bfa);color:#fff;text-decoration:none;font-size:12px;font-weight:600;padding:14px 44px;border-radius:10px;letter-spacing:0.03em;box-shadow:0 4px 20px rgba(124,58,237,0.35);">Open Full Report →</a>
  </div>
  <div style="padding:28px 40px 24px;background:#0f172a;border-top:1px solid #1e293b;border-bottom:1px solid #1e293b;">
    <p style="font-size:13px;color:#475569;margin-bottom:8px;">Warm regards,</p>
    <p style="font-size:16px;font-weight:700;color:#f8fafc;letter-spacing:-0.01em;margin-bottom:3px;">Convin Data Labs</p>
  </div>
  <div style="background:#0d0d1a;padding:40px 40px 44px;border-top:1px solid #1e293b;">
    <div style="text-align:center;padding-bottom:24px;border-bottom:1px solid #1e293b;margin-bottom:28px;">
      <div style="font-size:9px;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;color:#a78bfa;margin-bottom:10px;">Quick Feedback</div>
      <div style="font-size:19px;font-weight:600;color:#e2e8f0;margin-bottom:6px;">{sq}</div>
      <div style="font-size:12px;color:#334155;">Takes 15 seconds · Helps us improve.</div>
    </div>
    <div style="text-align:center;margin-bottom:8px;">
      <a href="https://feedback-dashboard-4mqlwnnzntsjdhjhy9a6br.streamlit.app/?rating=1" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="https://feedback-dashboard-4mqlwnnzntsjdhjhy9a6br.streamlit.app/?rating=2" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="https://feedback-dashboard-4mqlwnnzntsjdhjhy9a6br.streamlit.app/?rating=3" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="https://feedback-dashboard-4mqlwnnzntsjdhjhy9a6br.streamlit.app/?rating=4" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="https://feedback-dashboard-4mqlwnnzntsjdhjhy9a6br.streamlit.app/?rating=5" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a>
    </div>
    <div style="display:flex;justify-content:space-between;margin-bottom:20px;"><span style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:#1e293b;">Not useful</span><span style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:#1e293b;">Very useful</span></div>
    <div style="text-align:center;font-size:11px;color:#475569;margin-top:6px;">Click a star above to rate — opens in your browser</div>
  </div>
  <div style="padding:20px 40px;background:#0d0d1a;text-align:center;border-top:1px solid #1e293b;">
    <div><a href="#" style="font-size:11px;color:#334155;text-decoration:none;margin:0 10px;">Unsubscribe</a><a href="#" style="font-size:11px;color:#334155;text-decoration:none;margin:0 10px;">Preferences</a><a href="#" style="font-size:11px;color:#334155;text-decoration:none;margin:0 10px;">Privacy</a></div>
    <div style="font-size:11px;color:#1e293b;margin-top:6px;">Convin Data Labs · Registered client communication.</div>
  </div>
</div></body></html>"""


# ─── Template 5: Classic ──────────────────────────────────────────────────────

def _tpl_classic(c, h, b, ss, sc, rl, sq, extra_imgs_html=""):
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
  <div style="background:#2c1a0e;padding:22px 48px;text-align:center;">
    <div style="font-family:'Playfair Display',serif;font-size:13px;color:#c9a96e;letter-spacing:5px;text-transform:uppercase;margin-bottom:5px;">Convin Data Labs</div>
    <div class="orn">· · ·</div>
    <div style="font-size:10px;color:rgba(201,169,110,0.5);letter-spacing:3px;text-transform:uppercase;margin-top:5px;">Analytics &amp; Reports</div>
  </div>
  <div style="background:#faf5ed;border-bottom:1px solid #d5c4a8;padding:10px 48px;text-align:center;">
    <span style="font-size:11px;color:#8b7355;font-style:italic;">Prepared for <strong style="color:#2c1a0e;font-style:normal;">{c}</strong></span>
  </div>
  <div style="padding:48px 48px 40px;border-bottom:1px solid #d5c4a8;">
    <div style="font-size:11px;color:#c9a96e;font-style:italic;letter-spacing:0.05em;margin-bottom:14px;text-align:center;">Executive Summary</div>
    <h1 style="font-family:'Playfair Display',serif;font-size:26px;font-weight:700;color:#1a0a00;line-height:1.4;text-align:center;margin-bottom:18px;">{h}</h1>
    <div style="text-align:center;margin-bottom:24px;"><div style="display:inline-block;width:80px;height:1px;background:#c9a96e;"></div><span style="color:#c9a96e;font-size:14px;padding:0 10px;">◆</span><div style="display:inline-block;width:80px;height:1px;background:#c9a96e;"></div></div>
    <p style="font-size:14px;line-height:1.95;color:#3d2b1f;text-align:justify;">{b}</p>
  </div>
  {ss_html}{extra_imgs_html}
  <div style="padding:36px 48px;background:#faf5ed;border-bottom:1px solid #d5c4a8;text-align:center;">
    <div style="font-size:10px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:#8b7355;margin-bottom:14px;">Full Report Available</div>
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
      <a href="https://feedback-dashboard-4mqlwnnzntsjdhjhy9a6br.streamlit.app/?rating=1" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="https://feedback-dashboard-4mqlwnnzntsjdhjhy9a6br.streamlit.app/?rating=2" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="https://feedback-dashboard-4mqlwnnzntsjdhjhy9a6br.streamlit.app/?rating=3" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="https://feedback-dashboard-4mqlwnnzntsjdhjhy9a6br.streamlit.app/?rating=4" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="https://feedback-dashboard-4mqlwnnzntsjdhjhy9a6br.streamlit.app/?rating=5" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a>
    </div>
    <div style="display:flex;justify-content:space-between;margin-bottom:20px;"><span style="font-size:11px;color:#d5c4a8;font-style:italic;">Not useful</span><span style="font-size:11px;color:#d5c4a8;font-style:italic;">Very useful</span></div>
    <div style="text-align:center;font-size:11px;color:#9c8e80;font-style:italic;font-family:'Lora',serif;margin-top:6px;">Click a star above to rate — opens in your browser</div>
  </div>
  <div style="padding:20px 48px;background:#faf5ed;text-align:center;">
    <div class="orn" style="font-size:12px;margin-bottom:10px;">· · ·</div>
    <div><a href="#" style="font-size:11px;color:#8b7355;text-decoration:none;margin:0 10px;">Unsubscribe</a><a href="#" style="font-size:11px;color:#8b7355;text-decoration:none;margin:0 10px;">Preferences</a><a href="#" style="font-size:11px;color:#8b7355;text-decoration:none;margin:0 10px;">Privacy</a></div>
    <div style="font-size:11px;color:#c9a96e;margin-top:8px;">Convin Data Labs · Registered client communication.</div>
  </div>
</div></body></html>"""


# ─── Template 6: Neon ─────────────────────────────────────────────────────────

def _tpl_neon(c, h, b, ss, sc, rl, sq, extra_imgs_html=""):
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
    <div style="font-size:15px;font-weight:800;color:#06b6d4;letter-spacing:3px;text-transform:uppercase;text-shadow:0 0 20px rgba(6,182,212,0.5);margin-bottom:3px;">Convin Data Labs</div>
    <div style="font-size:11px;color:rgba(6,182,212,0.35);font-weight:400;letter-spacing:1.5px;text-transform:uppercase;">Analytics · Report Delivery</div>
  </div>
  <div style="padding:8px 40px;background:#030b14;border-bottom:1px solid #0c2a3a;">
    <span style="font-size:11px;color:#164e63;">For <span style="color:#06b6d4;font-weight:600;">{c}</span></span>
  </div>
  <div style="padding:44px 40px 36px;border-bottom:1px solid #0c2a3a;">
    <div style="display:inline-block;font-size:9px;font-weight:700;letter-spacing:0.15em;text-transform:uppercase;color:#06b6d4;background:rgba(6,182,212,0.06);border:1px solid rgba(6,182,212,0.2);padding:4px 12px;border-radius:99px;margin-bottom:20px;">Executive Summary</div>
    <h1 style="font-size:28px;font-weight:800;color:#e0f7fa;line-height:1.3;margin-bottom:16px;letter-spacing:-0.02em;">{h}</h1>
    <div style="width:50px;height:2px;background:linear-gradient(90deg,#06b6d4,transparent);margin-bottom:20px;box-shadow:0 0 8px rgba(6,182,212,0.6);"></div>
    <p style="font-size:14px;line-height:1.85;color:#475569;">{b}</p>
  </div>
  {ss_html}{extra_imgs_html}
  <div style="padding:36px 40px;background:#030b14;border-bottom:1px solid #0c2a3a;text-align:center;">
    <div style="font-size:10px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:#164e63;margin-bottom:14px;">Full Analysis Ready</div>
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
      <a href="https://feedback-dashboard-4mqlwnnzntsjdhjhy9a6br.streamlit.app/?rating=1" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="https://feedback-dashboard-4mqlwnnzntsjdhjhy9a6br.streamlit.app/?rating=2" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="https://feedback-dashboard-4mqlwnnzntsjdhjhy9a6br.streamlit.app/?rating=3" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="https://feedback-dashboard-4mqlwnnzntsjdhjhy9a6br.streamlit.app/?rating=4" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="https://feedback-dashboard-4mqlwnnzntsjdhjhy9a6br.streamlit.app/?rating=5" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a>
    </div>
    <div style="display:flex;justify-content:space-between;margin-bottom:20px;"><span style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:#0c2a3a;">Not useful</span><span style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:#0c2a3a;">Very useful</span></div>
    <div style="text-align:center;font-size:11px;color:rgba(6,182,212,0.4);letter-spacing:0.5px;margin-top:6px;">Click a star above to rate — opens in your browser</div>
  </div>
  <div style="padding:18px 40px;background:#020a12;text-align:center;border-top:1px solid #0c2a3a;">
    <div><a href="#" style="font-size:11px;color:#164e63;text-decoration:none;margin:0 10px;">Unsubscribe</a><a href="#" style="font-size:11px;color:#164e63;text-decoration:none;margin:0 10px;">Preferences</a><a href="#" style="font-size:11px;color:#164e63;text-decoration:none;margin:0 10px;">Privacy</a></div>
    <div style="font-size:11px;color:#0c2a3a;margin-top:6px;">Convin Data Labs · Registered client communication.</div>
  </div>
</div></body></html>"""


# ─── Template 7: Sunrise ──────────────────────────────────────────────────────

def _tpl_sunrise(c, h, b, ss, sc, rl, sq, extra_imgs_html=""):
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
    <h1 style="font-family:'Poppins',sans-serif;font-size:26px;font-weight:700;color:#1c0a00;line-height:1.3;margin-bottom:20px;letter-spacing:-0.01em;">{h}</h1>
    <p style="font-size:14px;line-height:1.85;color:#57534e;">{b}</p>
  </div>
  {ss_html}{extra_imgs_html}
  <div style="padding:36px 44px;background:#fff8f3;border-bottom:1px solid #fde8d0;text-align:center;">
    <div style="font-size:10px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#c2410c;margin-bottom:14px;">Full Report Available</div>
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
      <a href="https://feedback-dashboard-4mqlwnnzntsjdhjhy9a6br.streamlit.app/?rating=1" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="https://feedback-dashboard-4mqlwnnzntsjdhjhy9a6br.streamlit.app/?rating=2" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="https://feedback-dashboard-4mqlwnnzntsjdhjhy9a6br.streamlit.app/?rating=3" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="https://feedback-dashboard-4mqlwnnzntsjdhjhy9a6br.streamlit.app/?rating=4" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="https://feedback-dashboard-4mqlwnnzntsjdhjhy9a6br.streamlit.app/?rating=5" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a>
    </div>
    <div style="display:flex;justify-content:space-between;margin-bottom:20px;"><span style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:rgba(255,255,255,0.3);">Not useful</span><span style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:rgba(255,255,255,0.3);">Very useful</span></div>
    <div style="text-align:center;font-size:11px;color:rgba(255,255,255,0.5);margin-top:6px;">Click a star above to rate — opens in your browser</div>
  </div>
  <div style="padding:18px 44px;background:#fff8f3;text-align:center;border-top:1px solid #fde8d0;">
    <div><a href="#" style="font-size:11px;color:#c2410c;text-decoration:none;margin:0 10px;">Unsubscribe</a><a href="#" style="font-size:11px;color:#c2410c;text-decoration:none;margin:0 10px;">Preferences</a><a href="#" style="font-size:11px;color:#c2410c;text-decoration:none;margin:0 10px;">Privacy</a></div>
    <div style="font-size:11px;color:#fed7aa;margin-top:8px;">Convin Data Labs · Registered client communication.</div>
  </div>
</div></body></html>"""


# ─── Template 8: Forest ───────────────────────────────────────────────────────

def _tpl_forest(c, h, b, ss, sc, rl, sq, extra_imgs_html=""):
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
    <div style="font-size:15px;font-weight:800;color:#6ee7b7;letter-spacing:2px;text-transform:uppercase;margin-bottom:3px;">Convin Data Labs</div>
    <div style="font-size:11px;color:rgba(110,231,183,0.35);letter-spacing:1px;text-transform:uppercase;">Analytics · Report</div>
  </div>
  <div style="padding:8px 44px;background:#071a0e;border-bottom:1px solid #132e1c;">
    <span style="font-size:11px;color:#166534;">For <span style="color:#10b981;font-weight:600;">{c}</span></span>
  </div>
  <div style="padding:44px 44px 36px;border-bottom:1px solid #132e1c;">
    <div style="display:inline-block;font-size:9px;font-weight:700;letter-spacing:0.15em;text-transform:uppercase;color:#10b981;background:rgba(16,185,129,0.06);border:1px solid rgba(16,185,129,0.18);padding:4px 12px;border-radius:99px;margin-bottom:20px;">Executive Summary</div>
    <h1 style="font-size:28px;font-weight:700;color:#ecfdf5;line-height:1.3;margin-bottom:16px;letter-spacing:-0.02em;">{h}</h1>
    <div style="width:48px;height:2px;background:linear-gradient(90deg,#10b981,transparent);margin-bottom:20px;border-radius:2px;"></div>
    <p style="font-size:14px;line-height:1.85;color:#4b7a5e;">{b}</p>
  </div>
  {ss_html}{extra_imgs_html}
  <div style="padding:36px 44px;background:#071a0e;border-bottom:1px solid #132e1c;text-align:center;">
    <div style="font-size:10px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:#166534;margin-bottom:14px;">Full Analysis Ready</div>
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
      <a href="https://feedback-dashboard-4mqlwnnzntsjdhjhy9a6br.streamlit.app/?rating=1" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="https://feedback-dashboard-4mqlwnnzntsjdhjhy9a6br.streamlit.app/?rating=2" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="https://feedback-dashboard-4mqlwnnzntsjdhjhy9a6br.streamlit.app/?rating=3" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="https://feedback-dashboard-4mqlwnnzntsjdhjhy9a6br.streamlit.app/?rating=4" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="https://feedback-dashboard-4mqlwnnzntsjdhjhy9a6br.streamlit.app/?rating=5" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a>
    </div>
    <div style="display:flex;justify-content:space-between;margin-bottom:20px;"><span style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:#132e1c;">Not useful</span><span style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:#132e1c;">Very useful</span></div>
    <div style="text-align:center;font-size:11px;color:rgba(16,185,129,0.4);margin-top:6px;">Click a star above to rate — opens in your browser</div>
  </div>
  <div style="padding:18px 44px;background:#040f08;text-align:center;border-top:1px solid #132e1c;">
    <div><a href="#" style="font-size:11px;color:#166534;text-decoration:none;margin:0 10px;">Unsubscribe</a><a href="#" style="font-size:11px;color:#166534;text-decoration:none;margin:0 10px;">Preferences</a><a href="#" style="font-size:11px;color:#166534;text-decoration:none;margin:0 10px;">Privacy</a></div>
    <div style="font-size:11px;color:#132e1c;margin-top:6px;">Convin Data Labs · Registered client communication.</div>
  </div>
</div></body></html>"""


# ─── Template 9: Carbon ───────────────────────────────────────────────────────

def _tpl_carbon(c, h, b, ss, sc, rl, sq, extra_imgs_html=""):
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
  <div style="background:#111;padding:0;border-bottom:3px solid #f97316;">
    <div style="padding:24px 44px;display:flex;align-items:center;justify-content:space-between;">
      <div>
        <div style="font-size:16px;font-weight:800;color:#fff;letter-spacing:2px;text-transform:uppercase;margin-bottom:2px;">Convin Data Labs</div>
        <div style="font-size:10px;color:#444;letter-spacing:2px;text-transform:uppercase;">Analytics · Report</div>
      </div>
      <div style="width:36px;height:36px;background:#f97316;border-radius:6px;display:flex;align-items:center;justify-content:center;">
        <div style="font-size:14px;font-weight:800;color:#fff;">C</div>
      </div>
    </div>
  </div>
  <div style="padding:8px 44px;background:#141414;border-bottom:1px solid #222;">
    <span style="font-size:11px;color:#555;">Prepared for <span style="color:#f97316;font-weight:600;">{c}</span></span>
  </div>
  <div style="padding:48px 44px 40px;border-bottom:1px solid #222;">
    <div style="font-size:10px;font-weight:700;letter-spacing:0.15em;text-transform:uppercase;color:#f97316;margin-bottom:16px;">Executive Summary</div>
    <h1 style="font-size:30px;font-weight:800;color:#fff;line-height:1.25;margin-bottom:18px;letter-spacing:-0.03em;">{h}</h1>
    <div style="width:56px;height:3px;background:#f97316;margin-bottom:22px;"></div>
    <p style="font-size:14px;line-height:1.85;color:#888;">{b}</p>
  </div>
  {ss_html}{extra_imgs_html}
  <div style="padding:38px 44px;background:#141414;border-bottom:1px solid #222;text-align:center;">
    <div style="font-size:10px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:#555;margin-bottom:14px;">Full Analysis Ready</div>
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
      <a href="https://feedback-dashboard-4mqlwnnzntsjdhjhy9a6br.streamlit.app/?rating=1" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="https://feedback-dashboard-4mqlwnnzntsjdhjhy9a6br.streamlit.app/?rating=2" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="https://feedback-dashboard-4mqlwnnzntsjdhjhy9a6br.streamlit.app/?rating=3" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="https://feedback-dashboard-4mqlwnnzntsjdhjhy9a6br.streamlit.app/?rating=4" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a><a href="https://feedback-dashboard-4mqlwnnzntsjdhjhy9a6br.streamlit.app/?rating=5" target="_blank" rel="noopener" style="font-size:28px;text-decoration:none;color:#f59e0b;margin:0 5px;display:inline-block;line-height:1;font-style:normal;">★</a>
    </div>
    <div style="display:flex;justify-content:space-between;margin-bottom:20px;"><span style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:#2a2a2a;">Not useful</span><span style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:#2a2a2a;">Very useful</span></div>
    <div style="text-align:center;font-size:11px;color:#555;margin-top:6px;">Click a star above to rate — opens in your browser</div>
  </div>
  <div style="padding:18px 44px;background:#141414;text-align:center;border-top:1px solid #222;">
    <div><a href="#" style="font-size:11px;color:#444;text-decoration:none;margin:0 10px;">Unsubscribe</a><a href="#" style="font-size:11px;color:#444;text-decoration:none;margin:0 10px;">Preferences</a><a href="#" style="font-size:11px;color:#444;text-decoration:none;margin:0 10px;">Privacy</a></div>
    <div style="font-size:11px;color:#2a2a2a;margin-top:6px;">Convin Data Labs · Registered client communication.</div>
  </div>
</div></body></html>"""
