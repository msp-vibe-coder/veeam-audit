#!/usr/bin/env python3
"""
Process Veeam audit CSVs + Wasabi utilization CSV and write directly to PostgreSQL.

Replaces the old pipeline of: generate_combined_report.py -> analyze_trends.py -> sync.py
Now goes straight from raw CSV data into the Postgres database.

Usage:
    python scripts/process_and_store.py
    python scripts/process_and_store.py --date 2026-01-28
    python scripts/process_and_store.py --verbose
"""

import argparse
import os
import re
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
load_dotenv(PROJECT_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://veeam:changeme@localhost:5432/veeam_audit")

BASE_DATA_DIR = PROJECT_DIR / "input_veeam_audits"
WASABI_REPORTS_DIR = PROJECT_DIR / "input_wasabi_utilization"

# Default thresholds (overridden by DB settings if available)
WASABI_COST_PER_TB = 6.99
SALES_TAX_RATE = 0.0685
LOW_DISK_THRESHOLD_PCT = 20
DISCREPANCY_THRESHOLD_PCT = 20
DELETED_RATIO_THRESHOLD = 0.5


def load_settings_from_db(conn):
    """Load configurable settings from the database."""
    global WASABI_COST_PER_TB, SALES_TAX_RATE, LOW_DISK_THRESHOLD_PCT
    global DISCREPANCY_THRESHOLD_PCT, DELETED_RATIO_THRESHOLD

    try:
        cur = conn.cursor()
        cur.execute("SELECT key, value FROM settings")
        for key, value in cur.fetchall():
            if key == "wasabi_cost_per_tb":
                WASABI_COST_PER_TB = float(value)
            elif key == "sales_tax_rate":
                SALES_TAX_RATE = float(value)
            elif key == "low_disk_threshold_pct":
                LOW_DISK_THRESHOLD_PCT = float(value)
            elif key == "discrepancy_threshold_pct":
                DISCREPANCY_THRESHOLD_PCT = float(value)
            elif key == "deleted_ratio_threshold":
                DELETED_RATIO_THRESHOLD = float(value)
    except Exception:
        pass  # Use defaults if settings table doesn't exist or is empty


# -- Site code extraction (same logic as old project) --

def extract_bdr_server_from_filename(filename: str) -> str:
    name = filename.replace("VeeamFullAudit_", "").replace(".csv", "")
    match = re.match(r"^(.+?)_\d{4}-\d{2}-\d{2}_\d{6}$", name)
    return match.group(1) if match else name


def extract_site_code_from_bdr(bdr_server: str) -> str:
    match = re.match(r"^([A-Z]{2,4})-", bdr_server)
    if match:
        return match.group(1)
    match = re.match(r"^([A-Z]{2,4})CORP", bdr_server)
    if match:
        return match.group(1)
    match = re.match(r"^([A-Z]{2,4})LAB", bdr_server)
    if match:
        return match.group(1)
    match = re.match(r"^([A-Z]{3})([A-Z]{3,4})(PS|SLC)", bdr_server)
    if match:
        return match.group(1)
    match = re.match(r"^([A-Z]{2,4})[A-Z]{1,4}PS", bdr_server)
    if match:
        return match.group(1)
    return bdr_server[:3].upper()


def extract_site_code_from_bucket(bucket_name: str) -> str:
    parts = bucket_name.split("-")
    return parts[0].upper() if parts else bucket_name.upper()


# -- Data loading --

def get_most_recent_data_folder(target_date: str = None) -> Path:
    if target_date:
        folder = BASE_DATA_DIR / target_date
        if folder.exists():
            return folder
        raise FileNotFoundError(f"Data folder not found: {folder}")

    date_folders = [
        d for d in BASE_DATA_DIR.iterdir()
        if d.is_dir() and re.match(r"\d{4}-\d{2}-\d{2}", d.name)
    ]
    if not date_folders:
        raise FileNotFoundError(f"No date folders found in: {BASE_DATA_DIR}")
    date_folders.sort(key=lambda x: x.name, reverse=True)
    return date_folders[0]


def get_wasabi_file(report_date: date = None) -> Path:
    if report_date:
        exact = WASABI_REPORTS_DIR / f"all-bucket-utilization-{report_date}.csv"
        if exact.exists():
            return exact
    # Fallback to most recent file
    wasabi_files = list(WASABI_REPORTS_DIR.glob("*bucket-utilization*.csv"))
    if not wasabi_files:
        raise FileNotFoundError(f"No Wasabi utilization files found in: {WASABI_REPORTS_DIR}")
    wasabi_files.sort(key=lambda x: x.name, reverse=True)
    return wasabi_files[0]


def load_veeam_data(data_dir: Path) -> pd.DataFrame:
    veeam_files = list(data_dir.glob("VeeamFullAudit_*.csv"))
    if not veeam_files:
        raise ValueError(f"No Veeam data files found in: {data_dir}")

    all_data = []
    for filepath in veeam_files:
        try:
            df = pd.read_csv(filepath)
            bdr_server = extract_bdr_server_from_filename(filepath.name)
            df["BDR Server"] = bdr_server
            df["Site Code"] = extract_site_code_from_bdr(bdr_server)
            all_data.append(df)
        except Exception as e:
            print(f"  WARN: Error loading {filepath.name}: {e}")

    if not all_data:
        raise ValueError("No Veeam data could be loaded")
    return pd.concat(all_data, ignore_index=True)


def load_wasabi_data(wasabi_file: Path) -> pd.DataFrame:
    df = pd.read_csv(wasabi_file)
    df["Site Code"] = df["BucketName"].apply(extract_site_code_from_bucket)
    return df


# -- Metric computation --

def compute_metrics(veeam_df: pd.DataFrame, wasabi_df: pd.DataFrame, report_date: date):
    """Compute all metrics from raw data and return structured dicts."""

    wasabi_veeam = wasabi_df[wasabi_df["BucketName"].str.contains("veeam", case=False)].copy()

    # --- BDR metrics ---
    bdr_agg = veeam_df.groupby(["Site Code", "BDR Server"]).agg({
        "Total Backup Size GB": "first",
        "Disk Free GB": "first",
    }).reset_index()

    bdr_metrics = []
    for _, row in bdr_agg.iterrows():
        backup_gb = pd.to_numeric(row["Total Backup Size GB"], errors="coerce") or 0
        free_gb = pd.to_numeric(row["Disk Free GB"], errors="coerce") or 0
        total_disk = backup_gb + free_gb
        bdr_metrics.append({
            "report_date": report_date,
            "bdr_server": row["BDR Server"],
            "site_code": row["Site Code"],
            "backup_size_tb": round(backup_gb / 1024, 4),
            "disk_free_tb": round(free_gb / 1024, 4),
            "disk_free_pct": round(free_gb / total_disk * 100, 2) if total_disk > 0 else 0,
        })

    # --- Bucket metrics ---
    bucket_metrics = []
    for _, row in wasabi_veeam.iterrows():
        active_tb = float(row.get("BillableActiveStorageTB", 0) or 0)
        deleted_tb = float(row.get("BillableDeletedStorageTB", 0) or 0)
        active_cost = round(active_tb * WASABI_COST_PER_TB, 2)
        deleted_cost = round(deleted_tb * WASABI_COST_PER_TB, 2)
        total_cost = round((active_cost + deleted_cost) * (1 + SALES_TAX_RATE), 2)
        bucket_metrics.append({
            "report_date": report_date,
            "bucket_name": row["BucketName"],
            "site_code": row["Site Code"],
            "active_tb": round(active_tb, 4),
            "deleted_tb": round(deleted_tb, 4),
            "active_cost": active_cost,
            "deleted_cost": deleted_cost,
            "total_cost": total_cost,
        })

    # --- Site metrics ---
    # Storage per site
    wasabi_site_agg = wasabi_veeam.groupby("Site Code").agg({
        "BillableActiveStorageTB": "sum",
        "BillableDeletedStorageTB": "sum",
    }).reset_index()
    wasabi_by_site = {
        row["Site Code"]: row for _, row in wasabi_site_agg.iterrows()
    }

    # Veeam storage per site
    veeam_site_agg = veeam_df.groupby("Site Code").agg({
        "Total Backup Size GB": "first",
    })

    # But we need to sum across BDRs for total per site
    site_veeam_tb = {}
    for bdr in bdr_metrics:
        sc = bdr["site_code"]
        site_veeam_tb[sc] = site_veeam_tb.get(sc, 0) + bdr["backup_size_tb"]

    # Job metrics per site
    def calc_job_stats(group):
        total = len(group)
        if "Success Rate 24h %" in group.columns:
            rates = pd.to_numeric(group["Success Rate 24h %"], errors="coerce").fillna(100)
            failed = int((rates < 50).sum())
            warning = int(((rates >= 50) & (rates < 80)).sum())
            success = int((rates >= 80).sum())
        elif "Last Result" in group.columns:
            failed = int((group["Last Result"] == "Failed").sum())
            warning = int((group["Last Result"] == "Warning").sum())
            success = int((group["Last Result"] == "Success").sum())
        else:
            failed = warning = 0
            success = total

        success_rate = round(success / total * 100, 2) if total > 0 else 0

        # Backup modes
        increment = 0
        reverse = 0
        if "Backup Mode" in group.columns:
            modes = group["Backup Mode"].str.lower().fillna("")
            increment = int(modes.str.contains("increment").sum())
            reverse = int(modes.str.contains("reverse").sum())

        # Tiers (Gold/Silver/Bronze based on schedule or naming)
        gold = silver = bronze = 0
        if "Schedule" in group.columns:
            schedules = group["Schedule"].str.lower().fillna("")
            gold = int(schedules.str.contains("gold|daily|every day", regex=True).sum())
            silver = int(schedules.str.contains("silver|weekly", regex=True).sum())
            bronze = int(schedules.str.contains("bronze|monthly", regex=True).sum())
        if gold + silver + bronze == 0:
            gold = total  # Default all to gold if no schedule info

        return {
            "total_jobs": total,
            "success_jobs": success,
            "failed_jobs": failed,
            "warning_jobs": warning,
            "success_rate_pct": success_rate,
            "increment_jobs": increment,
            "reverse_increment_jobs": reverse,
            "gold_jobs": gold,
            "silver_jobs": silver,
            "bronze_jobs": bronze,
        }

    job_stats_by_site = {}
    for site_code, group in veeam_df.groupby("Site Code"):
        job_stats_by_site[site_code] = calc_job_stats(group)

    site_metrics = []
    all_sites = set(site_veeam_tb.keys()) | set(wasabi_by_site.keys())
    for sc in sorted(all_sites):
        veeam_tb = site_veeam_tb.get(sc, 0)
        wasabi_row = wasabi_by_site.get(sc, {})
        wasabi_active = float(wasabi_row.get("BillableActiveStorageTB", 0) if isinstance(wasabi_row, dict) else getattr(wasabi_row, "BillableActiveStorageTB", 0) or 0)
        wasabi_deleted = float(wasabi_row.get("BillableDeletedStorageTB", 0) if isinstance(wasabi_row, dict) else getattr(wasabi_row, "BillableDeletedStorageTB", 0) or 0)
        disc_pct = round((veeam_tb - wasabi_active) / veeam_tb * 100, 2) if veeam_tb > 0 else 0

        jobs = job_stats_by_site.get(sc, {})
        site_metrics.append({
            "report_date": report_date,
            "site_code": sc,
            "veeam_tb": round(veeam_tb, 4),
            "wasabi_active_tb": round(wasabi_active, 4),
            "wasabi_deleted_tb": round(wasabi_deleted, 4),
            "discrepancy_pct": disc_pct,
            "success_rate_pct": jobs.get("success_rate_pct", 0),
            "total_jobs": jobs.get("total_jobs", 0),
            "increment_jobs": jobs.get("increment_jobs", 0),
            "reverse_increment_jobs": jobs.get("reverse_increment_jobs", 0),
            "gold_jobs": jobs.get("gold_jobs", 0),
            "silver_jobs": jobs.get("silver_jobs", 0),
            "bronze_jobs": jobs.get("bronze_jobs", 0),
        })

    # --- Daily summary ---
    total_veeam = sum(sm["veeam_tb"] for sm in site_metrics)
    total_wasabi_active = sum(sm["wasabi_active_tb"] for sm in site_metrics)
    total_wasabi_deleted = sum(sm["wasabi_deleted_tb"] for sm in site_metrics)
    disc_pct = round((total_veeam - total_wasabi_active) / total_veeam * 100, 2) if total_veeam > 0 else 0
    total_cost = sum(bm["total_cost"] for bm in bucket_metrics)
    total_active_cost = sum(bm["active_cost"] for bm in bucket_metrics)
    total_deleted_cost = sum(bm["deleted_cost"] for bm in bucket_metrics)

    low_disk = sum(1 for b in bdr_metrics if b["disk_free_pct"] < LOW_DISK_THRESHOLD_PCT)
    high_disc = sum(1 for s in site_metrics if abs(s["discrepancy_pct"]) > DISCREPANCY_THRESHOLD_PCT)
    high_deleted = sum(1 for bm in bucket_metrics if bm["deleted_tb"] > bm["active_tb"] * DELETED_RATIO_THRESHOLD)

    total_jobs = sum(js.get("total_jobs", 0) for js in job_stats_by_site.values())
    total_success = sum(js.get("success_jobs", 0) for js in job_stats_by_site.values())
    total_failed = sum(js.get("failed_jobs", 0) for js in job_stats_by_site.values())
    total_warning = sum(js.get("warning_jobs", 0) for js in job_stats_by_site.values())

    daily_summary = {
        "report_date": report_date,
        "veeam_tb": round(total_veeam, 4),
        "wasabi_active_tb": round(total_wasabi_active, 4),
        "wasabi_deleted_tb": round(total_wasabi_deleted, 4),
        "discrepancy_pct": disc_pct,
        "total_cost": round(total_cost, 2),
        "active_cost": round(total_active_cost * (1 + SALES_TAX_RATE), 2),
        "deleted_cost": round(total_deleted_cost * (1 + SALES_TAX_RATE), 2),
        "low_disk_count": low_disk,
        "high_discrepancy_count": high_disc,
        "high_deleted_count": high_deleted,
        "failed_job_count": total_failed,
        "warning_job_count": total_warning,
        "total_jobs": total_jobs,
        "successful_jobs": total_success,
        "failed_jobs": total_failed,
        "warning_jobs": total_warning,
    }

    # --- Anomalies ---
    anomalies = []
    for bdr in bdr_metrics:
        if bdr["disk_free_pct"] < 10:
            anomalies.append({"report_date": report_date, "severity": "CRITICAL", "type": "low_disk",
                              "metric": "disk_free_pct", "current_value": bdr["disk_free_pct"],
                              "description": f"{bdr['bdr_server']} has only {bdr['disk_free_pct']}% disk free"})
        elif bdr["disk_free_pct"] < 15:
            anomalies.append({"report_date": report_date, "severity": "HIGH", "type": "low_disk",
                              "metric": "disk_free_pct", "current_value": bdr["disk_free_pct"],
                              "description": f"{bdr['bdr_server']} has only {bdr['disk_free_pct']}% disk free"})
        elif bdr["disk_free_pct"] < LOW_DISK_THRESHOLD_PCT:
            anomalies.append({"report_date": report_date, "severity": "MEDIUM", "type": "low_disk",
                              "metric": "disk_free_pct", "current_value": bdr["disk_free_pct"],
                              "description": f"{bdr['bdr_server']} has only {bdr['disk_free_pct']}% disk free"})

    for sm in site_metrics:
        if abs(sm["discrepancy_pct"]) > 50:
            anomalies.append({"report_date": report_date, "severity": "CRITICAL", "type": "high_discrepancy",
                              "metric": "discrepancy_pct", "current_value": sm["discrepancy_pct"],
                              "description": f"Site {sm['site_code']} has {sm['discrepancy_pct']}% storage discrepancy"})
        elif abs(sm["discrepancy_pct"]) > 35:
            anomalies.append({"report_date": report_date, "severity": "HIGH", "type": "high_discrepancy",
                              "metric": "discrepancy_pct", "current_value": sm["discrepancy_pct"],
                              "description": f"Site {sm['site_code']} has {sm['discrepancy_pct']}% storage discrepancy"})
        elif abs(sm["discrepancy_pct"]) > DISCREPANCY_THRESHOLD_PCT:
            anomalies.append({"report_date": report_date, "severity": "MEDIUM", "type": "high_discrepancy",
                              "metric": "discrepancy_pct", "current_value": sm["discrepancy_pct"],
                              "description": f"Site {sm['site_code']} has {sm['discrepancy_pct']}% storage discrepancy"})

    for js_site, js in job_stats_by_site.items():
        if js["failed_jobs"] >= 5:
            anomalies.append({"report_date": report_date, "severity": "CRITICAL", "type": "failed_jobs",
                              "metric": "failed_job_count", "current_value": js["failed_jobs"],
                              "description": f"Site {js_site} has {js['failed_jobs']} failed backup jobs"})
        elif js["failed_jobs"] >= 3:
            anomalies.append({"report_date": report_date, "severity": "HIGH", "type": "failed_jobs",
                              "metric": "failed_job_count", "current_value": js["failed_jobs"],
                              "description": f"Site {js_site} has {js['failed_jobs']} failed backup jobs"})

    return daily_summary, site_metrics, bdr_metrics, bucket_metrics, anomalies


# -- Database writes --

def write_to_postgres(conn, daily_summary, site_metrics, bdr_metrics, bucket_metrics, anomalies, verbose=False):
    cur = conn.cursor()
    rd = daily_summary["report_date"]

    # Daily summary (upsert)
    cur.execute(
        """INSERT INTO daily_summaries
        (report_date, veeam_tb, wasabi_active_tb, wasabi_deleted_tb, discrepancy_pct,
         total_cost, active_cost, deleted_cost,
         low_disk_count, high_discrepancy_count, high_deleted_count,
         failed_job_count, warning_job_count, total_jobs, successful_jobs, failed_jobs, warning_jobs)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (report_date) DO UPDATE SET
         veeam_tb=EXCLUDED.veeam_tb, wasabi_active_tb=EXCLUDED.wasabi_active_tb,
         wasabi_deleted_tb=EXCLUDED.wasabi_deleted_tb, discrepancy_pct=EXCLUDED.discrepancy_pct,
         total_cost=EXCLUDED.total_cost, active_cost=EXCLUDED.active_cost,
         deleted_cost=EXCLUDED.deleted_cost, low_disk_count=EXCLUDED.low_disk_count,
         high_discrepancy_count=EXCLUDED.high_discrepancy_count,
         high_deleted_count=EXCLUDED.high_deleted_count,
         failed_job_count=EXCLUDED.failed_job_count, warning_job_count=EXCLUDED.warning_job_count,
         total_jobs=EXCLUDED.total_jobs, successful_jobs=EXCLUDED.successful_jobs,
         failed_jobs=EXCLUDED.failed_jobs, warning_jobs=EXCLUDED.warning_jobs""",
        (rd, daily_summary["veeam_tb"], daily_summary["wasabi_active_tb"],
         daily_summary["wasabi_deleted_tb"], daily_summary["discrepancy_pct"],
         daily_summary["total_cost"], daily_summary["active_cost"],
         daily_summary["deleted_cost"], daily_summary["low_disk_count"],
         daily_summary["high_discrepancy_count"], daily_summary["high_deleted_count"],
         daily_summary["failed_job_count"], daily_summary["warning_job_count"],
         daily_summary["total_jobs"], daily_summary["successful_jobs"],
         daily_summary["failed_jobs"], daily_summary["warning_jobs"]),
    )
    if verbose:
        print(f"  Wrote daily summary for {rd}")

    # Site metrics (delete + reinsert for date)
    cur.execute("DELETE FROM site_metrics WHERE report_date = %s", (rd,))
    for sm in site_metrics:
        cur.execute(
            """INSERT INTO site_metrics
            (report_date, site_code, veeam_tb, wasabi_active_tb, wasabi_deleted_tb,
             discrepancy_pct, success_rate_pct, total_jobs, increment_jobs,
             reverse_increment_jobs, gold_jobs, silver_jobs, bronze_jobs)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (sm["report_date"], sm["site_code"], sm["veeam_tb"],
             sm["wasabi_active_tb"], sm["wasabi_deleted_tb"],
             sm["discrepancy_pct"], sm["success_rate_pct"], sm["total_jobs"],
             sm["increment_jobs"], sm["reverse_increment_jobs"],
             sm["gold_jobs"], sm["silver_jobs"], sm["bronze_jobs"]),
        )
    if verbose:
        print(f"  Wrote {len(site_metrics)} site metrics")

    # BDR metrics
    cur.execute("DELETE FROM bdr_metrics WHERE report_date = %s", (rd,))
    for bm in bdr_metrics:
        cur.execute(
            """INSERT INTO bdr_metrics
            (report_date, bdr_server, site_code, backup_size_tb, disk_free_tb, disk_free_pct)
            VALUES (%s,%s,%s,%s,%s,%s)""",
            (bm["report_date"], bm["bdr_server"], bm["site_code"],
             bm["backup_size_tb"], bm["disk_free_tb"], bm["disk_free_pct"]),
        )
    if verbose:
        print(f"  Wrote {len(bdr_metrics)} BDR metrics")

    # Bucket metrics
    cur.execute("DELETE FROM bucket_metrics WHERE report_date = %s", (rd,))
    for bk in bucket_metrics:
        cur.execute(
            """INSERT INTO bucket_metrics
            (report_date, bucket_name, site_code, active_tb, deleted_tb,
             active_cost, deleted_cost, total_cost)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
            (bk["report_date"], bk["bucket_name"], bk["site_code"],
             bk["active_tb"], bk["deleted_tb"],
             bk["active_cost"], bk["deleted_cost"], bk["total_cost"]),
        )
    if verbose:
        print(f"  Wrote {len(bucket_metrics)} bucket metrics")

    # Anomalies
    cur.execute("DELETE FROM anomalies WHERE report_date = %s", (rd,))
    for a in anomalies:
        cur.execute(
            """INSERT INTO anomalies
            (report_date, severity, type, metric, current_value, description)
            VALUES (%s,%s,%s,%s,%s,%s)""",
            (a["report_date"], a["severity"], a["type"],
             a.get("metric"), a.get("current_value"), a.get("description")),
        )
    if verbose:
        print(f"  Wrote {len(anomalies)} anomalies")

    conn.commit()


def main():
    parser = argparse.ArgumentParser(description="Process Veeam/Wasabi CSVs into PostgreSQL")
    parser.add_argument("--date", type=str, help="Target date folder (default: auto-detect)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed progress")
    parser.add_argument("--pg-dsn", type=str, default=DATABASE_URL, help="PostgreSQL connection string")
    args = parser.parse_args()

    print("=" * 60)
    print("Process & Store: CSV -> PostgreSQL")
    print("=" * 60)

    # Find data
    try:
        data_dir = get_most_recent_data_folder(args.date)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)

    report_date = datetime.strptime(data_dir.name, "%Y-%m-%d").date()
    print(f"  Data folder: {data_dir}")
    print(f"  Report date: {report_date}")

    try:
        wasabi_file = get_wasabi_file(report_date)
        print(f"  Wasabi file: {wasabi_file}")
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Load raw data
    print("\nLoading data...")
    veeam_df = load_veeam_data(data_dir)
    wasabi_df = load_wasabi_data(wasabi_file)
    print(f"  Loaded {len(veeam_df)} Veeam job rows from {len(list(data_dir.glob('*.csv')))} files")
    print(f"  Loaded {len(wasabi_df)} Wasabi bucket rows")

    # Connect to Postgres and load settings
    conn = psycopg2.connect(args.pg_dsn)
    load_settings_from_db(conn)

    # Compute metrics
    print("\nComputing metrics...")
    daily_summary, site_metrics, bdr_metrics, bucket_metrics, anomalies = compute_metrics(
        veeam_df, wasabi_df, report_date
    )

    print(f"  Sites: {len(site_metrics)}")
    print(f"  BDR servers: {len(bdr_metrics)}")
    print(f"  Buckets: {len(bucket_metrics)}")
    print(f"  Anomalies: {len(anomalies)}")
    print(f"  Total Veeam: {daily_summary['veeam_tb']:.2f} TB")
    print(f"  Total Wasabi Active: {daily_summary['wasabi_active_tb']:.2f} TB")
    print(f"  Total Cost: ${daily_summary['total_cost']:.2f}")

    # Write to database
    print("\nWriting to PostgreSQL...")
    write_to_postgres(conn, daily_summary, site_metrics, bdr_metrics, bucket_metrics, anomalies, args.verbose)
    conn.close()

    print("\nDone!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
