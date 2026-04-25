import { apiClient } from "./client";
import { InvestigationTask, TaskActionData, TaskCreatePayload } from "./types";

/**
 * Tasks Service - Manages AI-generated investigation tasks.
 */
export const tasksService = {
  /**
   * List all tasks for a business case.
   */
  async getTasks(caseId: string): Promise<InvestigationTask[]> {
    return apiClient.get<InvestigationTask[]>(`/tasks/${caseId}`);
  },

  /**
   * Create a task for a business case.
   */
  async createTask(caseId: string, data: TaskCreatePayload): Promise<InvestigationTask> {
    return apiClient.post<InvestigationTask>(`/tasks/${caseId}`, data);
  },

  /**
   * Update task status and optionally persist submitted action data.
   */
  async updateTask(
    caseId: string,
    taskId: string,
    status: InvestigationTask["status"],
    submittedValue?: TaskActionData
  ): Promise<InvestigationTask> {
    return apiClient.put<InvestigationTask>(`/tasks/${caseId}/${taskId}`, {
      status,
      ...(submittedValue !== undefined ? { submittedValue } : {}),
    });
  },

  /**
   * Delete a task from a business case.
   */
  async deleteTask(caseId: string, taskId: string): Promise<void> {
    await apiClient.delete(`/tasks/${caseId}/${taskId}`);
  }
};
