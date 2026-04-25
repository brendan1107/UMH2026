/**
 * F&B Genie - API Types
 */

export interface User {
  uid: string;
  email: string | null;
  displayName: string | null;
}

export type BusinessStage = "new" | "existing";

export interface BusinessCase {
  id: string;
  title: string;
  description: string;
  stage: BusinessStage;
  status: "active" | "insight_generated" | "archived" | "completed";
  createdAt: string;
  updatedAt: string;
}

export type TaskStatus = "pending" | "scheduled" | "skipped" | "completed";

export type TaskType = 
  | "answer_questions" 
  | "choose_option" 
  | "upload_file" 
  | "upload_image" 
  | "provide_text_input" 
  | "review_ai_suggestions"
  | "select_location"
  | "schedule_event";

export type TaskActionData =
  | { text: string }
  | { answers: Record<string, string> }
  | { selectedOption: string | null }
  | { location: { lat: number; lng: number; address: string } | null }
  | { eventDate: string }
  | {
      uploadId: string;
      fileName: string;
      fileType?: string;
      fileSize?: number;
      storagePath?: string;
      storageMode?: string;
      url?: string;
    }
  | Record<string, unknown>;

export interface TaskCreatePayload {
  title: string;
  description?: string;
  type?: TaskType;
  status?: TaskStatus;
  actionLabel?: string;
  data?: Record<string, unknown>;
  source?: string;
}

export interface InvestigationTask {
  id: string;
  caseId?: string;
  title: string;
  description?: string;
  status: TaskStatus;
  type: TaskType;
  actionLabel?: string;
  data?: Record<string, unknown>;
  source?: string;
  questions?: string[];
  submittedValue?: TaskActionData;
  completedAt?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
}

export interface ChatSession {
  id: string;
  caseId: string;
  createdAt: string;
}

export interface EvidenceUpload {
  id: string;
  name: string;
  size: string;
  type: "image" | "document";
  caseId?: string;
  fileName?: string;
  fileType?: string;
  fileSize?: number;
  storagePath?: string;
  storageMode?: "firebase_storage" | "metadata_only";
  url: string;
  createdAt: string;
}

export interface RecommendationData {
  status: "gathering" | "ready" | "generating_verdict";
  summary: string;
  strengths: string[];
  risks: string[];
  verdict?: "Continue" | "Continue with caution" | "Pivot" | "Stop / Cancel";
  verdictReasoning?: string;
  nextSteps?: string[];
}

export interface LocationSuggestion {
  id: string;
  title: string;
  subtitle: string;
  pros: string[];
  cons: string[];
  address?: string;
  footTraffic?: string;
  competition?: string;
}

export interface TargetLocation {
  name: string;
  lat: number;
  lng: number;
  address: string;
  placeId?: string;
  googleMapsUrl?: string;
  rating?: number;
  reviewCount?: number;
}

export interface Competitor {
  id: string;
  placeId?: string;
  name: string;
  category: string;
  rating: number;
  reviewCount: number;
  address: string;
  lat: number;
  lng: number;
  distanceMeters: number;
  riskLevel: "Low" | "Medium" | "High";
  riskScore: number;
  insight: string;
  googleMapsUrl?: string;
}

export interface SuggestedTask {
  title: string;
  description: string;
  type: TaskType;
  actionLabel: string;
  questions?: string[];
}

export interface SearchDiagnostics {
  radius: number;
  queriesRun: string[];
  rawResultCount: number;
  dedupedCount: number;
  filteredCount: number;
  source: string;
}

export interface LocationAnalysisResult {
  id?: string;
  caseId: string;
  source: "google_places" | "mock";
  fallbackReason?: string;
  analysisMode: "gemini" | "fallback";
  targetLocation: TargetLocation;
  radius: number;
  competitors: Competitor[];
  summary: string;
  riskLevel: "Low" | "Medium" | "High";
  riskScore: number;
  riskExplanation: string;
  followUpQuestions: string[];
  suggestedTasks: SuggestedTask[];
  searchDiagnostics?: SearchDiagnostics;
  createdAt: string;
}

export interface FinalVerdictResponse {
  verdict: "Continue" | "Continue with caution" | "Pivot" | "Stop / Cancel";
  reasoning: string;
  nextSteps: string[];
}
