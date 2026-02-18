#!/usr/bin/env python3
"""
Wasabi Audit File Downloader

Downloads Veeam audit files from a dedicated Wasabi S3 bucket into date-based folders.
Adapted from veeam-audit-old to work with the new project structure.
"""

import argparse
import os
import re
import sys
from pathlib import Path

try:
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError, NoCredentialsError
except ImportError:
    print("Error: boto3 is required. Install with: pip install boto3")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    print("Error: python-dotenv is required. Install with: pip install python-dotenv")
    sys.exit(1)

# Load environment variables
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
load_dotenv(PROJECT_DIR / ".env")

# Configuration
WASABI_ACCESS_KEY_ID = os.getenv("WASABI_ACCESS_KEY_ID", "")
WASABI_SECRET_ACCESS_KEY = os.getenv("WASABI_SECRET_ACCESS_KEY", "")
WASABI_REGION = os.getenv("WASABI_REGION", "us-east-1")
WASABI_ENDPOINT_URL = os.getenv("WASABI_ENDPOINT_URL", "https://s3.us-east-1.wasabisys.com")
WASABI_AUDIT_BUCKET = os.getenv("WASABI_AUDIT_BUCKET", "")
WASABI_AUDIT_PREFIX = os.getenv("WASABI_AUDIT_PREFIX", "Veeam/Audit/")

DATA_DIR = PROJECT_DIR / "input_veeam_audits"


def get_s3_client():
    if not WASABI_ACCESS_KEY_ID or not WASABI_SECRET_ACCESS_KEY:
        raise ValueError("Wasabi credentials not configured. Set in .env file.")
    if not WASABI_AUDIT_BUCKET:
        raise ValueError("WASABI_AUDIT_BUCKET not configured. Set in .env file.")

    config = Config(signature_version="s3v4", s3={"addressing_style": "path"})
    return boto3.client(
        "s3",
        endpoint_url=WASABI_ENDPOINT_URL,
        aws_access_key_id=WASABI_ACCESS_KEY_ID,
        aws_secret_access_key=WASABI_SECRET_ACCESS_KEY,
        region_name=WASABI_REGION,
        config=config,
    )


def list_bucket_files(s3_client, prefix=""):
    full_prefix = WASABI_AUDIT_PREFIX + prefix if WASABI_AUDIT_PREFIX else prefix
    files = []
    paginator = s3_client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=WASABI_AUDIT_BUCKET, Prefix=full_prefix):
        if "Contents" in page:
            for obj in page["Contents"]:
                files.append({
                    "key": obj["Key"],
                    "size": obj["Size"],
                    "last_modified": obj["LastModified"],
                    "filename": obj["Key"].split("/")[-1],
                })
    return files


def list_date_folders(s3_client):
    response = s3_client.list_objects_v2(
        Bucket=WASABI_AUDIT_BUCKET, Prefix=WASABI_AUDIT_PREFIX, Delimiter="/"
    )
    folders = []
    for cp in response.get("CommonPrefixes", []):
        folder_name = cp["Prefix"].rstrip("/").split("/")[-1]
        if re.match(r"^\d{4}-\d{2}-\d{2}$", folder_name):
            folders.append({"name": folder_name, "prefix": cp["Prefix"]})
    return sorted(folders, key=lambda x: x["name"], reverse=True)


def download_file(s3_client, key, local_path):
    local_path.parent.mkdir(parents=True, exist_ok=True)
    s3_client.download_file(WASABI_AUDIT_BUCKET, key, str(local_path))


def format_size(size_bytes):
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def main():
    parser = argparse.ArgumentParser(description="Download Veeam audit files from Wasabi S3")
    parser.add_argument("--date", type=str, default=None, help="Target date folder (default: auto-detect)")
    parser.add_argument("--list-only", action="store_true", help="List available date folders")
    args = parser.parse_args()

    print("=" * 60)
    print("Wasabi Audit File Downloader")
    print("=" * 60)

    try:
        s3_client = get_s3_client()
    except ValueError as e:
        print(f"\nError: {e}")
        sys.exit(1)

    print("\nConnecting to Wasabi...")
    try:
        date_folders = list_date_folders(s3_client)
    except (NoCredentialsError, ClientError) as e:
        print(f"Error: {e}")
        sys.exit(1)

    if not date_folders:
        print("No date folders found in bucket")
        sys.exit(0)

    print(f"  Found {len(date_folders)} date folder(s)")

    if args.list_only:
        for folder in date_folders:
            folder_files = list_bucket_files(s3_client, folder["name"] + "/")
            csv_files = [f for f in folder_files if f["filename"].endswith(".csv")]
            total_size = sum(f["size"] for f in csv_files)
            print(f"  {folder['name']}: {len(csv_files)} files ({format_size(total_size)})")
        return

    if args.date:
        target_date = args.date
        matching = [f for f in date_folders if f["name"] == target_date]
        if not matching:
            print(f"\nError: Date folder '{target_date}' not found")
            sys.exit(1)
    else:
        target_date = date_folders[0]["name"]
        print(f"\nAuto-detected most recent folder: {target_date}")

    folder_files = list_bucket_files(s3_client, target_date + "/")
    csv_files = [f for f in folder_files if f["filename"].endswith(".csv")]

    if not csv_files:
        print(f"No CSV files found in {target_date}/")
        sys.exit(0)

    print(f"  Found {len(csv_files)} CSV file(s)")
    target_dir = DATA_DIR / target_date
    print(f"\nDownloading to: {target_dir}")

    downloaded = 0
    total_size = 0
    for f in csv_files:
        local_path = target_dir / f["filename"]
        print(f"  Downloading {f['filename']}...")
        try:
            download_file(s3_client, f["key"], local_path)
            downloaded += 1
            total_size += f["size"]
        except ClientError as e:
            print(f"    Error: {e}")

    print(f"\nDownload complete! {downloaded} files, {format_size(total_size)}")


if __name__ == "__main__":
    main()
