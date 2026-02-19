#!/usr/bin/env python3
"""
Fetch Wasabi bucket utilization data via the Wasabi Stats API.

Output is saved to input_wasabi_utilization/all-bucket-utilization-YYYY-MM-DD.csv.
"""

import argparse
import csv
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
load_dotenv(PROJECT_DIR / ".env")

WASABI_STATS_API = "https://stats.wasabisys.com"
BYTES_TO_TB = 1024**4


def load_credentials():
    # Prefer dedicated stats API credentials, fall back to S3 credentials
    access_key = os.getenv("WASABI_STATS_ACCESS_KEY") or os.getenv("WASABI_ACCESS_KEY_ID")
    secret_key = os.getenv("WASABI_STATS_SECRET_KEY") or os.getenv("WASABI_SECRET_ACCESS_KEY")
    if not access_key or not secret_key:
        print("Error: WASABI_ACCESS_KEY_ID and WASABI_SECRET_ACCESS_KEY (or WASABI_STATS_ACCESS_KEY/SECRET_KEY) must be set in .env")
        sys.exit(1)
    return access_key, secret_key


def fetch_utilization(access_key, secret_key, from_date=None, to_date=None, latest=False):
    url = f"{WASABI_STATS_API}/v1/standalone/utilizations/bucket"
    headers = {"Authorization": f"{access_key}:{secret_key}"}
    all_records = []
    page_num = 0
    total_pages = None

    while True:
        params = {"pageNum": page_num, "pageSize": 100}
        if latest:
            params["latest"] = "true"
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date

        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            print(f"Error: API returned status {response.status_code}")
            sys.exit(1)

        data = response.json()
        if isinstance(data, dict) and "Records" in data:
            records = data["Records"]
            all_records.extend(records)
            if total_pages is None:
                total_pages = data.get("PageInfo", {}).get("PageCount", 1)
            if page_num + 1 >= total_pages or not records:
                break
            page_num += 1
        else:
            all_records = data if isinstance(data, list) else ([data] if data else [])
            break

    print(f"  Retrieved {len(all_records)} bucket records")
    return all_records


def deduplicate_by_bucket(records):
    latest_by_bucket = {}
    for record in records:
        bucket = record.get("Bucket", "")
        start_time = record.get("StartTime", "")
        if bucket not in latest_by_bucket or start_time > latest_by_bucket[bucket].get("StartTime", ""):
            latest_by_bucket[bucket] = record
    return list(latest_by_bucket.values())


def convert_to_csv_format(records):
    csv_records = []
    for record in records:
        bucket_name = record.get("Bucket") or record.get("BucketName", "")
        padded_bytes = record.get("PaddedStorageSizeBytes", 0) or 0
        deleted_bytes = record.get("DeletedStorageSizeBytes", 0) or 0
        active_tb = padded_bytes / BYTES_TO_TB
        deleted_tb = deleted_bytes / BYTES_TO_TB

        csv_records.append({
            "BucketName": bucket_name,
            "Region": record.get("Region", ""),
            "BucketNum": record.get("BucketNum", ""),
            "BucketStatus": "Deleted" if padded_bytes == 0 and deleted_bytes > 0 else "Active",
            "RecordDate": record.get("StartTime") or record.get("Date", ""),
            "NumBillableActiveStorageObjects": record.get("NumBillableObjects", 0) or 0,
            "NumBillableDeletedStorageObjects": record.get("NumBillableDeletedObjects", 0) or 0,
            "BillableActiveStorageTB": f"{active_tb:.4f}",
            "BillableDeletedStorageTB": f"{deleted_tb:.4f}",
        })
    return csv_records


def write_csv(records, output_path):
    if not records:
        return
    fieldnames = [
        "BucketName", "Region", "BucketNum", "BucketStatus", "RecordDate",
        "NumBillableActiveStorageObjects", "NumBillableDeletedStorageObjects",
        "BillableActiveStorageTB", "BillableDeletedStorageTB",
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    print(f"Wrote {len(records)} records to {output_path}")


def save_records_by_date(records, output_dir):
    """Group records by StartTime date and save per-date CSVs."""
    by_date = {}
    for r in records:
        d = r.get("StartTime", "")[:10]  # YYYY-MM-DD
        if d:
            by_date.setdefault(d, []).append(r)
    for d, recs in sorted(by_date.items()):
        deduped = deduplicate_by_bucket(recs)
        csv_recs = convert_to_csv_format(deduped)
        path = output_dir / f"all-bucket-utilization-{d}.csv"
        write_csv(csv_recs, path)
    print(f"\nSaved per-date CSVs for {len(by_date)} dates")


def main():
    parser = argparse.ArgumentParser(description="Fetch Wasabi bucket utilization via Stats API")
    parser.add_argument("--from", dest="from_date", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--to", dest="to_date", help="End date (YYYY-MM-DD)")
    parser.add_argument("--latest", action="store_true", help="Fetch only latest data point")
    parser.add_argument("--save-by-date", action="store_true",
                        help="Save separate CSV per date (for date-range queries)")
    parser.add_argument("--output", "-o", help="Output directory or file path")
    args = parser.parse_args()

    access_key, secret_key = load_credentials()
    use_latest = args.latest or (not args.from_date and not args.to_date)

    records = fetch_utilization(access_key, secret_key, args.from_date, args.to_date, use_latest)

    if args.save_by_date:
        output_dir = Path(args.output) if args.output else PROJECT_DIR / "input_wasabi_utilization"
        save_records_by_date(records, output_dir)
        print(f"\nSuccess! Per-date CSVs saved to: {output_dir}")
        return

    records = deduplicate_by_bucket(records)
    csv_records = convert_to_csv_format(records)

    if args.output:
        output_path = Path(args.output)
        if output_path.is_dir():
            output_path = output_path / f"all-bucket-utilization-{datetime.now().strftime('%Y-%m-%d')}.csv"
    else:
        output_path = PROJECT_DIR / "input_wasabi_utilization" / f"all-bucket-utilization-{datetime.now().strftime('%Y-%m-%d')}.csv"

    write_csv(csv_records, output_path)

    # Validate data freshness — detect stale API responses
    df = pd.read_csv(output_path)
    if "RecordDate" in df.columns and len(df) > 0:
        record_dates = pd.to_datetime(df["RecordDate"], errors="coerce")
        max_record = record_dates.max()
        if pd.notna(max_record):
            file_date = datetime.now().date()
            days_stale = (file_date - max_record.date()).days
            if days_stale > 7:
                print(f"\nWARNING: Wasabi data is stale! Most recent RecordDate={max_record.date()}, expected ~{file_date}")
                print(f"  Data is {days_stale} days old. API may be returning cached results.")
                sys.exit(1)

    print(f"\nSuccess! {len(csv_records)} buckets saved to: {output_path}")


if __name__ == "__main__":
    main()
