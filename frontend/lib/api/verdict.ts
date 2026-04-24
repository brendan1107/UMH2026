import { apiClient } from "./client";
import { FinalVerdictResponse } from "./types";

/**
 * Verdict Service - Handles final session analysis.
 */
export const verdictService = {
  async generateVerdict(caseId: string): Promise<FinalVerdictResponse> {
    // TODO: Connect to REAL backend: POST /reports/{case_id}/report/generate (or similar)
    // return apiClient.post<FinalVerdictResponse>(`/reports/${caseId}/verdict`);
    
    // MOCK FALLBACK
    return {
      verdict: "Continue with caution",
      reasoning: "Mock reasoning. Please connect the backend verdict service.",
      nextSteps: ["Step 1", "Step 2"]
    };
  }
};
