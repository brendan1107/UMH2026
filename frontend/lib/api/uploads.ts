import { apiClient } from "./client";
import { EvidenceUpload } from "./types";

/**
 * Uploads Service - Handles file uploads.
 */
export const uploadsService = {
  /**
   * Upload a file for a specific case.
   */
  async uploadFile(caseId: string, file: File): Promise<EvidenceUpload> {
    const formData = new FormData();
    formData.append("file", file);
    return apiClient.post<EvidenceUpload>(`/uploads/${caseId}/upload`, formData);
  },

  /**
   * List all uploads for a specific case.
   */
  async listUploads(caseId: string): Promise<EvidenceUpload[]> {
    return apiClient.get<EvidenceUpload[]>(`/uploads/${caseId}`);
  },

  /**
   * Delete a specific upload.
   */
  async deleteUpload(caseId: string, uploadId: string): Promise<{ status: string }> {
    return apiClient.delete<{ status: string }>(`/uploads/${caseId}/${uploadId}`);
  }
};
