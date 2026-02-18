#!/usr/bin/env python3
"""
Veeam/Wasabi Audit Pipeline Orchestrator (New Version)

Runs all data refresh steps in sequence:
1. Download Veeam audit files from Wasabi S3
2. Fetch Wasabi bucket utilization via API
3. Process CSVs and write directly to PostgreSQL

Usage:
    python scripts/pipeline.py                 # Run full pipeline
    python scripts/pipeline.py --skip-download # Skip download steps
    python scripts/pipeline.py --verbose
"""

import argparse
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
load_dotenv(PROJECT_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://veeam:changeme@localhost:5432/veeam_audit")
LOGS_DIR = PROJECT_DIR / "logs"

PIPELINE_STEPS = [
    {
        "name": "Download Veeam Audits",
        "script": "download_wasabi_audits.py",
        "skip_flag": "skip_download",
    },
    {
        "name": "Fetch Wasabi Utilization",
        "script": "fetch_wasabi_utilization.py",
        "skip_flag": "skip_download",
    },
    {
        "name": "Process & Store to PostgreSQL",
        "script": "process_and_store.py",
        "skip_flag": None,
    },
]


def setup_logging(verbose=False):
    LOGS_DIR.mkdir(exist_ok=True)
    logger = logging.getLogger("pipeline")
    logger.setLevel(logging.DEBUG)

    log_file = LOGS_DIR / f"pipeline_{datetime.now().strftime('%Y-%m-%d')}.log"
    fh = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(fh)

    if verbose:
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.INFO)
        ch.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        logger.addHandler(ch)

    return logger


def record_pipeline_run(status, started_at, log_text="", steps=None):
    """Record the pipeline run in the database."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        import json
        cur.execute(
            """INSERT INTO pipeline_runs (started_at, completed_at, status, steps, log_text)
            VALUES (%s, NOW(), %s, %s, %s)""",
            (started_at, status, json.dumps(steps or []), log_text),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass  # Don't fail pipeline if DB logging fails


def run_step(step, logger, python_exe, skip_flags):
    step_name = step["name"]
    skip_flag = step.get("skip_flag")

    if skip_flag and skip_flags.get(skip_flag, False):
        logger.info(f"SKIPPED: {step_name}")
        return True, "skipped"

    script_path = SCRIPT_DIR / step["script"]
    if not script_path.exists():
        logger.error(f"Script not found: {script_path}")
        return False, "not_found"

    cmd = [python_exe, str(script_path)]
    logger.info(f"STARTING: {step_name}")

    try:
        result = subprocess.run(cmd, cwd=str(PROJECT_DIR), capture_output=True, text=True, timeout=600)

        if result.stdout:
            for line in result.stdout.strip().split("\n"):
                if line:
                    logger.debug(f"  {line}")

        if result.returncode == 0:
            logger.info(f"COMPLETED: {step_name}")
            return True, "success"
        else:
            logger.error(f"FAILED: {step_name} (exit code {result.returncode})")
            if result.stderr:
                logger.error(f"  {result.stderr[:500]}")
            return False, "failed"
    except subprocess.TimeoutExpired:
        logger.error(f"TIMEOUT: {step_name}")
        return False, "timeout"
    except Exception as e:
        logger.error(f"EXCEPTION: {step_name}: {e}")
        return False, "exception"


def main():
    parser = argparse.ArgumentParser(description="Veeam/Wasabi Audit Pipeline")
    parser.add_argument("--skip-download", action="store_true", help="Skip download steps")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    logger = setup_logging(verbose=args.verbose)
    started_at = datetime.now()
    python_exe = sys.executable
    skip_flags = {"skip_download": args.skip_download}

    logger.info("=" * 60)
    logger.info("PIPELINE STARTED")
    logger.info("=" * 60)

    step_results = []
    success = True
    failed_step = None

    for step in PIPELINE_STEPS:
        ok, status = run_step(step, logger, python_exe, skip_flags)
        step_results.append({"name": step["name"], "status": status})
        if not ok:
            success = False
            failed_step = step["name"]
            break

    logger.info("=" * 60)
    if success:
        logger.info("PIPELINE COMPLETED SUCCESSFULLY")
    else:
        logger.error(f"PIPELINE FAILED at: {failed_step}")
    logger.info("=" * 60)

    record_pipeline_run(
        "completed" if success else "failed",
        started_at,
        steps=step_results,
    )

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
