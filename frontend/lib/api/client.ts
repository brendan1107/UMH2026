import { auth } from "../firebase";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api";
if (!process.env.NEXT_PUBLIC_API_URL) {
  console.warn("NEXT_PUBLIC_API_URL is missing in environment. Falling back to http://127.0.0.1:8000/api");
}

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
    
    // Normalize endpoint - ensure single leading slash
    const normalizedEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;

    // Construct final URL
    let url: string;
    if (endpoint.startsWith("http")) {
      url = endpoint;
    } else {
      // If endpoint already starts with /api/, we should use the domain part of BASE_URL
      // to avoid /api/api duplication.
      if (normalizedEndpoint.startsWith('/api/')) {
        // Extract domain from BASE_URL (e.g. http://127.0.0.1:8000)
        const domain = baseUrlStr.replace(/\/api$/, '');
        url = `${domain}${normalizedEndpoint}`;
      } else {
        // Standard case: append normalizedEndpoint to baseUrlStr
        url = `${baseUrlStr}${normalizedEndpoint}`;
      }
    }

    console.log(`[API Request] ${options.method || 'GET'} ${url}`);
    
    const response = await fetch(url, {
      ...options,
      headers,
    }).catch(err => {
      console.error(`[API Network Error] ${options.method || 'GET'} ${url}:`, err.message);
      throw err;
    });

    if (!response.ok) {
      const errorText = await response.text().catch(() => "No error details");
      console.error(`[API HTTP Error] ${response.status} ${url}: ${errorText}`);
    }

    return response;
  },
};
