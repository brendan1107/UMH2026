import { apiClient } from "./client";
import { RecommendationData } from "./types";

/**
 * Reports Service - Handles report generation and PDF export.
 */
export const reportsService = {
  async getLatestRecommendation(caseId: string): Promise<RecommendationData> {
    return apiClient.get<RecommendationData>(`/reports/${caseId}/report`);
  },

  async exportPdf(caseId: string): Promise<void> {
    const response = await apiClient.getBlob(`/reports/${caseId}/report/pdf`);
    // Create a URL for the blob and trigger download
    const url = window.URL.createObjectURL(response);
    const a = document.createElement("a");
    a.href = url;
    a.download = `fnb-genie-${caseId.slice(0, 8)}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  }
};
