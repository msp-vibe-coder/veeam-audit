"""add active_cost and deleted_cost to daily_summaries

Revision ID: 002
Revises: 001
Create Date: 2026-02-18
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("daily_summaries", sa.Column("active_cost", sa.Numeric(12, 2)))
    op.add_column("daily_summaries", sa.Column("deleted_cost", sa.Numeric(12, 2)))

    # Backfill from bucket_metrics: active_cost/deleted_cost there are pre-tax,
    # so multiply by 1.0685 to get the taxed amount matching total_cost.
    op.execute("""
        UPDATE daily_summaries ds
        SET active_cost = sub.active_cost,
            deleted_cost = sub.deleted_cost
        FROM (
            SELECT report_date,
                   ROUND(SUM(active_cost) * 1.0685, 2) AS active_cost,
                   ROUND(SUM(deleted_cost) * 1.0685, 2) AS deleted_cost
            FROM bucket_metrics
            GROUP BY report_date
        ) sub
        WHERE ds.report_date = sub.report_date
    """)


def downgrade() -> None:
    op.drop_column("daily_summaries", "deleted_cost")
    op.drop_column("daily_summaries", "active_cost")
