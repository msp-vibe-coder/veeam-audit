import axios from "axios";
import type {
  DashboardData,
  SiteListResponse,
  SiteDetailResponse,
  BdrMetric,
  BucketMetric,
  DailySummary,
  SiteMetric,
  Anomaly,
  Issue,
  GeneratedReport,
  Settings,
  PipelineStatus,
} from "@/types";

const api = axios.create({
  baseURL: "/veeam-audit/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
});

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------
export async function fetchDashboard(params?: {
  date_from?: string;
  date_to?: string;
}): Promise<DashboardData> {
  const { data } = await api.get<DashboardData>("/dashboard", { params });
  return data;
}

// ---------------------------------------------------------------------------
// Sites
// ---------------------------------------------------------------------------
export async function fetchSites(params?: {
  search?: string;
  sort_by?: string;
  sort_dir?: string;
  skip?: number;
  limit?: number;
}): Promise<SiteListResponse> {
  const { data } = await api.get<SiteListResponse>("/sites", { params });
  return data;
}

export async function fetchSiteDetail(code: string): Promise<SiteDetailResponse> {
  const { data } = await api.get<SiteDetailResponse>(`/sites/${encodeURIComponent(code)}`);
  return data;
}

export async function fetchSiteBdrs(code: string): Promise<BdrMetric[]> {
  const { data } = await api.get<BdrMetric[]>(`/sites/${encodeURIComponent(code)}/bdrs`);
  return data;
}

export async function fetchSiteBuckets(code: string): Promise<BucketMetric[]> {
  const { data } = await api.get<BucketMetric[]>(`/sites/${encodeURIComponent(code)}/buckets`);
  return data;
}

// ---------------------------------------------------------------------------
// Trends
// ---------------------------------------------------------------------------
export async function fetchTrendsDaily(params?: {
  date_from?: string;
  date_to?: string;
}): Promise<DailySummary[]> {
  const { data } = await api.get<DailySummary[]>("/trends/daily", { params });
  return data;
}

export async function fetchTrendsSites(): Promise<SiteMetric[]> {
  const { data } = await api.get<SiteMetric[]>("/trends/sites");
  return data;
}

export async function fetchAnomalies(params?: {
  severity?: string;
  type?: string;
  date_from?: string;
  date_to?: string;
}): Promise<Anomaly[]> {
  const { data } = await api.get<Anomaly[]>("/trends/anomalies", { params });
  return data;
}

// ---------------------------------------------------------------------------
// Issues
// ---------------------------------------------------------------------------
export async function fetchIssues(params?: {
  severity?: string;
  type?: string;
}): Promise<Issue[]> {
  const { data } = await api.get<Issue[]>("/issues", { params });
  return data;
}

// ---------------------------------------------------------------------------
// Reports
// ---------------------------------------------------------------------------
export async function generateReport(payload: {
  date_from: string;
  date_to: string;
}): Promise<GeneratedReport> {
  const { data } = await api.post<GeneratedReport>("/reports/generate", payload);
  return data;
}

export async function fetchReports(): Promise<GeneratedReport[]> {
  const { data } = await api.get<GeneratedReport[]>("/reports");
  return data;
}

export function downloadReportUrl(id: number): string {
  return `/veeam-audit/api/v1/reports/${id}/download`;
}

// ---------------------------------------------------------------------------
// Settings
// ---------------------------------------------------------------------------
export async function fetchSettings(): Promise<Settings> {
  const { data } = await api.get<Settings>("/settings");
  return data;
}

export async function updateSettings(payload: Partial<Settings>): Promise<Settings> {
  const { data } = await api.put<Settings>("/settings", payload);
  return data;
}

// ---------------------------------------------------------------------------
// Pipeline
// ---------------------------------------------------------------------------
export async function fetchPipelineStatus(): Promise<PipelineStatus> {
  const { data } = await api.get<PipelineStatus>("/pipeline/status");
  return data;
}

export default api;
