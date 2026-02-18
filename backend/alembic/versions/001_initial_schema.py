"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-02-18
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "daily_summaries",
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("veeam_tb", sa.Numeric(12, 4)),
        sa.Column("wasabi_active_tb", sa.Numeric(12, 4)),
        sa.Column("wasabi_deleted_tb", sa.Numeric(12, 4)),
        sa.Column("discrepancy_pct", sa.Numeric(8, 2)),
        sa.Column("total_cost", sa.Numeric(12, 2)),
        sa.Column("low_disk_count", sa.Integer(), server_default="0"),
        sa.Column("high_discrepancy_count", sa.Integer(), server_default="0"),
        sa.Column("high_deleted_count", sa.Integer(), server_default="0"),
        sa.Column("failed_job_count", sa.Integer(), server_default="0"),
        sa.Column("warning_job_count", sa.Integer(), server_default="0"),
        sa.Column("total_jobs", sa.Integer(), server_default="0"),
        sa.Column("successful_jobs", sa.Integer(), server_default="0"),
        sa.Column("failed_jobs", sa.Integer(), server_default="0"),
        sa.Column("warning_jobs", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("report_date"),
    )

    op.create_table(
        "site_metrics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("site_code", sa.String(50), nullable=False),
        sa.Column("site_name", sa.String(200)),
        sa.Column("veeam_tb", sa.Numeric(12, 4)),
        sa.Column("wasabi_active_tb", sa.Numeric(12, 4)),
        sa.Column("wasabi_deleted_tb", sa.Numeric(12, 4)),
        sa.Column("discrepancy_pct", sa.Numeric(8, 2)),
        sa.Column("success_rate_pct", sa.Numeric(5, 2)),
        sa.Column("total_jobs", sa.Integer(), server_default="0"),
        sa.Column("increment_jobs", sa.Integer(), server_default="0"),
        sa.Column("reverse_increment_jobs", sa.Integer(), server_default="0"),
        sa.Column("gold_jobs", sa.Integer(), server_default="0"),
        sa.Column("silver_jobs", sa.Integer(), server_default="0"),
        sa.Column("bronze_jobs", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("report_date", "site_code", name="uq_site_metrics_date_code"),
    )
    op.create_index("idx_site_metrics_date", "site_metrics", ["report_date"])
    op.create_index("idx_site_metrics_code", "site_metrics", ["site_code"])

    op.create_table(
        "bdr_metrics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("bdr_server", sa.String(200), nullable=False),
        sa.Column("site_code", sa.String(50)),
        sa.Column("backup_size_tb", sa.Numeric(12, 4)),
        sa.Column("disk_free_tb", sa.Numeric(12, 4)),
        sa.Column("disk_free_pct", sa.Numeric(5, 2)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("report_date", "bdr_server", name="uq_bdr_metrics_date_server"),
    )
    op.create_index("idx_bdr_metrics_date", "bdr_metrics", ["report_date"])

    op.create_table(
        "bucket_metrics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("bucket_name", sa.String(200), nullable=False),
        sa.Column("site_code", sa.String(50)),
        sa.Column("active_tb", sa.Numeric(12, 4)),
        sa.Column("deleted_tb", sa.Numeric(12, 4)),
        sa.Column("active_cost", sa.Numeric(12, 2)),
        sa.Column("deleted_cost", sa.Numeric(12, 2)),
        sa.Column("total_cost", sa.Numeric(12, 2)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("report_date", "bucket_name", name="uq_bucket_metrics_date_bucket"),
    )
    op.create_index("idx_bucket_metrics_date", "bucket_metrics", ["report_date"])

    op.create_table(
        "anomalies",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("type", sa.String(100), nullable=False),
        sa.Column("metric", sa.String(100)),
        sa.Column("previous_value", sa.Numeric(12, 4)),
        sa.Column("current_value", sa.Numeric(12, 4)),
        sa.Column("change_pct", sa.Numeric(8, 2)),
        sa.Column("description", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_anomalies_date", "anomalies", ["report_date"])
    op.create_index("idx_anomalies_severity", "anomalies", ["severity"])

    op.create_table(
        "settings",
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("value", postgresql.JSONB(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("key"),
    )

    op.create_table(
        "pipeline_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(20), server_default="running"),
        sa.Column("steps", postgresql.JSONB()),
        sa.Column("log_text", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "generated_reports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("report_type", sa.String(50)),
        sa.Column("date_from", sa.Date()),
        sa.Column("date_to", sa.Date()),
        sa.Column("file_path", sa.String(1000)),
        sa.Column("download_count", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("generated_reports")
    op.drop_table("pipeline_runs")
    op.drop_table("settings")
    op.drop_table("anomalies")
    op.drop_table("bucket_metrics")
    op.drop_table("bdr_metrics")
    op.drop_table("site_metrics")
    op.drop_table("daily_summaries")
