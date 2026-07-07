/**
 * API Client Configuration
 * Axios instance with base URL and interceptors
 */
import axios, {
  AxiosInstance,
  AxiosResponse,
  AxiosError,
  InternalAxiosRequestConfig,
} from 'axios';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// Default timeout in milliseconds (30 seconds)
const DEFAULT_TIMEOUT = 30000;

// Extended error interface for our custom error properties
export interface ApiClientError extends AxiosError {
  userMessage?: string;
  isDuplicate?: boolean;
}

export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: DEFAULT_TIMEOUT,
  // Send/receive the sc2mmr_session cookie. Needed for the group-password
  // login when the frontend and backend are on different origins (e.g.
  // Vercel + Cloud Run); harmless in local dev where auth is disabled.
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Notify the app shell that the backend rejected our session (401) so the
 * AuthGate can swap in the login screen without a full page reload.
 */
export const AUTH_EXPIRED_EVENT = 'sc2mmr:auth-expired';

// Request interceptor for debugging + optional admin token
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig): InternalAxiosRequestConfig => {
    console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
    // Admin endpoints (rating recalc, merge, retrain) require this header
    // once ADMIN_TOKEN is configured server-side. Operators set it once via
    // localStorage in the browser console:
    //   localStorage.setItem('sc2mmr_admin_token', '<token>')
    const adminToken = localStorage.getItem('sc2mmr_admin_token');
    if (adminToken) {
      config.headers['X-Admin-Token'] = adminToken;
    }
    return config;
  },
  (error: AxiosError): Promise<never> => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response: AxiosResponse): AxiosResponse => {
    return response;
  },
  (error: ApiClientError): Promise<never> => {
    console.error('[API Error]', error);

    // Handle common errors
    if (error.response) {
      const { status, data } = error.response as AxiosResponse<{ detail?: string }>;

      // Customize error messages
      switch (status) {
        case 400:
          error.userMessage = data.detail || 'Invalid request';
          break;
        case 401:
          error.userMessage = data.detail || 'Not signed in';
          // Skip the auth endpoints themselves: a wrong password on login
          // must not bounce the whole app back through the AuthGate.
          if (!error.config?.url?.startsWith('/auth/')) {
            window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT));
          }
          break;
        case 404:
          error.userMessage = data.detail || 'Resource not found';
          break;
        case 409:
          error.userMessage = data.detail || 'Duplicate entry';
          error.isDuplicate = true;
          break;
        case 500:
          error.userMessage = 'Server error. Please try again later.';
          break;
        default:
          error.userMessage = data.detail || 'An error occurred';
      }
    } else if (error.request) {
      error.userMessage = 'Cannot connect to server. Please check your connection.';
    } else {
      error.userMessage = 'An unexpected error occurred';
    }

    return Promise.reject(error);
  }
);

export default apiClient;
