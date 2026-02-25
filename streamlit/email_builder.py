"""
5 email template designs for Convin Data Labs report emails.
Fields used: client, headline, body, screenshot_url, screenshot_caption,
             report_link, survey_question, template (1-5)
"""

# Template registry: (name, description, swatch_bg)
TEMPLATE_NAMES = [
    ("Executive",  "Dark navy · Gold serif",      "#0d1b2a"),
    ("Minimal",    "Clean white · Blue accent",   "#f1f5f9"),
    ("Bold Blue",  "Royal blue · High contrast",  "#1e3a8a"),
    ("Modern",     "Dark gradient · Purple glow", "#13111f"),
    ("Classic",    "Warm cream · Serif elegant",  "#f4ede0"),
]


def build_email_html(draft: dict, template_id: int = 1) -> str:
    c  = draft.get("client")              or "—"
    h  = draft.get("headline")            or "—"
    b  = draft.get("body") or draft.get("intro") or ""
    ss = draft.get("screenshot_url")      or ""
    sc = draft.get("screenshot_caption")  or ""
    rl = draft.get("report_link")         or "#"
    sq = draft.get("survey_question")     or "Was this report useful to you?"
    builders = {1: _tpl_executive, 2: _tpl_minimal,
                3: _tpl_bold_blue, 4: _tpl_modern, 5: _tpl_classic}
    return builders.get(template_id, _tpl_executive)(c, h, b, ss, sc, rl, sq)


# ─── Shared helpers ───────────────────────────────────────────────────────────

def _screenshot(url, caption, wrap_css="", img_css=""):
    if not url:
        return ""
    cap = f'<p style="font-size:11px;font-style:italic;margin-top:10px;color:#9c8e80;">{caption}</p>' if caption else ""
    return f'<div style="{wrap_css}"><img src="{url}" alt="Screenshot" style="width:100%;display:block;{img_css}"/>{cap}</div>'


# ─── Template 1: Executive ────────────────────────────────────────────────────

def _tpl_executive(c, h, b, ss, sc, rl, sq):
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
    js = """
<script>
let sel=0;const stars=document.querySelectorAll('.star');
function rate(el,v){sel=v;stars.forEach((s,i)=>{s.style.color=i<v?'#b8962e':'#1e3050';s.style.borderColor=i<v?'#b8962e':'#1e3050';});document.getElementById('sbtn').disabled=false;}
function thanks(){document.getElementById('sbtn').parentNode.style.display='none';document.getElementById('ty').style.display='block';}
</script>"""
    ss_html = _screenshot(ss, sc,
        wrap_css="padding:0 44px 32px;border-bottom:1px solid #ede8e0;",
        img_css="border:1px solid #ddd8d0;")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>{css}</head><body>
<div class="wrap">
  <div style="background:#0d1b2a;padding:24px 44px;border-bottom:3px solid #b8962e;display:flex;align-items:center;justify-content:space-between;">
    <div style="font-family:'Playfair Display',serif;font-size:17px;color:#fff;letter-spacing:2px;text-transform:uppercase;">Convin Data Labs</div>
    <div style="font-size:11px;color:#4a6a8a;">Report · Animesh Koner</div>
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
  {ss_html}
  <div style="padding:40px 44px;background:#faf9f7;border-bottom:1px solid #ede8e0;text-align:center;">
    <div style="font-size:10px;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;color:#9c8e80;margin-bottom:10px;">Full Report</div>
    <div style="font-family:'Playfair Display',serif;font-size:20px;color:#0d1b2a;margin-bottom:24px;">Access the complete analysis</div>
    <a href="{rl}" style="display:inline-block;background:#0d1b2a;color:#fff;text-decoration:none;font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;padding:14px 40px;">Open Full Report</a>
  </div>
  <div style="padding:30px 44px 26px;background:#faf9f7;border-top:1px solid #ede8e0;border-bottom:1px solid #ede8e0;">
    <p style="font-size:14px;line-height:1.8;color:#6a5c4e;font-style:italic;margin-bottom:10px;">Warm regards,</p>
    <p style="font-family:'Playfair Display',serif;font-size:17px;font-weight:600;color:#0d1b2a;margin-bottom:3px;">Animesh Koner</p>
    <p style="font-size:12px;color:#b8962e;letter-spacing:0.08em;text-transform:uppercase;font-weight:600;">Convin Data Labs</p>
    <div style="width:40px;height:1px;background:#b8962e;margin-top:14px;"></div>
  </div>
  <div style="background:#0d1b2a;padding:40px 44px 44px;">
    <div style="text-align:center;padding-bottom:24px;border-bottom:1px solid #1e3050;margin-bottom:28px;">
      <div style="font-size:10px;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;color:#b8962e;margin-bottom:10px;">Quick Feedback</div>
      <div style="font-family:'Playfair Display',serif;font-size:20px;font-weight:400;color:#f0ede8;margin-bottom:6px;">{sq}</div>
      <div style="font-size:12px;color:#4a6a8a;">Takes 15 seconds · Helps us improve future reports.</div>
    </div>
    <div style="text-align:center;margin-bottom:10px;">
      <span class="star" onclick="rate(this,1)">★</span><span class="star" onclick="rate(this,2)">★</span><span class="star" onclick="rate(this,3)">★</span><span class="star" onclick="rate(this,4)">★</span><span class="star" onclick="rate(this,5)">★</span>
    </div>
    <div style="display:flex;justify-content:space-between;margin-bottom:24px;"><span style="font-size:10px;letter-spacing:1px;text-transform:uppercase;color:#2a4a6a;">Not useful</span><span style="font-size:10px;letter-spacing:1px;text-transform:uppercase;color:#2a4a6a;">Very useful</span></div>
    <label style="display:block;font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#4a6a8a;margin-bottom:8px;">Additional comments</label>
    <textarea style="width:100%;padding:12px 14px;background:#080f18;border:1px solid #1e3050;color:#c8d8e8;font-family:'Inter',sans-serif;font-size:13px;resize:vertical;min-height:72px;outline:none;box-sizing:border-box;" placeholder="Share your thoughts…"></textarea>
    <button id="sbtn" disabled onclick="thanks()" style="display:block;width:100%;margin-top:18px;padding:15px;background:#b8962e;color:#0d1b2a;font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;border:none;cursor:pointer;">Submit Feedback</button>
    <div id="ty" style="display:none;text-align:center;padding:20px;"><div style="font-size:10px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:#b8962e;margin-bottom:10px;">Thank You</div><div style="font-family:serif;font-size:18px;color:#f0ede8;">Your feedback has been noted.</div></div>
  </div>
  <div style="padding:22px 44px;background:#faf9f7;border-top:1px solid #ede8e0;text-align:center;">
    <div><a href="#" style="font-size:11px;color:#9c8e80;text-decoration:none;margin:0 10px;">Unsubscribe</a><a href="#" style="font-size:11px;color:#9c8e80;text-decoration:none;margin:0 10px;">Preferences</a><a href="#" style="font-size:11px;color:#9c8e80;text-decoration:none;margin:0 10px;">Privacy</a></div>
    <div style="font-size:11px;color:#c0b8ae;line-height:1.8;margin-top:8px;">Convin Data Labs · You are receiving this as a registered client.</div>
  </div>
</div>{js}</body></html>"""


# ─── Template 2: Minimal ──────────────────────────────────────────────────────

def _tpl_minimal(c, h, b, ss, sc, rl, sq):
    css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #f1f5f9; font-family: 'Inter', sans-serif; color: #111827; padding: 32px 16px 48px; }
.wrap { max-width: 600px; margin: 0 auto; background: #fff; border-radius: 16px; overflow: hidden; box-shadow: 0 1px 16px rgba(0,0,0,0.07); }
.star { font-size: 28px; cursor: pointer; color: #d1d5db; margin: 0 4px; display: inline-block; transition: color 0.12s; user-select: none; }
</style>"""
    js = """
<script>
let sel=0;const stars=document.querySelectorAll('.star');
function rate(el,v){sel=v;stars.forEach((s,i)=>{s.style.color=i<v?'#2563eb':'#d1d5db';});document.getElementById('sbtn').disabled=false;}
function thanks(){document.getElementById('sbtn').parentNode.style.display='none';document.getElementById('ty').style.display='block';}
</script>"""
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
  {ss_html}
  <div style="padding:36px 40px;background:#f9fafb;border-bottom:1px solid #f3f4f6;text-align:center;">
    <div style="font-size:10px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#9ca3af;margin-bottom:14px;">Full Report Available</div>
    <a href="{rl}" style="display:inline-block;background:#2563eb;color:#fff;text-decoration:none;font-size:12px;font-weight:600;padding:14px 42px;border-radius:10px;letter-spacing:0.01em;">Open Full Report →</a>
  </div>
  <div style="padding:28px 40px 24px;border-bottom:1px solid #f3f4f6;">
    <p style="font-size:13px;color:#9ca3af;margin-bottom:8px;">Best regards,</p>
    <p style="font-size:16px;font-weight:700;color:#111827;letter-spacing:-0.01em;margin-bottom:3px;">Animesh Koner</p>
    <p style="font-size:12px;color:#2563eb;font-weight:600;">Convin Data Labs</p>
  </div>
  <div style="padding:36px 40px;border-bottom:1px solid #f3f4f6;">
    <div style="text-align:center;margin-bottom:20px;">
      <div style="font-size:10px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#2563eb;margin-bottom:10px;">Quick Feedback</div>
      <div style="font-size:19px;font-weight:600;color:#111827;margin-bottom:6px;">{sq}</div>
      <div style="font-size:12px;color:#9ca3af;">Takes 15 seconds · Helps us improve.</div>
    </div>
    <div style="text-align:center;margin-bottom:8px;">
      <span class="star" onclick="rate(this,1)">★</span><span class="star" onclick="rate(this,2)">★</span><span class="star" onclick="rate(this,3)">★</span><span class="star" onclick="rate(this,4)">★</span><span class="star" onclick="rate(this,5)">★</span>
    </div>
    <div style="display:flex;justify-content:space-between;margin-bottom:20px;padding:0 4px;"><span style="font-size:11px;color:#d1d5db;">Not useful</span><span style="font-size:11px;color:#d1d5db;">Very useful</span></div>
    <textarea style="width:100%;padding:12px 14px;background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;color:#374151;font-family:'Inter',sans-serif;font-size:13px;resize:vertical;min-height:68px;outline:none;box-sizing:border-box;" placeholder="Additional comments (optional)"></textarea>
    <button id="sbtn" disabled onclick="thanks()" style="display:block;width:100%;margin-top:12px;padding:14px;background:#2563eb;color:#fff;font-size:12px;font-weight:600;letter-spacing:0.02em;border:none;border-radius:10px;cursor:pointer;">Submit Feedback</button>
    <div id="ty" style="display:none;text-align:center;padding:20px;"><div style="font-size:11px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#2563eb;margin-bottom:8px;">Thank You</div><div style="font-size:17px;color:#374151;">Your feedback has been noted.</div></div>
  </div>
  <div style="padding:20px 40px;text-align:center;background:#f9fafb;">
    <div><a href="#" style="font-size:11px;color:#9ca3af;text-decoration:none;margin:0 10px;">Unsubscribe</a><a href="#" style="font-size:11px;color:#9ca3af;text-decoration:none;margin:0 10px;">Preferences</a><a href="#" style="font-size:11px;color:#9ca3af;text-decoration:none;margin:0 10px;">Privacy</a></div>
    <div style="font-size:11px;color:#d1d5db;margin-top:8px;">Convin Data Labs · Registered client communication.</div>
  </div>
</div>{js}</body></html>"""


# ─── Template 3: Bold Blue ────────────────────────────────────────────────────

def _tpl_bold_blue(c, h, b, ss, sc, rl, sq):
    css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap');
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #1e3a8a; font-family: 'Inter', sans-serif; color: #0f172a; padding: 32px 16px 48px; }
.wrap { max-width: 600px; margin: 0 auto; background: #fff; box-shadow: 0 20px 80px rgba(0,0,0,0.45); }
.star { font-size: 30px; cursor: pointer; color: rgba(255,255,255,0.2); margin: 0 4px; display: inline-block; transition: color 0.12s; user-select: none; }
</style>"""
    js = """
<script>
let sel=0;const stars=document.querySelectorAll('.star');
function rate(el,v){sel=v;stars.forEach((s,i)=>{s.style.color=i<v?'#fbbf24':'rgba(255,255,255,0.2)';});document.getElementById('sbtn').disabled=false;}
function thanks(){document.getElementById('sbtn').parentNode.style.display='none';document.getElementById('ty').style.display='block';}
</script>"""
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
  {ss_html}
  <div style="padding:40px 44px;text-align:center;border-bottom:1px solid #e5e7eb;background:#f8faff;">
    <div style="font-size:11px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#93c5fd;margin-bottom:12px;">Full Analysis Ready</div>
    <div style="font-size:20px;font-weight:700;color:#0f172a;margin-bottom:24px;">Access the complete report</div>
    <a href="{rl}" style="display:inline-block;background:#1d4ed8;color:#fff;text-decoration:none;font-size:13px;font-weight:700;padding:16px 48px;letter-spacing:0.03em;">Open Full Report →</a>
  </div>
  <div style="padding:28px 44px 24px;background:#f8faff;border-bottom:2px solid #dbeafe;">
    <p style="font-size:13px;color:#6b7280;margin-bottom:8px;">Best regards,</p>
    <p style="font-size:17px;font-weight:800;color:#0f172a;letter-spacing:-0.02em;margin-bottom:3px;">Animesh Koner</p>
    <p style="font-size:12px;color:#1d4ed8;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;">Convin Data Labs</p>
  </div>
  <div style="background:#1d4ed8;padding:40px 44px 44px;">
    <div style="text-align:center;padding-bottom:24px;border-bottom:1px solid rgba(255,255,255,0.12);margin-bottom:28px;">
      <div style="font-size:10px;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;color:#93c5fd;margin-bottom:10px;">Quick Feedback</div>
      <div style="font-size:20px;font-weight:700;color:#fff;margin-bottom:6px;">{sq}</div>
      <div style="font-size:12px;color:rgba(255,255,255,0.4);">Takes 15 seconds · Helps us improve.</div>
    </div>
    <div style="text-align:center;margin-bottom:8px;">
      <span class="star" onclick="rate(this,1)">★</span><span class="star" onclick="rate(this,2)">★</span><span class="star" onclick="rate(this,3)">★</span><span class="star" onclick="rate(this,4)">★</span><span class="star" onclick="rate(this,5)">★</span>
    </div>
    <div style="display:flex;justify-content:space-between;margin-bottom:20px;"><span style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:rgba(255,255,255,0.2);">Not useful</span><span style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:rgba(255,255,255,0.2);">Very useful</span></div>
    <textarea style="width:100%;padding:12px 14px;background:rgba(0,0,0,0.2);border:1px solid rgba(255,255,255,0.15);color:#fff;font-family:'Inter',sans-serif;font-size:13px;resize:vertical;min-height:68px;outline:none;box-sizing:border-box;border-radius:4px;" placeholder="Additional comments (optional)"></textarea>
    <button id="sbtn" disabled onclick="thanks()" style="display:block;width:100%;margin-top:14px;padding:15px;background:#fff;color:#1d4ed8;font-size:12px;font-weight:700;letter-spacing:0.05em;text-transform:uppercase;border:none;cursor:pointer;">Submit Feedback</button>
    <div id="ty" style="display:none;text-align:center;padding:20px;"><div style="font-size:10px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:#93c5fd;margin-bottom:8px;">Thank You</div><div style="font-size:18px;color:#fff;">Your feedback has been noted.</div></div>
  </div>
  <div style="padding:22px 44px;background:#eff6ff;text-align:center;border-top:2px solid #dbeafe;">
    <div><a href="#" style="font-size:11px;color:#3b82f6;text-decoration:none;margin:0 10px;">Unsubscribe</a><a href="#" style="font-size:11px;color:#3b82f6;text-decoration:none;margin:0 10px;">Preferences</a><a href="#" style="font-size:11px;color:#3b82f6;text-decoration:none;margin:0 10px;">Privacy</a></div>
    <div style="font-size:11px;color:#93c5fd;margin-top:8px;">Convin Data Labs · Registered client communication.</div>
  </div>
</div>{js}</body></html>"""


# ─── Template 4: Modern ───────────────────────────────────────────────────────

def _tpl_modern(c, h, b, ss, sc, rl, sq):
    css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #0d0d1a; font-family: 'Inter', sans-serif; padding: 32px 16px 48px; }
.wrap { max-width: 600px; margin: 0 auto; background: #111827; border-radius: 24px; overflow: hidden; box-shadow: 0 24px 80px rgba(0,0,0,0.6); border: 1px solid #1e293b; }
.star { font-size: 28px; cursor: pointer; color: #1e293b; margin: 0 4px; display: inline-block; transition: color 0.12s; user-select: none; }
</style>"""
    js = """
<script>
let sel=0;const stars=document.querySelectorAll('.star');
function rate(el,v){sel=v;stars.forEach((s,i)=>{s.style.color=i<v?'#a78bfa':'#1e293b';});document.getElementById('sbtn').disabled=false;}
function thanks(){document.getElementById('sbtn').parentNode.style.display='none';document.getElementById('ty').style.display='block';}
</script>"""
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
  {ss_html}
  <div style="padding:36px 40px;background:#0f172a;border-bottom:1px solid #1e293b;text-align:center;">
    <div style="font-size:10px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:#475569;margin-bottom:14px;">Full Analysis</div>
    <a href="{rl}" style="display:inline-block;background:linear-gradient(135deg,#7c3aed,#a78bfa);color:#fff;text-decoration:none;font-size:12px;font-weight:600;padding:14px 44px;border-radius:10px;letter-spacing:0.03em;box-shadow:0 4px 20px rgba(124,58,237,0.35);">Open Full Report →</a>
  </div>
  <div style="padding:28px 40px 24px;background:#0f172a;border-top:1px solid #1e293b;border-bottom:1px solid #1e293b;">
    <p style="font-size:13px;color:#475569;margin-bottom:8px;">Warm regards,</p>
    <p style="font-size:16px;font-weight:700;color:#f8fafc;letter-spacing:-0.01em;margin-bottom:3px;">Animesh Koner</p>
    <p style="font-size:12px;color:#a78bfa;font-weight:500;letter-spacing:0.05em;">Convin Data Labs</p>
  </div>
  <div style="background:#0d0d1a;padding:40px 40px 44px;border-top:1px solid #1e293b;">
    <div style="text-align:center;padding-bottom:24px;border-bottom:1px solid #1e293b;margin-bottom:28px;">
      <div style="font-size:9px;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;color:#a78bfa;margin-bottom:10px;">Quick Feedback</div>
      <div style="font-size:19px;font-weight:600;color:#e2e8f0;margin-bottom:6px;">{sq}</div>
      <div style="font-size:12px;color:#334155;">Takes 15 seconds · Helps us improve.</div>
    </div>
    <div style="text-align:center;margin-bottom:8px;">
      <span class="star" onclick="rate(this,1)">★</span><span class="star" onclick="rate(this,2)">★</span><span class="star" onclick="rate(this,3)">★</span><span class="star" onclick="rate(this,4)">★</span><span class="star" onclick="rate(this,5)">★</span>
    </div>
    <div style="display:flex;justify-content:space-between;margin-bottom:20px;"><span style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:#1e293b;">Not useful</span><span style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:#1e293b;">Very useful</span></div>
    <textarea style="width:100%;padding:12px 14px;background:#111827;border:1px solid #1e293b;color:#94a3b8;font-family:'Inter',sans-serif;font-size:13px;resize:vertical;min-height:68px;outline:none;box-sizing:border-box;border-radius:8px;" placeholder="Additional comments (optional)"></textarea>
    <button id="sbtn" disabled onclick="thanks()" style="display:block;width:100%;margin-top:14px;padding:14px;background:linear-gradient(135deg,#7c3aed,#a78bfa);color:#fff;font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;border:none;border-radius:8px;cursor:pointer;">Submit Feedback</button>
    <div id="ty" style="display:none;text-align:center;padding:20px;"><div style="font-size:9px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:#a78bfa;margin-bottom:8px;">Thank You</div><div style="font-size:18px;color:#e2e8f0;">Your feedback has been noted.</div></div>
  </div>
  <div style="padding:20px 40px;background:#0d0d1a;text-align:center;border-top:1px solid #1e293b;">
    <div><a href="#" style="font-size:11px;color:#334155;text-decoration:none;margin:0 10px;">Unsubscribe</a><a href="#" style="font-size:11px;color:#334155;text-decoration:none;margin:0 10px;">Preferences</a><a href="#" style="font-size:11px;color:#334155;text-decoration:none;margin:0 10px;">Privacy</a></div>
    <div style="font-size:11px;color:#1e293b;margin-top:6px;">Convin Data Labs · Registered client communication.</div>
  </div>
</div>{js}</body></html>"""


# ─── Template 5: Classic ──────────────────────────────────────────────────────

def _tpl_classic(c, h, b, ss, sc, rl, sq):
    css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=Lora:wght@400;500;600&display=swap');
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #f0e6d3; font-family: 'Lora', Georgia, serif; color: #1a0a00; padding: 32px 16px 48px; }
.wrap { max-width: 600px; margin: 0 auto; background: #fffef9; border: 1px solid #d5c4a8; box-shadow: 0 4px 24px rgba(100,60,0,0.1); }
.star { font-size: 28px; cursor: pointer; color: #d5c4a8; margin: 0 4px; display: inline-block; transition: color 0.12s; user-select: none; }
.orn { color: #c9a96e; text-align: center; letter-spacing: 8px; font-size: 14px; }
</style>"""
    js = """
<script>
let sel=0;const stars=document.querySelectorAll('.star');
function rate(el,v){sel=v;stars.forEach((s,i)=>{s.style.color=i<v?'#c9a96e':'#d5c4a8';});document.getElementById('sbtn').disabled=false;}
function thanks(){document.getElementById('sbtn').parentNode.style.display='none';document.getElementById('ty').style.display='block';}
</script>"""
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
  {ss_html}
  <div style="padding:36px 48px;background:#faf5ed;border-bottom:1px solid #d5c4a8;text-align:center;">
    <div style="font-size:10px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:#8b7355;margin-bottom:14px;">Full Report Available</div>
    <a href="{rl}" style="display:inline-block;border:1.5px solid #2c1a0e;color:#2c1a0e;text-decoration:none;font-family:'Playfair Display',serif;font-size:13px;padding:12px 40px;letter-spacing:0.04em;">Open Full Report</a>
  </div>
  <div style="padding:32px 48px 28px;border-bottom:1px solid #d5c4a8;">
    <p style="font-size:14px;color:#8b7355;font-style:italic;margin-bottom:10px;">Warm regards,</p>
    <p style="font-family:'Playfair Display',serif;font-size:18px;color:#2c1a0e;margin-bottom:4px;">Animesh Koner</p>
    <p style="font-size:12px;color:#c9a96e;letter-spacing:0.08em;text-transform:uppercase;font-weight:600;">Convin Data Labs</p>
    <div style="width:48px;height:1px;background:#c9a96e;margin-top:16px;"></div>
  </div>
  <div style="padding:36px 48px;border-bottom:1px solid #d5c4a8;">
    <div style="text-align:center;margin-bottom:22px;">
      <div style="font-size:10px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:#c9a96e;margin-bottom:10px;">Quick Feedback</div>
      <div style="font-family:'Playfair Display',serif;font-size:19px;color:#1a0a00;margin-bottom:6px;font-style:italic;">{sq}</div>
      <div style="font-size:12px;color:#8b7355;">Takes 15 seconds · Helps us improve.</div>
    </div>
    <div style="text-align:center;margin-bottom:8px;">
      <span class="star" onclick="rate(this,1)">★</span><span class="star" onclick="rate(this,2)">★</span><span class="star" onclick="rate(this,3)">★</span><span class="star" onclick="rate(this,4)">★</span><span class="star" onclick="rate(this,5)">★</span>
    </div>
    <div style="display:flex;justify-content:space-between;margin-bottom:20px;"><span style="font-size:11px;color:#d5c4a8;font-style:italic;">Not useful</span><span style="font-size:11px;color:#d5c4a8;font-style:italic;">Very useful</span></div>
    <textarea style="width:100%;padding:12px 14px;background:#faf5ed;border:1px solid #d5c4a8;color:#3d2b1f;font-family:'Lora',Georgia,serif;font-size:13px;resize:vertical;min-height:68px;outline:none;box-sizing:border-box;" placeholder="Additional comments (optional)"></textarea>
    <button id="sbtn" disabled onclick="thanks()" style="display:block;width:100%;margin-top:14px;padding:13px;background:#2c1a0e;color:#c9a96e;font-size:11px;font-weight:600;letter-spacing:2px;text-transform:uppercase;border:none;cursor:pointer;font-family:'Lora',serif;">Submit Feedback</button>
    <div id="ty" style="display:none;text-align:center;padding:20px;"><div class="orn" style="font-size:16px;margin-bottom:8px;">◆</div><div style="font-family:'Playfair Display',serif;font-size:18px;color:#1a0a00;font-style:italic;">Your feedback has been noted.</div></div>
  </div>
  <div style="padding:20px 48px;background:#faf5ed;text-align:center;">
    <div class="orn" style="font-size:12px;margin-bottom:10px;">· · ·</div>
    <div><a href="#" style="font-size:11px;color:#8b7355;text-decoration:none;margin:0 10px;">Unsubscribe</a><a href="#" style="font-size:11px;color:#8b7355;text-decoration:none;margin:0 10px;">Preferences</a><a href="#" style="font-size:11px;color:#8b7355;text-decoration:none;margin:0 10px;">Privacy</a></div>
    <div style="font-size:11px;color:#c9a96e;margin-top:8px;">Convin Data Labs · Registered client communication.</div>
  </div>
</div>{js}</body></html>"""
