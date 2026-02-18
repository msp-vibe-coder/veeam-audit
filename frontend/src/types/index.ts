// ---------------------------------------------------------------------------
// Daily Summary
// ---------------------------------------------------------------------------
export interface DailySummary {
  report_date: string;
  veeam_tb: number;
  wasabi_active_tb: number;
  wasabi_deleted_tb: number;
  discrepancy_pct: number;
  total_cost: number;
  low_disk_count: number;
  high_discrepancy_count: number;
  high_deleted_count: number;
  failed_job_count: number;
  warning_job_count: number;
  total_jobs: number;
  successful_jobs: number;
  failed_jobs: number;
  warning_jobs: number;
}

// ---------------------------------------------------------------------------
// Site Metrics
// ---------------------------------------------------------------------------
export interface SiteMetric {
  id: number;
  report_date: string;
  site_code: string;
  site_name: string | null;
  veeam_tb: number;
  wasabi_active_tb: number;
  wasabi_deleted_tb: number;
  discrepancy_pct: number;
  success_rate_pct: number | null;
  total_jobs: number;
  increment_jobs: number;
  reverse_increment_jobs: number;
  gold_jobs: number;
  silver_jobs: number;
  bronze_jobs: number;
}

// ---------------------------------------------------------------------------
// BDR Metrics
// ---------------------------------------------------------------------------
export interface BdrMetric {
  id: number;
  report_date: string;
  bdr_server: string;
  site_code: string | null;
  backup_size_tb: number;
  disk_free_tb: number;
  disk_free_pct: number;
}

// ---------------------------------------------------------------------------
// Bucket Metrics
// ---------------------------------------------------------------------------
export interface BucketMetric {
  id: number;
  report_date: string;
  bucket_name: string;
  site_code: string | null;
  active_tb: number;
  deleted_tb: number;
  active_cost: number;
  deleted_cost: number;
  total_cost: number;
}

// ---------------------------------------------------------------------------
// Anomaly
// ---------------------------------------------------------------------------
export interface Anomaly {
  id: number;
  report_date: string;
  severity: string;
  type: string;
  metric: string | null;
  previous_value: number | null;
  current_value: number | null;
  change_pct: number | null;
  description: string | null;
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------
export interface DashboardKpis {
  total_veeam_tb: number;
  total_wasabi_tb: number;
  discrepancy_pct: number;
  total_cost: number;
  active_issues: number;
}

export interface DashboardData {
  kpis: DashboardKpis;
  daily_summaries: DailySummary[];
  latest_pipeline_run: PipelineStatus | null;
}

// ---------------------------------------------------------------------------
// Issues
// ---------------------------------------------------------------------------
export interface Issue {
  id: number;
  report_date: string;
  site_code: string | null;
  severity: string;
  type: string;
  description: string | null;
  detected_date: string;
}

// ---------------------------------------------------------------------------
// Reports
// ---------------------------------------------------------------------------
export interface GeneratedReport {
  id: number;
  filename: string;
  report_type: string | null;
  date_from: string | null;
  date_to: string | null;
  download_count: number;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Settings
// ---------------------------------------------------------------------------
export interface Settings {
  wasabi_cost_per_tb: number;
  sales_tax_rate: number;
  discrepancy_threshold_pct: number;
  low_disk_threshold_pct: number;
  deleted_ratio_threshold: number;
}

// ---------------------------------------------------------------------------
// Pipeline
// ---------------------------------------------------------------------------
export interface PipelineStatus {
  id: number | null;
  started_at: string | null;
  completed_at: string | null;
  status: string;
}

// ---------------------------------------------------------------------------
// Site Responses
// ---------------------------------------------------------------------------
export interface SiteListResponse {
  sites: SiteMetric[];
  total: number;
}

export interface SiteDetailResponse {
  site_code: string;
  site_name: string | null;
  current: SiteMetric;
  history: SiteMetric[];
}

// ---------------------------------------------------------------------------
// Utility types
// ---------------------------------------------------------------------------
export type Severity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

export type SortDirection = "asc" | "desc";

export interface Column<T> {
  key: string;
  label: string;
  sortable?: boolean;
  render?: (value: unknown, row: T) => React.ReactNode;
}
