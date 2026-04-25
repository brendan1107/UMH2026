import { apiClient } from "./client";
import { LocationSuggestion, LocationAnalysisResult } from "./types";

/**
 * Locations Service - Handles AI location suggestions and competitor analysis.
 */
export const locationsService = {
  async getLocationSuggestions(caseId: string): Promise<LocationSuggestion[]> {
    // TODO: This might be integrated into the task data or a separate endpoint
    // return apiClient.get<LocationSuggestion[]>(`/locations/${caseId}/suggestions`);
    return [];
  },

  async getCompetitors(params: {
    caseId?: string;
    targetLocation?: string;
    lat?: number;
    lng?: number;
    radius?: number;
    keyword?: string;
    previewOnly?: boolean;
  }): Promise<LocationAnalysisResult> {
    const queryParams: Record<string, string> = {};
    if (params.caseId) queryParams.case_id = params.caseId;
    if (params.targetLocation) queryParams.target_location = params.targetLocation;
    if (params.lat) queryParams.lat = params.lat.toString();
    if (params.lng) queryParams.lng = params.lng.toString();
    if (params.radius) queryParams.radius = params.radius.toString();
    if (params.keyword) queryParams.keyword = params.keyword;
    if (params.previewOnly) queryParams.preview_only = "true";

    const queryString = new URLSearchParams(queryParams).toString();
    return apiClient.get<LocationAnalysisResult>(`/locations/competitors?${queryString}`);
  }
};
