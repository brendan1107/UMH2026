import { apiClient } from "./client";
import { BusinessCase } from "./types";

/**
 * Cases Service - Handles CRUD for business investigations.
 */
export const casesService = {
  /**
   * List all cases for the current user.
   */
  async getCases(): Promise<BusinessCase[]> {
    return apiClient.get<BusinessCase[]>("/cases/");
  },

  /**
   * Create a new investigation case.
   */
  async createCase(data: Partial<BusinessCase>): Promise<BusinessCase> {
    return apiClient.post<BusinessCase>("/cases/", data);
  },

  /**
   * Get a specific case by ID.
   */
  async getCaseById(id: string): Promise<BusinessCase> {
    return apiClient.get<BusinessCase>(`/cases/${id}`);
  },

  /**
   * Save a final insight checkpoint for a case.
   */
  async saveFinalInsight(caseId: string, insight: any): Promise<void> {
    return apiClient.post(`/cases/${caseId}/insight`, insight);
  },

  /**
   * Update the status of a case.
   */
  async updateCaseStatus(caseId: string, status: BusinessCase["status"]): Promise<void> {
    return apiClient.put(`/cases/${caseId}/status`, { status });
  },

  /**
   * Archive a case.
   */
  async archiveCase(caseId: string): Promise<void> {
    return apiClient.post(`/cases/${caseId}/archive`);
  },

  /**
   * Complete the end session workflow.
   */
  async endSession(caseId: string, decision: "continue" | "archive", insight: any): Promise<void> {
    return apiClient.post(`/cases/${caseId}/end_session`, { decision, insight });
  },

  /**
   * Reopen an archived case.
   */
  async reopenCase(caseId: string): Promise<void> {
    return apiClient.post(`/cases/${caseId}/reopen`);
  },

  /**
   * Update the title of a case.
   */
  async updateCaseTitle(caseId: string, title: string): Promise<void> {
    return apiClient.put(`/cases/${caseId}/title`, { title });
  },

  /**
   * Delete a case.
   */
  async deleteCase(caseId: string): Promise<void> {
    return apiClient.delete(`/cases/${caseId}`);
  },

  /**
   * Save a conversation checkpoint for future AI context.
   */
  async saveConversationCheckpoint(caseId: string, checkpoint: any): Promise<void> {
    return apiClient.post(`/cases/${caseId}/checkpoint`, checkpoint);
  }
};
