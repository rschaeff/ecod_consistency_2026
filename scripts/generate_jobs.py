#!/usr/bin/env python3
"""Generate CLANS jobs for ECOD F-group consistency analysis.

This script:
1. Identifies H-groups with >=2 F-groups
2. Extracts F70 cluster representatives for each F-group
3. Generates FASTA files with F-group labels
4. Creates job manifest for SLURM submission
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor

# Add config to path
sys.path.insert(0, str(Path(__file__).parent.parent / "config"))
from config import (
    DB_CONFIG, ECOD_VERSION_ID, CLUSTER_PARAM_SET,
    MAX_DOMAINS_PER_JOB, MIN_DOMAINS_PER_FGROUP, PROJECT_ROOT
)


def get_db_connection():
    """Create database connection."""
    return psycopg2.connect(**DB_CONFIG)


def get_hgroups_with_multiple_fgroups(conn, version_id):
    """Get H-groups that have 2+ F-groups.

    Uses indexed f_group_assignments table only for speed.
    """
    query = """
        SELECT
            h_group_id,
            x_group_id,
            COUNT(DISTINCT f_group_id) as f_group_count,
            array_agg(DISTINCT f_group_id) as f_groups
        FROM ecod_commons.f_group_assignments
        WHERE version_id = %s
        GROUP BY h_group_id, x_group_id
        HAVING COUNT(DISTINCT f_group_id) >= 2
        ORDER BY h_group_id
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, (version_id,))
        return cur.fetchall()


def get_fgroup_representatives(conn, f_groups, version_id):
    """Get F70 cluster representatives for specified F-groups.

    Args:
        conn: Database connection
        f_groups: List of F-group IDs
        version_id: ECOD version ID
    """
    if not f_groups:
        return []

    query = """
        SELECT
            cr.f_group_id,
            fa.t_group_id,
            cr.representative_domain_id as domain_id,
            cr.representative_ecod_uid as ecod_uid,
            d.domain_id as domain_name,
            ds.sequence
        FROM ecod_commons.cluster_representatives cr
        JOIN ecod_commons.domains d
            ON cr.representative_domain_id = d.id
        JOIN ecod_commons.domain_sequences ds
            ON d.id = ds.domain_id
        JOIN (
            SELECT DISTINCT f_group_id, t_group_id
            FROM ecod_commons.f_group_assignments
            WHERE version_id = %s AND f_group_id = ANY(%s)
        ) fa ON cr.f_group_id = fa.f_group_id
        WHERE cr.parameter_set_name = %s
            AND cr.f_group_id = ANY(%s)
            AND d.is_obsolete = false
        ORDER BY cr.f_group_id, d.domain_id
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, (version_id, f_groups, CLUSTER_PARAM_SET, f_groups))
        return cur.fetchall()


def subsample_representatives(reps, max_domains):
    """Subsample representatives if H-group is too large.

    Strategy: proportionally sample from each F-group to maintain
    relative sizes while staying under max_domains.
    """
    if len(reps) <= max_domains:
        return reps

    # Group by F-group
    fgroup_reps = {}
    for rep in reps:
        fg = rep['f_group_id']
        if fg not in fgroup_reps:
            fgroup_reps[fg] = []
        fgroup_reps[fg].append(rep)

    # Calculate proportional sample sizes
    total = len(reps)
    sampled = []
    for fg, fg_reps in fgroup_reps.items():
        # At least MIN_DOMAINS_PER_FGROUP per F-group
        n_sample = max(
            MIN_DOMAINS_PER_FGROUP,
            int(len(fg_reps) * max_domains / total)
        )
        n_sample = min(n_sample, len(fg_reps))

        # Take evenly spaced samples
        step = len(fg_reps) / n_sample
        indices = [int(i * step) for i in range(n_sample)]
        sampled.extend([fg_reps[i] for i in indices])

    return sampled


def write_fasta(reps, output_path):
    """Write representatives to FASTA file with F-group labels in headers.

    Header format: >domain_name|ecod_uid|f_group_id|t_group_id
    """
    with open(output_path, 'w') as f:
        for rep in reps:
            header = f">{rep['domain_name']}|{rep['ecod_uid']}|{rep['f_group_id']}|{rep['t_group_id']}"
            f.write(f"{header}\n")
            # Wrap sequence at 80 characters
            seq = rep['sequence']
            for i in range(0, len(seq), 80):
                f.write(f"{seq[i:i+80]}\n")


def generate_job_manifest(jobs, output_path):
    """Write job manifest JSON for SLURM submission."""
    manifest = {
        "generated_at": datetime.now().isoformat(),
        "version_id": ECOD_VERSION_ID,
        "cluster_param_set": CLUSTER_PARAM_SET,
        "total_jobs": len(jobs),
        "jobs": jobs
    }
    with open(output_path, 'w') as f:
        json.dump(manifest, f, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Generate CLANS jobs for F-group consistency analysis"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print statistics without generating files"
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Limit number of jobs to generate (for testing)"
    )
    parser.add_argument(
        "--h-group", type=str, default=None,
        help="Generate job for specific H-group only"
    )
    args = parser.parse_args()

    fasta_dir = Path(PROJECT_ROOT) / "fasta"
    fasta_dir.mkdir(exist_ok=True)

    print(f"Connecting to database...")
    conn = get_db_connection()

    print(f"Finding H-groups with multiple F-groups...")
    hgroups = get_hgroups_with_multiple_fgroups(conn, ECOD_VERSION_ID)
    print(f"Found {len(hgroups)} H-groups with >=2 F-groups")

    if args.h_group:
        hgroups = [h for h in hgroups if h['h_group_id'] == args.h_group]
        if not hgroups:
            print(f"H-group {args.h_group} not found or has <2 F-groups")
            return

    if args.limit:
        hgroups = hgroups[:args.limit]

    if args.dry_run:
        print("\nDry run - statistics only:")
        print(f"  Total H-groups with >=2 F-groups: {len(hgroups)}")
        # Show F-group count distribution
        fg_counts = {}
        for h in hgroups:
            n = h['f_group_count']
            bucket = "2" if n == 2 else "3-5" if n <= 5 else "6-10" if n <= 10 else ">10"
            fg_counts[bucket] = fg_counts.get(bucket, 0) + 1
        print("  F-groups per H-group:")
        for bucket in ["2", "3-5", "6-10", ">10"]:
            if bucket in fg_counts:
                print(f"    {bucket}: {fg_counts[bucket]} H-groups")
        conn.close()
        return

    jobs = []
    total_domains = 0
    subsampled_count = 0

    print(f"\nGenerating FASTA files...")
    for i, hgroup in enumerate(hgroups):
        h_group_id = hgroup['h_group_id']
        x_group_id = hgroup['x_group_id']
        f_groups = hgroup['f_groups']

        # Get representatives for all F-groups in this H-group
        reps = get_fgroup_representatives(conn, f_groups, ECOD_VERSION_ID)

        if not reps:
            print(f"  Warning: No representatives found for {h_group_id}")
            continue

        original_count = len(reps)

        # Subsample if too large
        if len(reps) > MAX_DOMAINS_PER_JOB:
            reps = subsample_representatives(reps, MAX_DOMAINS_PER_JOB)
            subsampled_count += 1

        # Count unique F-groups
        fgroups = set(r['f_group_id'] for r in reps)

        # Generate safe filename
        safe_hgroup = h_group_id.replace('.', '_')
        fasta_path = fasta_dir / f"{safe_hgroup}.fasta"

        write_fasta(reps, fasta_path)

        job_info = {
            "job_id": i + 1,
            "h_group_id": h_group_id,
            "x_group_id": x_group_id,
            "f_group_count": len(fgroups),
            "domain_count": len(reps),
            "original_count": original_count,
            "subsampled": len(reps) < original_count,
            "fasta_file": str(fasta_path),
            "f_groups": sorted(list(fgroups))
        }
        jobs.append(job_info)
        total_domains += len(reps)

        if (i + 1) % 100 == 0:
            print(f"  Processed {i + 1}/{len(hgroups)} H-groups...")

    conn.close()

    # Write manifest
    manifest_path = Path(PROJECT_ROOT) / "jobs" / "job_manifest.json"
    generate_job_manifest(jobs, manifest_path)

    print(f"\nGeneration complete:")
    print(f"  Total jobs: {len(jobs)}")
    print(f"  Total domains: {total_domains:,}")
    print(f"  Subsampled jobs: {subsampled_count}")
    print(f"  Manifest: {manifest_path}")
    print(f"  FASTA files: {fasta_dir}")


if __name__ == "__main__":
    main()
