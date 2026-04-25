import { apiClient } from "./client";
import { ChatMessage } from "./types";

/**
 * Chat Service - Handles AI conversation flow.
 */
export const chatService = {
  /**
   * Send a message and receive an AI response.
   */
  async sendMessage(caseId: string, _sessionId: string, content: string): Promise<ChatMessage> {
    return apiClient.post<ChatMessage>(`/chat/${caseId}/messages`, { content });
  },

  /**
   * Get message history for a session.
   */
  async getMessages(caseId: string, _sessionId: string): Promise<ChatMessage[]> {
    return apiClient.get<ChatMessage[]>(`/chat/${caseId}/messages`);
  }
};
