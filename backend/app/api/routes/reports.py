"""
Report Routes

Handles business report generation and PDF export.
Reports are iteratively updated as the AI gathers more evidence.

Final verdict values: proceed, reconsider, do_not_open, improve, pivot, shut_down
(SAD Section 11).
"""
# This file defines the API endpoints for generating business reports and exporting 
# them as PDFs.
# The main functionalities include:
# - Retrieving the current business report and recommendation for a specific case.
# - Triggering a full report generation based on all available evidence, including facts,
# tasks, and uploaded files. The report will be iteratively updated as the AI gathers
# more information through the chat sessions.
# - Exporting the business report as a downloadable PDF file for users to save or share.
# The endpoints in this file will interact with the database to compile the report 
# content and use a PDF generation library to create the PDF file. This allows users to
#  have a comprehensive and professional report that summarizes the AI's analysis and
# recommendations for their F&B business case. The report will include the final verdict
# values such as proceed, reconsider, do_not_open, improve, pivot, shut_down based on
#  the AI's assessment of the business case. This helps users make informed decisions
#  about their business ventures. 

# For example, when a user wants to view their business report, the GET /api/cases/{case_id}/report endpoint will be called to retrieve the current report content. If they want to generate a new report based on the latest evidence, the POST /api/cases/{case_id}/report endpoint will trigger the report generation process. Finally, if they want to download the report as a PDF, the GET /api/cases/{case_id}/report/pdf endpoint will return the generated PDF file for download.

from io import BytesIO

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.db.session import get_db
from app.services.report_service import ReportService

router = APIRouter()


@router.get("/{case_id}/report")
async def get_report(case_id: str, db=Depends(get_db)):
    """Get the current business report and recommendation for a case."""
    report_service = ReportService(db_client=db)
    return await report_service.get_latest_report(case_id)


@router.post("/{case_id}/report/generate")
async def generate_report(case_id: str, db=Depends(get_db)):
    """Trigger a full report generation based on all available evidence."""
    report_service = ReportService(db_client=db)
    return await report_service.generate_full_report(case_id)


@router.get("/{case_id}/report/pdf")
async def export_report_pdf(case_id: str, db=Depends(get_db)):
    """Export the business report as a downloadable PDF."""
    report_service = ReportService(db_client=db)
    export_result = await report_service.export_pdf(case_id)
    pdf_bytes = export_result["pdf_bytes"]
    file_name = str(export_result.get("file_name") or f"report-{case_id}.pdf").replace(
        '"',
        "",
    )
    headers = {
        "Content-Disposition": f'attachment; filename="{file_name}"',
        "Content-Length": str(len(pdf_bytes)),
    }
    export_metadata = export_result.get("export") or {}
    if export_metadata.get("id"):
        headers["X-Report-Export-Id"] = str(export_metadata["id"])

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type=export_result.get("content_type") or "application/pdf",
        headers=headers,
    )
