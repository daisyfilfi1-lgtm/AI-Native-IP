import axios, { AxiosError, AxiosInstance } from 'axios';

import type { 
  IP, CreateIPRequest, 
  IngestRequest, IngestResponse, IngestStatus, MemoryUploadResponse,
  AssetsListResponse,
  RetrieveRequest, RetrieveResult,
} from '@/types';

// 直接定义 API 基础 URL
const API_BASE_URL = 'https://ai-native-ip-production.up.railway.app/api/v1';

console.log('[API] Using direct Railway URL:', API_BASE_URL);

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 30000,
    });

    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        console.error('API Error:', error.response?.data || error.message);
        throw error;
      }
    );
  }

  async listIPs(): Promise<IP[]> {
    const response = await this.client.get<IP[]>('/ip');
    return response.data;
  }

  async createIP(data: CreateIPRequest): Promise<IP> {
    const response = await this.client.post<IP>('/ip', data);
    return response.data;
  }

  async getIP(ipId: string): Promise<IP> {
    const response = await this.client.get<IP>(`/ip/${ipId}`);
    return response.data;
  }

  async ingestMemory(data: IngestRequest): Promise<IngestResponse> {
    const response = await this.client.post<IngestResponse>('/memory/ingest', data);
    return response.data;
  }

  async uploadMemoryFile(ipId: string, file: File): Promise<MemoryUploadResponse> {
    const MAX_FILE_SIZE = 10 * 1024 * 1024;
    if (file.size > MAX_FILE_SIZE) {
      throw new Error(`文件过大，最大支持 ${MAX_FILE_SIZE / 1024 / 1024}MB`);
    }

    const formData = new FormData();
    formData.append('ip_id', ipId);
    formData.append('file', file);
    
    const response = await this.client.post<MemoryUploadResponse>('/memory/upload', formData, {
      timeout: 60000,
      maxContentLength: 10 * 1024 * 1024,
      maxBodyLength: 10 * 1024 * 1024,
      transformRequest: [
        (data, headers) => {
          if (data instanceof FormData) {
            delete headers['Content-Type'];
          }
          return data;
        },
      ],
    });
    return response.data;
  }

  async getIngestStatus(taskId: string): Promise<IngestStatus> {
    const response = await this.client.get<IngestStatus>(`/memory/ingest/${taskId}`, {
      timeout: 20000,
    });
    return response.data;
  }

  async getAssets(ipId: string, limit = 20, offset = 0): Promise<AssetsListResponse> {
    const response = await this.client.get<AssetsListResponse>('/memory/assets', {
      params: { ip_id: ipId, limit, offset },
    });
    return response.data;
  }

  async retrieveMemory(data: RetrieveRequest): Promise<RetrieveResult[]> {
    const response = await this.client.post<{ results: RetrieveResult[] }>('/memory/retrieve', data);
    return response.data.results;
  }
}

export const api = new ApiClient();
export default api;
