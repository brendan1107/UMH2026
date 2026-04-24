import { apiClient } from "./client";
import { InvestigationTask } from "./types";

/**
 * Tasks Service - Manages AI-generated investigation tasks.
 */
export const tasksService = {
  /**
   * List all tasks for a business case.
   */
  async getTasks(caseId: string): Promise<InvestigationTask[]> {
    return apiClient.get<InvestigationTask[]>(`/tasks/${caseId}/tasks`);
  },

  /**
   * Update task status (complete, skip, etc.).
   */
  async updateTask(taskId: string, status: InvestigationTask["status"]): Promise<InvestigationTask> {
    return apiClient.put<InvestigationTask>(`/tasks/${taskId}`, { status });
  }
};
