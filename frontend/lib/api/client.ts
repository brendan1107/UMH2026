import { auth } from "../firebase";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

/**
 * apiClient - Wrapper for fetch that automatically adds Firebase Auth tokens.
 */
export const apiClient = {
  async get<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: "GET" });
  },

  async post<T>(endpoint: string, body?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    });
  },

  async put<T>(endpoint: string, body?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: "PUT",
      body: body ? JSON.stringify(body) : undefined,
    });
  },

  async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: "DELETE" });
  },

  /**
   * Internal request handler with token injection.
   */
  async request<T>(endpoint: string, options: RequestInit): Promise<T> {
    const user = auth.currentUser;
    const token = user ? await user.getIdToken() : null;

    const headers: HeadersInit = {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    };

    const url = endpoint.startsWith("http") ? endpoint : `${BASE_URL}${endpoint}`;
    
    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `API request failed: ${response.status}`);
    }

    // Handles empty responses (like 204 No Content)
    if (response.status === 204) return {} as T;

    return response.json();
  },
};
