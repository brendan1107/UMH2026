import { apiClient } from "./client";
import { FinalVerdictResponse } from "./types";

/**
 * Verdict Service - Handles final session analysis.
 */
export const verdictService = {
  async generateVerdict(caseId: string): Promise<FinalVerdictResponse> {
    return apiClient.post<FinalVerdictResponse>(`/reports/${caseId}/final-verdict`);
  }
};
