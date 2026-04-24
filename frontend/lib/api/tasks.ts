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
    // TODO: Connect to REAL backend: GET /tasks/{case_id}/tasks
    // return apiClient.get<InvestigationTask[]>(`/tasks/${caseId}/tasks`);
    
    return [];
  },

  /**
   * Update task status (complete, skip, etc.).
   */
  async updateTask(taskId: string, status: InvestigationTask["status"]): Promise<InvestigationTask> {
    // TODO: Connect to REAL backend: PUT /tasks/{task_id}
    // return apiClient.put<InvestigationTask>(`/tasks/${taskId}`, { status });
    
    // MOCK FALLBACK
    return { id: taskId, status } as InvestigationTask;
  }
};
