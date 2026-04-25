# app/utils/pdf_generator.py — full corrected file
from fpdf import FPDF
from datetime import datetime

SEVERITY_LABEL = {"high": "[HIGH]", "medium": "[MED]", "low": "[LOW]"}
DECISION_LABEL = {
    "GO":    "GO - Proceed",
    "PIVOT": "PIVOT - Change approach",
    "STOP":  "STOP - Do not proceed",
}

def _safe(text: str) -> str:
    """Strip characters unsupported by Helvetica latin-1."""
    replacements = {
        "\u2014": "-", "\u2013": "-",
        "\u2018": "'", "\u2019": "'",
        "\u201c": '"', "\u201d": '"',
        "\u2022": "*", "\u00a0": " ",
        "\u2026": "...",
    }
    s = str(text)
    for k, v in replacements.items():
        s = s.replace(k, v)
    # Drop any remaining non-latin-1 characters
    return s.encode("latin-1", errors="ignore").decode("latin-1")


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
    ) -> bytes:

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()
        pdf.set_left_margin(20)
        pdf.set_right_margin(20)
        effective_w = pdf.w - 40   # 210 - 40 = 170mm usable

        # ── Header ──────────────────────────────────────────
        pdf.set_font("Helvetica", "B", 20)
        pdf.set_text_color(17, 17, 17)
        pdf.cell(0, 10, "F&B Genie Feasibility Report", ln=True)

        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 6, _safe(f"{idea} - {location}"), ln=True)
        pdf.cell(0, 6, f"Generated: {datetime.utcnow().strftime('%d %b %Y %H:%M UTC')}", ln=True)
        pdf.ln(4)

        # ── Verdict ──────────────────────────────────────────
        self._section_title(pdf, "Verdict")

        decision   = verdict.get("decision", "-")
        confidence = verdict.get("confidence", 0)
        colors = {"GO": (21,128,61), "PIVOT": (180,83,9), "STOP": (185,28,28)}
        r, g, b = colors.get(decision, (50, 50, 50))

        pdf.set_font("Helvetica", "B", 22)
        pdf.set_text_color(r, g, b)
        pdf.cell(0, 12, DECISION_LABEL.get(decision, decision), ln=True)

        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(17, 17, 17)
        pdf.cell(0, 7, f"Confidence: {int(confidence * 100)}%", ln=True)
        pdf.ln(2)

        pdf.set_x(20)
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(17, 17, 17)
        pdf.multi_cell(effective_w, 6, _safe(verdict.get("summary", "")))

        pivot = verdict.get("pivot_suggestion")
        if pivot:
            pdf.ln(2)
            pdf.set_x(20)
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(17, 17, 17)
            pdf.cell(0, 7, "Suggested pivot:", ln=True)
            pdf.set_x(20)
            pdf.set_font("Helvetica", "", 11)
            pdf.multi_cell(effective_w, 6, _safe(pivot))
        pdf.ln(4)

        # ── Key numbers ──────────────────────────────────────
        self._section_title(pdf, "Key Numbers")

        rows = [
            ("Competitors within 1km",  str(fact_sheet.get("competitor_count", "-"))),
            ("Avg competitor rating",    f"{fact_sheet.get('avg_competitor_rating', '-')}/5"),
            ("Lunch footfall estimate",  f"{fact_sheet.get('estimated_footfall_lunch', '-')} pax/hr"),
            ("Break-even covers/day",    str(fact_sheet.get("break_even_covers", "-"))),
            ("Months to break even",     str(fact_sheet.get("months_to_breakeven", "-"))),
            ("Confirmed monthly rent",   f"RM {fact_sheet.get('confirmed_rent_myr', '-')}"),
            ("Starting budget",          f"RM {int(budget_myr):,}"),
        ]

        col_w = effective_w / 2
        pdf.set_font("Helvetica", "", 10)
        for label, value in rows:
            pdf.set_x(20)
            pdf.set_fill_color(245, 245, 245)
            pdf.set_text_color(17, 17, 17)
            pdf.cell(col_w, 8, f"  {_safe(label)}", border=1, fill=True)
            pdf.cell(col_w, 8, f"  {_safe(value)}", border=1, ln=True)
        pdf.ln(4)

        # ── Risk analysis ─────────────────────────────────────
        self._section_title(pdf, "Risk Analysis")

        risk_colors = {"high": (185,28,28), "medium": (180,83,9), "low": (29,78,216)}

        for risk in audit_risks:
            sev = risk.get("severity", "low")
            r2, g2, b2 = risk_colors.get(sev, (50, 50, 50))

            # Risk title
            pdf.set_x(20)
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(r2, g2, b2)
            title_text = _safe(
                f"{SEVERITY_LABEL.get(sev,'')} "
                f"[{risk.get('category','').upper()}] "
                f"{risk.get('title','')}"
            )
            pdf.multi_cell(effective_w, 7, title_text)

            # Reasoning
            pdf.set_x(20)
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(17, 17, 17)
            pdf.multi_cell(effective_w, 5, _safe(risk.get("reasoning", "")))

            # Mitigation
            pdf.set_x(20)
            pdf.set_font("Helvetica", "I", 10)
            pdf.set_text_color(37, 99, 235)
            pdf.multi_cell(effective_w, 5, _safe(f"Mitigation: {risk.get('mitigation', '')}"))

            pdf.set_text_color(17, 17, 17)
            pdf.ln(4)

        # ── Footer ────────────────────────────────────────────
        pdf.set_y(-18)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(150, 150, 150)
        pdf.set_x(20)
        pdf.cell(
            effective_w, 5,
            _safe(f"F&B Genie | Case: {case_id[:8]} | AI-generated - verify with professional advisors"),
            align="C"
        )

        return bytes(pdf.output())

    def _section_title(self, pdf: FPDF, title: str):
        pdf.set_x(20)
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(17, 17, 17)
        pdf.cell(0, 8, title, ln=True)
        pdf.set_draw_color(200, 200, 200)
        pdf.line(20, pdf.get_y(), pdf.w - 20, pdf.get_y())
        pdf.ln(4)