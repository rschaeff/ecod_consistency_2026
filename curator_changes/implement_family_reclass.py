#!/usr/bin/env python3
"""
Implement family-level reclassification changes (2A, 2B).

Moves domains from one F-group to another existing F-group. Source F-groups
are deprecated if emptied.

Algorithm:
  1. Verify source and target F-groups exist
  2. Move rep domains in ecod_rep (implement_reassign_f_group)
  3. Move all domains in ecod_commons (UPDATE f_group_assignments)
  4. Deprecate source F-group if empty

Usage:
    python implement_family_reclass.py --dry-run
    python implement_family_reclass.py --execute
    python implement_family_reclass.py --execute --change 2A
"""

import argparse
import logging
import sys
from datetime import datetime

import curator_ops as ops
from change_definitions import FAMILY_RECLASSIFICATIONS, REQUESTED_BY

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
)
logger = logging.getLogger(__name__)


def plan_reclassification(conn, reclass_def):
    """Plan a family reclassification. Returns action dict or None."""
    change_id = reclass_def['id']
    source_f = reclass_def['source_f']
    target_f = reclass_def['target_f']

    print(f"\n--- Planning Change {change_id}: {reclass_def['description']} ---")
    print(f"  Source F-group: {source_f}")
    print(f"  Target F-group: {target_f}")

    # Verify preconditions
    ok, msg = ops.verify_change_preconditions(conn, source_f, target_f)
    if not ok:
        print(f"  ERROR: {msg}")
        return None

    source_cluster = ops.verify_fgroup_exists(conn, source_f)
    target_cluster = ops.verify_fgroup_exists(conn, target_f)

    # Count domains
    rep_domains = ops.get_rep_domains_in_fgroup(conn, source_f)
    commons_count = ops.count_fgroup_members(conn, source_f, 'ecod_commons')

    # Count target current state
    target_rep_count = ops.count_fgroup_members(conn, target_f, 'ecod_rep')
    target_commons_count = ops.count_fgroup_members(conn, target_f, 'ecod_commons')

    print(f"  Source {source_f} ({source_cluster['name']}): "
          f"{len(rep_domains)} reps, {commons_count} commons")
    print(f"  Target {target_f} ({target_cluster['name']}): "
          f"{target_rep_count} reps, {target_commons_count} commons")

    # Determine if source F-group will be fully emptied
    move_entire = reclass_def.get('move_entire_fgroup', True)

    return {
        'change_id': change_id,
        'reclass_def': reclass_def,
        'source_f': source_f,
        'target_f': target_f,
        'source_name': source_cluster['name'],
        'target_name': target_cluster['name'],
        'rep_domains': rep_domains,
        'commons_count': commons_count,
        'move_entire': move_entire,
    }


def execute_reclassification(conn, plan, dry_run=True):
    """Execute a single family reclassification."""
    change_id = plan['change_id']
    source_f = plan['source_f']
    target_f = plan['target_f']
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    results = {
        'change_id': change_id,
        'domains_reassigned_rep': 0,
        'domains_reassigned_commons': 0,
        'source_deprecated': False,
        'errors': [],
    }

    justification = (
        f"Curator change {change_id}: {plan['reclass_def']['description']}. "
        f"Reclassify {source_f} -> {target_f}. "
        f"Batch: {REQUESTED_BY}_{timestamp}"
    )

    try:
        # Step 1: Create a change request for tracking
        request_id = None
        if not dry_run:
            request_id = ops.create_change_request(
                conn, 'rename', 'F',
                original_id=source_f,
                new_id=target_f,
                new_name=f"Reclassify {source_f} -> {target_f}",
                justification=justification,
            )
            ops.approve_change_request(conn, request_id)

        # Step 2: Move rep domains in ecod_rep
        for domain in plan['rep_domains']:
            if dry_run:
                print(f"  [DRY RUN] Would reassign rep {domain['ecod_domain_id']} "
                      f"from {source_f} -> {target_f}")
            else:
                ops.reassign_domain_fgroup(
                    conn, domain['uid'], target_f, request_id,
                )
                results['domains_reassigned_rep'] += 1
                print(f"  Reassigned rep {domain['ecod_domain_id']} -> {target_f}")

        # Step 3: Move ALL domains in ecod_commons
        if dry_run:
            print(f"  [DRY RUN] Would reassign {plan['commons_count']} "
                  f"ecod_commons domains from {source_f} -> {target_f}")
        else:
            count = ops.reassign_commons_domains(
                conn, source_f, target_f, justification,
            )
            results['domains_reassigned_commons'] = count
            print(f"  Reassigned {count} ecod_commons domains -> {target_f}")

        # Step 4: Deprecate source F-group if empty
        if plan['move_entire']:
            if dry_run:
                print(f"  [DRY RUN] Would deprecate F-group {source_f}")
            else:
                remaining_rep = ops.count_fgroup_members(conn, source_f, 'ecod_rep')
                remaining_commons = ops.count_fgroup_members(conn, source_f, 'ecod_commons')
                if remaining_rep == 0 and remaining_commons == 0:
                    ops.deprecate_group(conn, source_f, 'F',
                                        justification=justification)
                    results['source_deprecated'] = True
                    print(f"  Deprecated F-group {source_f}")
                else:
                    print(f"  Source {source_f} not empty after move: "
                          f"reps={remaining_rep}, commons={remaining_commons}")

        # Commit
        if not dry_run:
            conn.commit()

    except Exception as e:
        msg = f"Error in change {change_id}: {e}"
        results['errors'].append(msg)
        logger.error(msg, exc_info=True)
        if not dry_run:
            conn.rollback()

    return results


def verify_reclassification(conn, reclass_def):
    """Verify a reclassification completed correctly."""
    change_id = reclass_def['id']
    source_f = reclass_def['source_f']
    target_f = reclass_def['target_f']

    print(f"\n--- Verification for Change {change_id} ---")

    source = ops.verify_fgroup_exists(conn, source_f)
    if source:
        status = "DEPRECATED" if source['is_deprecated'] else "ACTIVE"
        rep_count = ops.count_fgroup_members(conn, source_f, 'ecod_rep')
        commons_count = ops.count_fgroup_members(conn, source_f, 'ecod_commons')
        print(f"  Source {source_f}: {status}, reps={rep_count}, commons={commons_count}")

    target = ops.verify_fgroup_exists(conn, target_f)
    if target:
        rep_count = ops.count_fgroup_members(conn, target_f, 'ecod_rep')
        commons_count = ops.count_fgroup_members(conn, target_f, 'ecod_commons')
        print(f"  Target {target_f}: reps={rep_count}, commons={commons_count}")

    # Check for 2B: whether 310.1.1 still has 310.1.1.2
    if change_id.startswith('2B'):
        sibling = "310.1.1.2"
        sibling_cluster = ops.verify_fgroup_exists(conn, sibling)
        if sibling_cluster and not sibling_cluster['is_deprecated']:
            count = ops.count_fgroup_members(conn, sibling, 'ecod_commons')
            print(f"  Sibling {sibling} ({sibling_cluster['name']}): "
                  f"ACTIVE, commons={count}")


def main():
    parser = argparse.ArgumentParser(
        description='Implement family-level reclassification changes (2A, 2B)'
    )
    parser.add_argument('--dry-run', action='store_true', default=True,
                        help='Preview changes without executing (default)')
    parser.add_argument('--execute', action='store_true',
                        help='Execute changes (overrides --dry-run)')
    parser.add_argument('--change', type=str, default=None,
                        help='Execute only a specific change (e.g., 2A)')
    parser.add_argument('--verify-only', action='store_true',
                        help='Only run verification, no changes')

    args = parser.parse_args()
    dry_run = not args.execute

    reclass_list = FAMILY_RECLASSIFICATIONS
    if args.change:
        reclass_list = [r for r in reclass_list
                        if r['id'] == args.change or r['id'].startswith(args.change)]
        if not reclass_list:
            print(f"Error: Change '{args.change}' not found. "
                  f"Available: {[r['id'] for r in FAMILY_RECLASSIFICATIONS]}")
            sys.exit(1)

    conn = ops.get_db_connection()

    try:
        for reclass_def in reclass_list:
            if args.verify_only:
                verify_reclassification(conn, reclass_def)
                continue

            plan = plan_reclassification(conn, reclass_def)
            if plan is None:
                print(f"Skipping change {reclass_def['id']} due to planning errors")
                continue

            ops.print_change_summary(
                reclass_def['id'],
                reclass_def['description'],
                [f"{plan['source_f']} ({plan['source_name']}) -> "
                 f"{plan['target_f']} ({plan['target_name']})",
                 f"Rep domains: {len(plan['rep_domains'])}",
                 f"Commons domains: {plan['commons_count']}"],
                dry_run=dry_run,
            )

            results = execute_reclassification(conn, plan, dry_run)

            print(f"\n--- Results for Change {reclass_def['id']} ---")
            print(f"  Rep domains reassigned: {results['domains_reassigned_rep']}")
            print(f"  Commons domains reassigned: {results['domains_reassigned_commons']}")
            print(f"  Source deprecated: {results['source_deprecated']}")
            if results['errors']:
                print(f"  ERRORS: {results['errors']}")

            if not dry_run:
                verify_reclassification(conn, reclass_def)

    finally:
        conn.close()


if __name__ == '__main__':
    main()
