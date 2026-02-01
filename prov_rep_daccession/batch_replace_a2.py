#!/usr/bin/env python3
"""
Batch replacement script for A2 F-groups WITH good_domain replacement candidates.

This script handles F-groups where:
- Only 1 representative domain exists in ecod_rep.domain (simple_topology)
- Multiple domains are assigned in ecod_commons.f_group_assignments
- A good_domain replacement candidate EXISTS

Actions performed:
1. Add the good_domain replacement to ecod_rep.domain (if not present)
2. Promote the good_domain as provisional_manual_rep
3. Delete the old simple_topology domain from ecod_rep.domain

Note: ecod_commons.f_group_assignments are NOT changed - the F-group remains active
with a new representative.

Usage:
    python batch_replace_a2.py --dry-run           # Preview changes
    python batch_replace_a2.py --execute           # Execute replacements
"""

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor

# Database connection parameters
DB_CONFIG = {
    'host': 'dione',
    'port': 45000,
    'database': 'ecod_protein',
    'user': 'ecod'
}

JUSTIFICATION_TEMPLATE = """Replace simple_topology provisional representative with good_domain candidate.

Old representative (DELETED from ecod_rep):
  Domain: {old_rep}
  Classification: simple_topology

New representative:
  Domain: {new_rep}
  Classification: good_domain
  Source: {new_source}
  Length: {new_length} aa
  HH probability: {hh_prob}
  DPAM probability: {dpam_prob}

F-group: {f_id}
Pfam: {pfam_acc}
Assigned domains in ecod_commons: {assigned_count} (unchanged)

Reference: DEFICIENCY_REPORT_605.1.md
Batch: simple_topology_replacement_{date}"""

REQUESTED_BY = 'consistency_pipeline'


def get_db_connection():
    """Create database connection."""
    return psycopg2.connect(**DB_CONFIG)


def load_a2_replacements(analysis_file: Path) -> list:
    """Load A2 F-groups with REPLACE_REP action from analysis results."""
    replacements = []
    with open(analysis_file, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            if row['action'] == 'REPLACE_REP' and row['best_candidate']:
                replacements.append({
                    'f_id': row['f_id'],
                    'h_group': row['h_group'],
                    'current_rep': row['current_rep'],
                    'pfam_acc': row['pfam_acc'],
                    'assigned_count': int(row['assigned_count']),
                    'new_rep': row['best_candidate'],
                    'new_source': row['best_source'],
                    'new_length': row['best_length'],
                    'hh_prob': row['best_hh_prob'],
                    'dpam_prob': row['best_dpam_prob']
                })
    return replacements


def get_domain_from_ecod_rep(conn, ecod_domain_id: str) -> dict:
    """Get domain details from ecod_rep.domain."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT uid, ecod_domain_id, f_id::text, t_id::text,
                   provisional_manual_rep, manual_rep, ecod_uid
            FROM ecod_rep.domain
            WHERE ecod_domain_id = %s
        """, (ecod_domain_id,))
        return cur.fetchone()


def get_domain_from_ecod_commons(conn, ecod_domain_id: str) -> dict:
    """Get domain details from ecod_commons.domains."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT id, ecod_uid, domain_id, range_definition, sequence_length
            FROM ecod_commons.domains
            WHERE domain_id = %s
        """, (ecod_domain_id,))
        return cur.fetchone()


def verify_fgroup_state(conn, f_id: str) -> dict:
    """Verify F-group exists and is not deprecated."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT id::text as f_id, name, is_deprecated, parent::text as t_id
            FROM ecod_rep.cluster
            WHERE id::text = %s AND type = 'F'
        """, (f_id,))
        return cur.fetchone()


def generate_batch_id() -> str:
    """Generate a unique batch ID for tracking related changes."""
    return f"simple_topology_replacement_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def add_domain_to_ecod_rep(conn, ecod_domain_id: str, f_id: str, justification: str) -> int:
    """
    Add a domain to ecod_rep.domain from ecod_commons.
    Returns the new domain UID.
    """
    # Look up domain in ecod_commons
    commons_domain = get_domain_from_ecod_commons(conn, ecod_domain_id)
    if not commons_domain:
        raise ValueError(f"Domain {ecod_domain_id} not found in ecod_commons.domains")

    # Get T-group from F-group
    t_id = '.'.join(f_id.split('.')[:3])

    with conn.cursor() as cur:
        # Insert into ecod_rep.domain
        cur.execute("""
            INSERT INTO ecod_rep.domain (
                ecod_uid, ecod_domain_id, f_id, t_id,
                manual_rep, provisional_manual_rep,
                seqid_range, pdb_range
            ) VALUES (
                %s, %s, %s, %s,
                FALSE, TRUE,
                %s, %s
            )
            RETURNING uid
        """, (
            commons_domain['ecod_uid'],
            ecod_domain_id,
            f_id,
            t_id,
            commons_domain['range_definition'],
            commons_domain['range_definition']
        ))
        new_uid = cur.fetchone()[0]

        # Log the addition
        cur.execute("""
            INSERT INTO ecod_rep.domain_modification_log (
                domain_uid, modification_type, old_value, new_value,
                justification, requested_by, timestamp
            ) VALUES (
                %s, 'add_domain_as_provisional_rep', 'N/A',
                'Added from ecod_commons as replacement provisional_manual_rep',
                %s, %s, NOW()
            )
        """, (new_uid, justification, REQUESTED_BY))

        return new_uid


def promote_provisional_rep(conn, domain_uid: int, justification: str) -> bool:
    """Promote a domain to provisional representative."""
    with conn.cursor() as cur:
        # Get old value
        cur.execute("SELECT provisional_manual_rep FROM ecod_rep.domain WHERE uid = %s", (domain_uid,))
        old_value = cur.fetchone()[0]

        # Update domain
        cur.execute("""
            UPDATE ecod_rep.domain
            SET provisional_manual_rep = TRUE
            WHERE uid = %s
        """, (domain_uid,))

        # Log modification
        cur.execute("""
            INSERT INTO ecod_rep.domain_modification_log (
                domain_uid, modification_type, old_value, new_value,
                justification, requested_by, timestamp
            ) VALUES (
                %s, 'promote_provisional_rep', %s, 'TRUE',
                %s, %s, NOW()
            )
        """, (domain_uid, str(old_value), justification, REQUESTED_BY))

        return True


def delete_domain_from_ecod_rep(conn, domain: dict, justification: str) -> bool:
    """Delete a domain from ecod_rep.domain with audit trail."""
    with conn.cursor() as cur:
        # Log the deletion
        cur.execute("""
            INSERT INTO ecod_rep.domain_modification_log (
                domain_uid, modification_type, old_value, new_value,
                justification, requested_by, timestamp
            ) VALUES (
                %s, 'delete_domain', %s, 'DELETED',
                %s, %s, NOW()
            )
        """, (
            domain['uid'],
            f"ecod_domain_id={domain['ecod_domain_id']}, f_id={domain['f_id']}, "
            f"provisional_manual_rep={domain['provisional_manual_rep']}",
            justification,
            REQUESTED_BY
        ))

        # Delete the domain
        cur.execute("""
            DELETE FROM ecod_rep.domain
            WHERE uid = %s
        """, (domain['uid'],))

        return cur.rowcount == 1


def replace_provisional_rep(conn, replacement: dict, dry_run: bool = True) -> dict:
    """
    Replace the provisional representative for an F-group.

    Actions:
    1. Add new good_domain rep to ecod_rep (if not present) and promote
    2. Delete old simple_topology rep from ecod_rep

    Returns dict with status and details.
    """
    f_id = replacement['f_id']
    result = {
        'f_id': f_id,
        'old_rep': replacement['current_rep'],
        'new_rep': replacement['new_rep'],
        'status': None,
        'request_id': None,
        'error': None
    }

    # Verify F-group state
    cluster = verify_fgroup_state(conn, f_id)
    if not cluster:
        result['status'] = 'SKIPPED'
        result['error'] = 'F-group not found in ecod_rep.cluster'
        return result

    if cluster['is_deprecated']:
        result['status'] = 'SKIPPED'
        result['error'] = 'F-group already deprecated'
        return result

    # Check current representative exists
    old_domain = get_domain_from_ecod_rep(conn, replacement['current_rep'])
    if not old_domain:
        result['status'] = 'SKIPPED'
        result['error'] = f"Current rep {replacement['current_rep']} not found in ecod_rep"
        return result

    if not old_domain['provisional_manual_rep']:
        result['status'] = 'SKIPPED'
        result['error'] = f"Current rep {replacement['current_rep']} is not provisional_manual_rep"
        return result

    if dry_run:
        result['status'] = 'DRY_RUN'
        result['error'] = (
            f"Would: 1) Add/promote {replacement['new_rep']} as new rep, "
            f"2) Delete {replacement['current_rep']} from ecod_rep"
        )
        return result

    # Build justification
    justification = JUSTIFICATION_TEMPLATE.format(
        old_rep=replacement['current_rep'],
        new_rep=replacement['new_rep'],
        new_source=replacement['new_source'],
        new_length=replacement['new_length'] or 'N/A',
        hh_prob=replacement['hh_prob'] or 'N/A',
        dpam_prob=replacement['dpam_prob'] or 'N/A',
        f_id=f_id,
        pfam_acc=replacement['pfam_acc'],
        assigned_count=replacement['assigned_count'],
        date=datetime.now().strftime('%Y%m%d')
    )

    try:
        # Check if new representative already exists in ecod_rep
        new_domain = get_domain_from_ecod_rep(conn, replacement['new_rep'])

        if new_domain:
            # Domain already exists - just promote it
            promote_provisional_rep(conn, new_domain['uid'], justification)
        else:
            # Need to add domain to ecod_rep first (sets provisional_manual_rep=TRUE)
            add_domain_to_ecod_rep(conn, replacement['new_rep'], f_id, justification)

        # Delete old simple_topology domain from ecod_rep
        if not delete_domain_from_ecod_rep(conn, old_domain, justification):
            raise Exception(f"Failed to delete old domain {old_domain['ecod_domain_id']}")

        result['status'] = 'SUCCESS'

    except Exception as e:
        result['status'] = 'FAILED'
        result['error'] = str(e)
        conn.rollback()

    return result


def run_batch_replacement(
    analysis_file: Path,
    dry_run: bool = True,
    batch_size: int = 50,
    output_file: Path = None
):
    """
    Run batch replacement of A2 provisional representatives.
    """
    # Load replacements
    replacements = load_a2_replacements(analysis_file)
    print(f"Loaded {len(replacements)} A2 F-groups with replacement candidates")

    if dry_run:
        print("\n=== DRY RUN MODE - No changes will be made ===\n")
    else:
        print(f"\n=== EXECUTE MODE - Processing in batches of {batch_size} ===\n")

    results = []
    success_count = 0
    skip_count = 0
    fail_count = 0

    conn = get_db_connection()

    try:
        for i, replacement in enumerate(replacements, 1):
            result = replace_provisional_rep(conn, replacement, dry_run)
            results.append(result)

            if result['status'] == 'SUCCESS':
                success_count += 1
                conn.commit()
            elif result['status'] == 'SKIPPED' or result['status'] == 'DRY_RUN':
                skip_count += 1
            else:
                fail_count += 1

            # Progress update
            if i % 20 == 0:
                print(f"  Processed {i}/{len(replacements)}...")

            # Batch commit point
            if not dry_run and i % batch_size == 0:
                print(f"  Batch checkpoint at {i}")

        # Final commit
        if not dry_run:
            conn.commit()

    finally:
        conn.close()

    # Summary
    print("\n" + "=" * 60)
    print("REPLACEMENT SUMMARY")
    print("=" * 60)
    print(f"Total F-groups:  {len(replacements)}")
    print(f"Success:         {success_count}")
    print(f"Skipped:         {skip_count}")
    print(f"Failed:          {fail_count}")
    print("=" * 60)

    # Write results to file
    if output_file:
        with open(output_file, 'w') as f:
            writer = csv.DictWriter(
                f,
                fieldnames=['f_id', 'old_rep', 'new_rep', 'status', 'request_id', 'error'],
                delimiter='\t'
            )
            writer.writeheader()
            writer.writerows(results)
        print(f"\nResults written to: {output_file}")

    # Print failures
    failures = [r for r in results if r['status'] == 'FAILED']
    if failures:
        print("\nFailed replacements:")
        for f in failures:
            print(f"  {f['f_id']}: {f['error']}")

    return results


def main():
    parser = argparse.ArgumentParser(
        description='Batch replace A2 simple_topology provisional reps with good_domain candidates'
    )
    parser.add_argument(
        '--dry-run', action='store_true', default=True,
        help='Preview changes without executing (default)'
    )
    parser.add_argument(
        '--execute', action='store_true',
        help='Execute replacements (overrides --dry-run)'
    )
    parser.add_argument(
        '--batch-size', type=int, default=50,
        help='Number of replacements per batch commit (default: 50)'
    )
    parser.add_argument(
        '--analysis-file', type=Path,
        default=Path('/home/rschaeff/work/ecod_consistency_2026/prov_rep_daccession/a2_replacement_analysis.tsv'),
        help='Path to A2 analysis results TSV'
    )
    parser.add_argument(
        '--output-file', type=Path,
        default=Path('/home/rschaeff/work/ecod_consistency_2026/prov_rep_daccession/replacement_results.tsv'),
        help='Path to output results TSV'
    )

    args = parser.parse_args()

    dry_run = not args.execute

    if not args.analysis_file.exists():
        print(f"Error: Analysis file not found: {args.analysis_file}")
        sys.exit(1)

    run_batch_replacement(
        analysis_file=args.analysis_file,
        dry_run=dry_run,
        batch_size=args.batch_size,
        output_file=args.output_file
    )


if __name__ == '__main__':
    main()
