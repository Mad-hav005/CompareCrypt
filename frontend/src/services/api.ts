/**
 * Isolated API service for interacting with the FastAPI backend.
 */

import type {
  HealthResponse,
  ExactMatchRequest,
  ExactMatchResponse,
  FuzzyMatchRequest,
  FuzzyMatchResponse,
  ThresholdMatchRequest,
  ThresholdMatchResponse,
  UploadDatasetResponse,
  StartERJobRequest,
  ERJobStatus,
  ERJobResults,
} from '../types/api';


const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '');

class ApiService {
  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    try {
      const response = await fetch(url, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
        ...options,
      });

      if (!response.ok) {
        let errorMessage = `HTTP Error ${response.status}: ${response.statusText}`;
        try {
          const errorData = await response.json();
          if (errorData.detail) {
            errorMessage = typeof errorData.detail === 'string' 
              ? errorData.detail 
              : JSON.stringify(errorData.detail);
          }
        } catch {
          // Response was not JSON
        }
        throw new Error(errorMessage);
      }

      return (await response.json()) as T;
    } catch (err: unknown) {
      if (err instanceof TypeError && err.message.includes('fetch')) {
        throw new Error(
          `Unable to connect to FuzzyCrypt backend at ${API_BASE_URL}. Please ensure the FastAPI server is running.`
        );
      }
      throw err instanceof Error ? err : new Error(String(err));
    }
  }

  async checkHealth(): Promise<HealthResponse> {
    return this.request<HealthResponse>('/health');
  }

  async runExactPSI(
    aliceData: string[],
    bobData: string[],
    normalize: boolean = true
  ): Promise<ExactMatchResponse> {
    const payload: ExactMatchRequest = {
      alice_data: aliceData,
      bob_data: bobData,
      normalize,
    };
    return this.request<ExactMatchResponse>('/api/matching/exact', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async runFuzzyMatching(
    aliceData: string[],
    bobData: string[],
    threshold: number = 0.85,
    normalize: boolean = true
  ): Promise<FuzzyMatchResponse> {
    const payload: FuzzyMatchRequest = {
      alice_data: aliceData,
      bob_data: bobData,
      threshold,
      normalize,
    };
    return this.request<FuzzyMatchResponse>('/api/matching/fuzzy', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async runThresholdCrypto(
    aliceData: string[],
    bobData: string[],
    threshold: number = 0.80
  ): Promise<ThresholdMatchResponse> {
    const payload: ThresholdMatchRequest = {
      alice_data: aliceData,
      bob_data: bobData,
      threshold,
    };
    return this.request<ThresholdMatchResponse>('/api/matching/threshold-crypto', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  // ─── Entity Resolution ───────────────────────────────────────────────────

  async createERJob(): Promise<{ job_id: string }> {
    return this.request<{ job_id: string }>('/api/er/new', { method: 'POST' });
  }

  async uploadERDataset(
    jobId: string,
    party: 'A' | 'B',
    file: File
  ): Promise<UploadDatasetResponse> {
    const formData = new FormData();
    formData.append('job_id', jobId);
    formData.append('file', file);

    const url = `${API_BASE_URL}/api/er/upload/${party}`;
    try {
      const response = await fetch(url, {
        method: 'POST',
        body: formData,
        // Note: Do NOT set Content-Type header for multipart/form-data — let browser set boundary
      });

      if (!response.ok) {
        let errorMessage = `HTTP Error ${response.status}`;
        try {
          const errorData = await response.json();
          if (errorData.detail) errorMessage = errorData.detail;
        } catch { /* ignore */ }
        throw new Error(errorMessage);
      }

      return (await response.json()) as UploadDatasetResponse;
    } catch (err: unknown) {
      if (err instanceof TypeError && err.message.includes('fetch')) {
        throw new Error(`Unable to connect to FuzzyCrypt backend at ${API_BASE_URL}.`);
      }
      throw err instanceof Error ? err : new Error(String(err));
    }
  }

  async startERJob(request: StartERJobRequest): Promise<ERJobStatus> {
    return this.request<ERJobStatus>('/api/er/start', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async getERStatus(jobId: string): Promise<ERJobStatus> {
    return this.request<ERJobStatus>(`/api/er/status/${jobId}`);
  }

  async getERResults(
    jobId: string,
    page: number = 1,
    pageSize: number = 50,
    sortBy: string = 'overall_score',
    sortDesc: boolean = true,
    minScore?: number
  ): Promise<ERJobResults> {
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
      sort_by: sortBy,
      sort_desc: String(sortDesc),
    });
    if (minScore !== undefined) params.append('min_score', String(minScore));

    return this.request<ERJobResults>(`/api/er/results/${jobId}?${params.toString()}`);
  }

  getERExportUrl(jobId: string): string {
    return `${API_BASE_URL}/api/er/export/${jobId}`;
  }
}

export const apiService = new ApiService();
