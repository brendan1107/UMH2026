import { apiClient } from "./client";
import { EvidenceUpload } from "./types";

/**
 * Uploads Service - Handles file uploads.
 */
export const uploadsService = {
  async uploadFile(caseId: string, file: File): Promise<EvidenceUpload> {
    const formData = new FormData();
    formData.append("file", file);
    return apiClient.post<EvidenceUpload>(`/uploads/${caseId}/upload`, formData);
  }
};
