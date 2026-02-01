#!/usr/bin/env python3
"""
Batch deprecation script for A2 F-groups WITHOUT good_domain replacement candidates.

This script handles F-groups where:
- Only 1 representative domain exists in ecod_rep.domain (simple_topology)
- Multiple domains are assigned in ecod_commons.f_group_assignments
- NO good_domain replacement candidate exists

Actions performed:
1. Delete the simple_topology domain from ecod_rep.domain (with audit trail)
2. Deprecate the F-group in ecod_rep.cluster
3. Reassign ALL domains in ecod_commons.f_group_assignments to the .0 pseudo F-group

Usage:
    python batch_deprecate_a2_no_replacement.py --dry-run     # Preview changes
    python batch_deprecate_a2_no_replacement.py --execute     # Execute deprecations
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

JUSTIFICATION_TEMPLATE = """Simple topology domains should not serve as provisional manual representatives.
No good_domain replacement candidate available.

Domain: {domain_id}
Classification: simple_topology
Source: {source}
Pfam: {pfam_acc}
H-group: {h_group}

Assigned domains in ecod_commons: {assigned_count}
Good domain candidates found: 0

Actions taken:
- Domain deleted from ecod_rep.domain
- F-group deprecated in ecod_rep.cluster
- {assigned_count} domain(s) reassigned to {pseudo_fgroup} in ecod_commons

Reference: DEFICIENCY_REPORT_605.1.md
Batch: simple_topology_deaccession_a2_no_replacement_{date}"""

REQUESTED_BY = 'consistency_pipeline'


def get_db_connection():
    """Create database connection."""
    return psycopg2.connect(**DB_CONFIG)


def load_a2_no_replacement(analysis_file: Path) -> list:
    """Load A2 F-groups that need MANUAL_REVIEW (no replacement) from analysis results."""
    fgroups = []
    with open(analysis_file, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            if row['action'] == 'MANUAL_REVIEW':
                fgroups.append({
                    'f_id': row['f_id'],
                    'h_group': row['h_group'],
                    'prov_rep_domain': row['current_rep'],
                    'pfam_acc': row['pfam_acc'],
                    'assigned_count': int(row['assigned_count']),
                    'source': 'simple_topology'  # All are simple_topology
                })
    return fgroups


def get_pseudo_fgroup(f_id: str) -> str:
    """Get the .0 pseudo F-group for a given F-group ID.

    Example: 605.1.1.113 -> 605.1.1.0
    """
    parts = f_id.split('.')
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.{parts[2]}.0"
    return None


def verify_fgroup_state(conn, f_id: str) -> dict:
    """Verify F-group exists and is not already deprecated."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT id::text as f_id, name, is_deprecated, parent::text as t_id
            FROM ecod_rep.cluster
            WHERE id::text = %s AND type = 'F'
        """, (f_id,))
        return cur.fetchone()


def get_domain_uid(conn, ecod_domain_id: str) -> dict:
    """Get domain details from ecod_rep.domain."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT uid, ecod_domain_id, f_id::text, t_id::text,
                   provisional_manual_rep, manual_rep, ecod_uid
            FROM ecod_rep.domain
            WHERE ecod_domain_id = %s
        """, (ecod_domain_id,))
        return cur.fetchone()


def delete_domain_from_ecod_rep(conn, domain: dict, request_id: int) -> bool:
    """Delete a domain from ecod_rep.domain with audit trail."""
    with conn.cursor() as cur:
        # Log the deletion in domain_modification_log
        cur.execute("""
            INSERT INTO ecod_rep.domain_modification_log (
                domain_uid, modification_type, old_value, new_value,
                justification, requested_by, timestamp
            ) VALUES (
                %s, 'delete_domain', %s, 'DELETED',
                'Change request #' || %s || ' - Simple topology domain removed from ecod_rep (no replacement available)',
                %s, NOW()
            )
        """, (
            domain['uid'],
            f"ecod_domain_id={domain['ecod_domain_id']}, f_id={domain['f_id']}, "
            f"provisional_manual_rep={domain['provisional_manual_rep']}",
            request_id,
            REQUESTED_BY
        ))

        # Delete the domain
        cur.execute("""
            DELETE FROM ecod_rep.domain
            WHERE uid = %s
        """, (domain['uid'],))

        return cur.rowcount == 1


def create_deprecation_request(conn, f_id: str, justification: str) -> int:
    """Create a hierarchy change request for F-group deprecation."""
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO ecod_rep.hierarchy_change_request (
                request_type, group_type, original_id, justification,
                requested_by, status, requested_at
            ) VALUES (
                'deprecate', 'F', %s, %s, %s, 'pending', NOW()
            )
            RETURNING id
        """, (f_id, justification, REQUESTED_BY))
        return cur.fetchone()[0]


def approve_request(conn, request_id: int) -> bool:
    """Approve a pending hierarchy change request."""
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE ecod_rep.hierarchy_change_request
            SET status = 'approved',
                reviewed_by = %s,
                reviewed_at = NOW()
            WHERE id = %s AND status = 'pending'
            RETURNING id
        """, (REQUESTED_BY, request_id))
        return cur.fetchone() is not None


def implement_deprecation(conn, request_id: int) -> bool:
    """Implement F-group deprecation using the standard function."""
    with conn.cursor() as cur:
        try:
            cur.execute("""
                SELECT ecod_rep.implement_deprecate_group(%s)
            """, (request_id,))
            result = cur.fetchone()[0]

            # Update request status
            cur.execute("""
                UPDATE ecod_rep.hierarchy_change_request
                SET status = 'implemented',
                    implementation_date = NOW()
                WHERE id = %s
            """, (request_id,))

            return result
        except Exception as e:
            # Mark as failed
            cur.execute("""
                UPDATE ecod_rep.hierarchy_change_request
                SET status = 'failed',
                    notes = %s
                WHERE id = %s
            """, (str(e), request_id))
            raise


def reassign_to_pseudo_fgroup(conn, f_id: str, pseudo_fgroup: str) -> int:
    """Reassign all domains from f_id to pseudo F-group in ecod_commons."""
    with conn.cursor() as cur:
        # Update f_group_assignments
        # Use 'manual' as assignment_method (valid per check constraint)
        cur.execute("""
            UPDATE ecod_commons.f_group_assignments
            SET f_group_id = %s,
                assignment_method = 'manual',
                notes = COALESCE(notes, '') ||
                        E'\nReassigned from ' || %s || ' (deprecated simple_topology F-group, no replacement) on ' ||
                        NOW()::text
            WHERE f_group_id = %s
        """, (pseudo_fgroup, f_id, f_id))

        return cur.rowcount


def deprecate_fgroup(conn, fgroup: dict, dry_run: bool = True) -> dict:
    """
    Deprecate a single F-group with full audit trail.

    Actions:
    1. Delete domain from ecod_rep.domain
    2. Deprecate F-group in ecod_rep.cluster
    3. Reassign ALL domains in ecod_commons to .0 pseudo F-group

    Returns dict with status and details.
    """
    f_id = fgroup['f_id']
    pseudo_fgroup = get_pseudo_fgroup(f_id)

    result = {
        'f_id': f_id,
        'domain': fgroup['prov_rep_domain'],
        'pseudo_fgroup': pseudo_fgroup,
        'assigned_count': fgroup['assigned_count'],
        'status': None,
        'request_id': None,
        'domains_reassigned': 0,
        'error': None
    }

    # Verify current state
    cluster = verify_fgroup_state(conn, f_id)
    if not cluster:
        result['status'] = 'SKIPPED'
        result['error'] = 'F-group not found in ecod_rep.cluster'
        return result

    if cluster['is_deprecated']:
        result['status'] = 'SKIPPED'
        result['error'] = 'F-group already deprecated'
        return result

    # Get domain details
    domain = get_domain_uid(conn, fgroup['prov_rep_domain'])
    if not domain:
        result['status'] = 'SKIPPED'
        result['error'] = f"Domain {fgroup['prov_rep_domain']} not found in ecod_rep.domain"
        return result

    if dry_run:
        result['status'] = 'DRY_RUN'
        result['error'] = (
            f"Would: 1) Delete domain {fgroup['prov_rep_domain']} from ecod_rep, "
            f"2) Deprecate {f_id}, "
            f"3) Reassign {fgroup['assigned_count']} domains to {pseudo_fgroup}"
        )
        return result

    # Build justification
    justification = JUSTIFICATION_TEMPLATE.format(
        domain_id=fgroup['prov_rep_domain'],
        source=fgroup['source'],
        pfam_acc=fgroup['pfam_acc'],
        h_group=fgroup['h_group'],
        assigned_count=fgroup['assigned_count'],
        pseudo_fgroup=pseudo_fgroup,
        date=datetime.now().strftime('%Y%m%d')
    )

    try:
        # Step 1: Create change request
        request_id = create_deprecation_request(conn, f_id, justification)
        result['request_id'] = request_id

        # Step 2: Approve request
        if not approve_request(conn, request_id):
            raise Exception("Failed to approve request")

        # Step 3: Delete domain from ecod_rep.domain (before deprecating F-group)
        if not delete_domain_from_ecod_rep(conn, domain, request_id):
            raise Exception(f"Failed to delete domain {domain['ecod_domain_id']}")

        # Step 4: Deprecate F-group
        if not implement_deprecation(conn, request_id):
            raise Exception("implement_deprecate_group returned False")

        # Step 5: Reassign ALL domains in ecod_commons to .0 pseudo F-group
        reassigned_count = reassign_to_pseudo_fgroup(conn, f_id, pseudo_fgroup)
        result['domains_reassigned'] = reassigned_count

        result['status'] = 'SUCCESS'

    except Exception as e:
        result['status'] = 'FAILED'
        result['error'] = str(e)
        conn.rollback()

    return result


def run_batch_deprecation(
    analysis_file: Path,
    dry_run: bool = True,
    batch_size: int = 50,
    output_file: Path = None
):
    """
    Run batch deprecation of A2 F-groups without replacement candidates.
    """
    # Load F-groups to deprecate
    fgroups = load_a2_no_replacement(analysis_file)
    print(f"Loaded {len(fgroups)} A2 F-groups (no replacement) for deprecation")

    # Calculate total domains that will be reassigned
    total_assigned = sum(fg['assigned_count'] for fg in fgroups)
    print(f"Total domains to be reassigned to .0: {total_assigned}")

    if dry_run:
        print("\n=== DRY RUN MODE - No changes will be made ===\n")
    else:
        print(f"\n=== EXECUTE MODE - Processing in batches of {batch_size} ===\n")

    results = []
    success_count = 0
    skip_count = 0
    fail_count = 0
    total_reassigned = 0

    conn = get_db_connection()

    try:
        for i, fgroup in enumerate(fgroups, 1):
            result = deprecate_fgroup(conn, fgroup, dry_run)
            results.append(result)

            if result['status'] == 'SUCCESS':
                success_count += 1
                total_reassigned += result['domains_reassigned']
                conn.commit()
            elif result['status'] == 'SKIPPED' or result['status'] == 'DRY_RUN':
                skip_count += 1
            else:
                fail_count += 1

            # Progress update
            if i % 20 == 0:
                print(f"  Processed {i}/{len(fgroups)}...")

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
    print("DEPRECATION SUMMARY (A2 No Replacement)")
    print("=" * 60)
    print(f"Total F-groups:           {len(fgroups)}")
    print(f"Success:                  {success_count}")
    print(f"Skipped:                  {skip_count}")
    print(f"Failed:                   {fail_count}")
    print(f"Domains reassigned to .0: {total_reassigned}")
    print("=" * 60)

    # Write results to file
    if output_file:
        with open(output_file, 'w') as f:
            fieldnames = ['f_id', 'domain', 'pseudo_fgroup', 'assigned_count',
                          'status', 'request_id', 'domains_reassigned', 'error']
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t')
            writer.writeheader()
            writer.writerows(results)
        print(f"\nResults written to: {output_file}")

    # Print failures
    failures = [r for r in results if r['status'] == 'FAILED']
    if failures:
        print("\nFailed deprecations:")
        for f in failures:
            print(f"  {f['f_id']}: {f['error']}")

    return results


def main():
    parser = argparse.ArgumentParser(
        description='Batch deprecate A2 F-groups without good_domain replacement candidates'
    )
    parser.add_argument(
        '--dry-run', action='store_true', default=True,
        help='Preview changes without executing (default)'
    )
    parser.add_argument(
        '--execute', action='store_true',
        help='Execute deprecations (overrides --dry-run)'
    )
    parser.add_argument(
        '--batch-size', type=int, default=50,
        help='Number of deprecations per batch commit (default: 50)'
    )
    parser.add_argument(
        '--analysis-file', type=Path,
        default=Path('/home/rschaeff/work/ecod_consistency_2026/prov_rep_daccession/a2_replacement_analysis.tsv'),
        help='Path to A2 analysis results TSV'
    )
    parser.add_argument(
        '--output-file', type=Path,
        default=Path('/home/rschaeff/work/ecod_consistency_2026/prov_rep_daccession/deprecation_a2_no_replacement_results.tsv'),
        help='Path to output results TSV'
    )

    args = parser.parse_args()

    dry_run = not args.execute

    if not args.analysis_file.exists():
        print(f"Error: Analysis file not found: {args.analysis_file}")
        sys.exit(1)

    run_batch_deprecation(
        analysis_file=args.analysis_file,
        dry_run=dry_run,
        batch_size=args.batch_size,
        output_file=args.output_file
    )


if __name__ == '__main__':
    main()
