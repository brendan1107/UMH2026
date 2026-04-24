import { apiClient } from "./client";
import { RecommendationData } from "./types";

/**
 * Reports Service - Handles report generation and PDF export.
 */
export const reportsService = {
  async getLatestRecommendation(caseId: string): Promise<RecommendationData> {
    // TODO: Connect to REAL backend: GET /reports/{case_id}/report
    // return apiClient.get<RecommendationData>(`/reports/${caseId}/report`);
    
    throw new Error("Report not generated yet");
  },

  async exportPdf(caseId: string): Promise<void> {
    // TODO: Connect to REAL backend: GET /reports/{case_id}/report/pdf
    // const response = await apiClient.get<Blob>(`/reports/${caseId}/report/pdf`);
    // ... handle blob download ...
  }
};
