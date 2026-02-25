"""
Generates the Convin Data Labs report email HTML from a draft dict.
Fields used: client, headline, body, screenshot_url, screenshot_caption,
             report_link, survey_question.
"""

EMAIL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600&family=Inter:wght@400;500;600;700&display=swap');
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #e8e3db; font-family: 'Inter', sans-serif; color: #1c1c1c; padding: 32px 16px 48px; }
.wrap { max-width: 600px; margin: 0 auto; background: #fff; box-shadow: 0 8px 48px rgba(0,0,0,0.15); }

/* Header */
.header { background: #0d1b2a; padding: 24px 44px; border-bottom: 3px solid #b8962e; display: flex; align-items: center; justify-content: space-between; }
.brand  { font-family: 'Playfair Display', serif; font-size: 17px; color: #fff; letter-spacing: 2px; text-transform: uppercase; }
.live-dot { width: 7px; height: 7px; border-radius: 50%; background: #10b981; display: inline-block; margin-right: 5px; }

/* Recipient bar */
.recipient-bar { background: #faf9f7; border-bottom: 1px solid #e4ded6; padding: 10px 44px; }
.recipient-bar span { font-size: 11px; color: #9c8e80; }
.recipient-bar strong { color: #4a4a4a; font-weight: 600; }

/* Hero */
.hero { padding: 44px 44px 36px; border-bottom: 1px solid #ede8e0; }
.kicker { font-size: 10px; font-weight: 700; letter-spacing: 2.5px; text-transform: uppercase; color: #b8962e; margin-bottom: 14px; }
.hero h1 { font-family: 'Playfair Display', serif; font-size: 26px; font-weight: 600; line-height: 1.3; color: #0d1b2a; margin-bottom: 18px; }
.hero-rule { width: 44px; height: 2px; background: #b8962e; margin: 0 0 20px; }
.hero-body { font-size: 14px; line-height: 1.85; color: #4a4a4a; }

/* Screenshot */
.screenshot-section { padding: 32px 44px; border-bottom: 1px solid #ede8e0; }
.screenshot-section img { width: 100%; display: block; border: 1px solid #ddd8d0; }
.screenshot-caption { font-size: 11px; color: #9c8e80; font-style: italic; margin-top: 10px; }

/* CTA */
.cta-block { padding: 40px 44px; background: #faf9f7; border-bottom: 1px solid #ede8e0; text-align: center; }
.cta-eyebrow { font-size: 10px; font-weight: 700; letter-spacing: 2.5px; text-transform: uppercase; color: #9c8e80; margin-bottom: 10px; }
.cta-heading { font-family: 'Playfair Display', serif; font-size: 20px; color: #0d1b2a; margin-bottom: 24px; }
.cta-btn { display: inline-block; background: #0d1b2a; color: #fff; text-decoration: none; font-size: 11px; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; padding: 14px 40px; }

/* Survey */
.survey-wrap { background: #0d1b2a; padding: 40px 44px 44px; }
.survey-top  { text-align: center; padding-bottom: 24px; border-bottom: 1px solid #1e3050; margin-bottom: 28px; }
.survey-kicker  { font-size: 10px; font-weight: 700; letter-spacing: 2.5px; text-transform: uppercase; color: #b8962e; margin-bottom: 10px; }
.survey-heading { font-family: 'Playfair Display', serif; font-size: 20px; font-weight: 400; color: #f0ede8; margin-bottom: 6px; }
.survey-sub     { font-size: 12px; color: #4a6a8a; }
.stars-row { display: flex; justify-content: center; gap: 8px; margin-bottom: 10px; }
.star { width: 52px; height: 52px; background: #0a1520; border: 1px solid #1e3050; color: #1e3050; font-size: 24px; display: flex; align-items: center; justify-content: center; cursor: pointer; user-select: none; }
.star-scale { display: flex; justify-content: space-between; margin-bottom: 24px; }
.star-scale span { font-size: 10px; letter-spacing: 1px; text-transform: uppercase; color: #2a4a6a; }
.field-label { display: block; font-size: 10px; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; color: #4a6a8a; margin-bottom: 8px; }
.field-input { width: 100%; padding: 12px 14px; background: #080f18; border: 1px solid #1e3050; color: #c8d8e8; font-family: 'Inter', sans-serif; font-size: 13px; resize: vertical; min-height: 72px; outline: none; }
.submit-btn { display: block; width: 100%; margin-top: 18px; padding: 15px; background: #b8962e; color: #0d1b2a; font-size: 11px; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; border: none; cursor: pointer; }
#ty { display:none; text-align:center; padding:20px; }

/* Footer */
.footer { padding: 22px 44px; background: #faf9f7; border-top: 1px solid #ede8e0; text-align: center; }
.footer-links a { font-size: 11px; color: #9c8e80; text-decoration: none; margin: 0 10px; }
.footer-addr { font-size: 11px; color: #c0b8ae; line-height: 1.8; margin-top: 8px; }
</style>
"""


def build_email_html(draft: dict) -> str:
    client       = draft.get("client") or "—"
    headline     = draft.get("headline") or "—"
    body         = draft.get("body") or draft.get("intro") or ""
    screenshot   = draft.get("screenshot_url") or ""
    caption      = draft.get("screenshot_caption") or ""
    report_link  = draft.get("report_link") or "#"
    survey_q     = draft.get("survey_question") or "Was this report useful to you?"

    screenshot_html = ""
    if screenshot:
        screenshot_html = f"""
  <div class="screenshot-section">
    <img src="{screenshot}" alt="Report screenshot"/>
    {"<p class='screenshot-caption'>" + caption + "</p>" if caption else ""}
  </div>"""

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
{EMAIL_CSS}
</head><body>
<div class="wrap">

  <div class="header">
    <div class="brand">Convin Data Labs</div>
    <div style="font-size:11px;color:#4a6a8a;">Report · Animesh Koner</div>
  </div>

  <div class="recipient-bar">
    <span>Prepared for <strong>{client}</strong></span>
  </div>

  <div class="hero">
    <div class="kicker">Executive Summary</div>
    <h1>{headline}</h1>
    <div class="hero-rule"></div>
    <p class="hero-body">{body}</p>
  </div>

{screenshot_html}

  <div class="cta-block">
    <div class="cta-eyebrow">Full Report</div>
    <div class="cta-heading">Access the complete analysis</div>
    <a href="{report_link}" class="cta-btn">Open Full Report</a>
  </div>

  <div class="survey-wrap">
    <div class="survey-top">
      <div class="survey-kicker">Quick Feedback</div>
      <div class="survey-heading">{survey_q}</div>
      <div class="survey-sub">Takes 15 seconds · Helps us improve future reports.</div>
    </div>
    <div class="stars-row">
      <div class="star" onclick="rate(this,1)">★</div>
      <div class="star" onclick="rate(this,2)">★</div>
      <div class="star" onclick="rate(this,3)">★</div>
      <div class="star" onclick="rate(this,4)">★</div>
      <div class="star" onclick="rate(this,5)">★</div>
    </div>
    <div class="star-scale"><span>Not useful</span><span>Somewhat</span><span>Very useful</span></div>
    <label class="field-label">Additional comments (optional)</label>
    <textarea class="field-input" placeholder="Share your thoughts…" rows="2"></textarea>
    <button class="submit-btn" id="sbtn" disabled onclick="thanks()">Submit Feedback</button>
    <div id="ty">
      <div style="font-size:10px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:#b8962e;margin-bottom:10px;">Thank You</div>
      <div style="font-family:serif;font-size:18px;color:#f0ede8;">Your feedback has been noted.</div>
    </div>
  </div>

  <div class="footer">
    <div class="footer-links">
      <a href="#">Unsubscribe</a><a href="#">Preferences</a><a href="#">Privacy</a>
    </div>
    <div class="footer-addr">Convin Data Labs · You are receiving this as a registered client.</div>
  </div>

</div>
<script>
let sel=0;
const stars=document.querySelectorAll('.star');
function rate(el,v){{
  sel=v;
  stars.forEach((s,i)=>{{s.style.color=i<v?'#b8962e':'#1e3050';s.style.borderColor=i<v?'#b8962e':'#1e3050';}});
  document.getElementById('sbtn').disabled=false;
}}
function thanks(){{
  document.getElementById('sbtn').parentNode.style.display='none';
  document.getElementById('ty').style.display='block';
}}
</script>
</body></html>"""
