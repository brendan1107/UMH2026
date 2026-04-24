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
    // TODO: Connect to REAL backend: GET /cases/
    // return apiClient.get<BusinessCase[]>("/cases/");
    
    // MOCK FALLBACK
    return [];
  },

  /**
   * Create a new investigation case.
   */
  async createCase(data: Partial<BusinessCase>): Promise<BusinessCase> {
    // TODO: Connect to REAL backend: POST /cases/
    // return apiClient.post<BusinessCase>("/cases/", data);
    
    // MOCK FALLBACK
    return {
      id: "demo-" + Date.now(),
      title: data.title || "New Project",
      description: data.description || "",
      stage: data.stage || "new",
      status: "active",
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
  },

  /**
   * Get a specific case by ID.
   */
  async getCaseById(id: string): Promise<BusinessCase> {
    // TODO: Connect to REAL backend: GET /cases/{id}
    // return apiClient.get<BusinessCase>(`/cases/${id}`);
    
    throw new Error("Case not found");
  },

  /**
   * Save a final insight checkpoint for a case.
   */
  async saveFinalInsight(caseId: string, insight: any): Promise<void> {
    // TODO: Connect to REAL backend: POST /cases/{caseId}/insight
    console.log(`Mock: Saved final insight for case ${caseId}`, insight);
  },

  /**
   * Update the status of a case.
   */
  async updateCaseStatus(caseId: string, status: BusinessCase["status"]): Promise<void> {
    // TODO: Connect to REAL backend: PUT /cases/{caseId}/status
    console.log(`Mock: Updated case ${caseId} status to ${status}`);
  },

  /**
   * Archive a case.
   */
  async archiveCase(caseId: string): Promise<void> {
    // TODO: Connect to REAL backend: POST /cases/{caseId}/archive
    console.log(`Mock: Archived case ${caseId}`);
  },

  /**
   * Complete the end session workflow.
   */
  async endSession(caseId: string, decision: "continue" | "archive", insight: any): Promise<void> {
    // TODO: Connect to REAL backend: POST /cases/{caseId}/end_session
    // This could be a single endpoint that wraps the saving of insight and status update.
    await this.saveFinalInsight(caseId, insight);
    await this.updateCaseStatus(caseId, decision === "archive" ? "archived" : "insight_generated");
  },

  /**
   * Reopen an archived case.
   */
  async reopenCase(caseId: string): Promise<void> {
    // TODO: Connect to REAL backend: POST /cases/{caseId}/reopen
    console.log(`Mock: Reopened case ${caseId}`);
    await this.updateCaseStatus(caseId, "active");
  },

  /**
   * Update the title of a case.
   */
  async updateCaseTitle(caseId: string, title: string): Promise<void> {
    // TODO: Connect to REAL backend: PATCH /cases/{caseId}/title
    console.log(`Mock: Updated case ${caseId} title to: ${title}`);
  },

  /**
   * Delete a case.
   */
  async deleteCase(caseId: string): Promise<void> {
    // TODO: Connect to REAL backend: DELETE /cases/{caseId}
    console.log(`Mock: Deleted case ${caseId}`);
  },

  /**
   * Save a conversation checkpoint for future AI context.
   */
  async saveConversationCheckpoint(caseId: string, checkpoint: any): Promise<void> {
    // TODO: Connect to REAL backend: POST /cases/{caseId}/checkpoint
    console.log(`Mock: Saved conversation checkpoint for case ${caseId}`, checkpoint);
  }
};
