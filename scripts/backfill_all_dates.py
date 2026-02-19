#!/usr/bin/env python3
"""
Backfill All Historical Dates from Wasabi S3

Downloads all date folders from Wasabi S3 and processes each one into PostgreSQL.
Used to populate a fresh database with all historical Veeam audit data.

Also fetches per-date Wasabi bucket utilization via the Stats API (supports
historical date ranges with --from/--to), so each date gets its own cost data.

Usage:
    python scripts/backfill_all_dates.py --verbose
    python scripts/backfill_all_dates.py --dry-run        # List dates without processing
    python scripts/backfill_all_dates.py --start 2025-12-01  # Start from specific date
"""

import argparse
import os
import sys
import subprocess
import time
from pathlib import Path

from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
load_dotenv(PROJECT_DIR / ".env")

# Import S3 helpers from the download script
sys.path.insert(0, str(SCRIPT_DIR))
from download_wasabi_audits import (
    get_s3_client,
    list_date_folders,
    list_bucket_files,
    download_file,
    format_size,
    DATA_DIR,
)


def download_date_folder(s3_client, date_name, verbose=False):
    """Download all CSVs for a single date folder from S3."""
    target_dir = DATA_DIR / date_name
    folder_files = list_bucket_files(s3_client, date_name + "/")
    csv_files = [f for f in folder_files if f["filename"].endswith(".csv")]

    if not csv_files:
        if verbose:
            print(f"    No CSV files in {date_name}/")
        return 0

    # Check if already downloaded (all files present)
    existing = set(f.name for f in target_dir.glob("*.csv")) if target_dir.exists() else set()
    needed = [f for f in csv_files if f["filename"] not in existing]

    if not needed:
        if verbose:
            print(f"    Already downloaded ({len(csv_files)} files)")
        return len(csv_files)

    downloaded = 0
    for f in needed:
        local_path = target_dir / f["filename"]
        try:
            download_file(s3_client, f["key"], local_path)
            downloaded += 1
        except Exception as e:
            print(f"    ERROR downloading {f['filename']}: {e}")

    if verbose:
        print(f"    Downloaded {downloaded} new files ({len(existing)} already existed)")
    return len(csv_files)


def process_date(date_name, verbose=False):
    """Run process_and_store.py for a single date."""
    cmd = [sys.executable, str(SCRIPT_DIR / "process_and_store.py"), "--date", date_name]
    if verbose:
        cmd.append("--verbose")

    result = subprocess.run(cmd, cwd=str(PROJECT_DIR), capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        print(f"    FAILED processing {date_name}")
        if result.stderr:
            # Show last few lines of stderr
            for line in result.stderr.strip().split("\n")[-5:]:
                print(f"      {line}")
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description="Backfill all historical dates from Wasabi S3 into PostgreSQL")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed progress")
    parser.add_argument("--dry-run", action="store_true", help="List dates without downloading or processing")
    parser.add_argument("--start", type=str, help="Start from this date (skip earlier dates)")
    parser.add_argument("--skip-download", action="store_true", help="Skip S3 download (use existing local files)")
    args = parser.parse_args()

    print("=" * 60)
    print("Backfill All Historical Dates")
    print("=" * 60)

    # Connect to S3 and list all date folders
    if not args.skip_download:
        print("\nConnecting to Wasabi S3...")
        try:
            s3_client = get_s3_client()
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)

    if args.skip_download:
        # Use local folders instead
        date_folders_raw = sorted(
            [d.name for d in DATA_DIR.iterdir() if d.is_dir() and len(d.name) == 10],
        )
        date_folders = [{"name": d} for d in date_folders_raw]
    else:
        date_folders = list_date_folders(s3_client)
        # list_date_folders returns newest-first; reverse for chronological order
        date_folders.reverse()

    if not date_folders:
        print("No date folders found!")
        sys.exit(1)

    # Apply --start filter
    if args.start:
        date_folders = [f for f in date_folders if f["name"] >= args.start]

    total = len(date_folders)
    print(f"\nFound {total} date folder(s): {date_folders[0]['name']} to {date_folders[-1]['name']}")

    if args.dry_run:
        print("\nDate folders:")
        for f in date_folders:
            print(f"  {f['name']}")
        print(f"\nTotal: {total} dates (dry run, nothing downloaded or processed)")
        return 0

    # Fetch per-date Wasabi utilization data via Stats API
    if not args.skip_download:
        earliest_date = date_folders[0]["name"]
        latest_date = date_folders[-1]["name"]
        fetch_script = str(SCRIPT_DIR / "fetch_wasabi_utilization.py")
        print(f"\nFetching Wasabi utilization data from {earliest_date} to {latest_date}...")
        wasabi_result = subprocess.run(
            [sys.executable, fetch_script, "--from", earliest_date, "--to", latest_date, "--save-by-date"],
            cwd=str(PROJECT_DIR),
            capture_output=True,
            text=True,
            timeout=300,
        )
        if wasabi_result.returncode != 0:
            print("WARNING: Failed to fetch Wasabi utilization data")
            if wasabi_result.stderr:
                for line in wasabi_result.stderr.strip().split("\n")[-5:]:
                    print(f"  {line}")
            print("  Continuing with whatever Wasabi data is available locally...\n")
        else:
            if args.verbose and wasabi_result.stdout:
                for line in wasabi_result.stdout.strip().split("\n"):
                    print(f"  {line}")
            print("  Wasabi utilization data fetched successfully.\n")

    # Process each date
    print()
    succeeded = 0
    failed = 0
    skipped = 0
    start_time = time.time()

    for i, folder in enumerate(date_folders, 1):
        date_name = folder["name"]
        print(f"[{i}/{total}] {date_name}")

        # Download
        if not args.skip_download:
            file_count = download_date_folder(s3_client, date_name, verbose=args.verbose)
            if file_count == 0:
                print(f"    Skipped (no CSV files)")
                skipped += 1
                continue

        # Check local folder exists
        local_dir = DATA_DIR / date_name
        if not local_dir.exists() or not list(local_dir.glob("*.csv")):
            print(f"    Skipped (no local data)")
            skipped += 1
            continue

        # Process
        ok = process_date(date_name, verbose=args.verbose)
        if ok:
            succeeded += 1
            if args.verbose:
                print(f"    OK")
        else:
            failed += 1

    elapsed = time.time() - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)

    print()
    print("=" * 60)
    print(f"Backfill complete in {minutes}m {seconds}s")
    print(f"  Succeeded: {succeeded}")
    print(f"  Failed:    {failed}")
    print(f"  Skipped:   {skipped}")
    print(f"  Total:     {total}")
    print("=" * 60)

    return 1 if failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
