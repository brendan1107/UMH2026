"""PDF report generation helpers."""

from html import escape
from pathlib import Path
from typing import Any

from reportlab.lib.pagesizes import letter
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from reportlab.lib.styles import getSampleStyleSheet


class PDFGenerator:
    """Generate a downloadable business report PDF."""

    def generate(self, report_data: dict, output_path: str) -> str:
        """Generate a PDF report and return the output path."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        doc = SimpleDocTemplate(
            str(path),
            pagesize=letter,
            title="F&B Genie Business Report",
            leftMargin=48,
            rightMargin=48,
            topMargin=48,
            bottomMargin=48,
        )
        styles = getSampleStyleSheet()
        story = [
            Paragraph("F&B Genie Business Report", styles["Title"]),
            Spacer(1, 12),
        ]

        self._append_section(story, styles, "Case", report_data.get("case"))
        self._append_section(story, styles, "Recommendation", report_data.get("recommendation"))
        self._append_section(story, styles, "Facts", report_data.get("facts"))
        self._append_section(story, styles, "Evidence", report_data.get("evidence"))
        self._append_section(story, styles, "Tasks", report_data.get("tasks"))

        doc.build(story)
        return str(path)

    def _append_section(self, story: list, styles: dict, title: str, value: Any) -> None:
        story.append(Paragraph(escape(title), styles["Heading2"]))
        for line in self._format_value(value):
            story.append(Paragraph(escape(line), styles["BodyText"]))
        story.append(Spacer(1, 10))

    def _format_value(self, value: Any) -> list[str]:
        if value is None:
            return ["No data available."]
        if isinstance(value, dict):
            return [
                f"{self._label(key)}: {self._scalar_text(item)}"
                for key, item in value.items()
                if item not in (None, "", [], {})
            ] or ["No data available."]
        if isinstance(value, list):
            if not value:
                return ["No data available."]
            lines = []
            for index, item in enumerate(value, start=1):
                if isinstance(item, dict):
                    summary = "; ".join(
                        f"{self._label(key)}: {self._scalar_text(data)}"
                        for key, data in item.items()
                        if data not in (None, "", [], {})
                    )
                    lines.append(f"{index}. {summary or 'No details'}")
                else:
                    lines.append(f"{index}. {self._scalar_text(item)}")
            return lines
        return [self._scalar_text(value)]

    @staticmethod
    def _label(value: str) -> str:
        return str(value).replace("_", " ").replace("-", " ").title()

    @staticmethod
    def _scalar_text(value: Any) -> str:
        if isinstance(value, (dict, list)):
            return str(value)
        return str(value)
