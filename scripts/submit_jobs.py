#!/usr/bin/env python3
"""Submit CLANS jobs to SLURM cluster.

This script reads the job manifest and submits array jobs to SLURM.
It supports batching for very large job counts and can resume from
partial completions.
"""

import os
import sys
import json
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "config"))
from config import PROJECT_ROOT, SLURM_CONFIG


def load_manifest():
    """Load job manifest."""
    manifest_path = Path(PROJECT_ROOT) / "jobs" / "job_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"Job manifest not found: {manifest_path}\n"
            "Run generate_jobs.py first."
        )
    with open(manifest_path) as f:
        return json.load(f)


def get_completed_jobs():
    """Find jobs that have actually completed successfully.

    A job is only considered complete if:
    1. It has a job_complete.json marker
    2. The .clans output file actually exists

    This handles the case where jobs ran but failed to produce output
    (e.g., due to BLAST race conditions).
    """
    results_dir = Path(PROJECT_ROOT) / "results"
    completed = set()

    if not results_dir.exists():
        return completed

    for job_dir in results_dir.iterdir():
        if job_dir.is_dir():
            complete_marker = job_dir / "job_complete.json"
            if complete_marker.exists():
                try:
                    with open(complete_marker) as f:
                        info = json.load(f)
                        job_id = info.get("job_id")
                        output_file = info.get("output_file")

                        # Only count as complete if .clans file exists
                        if output_file and Path(output_file).exists():
                            completed.add(job_id)
                except:
                    pass

    return completed


def generate_slurm_script(job_ids, batch_name=None):
    """Generate SLURM submission command."""
    script_path = Path(PROJECT_ROOT) / "scripts" / "run_clans_job.sh"

    if not job_ids:
        return None

    # Create array specification
    if len(job_ids) == 1:
        array_spec = str(job_ids[0])
    else:
        # Group consecutive IDs into ranges
        ranges = []
        start = job_ids[0]
        prev = job_ids[0]

        for jid in job_ids[1:]:
            if jid == prev + 1:
                prev = jid
            else:
                if start == prev:
                    ranges.append(str(start))
                else:
                    ranges.append(f"{start}-{prev}")
                start = jid
                prev = jid

        # Add last range
        if start == prev:
            ranges.append(str(start))
        else:
            ranges.append(f"{start}-{prev}")

        array_spec = ",".join(ranges)

    # Build sbatch command
    cmd = [
        "sbatch",
        f"--array={array_spec}",
        f"--partition={SLURM_CONFIG['partition']}",
        f"--time={SLURM_CONFIG['time']}",
        f"--mem={SLURM_CONFIG['mem']}",
        f"--cpus-per-task={SLURM_CONFIG['cpus_per_task']}",
    ]

    if batch_name:
        cmd.append(f"--job-name=clans_{batch_name}")

    cmd.append(str(script_path))

    return cmd


def submit_batch(cmd, dry_run=False):
    """Submit job to SLURM."""
    if dry_run:
        print(f"  Would run: {' '.join(cmd)}")
        return None

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"  Error submitting job: {result.stderr}")
        return None

    # Parse job ID from output
    # Format: "Submitted batch job 12345"
    output = result.stdout.strip()
    if "Submitted batch job" in output:
        job_id = output.split()[-1]
        return job_id

    return output


def main():
    parser = argparse.ArgumentParser(
        description="Submit CLANS jobs to SLURM"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print commands without submitting"
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Skip already completed jobs"
    )
    parser.add_argument(
        "--batch-size", type=int, default=500,
        help="Max jobs per array submission (default: 500)"
    )
    parser.add_argument(
        "--job-range", type=str, default=None,
        help="Specific job range to submit (e.g., '1-100' or '50')"
    )
    parser.add_argument(
        "--h-groups", type=str, nargs="+", default=None,
        help="Specific H-groups to submit"
    )
    args = parser.parse_args()

    # Change to project directory
    os.chdir(PROJECT_ROOT)

    print("Loading job manifest...")
    manifest = load_manifest()
    all_jobs = manifest["jobs"]
    print(f"Total jobs in manifest: {len(all_jobs)}")

    # Filter by job range if specified
    if args.job_range:
        if "-" in args.job_range:
            start, end = map(int, args.job_range.split("-"))
            all_jobs = [j for j in all_jobs if start <= j["job_id"] <= end]
        else:
            job_id = int(args.job_range)
            all_jobs = [j for j in all_jobs if j["job_id"] == job_id]
        print(f"Filtered to {len(all_jobs)} jobs by range")

    # Filter by H-groups if specified
    if args.h_groups:
        all_jobs = [j for j in all_jobs if j["h_group_id"] in args.h_groups]
        print(f"Filtered to {len(all_jobs)} jobs by H-group")

    # Check for completed jobs
    job_ids = [j["job_id"] for j in all_jobs]

    if args.resume:
        completed = get_completed_jobs()
        if completed:
            print(f"Found {len(completed)} completed jobs")
            job_ids = [jid for jid in job_ids if jid not in completed]
            print(f"Jobs remaining: {len(job_ids)}")

    if not job_ids:
        print("No jobs to submit!")
        return

    # Sort job IDs for optimal array specification
    job_ids = sorted(job_ids)

    # Submit in batches
    batches = []
    for i in range(0, len(job_ids), args.batch_size):
        batch = job_ids[i:i + args.batch_size]
        batches.append(batch)

    print(f"\nSubmitting {len(job_ids)} jobs in {len(batches)} batch(es)...")

    submitted_jobs = []
    for i, batch in enumerate(batches):
        batch_name = f"batch{i+1}" if len(batches) > 1 else "all"
        cmd = generate_slurm_script(batch, batch_name)

        if cmd:
            print(f"\nBatch {i+1}: {len(batch)} jobs (IDs {batch[0]}-{batch[-1]})")
            slurm_id = submit_batch(cmd, args.dry_run)
            if slurm_id:
                print(f"  Submitted as SLURM job {slurm_id}")
                submitted_jobs.append({
                    "slurm_job_id": slurm_id,
                    "job_ids": batch,
                    "submitted_at": datetime.now().isoformat()
                })

    # Save submission record
    if submitted_jobs and not args.dry_run:
        record_path = Path(PROJECT_ROOT) / "jobs" / "submission_record.json"
        existing = []
        if record_path.exists():
            with open(record_path) as f:
                existing = json.load(f)

        existing.extend(submitted_jobs)
        with open(record_path, 'w') as f:
            json.dump(existing, f, indent=2)

        print(f"\nSubmission record saved to: {record_path}")

    print("\nDone!")
    if not args.dry_run:
        print("Monitor with: squeue -u $USER")
        print(f"Logs in: {PROJECT_ROOT}/logs/")


if __name__ == "__main__":
    main()
