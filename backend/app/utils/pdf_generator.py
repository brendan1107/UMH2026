from __future__ import annotations

import html
import io
from datetime import datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


SEVERITY_LABEL = {"high": "HIGH", "medium": "MEDIUM", "low": "LOW"}
DECISION_LABEL = {
    "GO": "GO - Proceed",
    "PIVOT": "PIVOT - Change approach",
    "STOP": "STOP - Do not proceed",
}
DECISION_COLORS = {
    "GO": colors.HexColor("#15803d"),
    "PIVOT": colors.HexColor("#b45309"),
    "STOP": colors.HexColor("#b91c1c"),
}
SEVERITY_COLORS = {
    "high": colors.HexColor("#b91c1c"),
    "medium": colors.HexColor("#b45309"),
    "low": colors.HexColor("#1d4ed8"),
}


def _safe(value: Any) -> str:
    """Keep generated PDFs compatible with ReportLab's built-in Helvetica font."""
    if value is None or value == "":
        return "-"

    text = str(value)
    replacements = {
        "\u2014": "-",
        "\u2013": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2022": "*",
        "\u00a0": " ",
        "\u2026": "...",
    }
    for source, replacement in replacements.items():
        text = text.replace(source, replacement)

    return text.encode("latin-1", errors="ignore").decode("latin-1")


def _paragraph(text: Any, style: ParagraphStyle) -> Paragraph:
    return Paragraph(html.escape(_safe(text)).replace("\n", "<br/>"), style)


def _money(value: Any) -> str:
    try:
        return f"RM {float(str(value).replace(',', '')):,.0f}"
    except (TypeError, ValueError):
        return "RM -"


def _confidence(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "-"

    if number <= 1:
        number *= 100
    return f"{number:.0f}%"


class PDFGenerator:
    def generate_feasibility_report(
        self,
        case_id: str,
        idea: str,
        location: str,
        budget_myr: float,
        verdict: dict,
        fact_sheet: dict,
        audit_risks: list,
        strengths: list[str] | None = None,
    ) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            topMargin=1.8 * cm,
            bottomMargin=1.8 * cm,
            title="F&B Genie Feasibility Report",
        )

        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle("Meta", parent=styles["Normal"], fontSize=9, textColor=colors.HexColor("#64748b")))
        styles.add(ParagraphStyle("Small", parent=styles["Normal"], fontSize=9, leading=12))

        story = [
            _paragraph("F&B Genie Feasibility Report", styles["Title"]),
            _paragraph(f"{idea} - {location}", styles["Meta"]),
            _paragraph(f"Generated: {datetime.utcnow().strftime('%d %b %Y %H:%M UTC')}", styles["Meta"]),
            Spacer(1, 0.35 * cm),
        ]

        decision = _safe(verdict.get("decision")).upper()
        verdict_style = ParagraphStyle(
            "Verdict",
            parent=styles["Heading1"],
            fontSize=22,
            leading=27,
            textColor=DECISION_COLORS.get(decision, colors.HexColor("#334155")),
            spaceAfter=4,
        )

        story.extend(
            [
                _paragraph("Verdict", styles["Heading2"]),
                _paragraph(DECISION_LABEL.get(decision, decision), verdict_style),
                _paragraph(f"Confidence: {_confidence(verdict.get('confidence'))}", styles["Normal"]),
                Spacer(1, 0.12 * cm),
                _paragraph(verdict.get("summary") or "No verdict summary was generated.", styles["Normal"]),
            ]
        )

        pivot_suggestion = verdict.get("pivot_suggestion")
        if pivot_suggestion:
            story.extend(
                [
                    Spacer(1, 0.15 * cm),
                    _paragraph(f"Suggested pivot: {pivot_suggestion}", styles["Normal"]),
                ]
            )

        story.append(Spacer(1, 0.45 * cm))

        story.append(_paragraph("Key Numbers", styles["Heading2"]))
        table_rows = [
            ["Metric", "Value"],
            ["Competitors within 1km", _safe(fact_sheet.get("competitor_count"))],
            ["Average competitor rating", f"{_safe(fact_sheet.get('avg_competitor_rating'))}/5"],
            ["Lunch footfall estimate", f"{_safe(fact_sheet.get('estimated_footfall_lunch'))} pax/hr"],
            ["Break-even covers/day", _safe(fact_sheet.get("break_even_covers"))],
            ["Months to break even", _safe(fact_sheet.get("months_to_breakeven"))],
            ["Confirmed monthly rent", _money(fact_sheet.get("confirmed_rent_myr"))],
            ["Starting budget", _money(budget_myr)],
        ]
        story.append(self._table(table_rows))
        story.append(Spacer(1, 0.45 * cm))

        if strengths:
            story.append(_paragraph("Key Strengths", styles["Heading2"]))
            for strength in strengths:
                story.append(_paragraph(f"- {strength}", styles["Normal"]))
            story.append(Spacer(1, 0.35 * cm))

        story.append(_paragraph("Risk Analysis", styles["Heading2"]))
        if audit_risks:
            for risk in audit_risks:
                if isinstance(risk, str):
                    story.append(_paragraph(risk, styles["Normal"]))
                    story.append(Spacer(1, 0.2 * cm))
                    continue

                severity = _safe(risk.get("severity", "low")).lower()
                title_style = ParagraphStyle(
                    f"RiskTitle-{len(story)}",
                    parent=styles["Heading3"],
                    fontSize=11,
                    leading=14,
                    textColor=SEVERITY_COLORS.get(severity, colors.HexColor("#334155")),
                    spaceAfter=2,
                )
                category = _safe(risk.get("category", "")).upper()
                label = SEVERITY_LABEL.get(severity, severity.upper())
                title = _safe(risk.get("title", "Risk"))
                story.append(_paragraph(f"[{label}] [{category}] {title}", title_style))
                story.append(_paragraph(risk.get("reasoning") or "-", styles["Small"]))
                if risk.get("mitigation"):
                    story.append(_paragraph(f"Mitigation: {risk.get('mitigation')}", styles["Small"]))
                story.append(Spacer(1, 0.25 * cm))
        else:
            story.append(_paragraph("No major risks were recorded for this report.", styles["Normal"]))

        doc.build(story, onFirstPage=self._footer(case_id), onLaterPages=self._footer(case_id))
        return buffer.getvalue()

    def _table(self, rows: list[list[str]]) -> Table:
        table = Table(rows, colWidths=[8.3 * cm, 7.2 * cm], hAlign="LEFT")
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        return table

    def _footer(self, case_id: str):
        def draw(canvas, doc):
            canvas.saveState()
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(colors.HexColor("#94a3b8"))
            canvas.drawCentredString(
                A4[0] / 2,
                1 * cm,
                _safe(f"F&B Genie | Case: {case_id[:8]} | AI-generated report - verify key assumptions before acting"),
            )
            canvas.restoreState()

        return draw
