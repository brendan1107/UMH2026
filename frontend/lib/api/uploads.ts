import { apiClient } from "./client";
import { EvidenceUpload } from "./types";

/**
 * Uploads Service - Handles file uploads.
 */
export const uploadsService = {
  async uploadFile(caseId: string, file: File): Promise<EvidenceUpload> {
    // TODO: Connect to REAL backend: POST /uploads/{case_id}/upload
    // const formData = new FormData();
    // formData.append("file", file);
    // return apiClient.post<EvidenceUpload>(`/uploads/${caseId}/upload`, formData);
    
    // MOCK FALLBACK
    return {
      id: Date.now().toString(),
      name: file.name,
      size: (file.size / 1024 / 1024).toFixed(1) + " MB",
      type: file.type.startsWith("image/") ? "image" : "document",
      url: "#",
      createdAt: new Date().toISOString()
    };
  }
};
