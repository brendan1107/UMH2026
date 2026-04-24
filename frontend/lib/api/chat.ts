import { apiClient } from "./client";
import { ChatMessage } from "./types";

/**
 * Chat Service - Handles AI conversation flow.
 */
export const chatService = {
  /**
   * Send a message and receive an AI response.
   */
  async sendMessage(caseId: string, sessionId: string, content: string): Promise<ChatMessage> {
    // TODO: Connect to REAL backend: POST /chat/{case_id}/sessions/{session_id}/messages
    // return apiClient.post<ChatMessage>(`/chat/${caseId}/sessions/${sessionId}/messages`, { content });
    
    // MOCK FALLBACK (Handled by component state for now)
    return {
      id: Date.now().toString(),
      role: "assistant",
      content: "This is a mock AI response. Please connect the backend chat service.",
      createdAt: new Date().toISOString(),
    };
  },

  /**
   * Get message history for a session.
   */
  async getMessages(caseId: string, sessionId: string): Promise<ChatMessage[]> {
    // TODO: Connect to REAL backend: GET /chat/{case_id}/sessions/{session_id}/messages
    // return apiClient.get<ChatMessage[]>(`/chat/${caseId}/sessions/${sessionId}/messages`);
    
    return [];
  }
};
