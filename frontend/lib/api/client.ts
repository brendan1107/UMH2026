import { auth } from "../firebase";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api";

/**
 * apiClient - Wrapper for fetch that automatically adds Firebase Auth tokens.
 */
export const apiClient = {
  async get<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: "GET" });
  },

  async getBlob(endpoint: string): Promise<Blob> {
    return this.requestBlob(endpoint, { method: "GET" });
  },

  async post<T>(endpoint: string, body?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: "POST",
      body: body instanceof FormData ? body : (body ? JSON.stringify(body) : undefined),
    });
  },

  async put<T>(endpoint: string, body?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: "PUT",
      body: body instanceof FormData ? body : (body ? JSON.stringify(body) : undefined),
    });
  },

  async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: "DELETE" });
  },

  /**
   * Internal request handler with token injection.
   */
  async request<T>(endpoint: string, options: RequestInit): Promise<T> {
    const response = await this.fetchRaw(endpoint, options);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `API request failed: ${response.status}`);
    }

    // Handles empty responses (like 204 No Content)
    if (response.status === 204) return {} as T;

    return response.json();
  },

  async requestBlob(endpoint: string, options: RequestInit): Promise<Blob> {
    const response = await this.fetchRaw(endpoint, options);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `API request failed: ${response.status}`);
    }

    return response.blob();
  },

  async fetchRaw(endpoint: string, options: RequestInit): Promise<Response> {
    const user = auth.currentUser;
    const token = user ? await user.getIdToken() : null;

    const headers: HeadersInit = {
      ...(!(options.body instanceof FormData) ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    };

    let baseUrlStr = BASE_URL.endsWith('/') ? BASE_URL.slice(0, -1) : BASE_URL;
    
    // Ensure the base URL includes /api to match FastAPI's router prefixes
    if (!baseUrlStr.endsWith('/api') && !endpoint.startsWith('/api/')) {
      baseUrlStr += '/api';
    }

    const endpointStr = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    const url = endpoint.startsWith("http") ? endpoint : `${baseUrlStr}${endpointStr}`;
    
    let response: Response;
    try {
      response = await fetch(url, {
        ...options,
        headers,
      });
    } catch {
      throw new Error(`Backend API is unreachable at ${url}. Confirm the FastAPI server is running and NEXT_PUBLIC_API_URL is correct.`);
    }
    return response;
  },
};
