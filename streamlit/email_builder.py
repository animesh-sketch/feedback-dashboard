"""
Generates the LivePure report email HTML from a draft dict.
Called by app.py → render_drafts_tab → preview button.
"""

EMAIL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600&family=Inter:wght@400;500;600;700&display=swap');
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #e8e3db; font-family: 'Inter', sans-serif; color: #1c1c1c; padding: 32px 16px 48px; }
.wrap { max-width: 600px; margin: 0 auto; background: #fff; box-shadow: 0 8px 48px rgba(0,0,0,0.15); }
.header { background: #0d1b2a; padding: 26px 44px; border-bottom: 3px solid #b8962e; display: flex; align-items: center; justify-content: space-between; }
.brand { font-family: 'Playfair Display', serif; font-size: 17px; font-weight: 400; color: #fff; letter-spacing: 2px; text-transform: uppercase; }
.header-right { text-align: right; }
.report-type { font-size: 10px; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; color: #b8962e; }
.report-date { font-size: 11px; color: #4a6a8a; margin-top: 3px; }
.recipient-bar { background: #faf9f7; border-bottom: 1px solid #e4ded6; padding: 11px 44px; display: flex; justify-content: space-between; }
.recipient-bar span { font-size: 11px; color: #9c8e80; }
.recipient-bar strong { color: #4a4a4a; font-weight: 600; }
.hero { padding: 40px 44px 32px; border-bottom: 1px solid #ede8e0; }
.kicker { font-size: 10px; font-weight: 700; letter-spacing: 2.5px; text-transform: uppercase; color: #b8962e; margin-bottom: 14px; }
.hero h1 { font-family: 'Playfair Display', serif; font-size: 26px; font-weight: 600; line-height: 1.25; color: #0d1b2a; margin-bottom: 14px; }
.hero-rule { width: 44px; height: 2px; background: #b8962e; margin: 16px 0; }
.hero-body { font-size: 14px; line-height: 1.8; color: #4a4a4a; }
.kpi-strip { background: #0d1b2a; display: flex; border-bottom: 3px solid #b8962e; }
.kpi-item { flex: 1; padding: 22px 16px; text-align: center; border-right: 1px solid #1e3050; }
.kpi-item:last-child { border-right: none; }
.kpi-label { font-size: 9px; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; color: #4a6a8a; margin-bottom: 7px; }
.kpi-value { font-family: 'Playfair Display', serif; font-size: 24px; font-weight: 600; color: #f0ede8; line-height: 1; margin-bottom: 5px; }
.kpi-delta { font-size: 11px; font-weight: 600; }
.kpi-sub { font-size: 10px; color: #2a4a6a; margin-top: 2px; }
.up { color: #6abf6a; } .down { color: #e06060; }
.section { padding: 32px 44px; border-bottom: 1px solid #ede8e0; }
.section-label { font-size: 10px; font-weight: 700; letter-spacing: 2.5px; text-transform: uppercase; color: #b8962e; margin-bottom: 16px; }
.chart-full { width: 100%; border: 1px solid #ddd8d0; display: block; margin-bottom: 8px; background: #f8f6f2; }
.chart-caption { font-size: 11px; color: #9c8e80; font-style: italic; margin-bottom: 24px; }
.chart-row { display: flex; gap: 16px; margin-bottom: 8px; }
.chart-col { flex: 1; }
.chart-col img { width: 100%; border: 1px solid #ddd8d0; display: block; }
.chart-col .chart-caption { margin-bottom: 0; }
.insight-box { background: #faf9f7; border-left: 3px solid #b8962e; padding: 14px 18px; margin: 20px 0 0; }
.insight-label { font-size: 9px; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; color: #b8962e; margin-bottom: 5px; }
.insight-text { font-size: 13px; line-height: 1.7; color: #1c1c1c; }
.findings { list-style: none; border-top: 1px solid #ede8e0; margin-top: 20px; }
.findings li { display: flex; gap: 12px; padding: 12px 0; border-bottom: 1px solid #ede8e0; font-size: 13px; color: #4a4a4a; line-height: 1.6; align-items: flex-start; }
.f-num { font-size: 10px; font-weight: 700; color: #b8962e; letter-spacing: 1px; flex-shrink: 0; padding-top: 2px; width: 22px; }
.findings strong { color: #0d1b2a; }
.cta-block { padding: 40px 44px; background: #faf9f7; border-bottom: 1px solid #ede8e0; text-align: center; }
.cta-eyebrow { font-size: 10px; font-weight: 700; letter-spacing: 2.5px; text-transform: uppercase; color: #9c8e80; margin-bottom: 10px; }
.cta-heading { font-family: 'Playfair Display', serif; font-size: 20px; color: #0d1b2a; margin-bottom: 6px; }
.cta-meta { font-size: 12px; color: #9c8e80; margin-bottom: 24px; }
.cta-btn { display: inline-block; background: #0d1b2a; color: #fff; text-decoration: none; font-size: 11px; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; padding: 14px 40px; }
.survey-wrap { background: #0d1b2a; padding: 40px 44px 44px; }
.survey-top { text-align: center; padding-bottom: 24px; border-bottom: 1px solid #1e3050; margin-bottom: 28px; }
.survey-kicker { font-size: 10px; font-weight: 700; letter-spacing: 2.5px; text-transform: uppercase; color: #b8962e; margin-bottom: 10px; }
.survey-heading { font-family: 'Playfair Display', serif; font-size: 20px; font-weight: 400; color: #f0ede8; margin-bottom: 6px; }
.survey-sub { font-size: 12px; color: #4a6a8a; }
.stars-row { display: flex; justify-content: center; gap: 8px; margin-bottom: 10px; }
.star { width: 52px; height: 52px; background: #0a1520; border: 1px solid #1e3050; color: #1e3050; font-size: 24px; display: flex; align-items: center; justify-content: center; cursor: pointer; user-select: none; }
.star-scale { display: flex; justify-content: space-between; margin-bottom: 24px; }
.star-scale span { font-size: 10px; letter-spacing: 1px; text-transform: uppercase; color: #2a4a6a; }
.field-label { display: block; font-size: 10px; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; color: #4a6a8a; margin-bottom: 8px; }
.field-input { width: 100%; padding: 12px 14px; background: #080f18; border: 1px solid #1e3050; color: #c8d8e8; font-family: 'Inter', sans-serif; font-size: 13px; resize: vertical; min-height: 72px; outline: none; }
.submit-btn { display: block; width: 100%; margin-top: 18px; padding: 15px; background: #b8962e; color: #0d1b2a; font-size: 11px; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; border: none; cursor: pointer; }
.footer { padding: 24px 44px; background: #faf9f7; border-top: 1px solid #ede8e0; text-align: center; }
.footer-links { margin-bottom: 10px; }
.footer-links a { font-size: 11px; color: #9c8e80; text-decoration: none; margin: 0 10px; }
.footer-addr { font-size: 11px; color: #c0b8ae; line-height: 1.8; }
</style>
"""


def _kpi_html(kpi: dict) -> str:
    trend_cls = "up" if kpi.get("trend") == "up" else "down"
    return f"""
    <div class="kpi-item">
        <div class="kpi-label">{kpi.get('label','—')}</div>
        <div class="kpi-value">{kpi.get('value','—')}</div>
        <div class="kpi-delta {trend_cls}">{kpi.get('delta','')}</div>
        <div class="kpi-sub">{kpi.get('period','')}</div>
    </div>"""


def _finding_html(idx: int, text: str) -> str:
    if not text.strip():
        return ""
    return f'<li><span class="f-num">{idx:02d}</span><span>{text}</span></li>'


def build_email_html(draft: dict) -> str:
    kpis_html = "".join(_kpi_html(k) for k in draft.get("kpis", []))

    c1_url = draft.get("chart1_url") or "https://placehold.co/512x260/0d1b2a/b8962e?text=Chart+1"
    c2_url = draft.get("chart2_url") or "https://placehold.co/240x160/0d1b2a/b8962e?text=Chart+2"
    c3_url = draft.get("chart3_url") or "https://placehold.co/240x160/0d1b2a/b8962e?text=Chart+3"

    findings_items = "".join(
        _finding_html(i + 1, f)
        for i, f in enumerate(draft.get("findings", []))
    )

    report_link = draft.get("report_link") or "#"
    survey_q    = draft.get("survey_question") or "Was this report useful to you?"

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
{EMAIL_CSS}
</head><body>
<div class="wrap">

  <div class="header">
    <div class="brand">LivePure</div>
    <div class="header-right">
      <div class="report-type">{draft.get('report_type','Monthly Analytics Report')}</div>
      <div class="report-date">{draft.get('date','')}</div>
    </div>
  </div>

  <div class="recipient-bar">
    <span>Prepared for <strong>{draft.get('client','—')}</strong></span>
    <span>Analyst: <strong>{draft.get('analyst','Animesh Koner')}</strong></span>
  </div>

  <div class="hero">
    <div class="kicker">Executive Summary</div>
    <h1>{draft.get('headline','—')}</h1>
    <div class="hero-rule"></div>
    <p class="hero-body">{draft.get('intro','')}</p>
  </div>

  <div class="kpi-strip">{kpis_html}</div>

  <div class="section">
    <div class="section-label">Charts &amp; Visualisations</div>
    <img class="chart-full" src="{c1_url}" alt="Chart 1"/>
    <p class="chart-caption">{draft.get('chart1_caption','Fig. 1 — Replace with your chart.')}</p>
    <div class="chart-row">
      <div class="chart-col">
        <img src="{c2_url}" alt="Chart 2"/>
        <p class="chart-caption">{draft.get('chart2_caption','Fig. 2')}</p>
      </div>
      <div class="chart-col">
        <img src="{c3_url}" alt="Chart 3"/>
        <p class="chart-caption">{draft.get('chart3_caption','Fig. 3')}</p>
      </div>
    </div>
    <div class="insight-box">
      <div class="insight-label">Key Insight</div>
      <p class="insight-text">{draft.get('insight','')}</p>
    </div>
  </div>

  <div class="section">
    <div class="section-label">Top Findings</div>
    <ul class="findings">{findings_items}</ul>
  </div>

  <div class="cta-block">
    <div class="cta-eyebrow">Full Report</div>
    <div class="cta-heading">Access the complete analysis</div>
    <div class="cta-meta">Includes raw data · Methodology · Appendix</div>
    <a href="{report_link}" class="cta-btn">Open Full Report</a>
  </div>

  <div class="survey-wrap">
    <div class="survey-top">
      <div class="survey-kicker">Quick Feedback</div>
      <div class="survey-heading">{survey_q}</div>
      <div class="survey-sub">Takes 15 seconds. Helps us improve future reports.</div>
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
    <div id="ty" style="display:none;text-align:center;padding:20px;">
      <div style="font-size:10px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:#b8962e;margin-bottom:10px;">Thank You</div>
      <div style="font-family:serif;font-size:18px;color:#f0ede8;margin-bottom:6px;">Your feedback has been noted.</div>
    </div>
  </div>

  <div class="footer">
    <div class="footer-links">
      <a href="#">Unsubscribe</a><a href="#">Preferences</a><a href="#">Privacy</a>
    </div>
    <div class="footer-addr">LivePure<br/>You are receiving this report because you are a registered client.</div>
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
