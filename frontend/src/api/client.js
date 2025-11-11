/**
 * API Client Configuration
 * Axios instance with base URL and interceptors
 */
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for debugging
apiClient.interceptors.request.use(
  (config) => {
    console.log(`[API] ${config.method.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    console.error('[API Error]', error);

    // Handle common errors
    if (error.response) {
      const { status, data } = error.response;

      // Customize error messages
      switch (status) {
        case 400:
          error.userMessage = data.detail || 'Invalid request';
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
