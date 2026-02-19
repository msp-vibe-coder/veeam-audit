from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Daily Summary
# ---------------------------------------------------------------------------

class DailySummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    report_date: date
    veeam_tb: float
    wasabi_active_tb: float
    wasabi_deleted_tb: float
    discrepancy_pct: float
    total_cost: float
    active_cost: float = 0
    deleted_cost: float = 0
    low_disk_count: int
    high_discrepancy_count: int
    high_deleted_count: int
    failed_job_count: int
    warning_job_count: int
    total_jobs: int
    successful_jobs: int
    failed_jobs: int
    warning_jobs: int


# ---------------------------------------------------------------------------
# Site Metrics
# ---------------------------------------------------------------------------

class SiteMetricOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    report_date: date
    site_code: str
    site_name: Optional[str] = None
    veeam_tb: float
    wasabi_active_tb: float
    wasabi_deleted_tb: float
    discrepancy_pct: float
    success_rate_pct: Optional[float] = None
    total_jobs: int
    increment_jobs: int
    reverse_increment_jobs: int
    gold_jobs: int
    silver_jobs: int
    bronze_jobs: int


# ---------------------------------------------------------------------------
# BDR Metrics
# ---------------------------------------------------------------------------

class BdrMetricOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    report_date: date
    bdr_server: str
    site_code: Optional[str] = None
    backup_size_tb: float
    disk_free_tb: float
    disk_free_pct: float


# ---------------------------------------------------------------------------
# Bucket Metrics
# ---------------------------------------------------------------------------

class BucketMetricOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    report_date: date
    bucket_name: str
    site_code: Optional[str] = None
    active_tb: float
    deleted_tb: float
    active_cost: float
    deleted_cost: float
    total_cost: float


# ---------------------------------------------------------------------------
# Anomalies
# ---------------------------------------------------------------------------

class AnomalyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    report_date: date
    severity: str
    type: str
    metric: Optional[str] = None
    previous_value: Optional[float] = None
    current_value: Optional[float] = None
    change_pct: Optional[float] = None
    description: Optional[str] = None


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class DashboardResponse(BaseModel):
    kpis: dict
    daily_summaries: list[DailySummaryOut]
    latest_pipeline_run: Optional[dict] = None


# ---------------------------------------------------------------------------
# Sites
# ---------------------------------------------------------------------------

class SiteListResponse(BaseModel):
    sites: list[SiteMetricOut]
    total: int


class SiteDetailResponse(BaseModel):
    site_code: str
    site_name: Optional[str] = None
    current: SiteMetricOut
    history: list[SiteMetricOut]


# ---------------------------------------------------------------------------
# Issues
# ---------------------------------------------------------------------------

class IssueOut(BaseModel):
    id: int
    report_date: date
    site_code: Optional[str] = None
    severity: str
    type: str
    description: Optional[str] = None
    detected_date: date


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

class ReportGenerateRequest(BaseModel):
    date_from: date
    date_to: date


class GeneratedReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    report_type: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    download_count: int
    created_at: datetime


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

class SettingsOut(BaseModel):
    wasabi_cost_per_tb: float
    sales_tax_rate: float
    discrepancy_threshold_pct: float
    low_disk_threshold_pct: float
    deleted_ratio_threshold: float


class SettingsUpdate(BaseModel):
    wasabi_cost_per_tb: Optional[float] = None
    sales_tax_rate: Optional[float] = None
    discrepancy_threshold_pct: Optional[float] = None
    low_disk_threshold_pct: Optional[float] = None
    deleted_ratio_threshold: Optional[float] = None


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class PipelineStatusOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str
