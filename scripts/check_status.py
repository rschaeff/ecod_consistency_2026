#!/usr/bin/env python3
"""Check status of CLANS consistency analysis jobs.

Reports on completed, running, pending, and failed jobs.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent / "config"))
from config import PROJECT_ROOT


def load_manifest():
    """Load job manifest."""
    manifest_path = Path(PROJECT_ROOT) / "jobs" / "job_manifest.json"
    if not manifest_path.exists():
        return None
    with open(manifest_path) as f:
        return json.load(f)


def get_completed_jobs():
    """Find completed jobs and their info."""
    results_dir = Path(PROJECT_ROOT) / "results"
    completed = {}

    if not results_dir.exists():
        return completed

    for job_dir in results_dir.iterdir():
        if job_dir.is_dir():
            complete_marker = job_dir / "job_complete.json"
            if complete_marker.exists():
                try:
                    with open(complete_marker) as f:
                        info = json.load(f)
                        completed[info.get("job_id")] = info
                except:
                    pass

    return completed


def get_slurm_jobs():
    """Get running/pending SLURM jobs."""
    try:
        result = subprocess.run(
            ["squeue", "-u", os.environ.get("USER", ""), "-h",
             "-o", "%i %j %t %M %R"],
            capture_output=True, text=True
        )
        jobs = {"running": [], "pending": []}

        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 3:
                job_id, name, state = parts[0], parts[1], parts[2]
                if "clans" in name.lower():
                    if state == "R":
                        jobs["running"].append(job_id)
                    elif state in ("PD", "CF"):
                        jobs["pending"].append(job_id)

        return jobs
    except:
        return {"running": [], "pending": []}


def get_failed_jobs():
    """Find jobs that have log files but no completion marker."""
    logs_dir = Path(PROJECT_ROOT) / "logs"
    results_dir = Path(PROJECT_ROOT) / "results"
    failed = []

    if not logs_dir.exists():
        return failed

    # Find all error logs
    for err_log in logs_dir.glob("clans_*.err"):
        # Check if it has content (indicates error)
        if err_log.stat().st_size > 0:
            # Parse job ID from filename: clans_JOBID_ARRAYID.err
            parts = err_log.stem.split("_")
            if len(parts) >= 3:
                try:
                    array_id = int(parts[2])
                    failed.append({
                        "job_id": array_id,
                        "error_log": str(err_log)
                    })
                except:
                    pass

    return failed


def main():
    manifest = load_manifest()
    if not manifest:
        print("No job manifest found. Run generate_jobs.py first.")
        return

    total_jobs = len(manifest["jobs"])
    completed = get_completed_jobs()
    slurm_jobs = get_slurm_jobs()
    failed = get_failed_jobs()

    # Calculate statistics
    completed_ids = set(completed.keys())
    failed_ids = set(f["job_id"] for f in failed) - completed_ids

    print("=" * 50)
    print("ECOD F-group Consistency Analysis - Job Status")
    print("=" * 50)
    print(f"\nTotal jobs: {total_jobs}")
    print(f"Completed:  {len(completed_ids)} ({100*len(completed_ids)/total_jobs:.1f}%)")
    print(f"Running:    {len(slurm_jobs['running'])}")
    print(f"Pending:    {len(slurm_jobs['pending'])}")
    print(f"Failed:     {len(failed_ids)}")

    remaining = total_jobs - len(completed_ids)
    print(f"Remaining:  {remaining}")

    # Size distribution of completed jobs
    if completed:
        print("\n--- Completed Job Statistics ---")
        sizes = [completed[jid].get("domain_count", 0) for jid in completed_ids]
        print(f"Domain count range: {min(sizes)} - {max(sizes)}")
        print(f"Average domains: {sum(sizes)/len(sizes):.1f}")

    # Show failed jobs
    if failed_ids:
        print("\n--- Failed Jobs ---")
        for f in failed[:10]:  # Show first 10
            if f["job_id"] in failed_ids:
                print(f"  Job {f['job_id']}: {f['error_log']}")
        if len(failed_ids) > 10:
            print(f"  ... and {len(failed_ids) - 10} more")

    # Show running jobs
    if slurm_jobs['running']:
        print(f"\n--- Running Jobs ({len(slurm_jobs['running'])}) ---")
        print(f"  SLURM IDs: {', '.join(slurm_jobs['running'][:10])}")
        if len(slurm_jobs['running']) > 10:
            print(f"  ... and {len(slurm_jobs['running']) - 10} more")

    print("\n" + "=" * 50)


if __name__ == "__main__":
    main()
