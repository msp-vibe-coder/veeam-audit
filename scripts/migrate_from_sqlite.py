#!/usr/bin/env python3
"""
One-time migration: SQLite (veeam-audit-old) -> PostgreSQL (veeam-audit).

Reads all rows from the old SQLite database and inserts them into the
corresponding PostgreSQL tables. Also migrates settings from settings.json.

Usage:
    python scripts/migrate_from_sqlite.py
    python scripts/migrate_from_sqlite.py --sqlite-path /path/to/veeam_audit.db
    python scripts/migrate_from_sqlite.py --dry-run
"""

import argparse
import json
import sqlite3
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values


# Default paths
DEFAULT_SQLITE_PATH = Path(r"C:\coding\backups\veeam-audit-old\data\veeam_audit.db")
DEFAULT_SETTINGS_PATH = Path(r"C:\coding\backups\veeam-audit-old\data\settings.json")
DEFAULT_PG_DSN = "postgresql://veeam:changeme@localhost:5432/veeam_audit"


def connect_sqlite(path: Path) -> sqlite3.Connection:
    if not path.exists():
        print(f"ERROR: SQLite database not found at {path}")
        sys.exit(1)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def connect_postgres(dsn: str):
    return psycopg2.connect(dsn)


def safe_float(val):
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def safe_int(val):
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def safe_date(val):
    if val is None:
        return None
    if isinstance(val, date):
        return val
    try:
        return datetime.strptime(str(val)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def migrate_daily_summaries(sqlite_conn, pg_conn, dry_run=False):
    print("\n--- daily_summaries ---")
    cursor = sqlite_conn.execute("SELECT * FROM daily_summaries ORDER BY report_date")
    rows = cursor.fetchall()
    print(f"  Found {len(rows)} rows in SQLite")

    if dry_run or not rows:
        return len(rows)

    pg_cur = pg_conn.cursor()
    inserted = 0
    skipped = 0

    for row in rows:
        rd = safe_date(row["report_date"])
        if not rd:
            skipped += 1
            continue

        try:
            pg_cur.execute(
                """INSERT INTO daily_summaries
                (report_date, veeam_tb, wasabi_active_tb, wasabi_deleted_tb,
                 discrepancy_pct, total_cost, low_disk_count, high_discrepancy_count,
                 high_deleted_count, failed_job_count, warning_job_count,
                 total_jobs, successful_jobs, failed_jobs, warning_jobs)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (report_date) DO NOTHING""",
                (
                    rd,
                    safe_float(row["veeam_tb"]),
                    safe_float(row["wasabi_active_tb"]),
                    safe_float(row["wasabi_deleted_tb"]),
                    safe_float(row["discrepancy_pct"]),
                    safe_float(row["total_cost"]),
                    safe_int(row["low_disk_count"]),
                    safe_int(row["high_discrepancy_count"]),
                    safe_int(row["high_deleted_count"]),
                    safe_int(row["failed_jobs_count"]),
                    safe_int(row["warning_jobs_count"]),
                    safe_int(row["total_jobs"]),
                    safe_int(row["success_jobs"]),
                    safe_int(dict(row).get("failed_jobs", 0) or 0),
                    safe_int(dict(row).get("warning_jobs", 0) or 0),
                ),
            )
            inserted += 1
        except Exception as e:
            print(f"  WARN: Skipping daily_summary {rd}: {e}")
            pg_conn.rollback()
            skipped += 1
            continue

    pg_conn.commit()
    print(f"  Inserted: {inserted}, Skipped: {skipped}")
    return inserted


def migrate_site_metrics(sqlite_conn, pg_conn, dry_run=False):
    print("\n--- site_metrics ---")
    cursor = sqlite_conn.execute("SELECT * FROM site_metrics ORDER BY report_date, site_code")
    rows = cursor.fetchall()
    print(f"  Found {len(rows)} rows in SQLite")

    if dry_run or not rows:
        return len(rows)

    pg_cur = pg_conn.cursor()
    inserted = 0
    skipped = 0

    for row in rows:
        rd = safe_date(row["report_date"])
        if not rd:
            skipped += 1
            continue

        try:
            pg_cur.execute(
                """INSERT INTO site_metrics
                (report_date, site_code, veeam_tb, wasabi_active_tb, wasabi_deleted_tb,
                 discrepancy_pct, success_rate_pct, total_jobs,
                 increment_jobs, reverse_increment_jobs, gold_jobs, silver_jobs, bronze_jobs)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (report_date, site_code) DO NOTHING""",
                (
                    rd,
                    row["site_code"],
                    safe_float(row["veeam_tb"]),
                    safe_float(row["wasabi_active_tb"]),
                    safe_float(row["wasabi_deleted_tb"]),
                    safe_float(row["discrepancy_pct"]),
                    safe_float(row["success_rate_pct"]),
                    safe_int(row["total_jobs"]),
                    safe_int(row["increment_jobs"]),
                    safe_int(row["reverse_jobs"]),
                    safe_int(row["gold_jobs"]),
                    safe_int(row["silver_jobs"]),
                    safe_int(row["bronze_jobs"]),
                ),
            )
            inserted += 1
        except Exception as e:
            print(f"  WARN: Skipping site_metric {rd}/{row['site_code']}: {e}")
            pg_conn.rollback()
            skipped += 1

    pg_conn.commit()
    print(f"  Inserted: {inserted}, Skipped: {skipped}")
    return inserted


def migrate_bdr_metrics(sqlite_conn, pg_conn, dry_run=False):
    print("\n--- bdr_metrics ---")
    cursor = sqlite_conn.execute("SELECT * FROM bdr_metrics ORDER BY report_date, bdr_server")
    rows = cursor.fetchall()
    print(f"  Found {len(rows)} rows in SQLite")

    if dry_run or not rows:
        return len(rows)

    pg_cur = pg_conn.cursor()
    inserted = 0
    skipped = 0

    for row in rows:
        rd = safe_date(row["report_date"])
        if not rd:
            skipped += 1
            continue

        try:
            pg_cur.execute(
                """INSERT INTO bdr_metrics
                (report_date, bdr_server, site_code, backup_size_tb, disk_free_tb, disk_free_pct)
                VALUES (%s,%s,%s,%s,%s,%s)
                ON CONFLICT (report_date, bdr_server) DO NOTHING""",
                (
                    rd,
                    row["bdr_server"],
                    row["site_code"],
                    safe_float(row["backup_size_tb"]),
                    safe_float(row["disk_free_tb"]),
                    safe_float(row["disk_free_pct"]),
                ),
            )
            inserted += 1
        except Exception as e:
            print(f"  WARN: Skipping bdr_metric {rd}/{row['bdr_server']}: {e}")
            pg_conn.rollback()
            skipped += 1

    pg_conn.commit()
    print(f"  Inserted: {inserted}, Skipped: {skipped}")
    return inserted


def migrate_bucket_metrics(sqlite_conn, pg_conn, dry_run=False):
    print("\n--- bucket_metrics ---")
    cursor = sqlite_conn.execute("SELECT * FROM bucket_metrics ORDER BY report_date, bucket_name")
    rows = cursor.fetchall()
    print(f"  Found {len(rows)} rows in SQLite")

    if dry_run or not rows:
        return len(rows)

    pg_cur = pg_conn.cursor()
    inserted = 0
    skipped = 0

    for row in rows:
        rd = safe_date(row["report_date"])
        if not rd:
            skipped += 1
            continue

        try:
            pg_cur.execute(
                """INSERT INTO bucket_metrics
                (report_date, bucket_name, site_code, active_tb, deleted_tb,
                 active_cost, deleted_cost, total_cost)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (report_date, bucket_name) DO NOTHING""",
                (
                    rd,
                    row["bucket_name"],
                    row["site_code"],
                    safe_float(row["active_tb"]),
                    safe_float(row["deleted_tb"]),
                    safe_float(row["active_cost"]),
                    safe_float(row["deleted_cost"]),
                    safe_float(row["total_cost"]),
                ),
            )
            inserted += 1
        except Exception as e:
            print(f"  WARN: Skipping bucket_metric {rd}/{row['bucket_name']}: {e}")
            pg_conn.rollback()
            skipped += 1

    pg_conn.commit()
    print(f"  Inserted: {inserted}, Skipped: {skipped}")
    return inserted


def migrate_anomalies(sqlite_conn, pg_conn, dry_run=False):
    print("\n--- anomalies ---")
    cursor = sqlite_conn.execute("SELECT * FROM anomalies ORDER BY report_date")
    rows = cursor.fetchall()
    print(f"  Found {len(rows)} rows in SQLite")

    if dry_run or not rows:
        return len(rows)

    pg_cur = pg_conn.cursor()
    inserted = 0
    skipped = 0

    for row in rows:
        rd = safe_date(row["report_date"])
        if not rd:
            skipped += 1
            continue

        try:
            pg_cur.execute(
                """INSERT INTO anomalies
                (report_date, severity, type, metric, previous_value,
                 current_value, change_pct, description)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    rd,
                    row["severity"] or "MEDIUM",
                    row["anomaly_type"] or "unknown",
                    row["metric"],
                    safe_float(row["previous_value"]),
                    safe_float(row["current_value"]),
                    safe_float(row["change_pct"]),
                    row["description"],
                ),
            )
            inserted += 1
        except Exception as e:
            print(f"  WARN: Skipping anomaly {rd}: {e}")
            pg_conn.rollback()
            skipped += 1

    pg_conn.commit()
    print(f"  Inserted: {inserted}, Skipped: {skipped}")
    return inserted


def migrate_settings(settings_path: Path, pg_conn, dry_run=False):
    print("\n--- settings ---")

    defaults = {
        "wasabi_cost_per_tb": 6.99,
        "sales_tax_rate": 0.0685,
        "discrepancy_threshold_pct": 20,
        "low_disk_threshold_pct": 20,
        "deleted_ratio_threshold": 0.5,
    }

    settings = defaults.copy()
    if settings_path.exists():
        try:
            with open(settings_path, "r") as f:
                settings.update(json.load(f))
            print(f"  Loaded settings from {settings_path}")
        except (json.JSONDecodeError, IOError) as e:
            print(f"  WARN: Could not load settings file: {e}")
            print("  Using defaults")
    else:
        print(f"  Settings file not found at {settings_path}, using defaults")

    if dry_run:
        for k, v in settings.items():
            print(f"    {k} = {v}")
        return len(settings)

    pg_cur = pg_conn.cursor()
    for key, value in settings.items():
        pg_cur.execute(
            """INSERT INTO settings (key, value)
            VALUES (%s, %s)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()""",
            (key, json.dumps(value)),
        )

    pg_conn.commit()
    print(f"  Migrated {len(settings)} settings")
    return len(settings)


def main():
    parser = argparse.ArgumentParser(description="Migrate data from SQLite to PostgreSQL")
    parser.add_argument(
        "--sqlite-path",
        type=str,
        default=str(DEFAULT_SQLITE_PATH),
        help=f"Path to SQLite database (default: {DEFAULT_SQLITE_PATH})",
    )
    parser.add_argument(
        "--settings-path",
        type=str,
        default=str(DEFAULT_SETTINGS_PATH),
        help=f"Path to settings.json (default: {DEFAULT_SETTINGS_PATH})",
    )
    parser.add_argument(
        "--pg-dsn",
        type=str,
        default=DEFAULT_PG_DSN,
        help="PostgreSQL connection string",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count rows without writing to PostgreSQL",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("SQLite -> PostgreSQL Migration")
    print("=" * 60)
    print(f"  SQLite:   {args.sqlite_path}")
    print(f"  Postgres: {args.pg_dsn}")
    print(f"  Settings: {args.settings_path}")
    if args.dry_run:
        print("  MODE: DRY RUN (no writes)")

    # Connect
    sqlite_conn = connect_sqlite(Path(args.sqlite_path))
    pg_conn = None if args.dry_run else connect_postgres(args.pg_dsn)

    totals = {}
    try:
        totals["daily_summaries"] = migrate_daily_summaries(sqlite_conn, pg_conn, args.dry_run)
        totals["site_metrics"] = migrate_site_metrics(sqlite_conn, pg_conn, args.dry_run)
        totals["bdr_metrics"] = migrate_bdr_metrics(sqlite_conn, pg_conn, args.dry_run)
        totals["bucket_metrics"] = migrate_bucket_metrics(sqlite_conn, pg_conn, args.dry_run)
        totals["anomalies"] = migrate_anomalies(sqlite_conn, pg_conn, args.dry_run)
        totals["settings"] = migrate_settings(Path(args.settings_path), pg_conn, args.dry_run)
    finally:
        sqlite_conn.close()
        if pg_conn:
            pg_conn.close()

    print("\n" + "=" * 60)
    print("Migration Summary")
    print("=" * 60)
    for table, count in totals.items():
        print(f"  {table}: {count}")
    print("\nDone!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
