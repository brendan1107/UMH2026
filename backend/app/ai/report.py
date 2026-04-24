# app/ai/report.py
#pip install reportlab

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_LEFT
import io

from app.ai.schemas import BusinessCase, AuditResult

VERDICT_COLORS = {
    "GO":    colors.HexColor("#15803d"),
    "PIVOT": colors.HexColor("#b45309"),
    "STOP":  colors.HexColor("#b91c1c"),
}

SEVERITY_COLORS = {
    "high":   colors.HexColor("#b91c1c"),
    "medium": colors.HexColor("#b45309"),
    "low":    colors.HexColor("#1d4ed8"),
}


async def generate_report(case: BusinessCase, verdict, audit: AuditResult) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)

    styles = getSampleStyleSheet()
    story = []

    # ── Title ──
    story.append(Paragraph("F&B Genie Feasibility Report", styles["Title"]))
    story.append(Paragraph(f"{case.idea} — {case.location}", styles["Normal"]))
    story.append(Spacer(1, 0.5*cm))

    # ── Verdict ──
    verdict_color = VERDICT_COLORS.get(verdict.decision, colors.black)
    verdict_style = ParagraphStyle("verdict", fontSize=24, textColor=verdict_color, spaceAfter=6)
    story.append(Paragraph("Verdict", styles["Heading2"]))
    story.append(Paragraph(verdict.decision, verdict_style))
    story.append(Paragraph(f"Confidence: {verdict.confidence * 100:.0f}%", styles["Normal"]))
    story.append(Paragraph(verdict.summary, styles["Normal"]))
    if verdict.pivot_suggestion:
        story.append(Paragraph(f"<b>Suggested pivot:</b> {verdict.pivot_suggestion}", styles["Normal"]))
    story.append(Spacer(1, 0.5*cm))

    # ── Key Numbers ──
    story.append(Paragraph("Key Numbers", styles["Heading2"]))
    fs = case.fact_sheet
    table_data = [
        ["Metric", "Value"],
        ["Competitors within 1km",    str(fs.get("competitor_count", "—"))],
        ["Avg competitor rating",     str(fs.get("avg_competitor_rating", "—")) + "/5"],
        ["Estimated lunch footfall",  str(fs.get("estimated_footfall_lunch", "—")) + " pax/hr"],
        ["Break-even covers/day",     str(fs.get("break_even_covers", "—"))],
        ["Months to break even",      str(fs.get("months_to_breakeven", "—"))],
    ]
    table = Table(table_data, colWidths=[10*cm, 6*cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f9f9f9")),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID",       (0, 0), (-1, -1), 0.5, colors.HexColor("#eeeeee")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafafa")]),
        ("PADDING",    (0, 0), (-1, -1), 8),
    ]))
    story.append(table)
    story.append(Spacer(1, 0.5*cm))

    # ── Risk Analysis ──
    story.append(Paragraph("Risk Analysis", styles["Heading2"]))
    for risk in audit.risks:
        risk_color = SEVERITY_COLORS.get(risk.severity, colors.black)
        label_style = ParagraphStyle("risk_label", textColor=risk_color, fontName="Helvetica-Bold", spaceAfter=2)
        story.append(Paragraph(f"[{risk.severity.upper()}] {risk.title}", label_style))
        story.append(Paragraph(risk.reasoning, styles["Normal"]))
        story.append(Paragraph(f"<b>Mitigation:</b> {risk.mitigation}", styles["Normal"]))
        story.append(Spacer(1, 0.3*cm))

    doc.build(story)
    return buffer.getvalue()