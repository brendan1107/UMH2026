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
  | "review_ai_suggestions";

export interface InvestigationTask {
  id: string;
  title: string;
  description?: string;
  status: TaskStatus;
  type: TaskType;
  actionLabel?: string;
  data?: any;
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

export interface FinalVerdictResponse {
  verdict: "Continue" | "Continue with caution" | "Pivot" | "Stop / Cancel";
  reasoning: string;
  nextSteps: string[];
}
