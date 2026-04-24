import { apiClient } from "./client";
import { LocationSuggestion } from "./types";

/**
 * Locations Service - Handles AI location suggestions.
 */
export const locationsService = {
  async getLocationSuggestions(caseId: string): Promise<LocationSuggestion[]> {
    // TODO: This might be integrated into the task data or a separate endpoint
    // return apiClient.get<LocationSuggestion[]>(`/locations/${caseId}/suggestions`);
    return [];
  }
};
