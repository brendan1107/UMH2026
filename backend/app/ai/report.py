# PDF generation

# app/ai/report.py
# pip install weasyprint jinja2
from jinja2 import Template
from weasyprint import HTML
from app.ai.schemas import BusinessCase, AuditResult

REPORT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<style>
  body { font-family: sans-serif; padding: 40px; color: #111; }
  h1   { font-size: 28px; margin-bottom: 4px; }
  .verdict-GO    { color: #15803d; }
  .verdict-PIVOT { color: #b45309; }
  .verdict-STOP  { color: #b91c1c; }
  .section { margin-top: 32px; }
  .section h2 { font-size: 16px; border-bottom: 1px solid #eee; padding-bottom: 6px; }
  table { width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 13px; }
  td, th { padding: 8px 12px; border: 1px solid #eee; text-align: left; }
  th { background: #f9f9f9; font-weight: 600; }
  .risk-high   { color: #b91c1c; }
  .risk-medium { color: #b45309; }
  .risk-low    { color: #1d4ed8; }
</style>
</head>
<body>

<h1>F&B Genie Feasibility Report</h1>
<p style="color:#666;font-size:13px">{{ case.idea }} — {{ case.location }}</p>

<div class="section">
  <h2>Verdict</h2>
  <p class="verdict-{{ verdict.decision }}" style="font-size:24px;font-weight:700">
    {{ verdict.decision }}
  </p>
  <p>Confidence: {{ (verdict.confidence * 100) | round }}%</p>
  <p>{{ verdict.summary }}</p>
  {% if verdict.pivot_suggestion %}
  <p><strong>Suggested pivot:</strong> {{ verdict.pivot_suggestion }}</p>
  {% endif %}
</div>

<div class="section">
  <h2>Key numbers</h2>
  <table>
    <tr><th>Metric</th><th>Value</th></tr>
    <tr><td>Competitors within 1km</td><td>{{ case.fact_sheet.competitor_count }}</td></tr>
    <tr><td>Avg competitor rating</td><td>{{ case.fact_sheet.avg_competitor_rating }}/5</td></tr>
    <tr><td>Estimated lunch footfall</td><td>{{ case.fact_sheet.estimated_footfall_lunch }} pax/hr</td></tr>
    <tr><td>Break-even covers/day</td><td>{{ case.fact_sheet.break_even_covers }}</td></tr>
    <tr><td>Months to break even</td><td>{{ case.fact_sheet.months_to_breakeven }}</td></tr>
  </table>
</div>

<div class="section">
  <h2>Risk analysis</h2>
  {% for risk in audit.risks %}
  <div style="margin-bottom:16px;padding:12px;border:1px solid #eee;border-radius:8px">
    <p class="risk-{{ risk.severity }}" style="font-weight:600;margin:0 0 4px">
      [{{ risk.severity | upper }}] {{ risk.title }}
    </p>
    <p style="font-size:13px;margin:0 0 4px">{{ risk.reasoning }}</p>
    <p style="font-size:12px;color:#2563eb;margin:0">Mitigation: {{ risk.mitigation }}</p>
  </div>
  {% endfor %}
</div>

</body>
</html>
"""

async def generate_report(
    case: BusinessCase,
    verdict,
    audit: AuditResult,
) -> bytes:
    """Returns PDF bytes. Your teammate streams this to the browser."""
    html_str = Template(REPORT_TEMPLATE).render(
        case=case,
        verdict=verdict,
        audit=audit,
    )
    pdf_bytes = HTML(string=html_str).write_pdf()
    return pdf_bytes
