import { AxiosResponse } from 'axios';
import apiClient from './client';

export interface DerivedDataStatus {
  stale: boolean;
  stale_since: string | null;
  stale_reason: string | null;
  rebuild_due_at: string | null;
  rebuilding: boolean;
  last_rebuilt_at: string | null;
  last_rebuild_seconds: number | null;
  last_error: string | null;
}

export const maintenanceApi = {
  getDerivedDataStatus: (): Promise<AxiosResponse<DerivedDataStatus>> =>
    apiClient.get<DerivedDataStatus>('/maintenance/derived-data'),
  rebuildIfDue: (): Promise<AxiosResponse<DerivedDataStatus>> =>
    apiClient.post<DerivedDataStatus>('/maintenance/derived-data/rebuild-if-due'),
  rebuildNow: (): Promise<AxiosResponse<DerivedDataStatus>> =>
    apiClient.post<DerivedDataStatus>('/maintenance/derived-data/rebuild'),
};
