#!/usr/bin/env python3
"""
Implement X-group merge changes (1A, 1B, 1C).

Each merge dissolves a source X-group and moves its F-groups into a target
T-group. Source hierarchy (X/H/T) is deprecated after all domains are moved.

Algorithm per merge:
  1. For each source F-group, create a new target F-group (via assign_next_f_id)
  2. Move all rep domains in ecod_rep (implement_reassign_f_group)
  3. Move all domains in ecod_commons (UPDATE f_group_assignments)
  4. Deprecate emptied source F-groups
  5. Deprecate source T-group, H-group, X-group (bottom-up)

Usage:
    python implement_xgroup_merges.py --dry-run           # Preview changes
    python implement_xgroup_merges.py --execute           # Execute all merges
    python implement_xgroup_merges.py --execute --change 1C  # Execute one merge
"""

import argparse
import logging
import sys
from datetime import datetime

import curator_ops as ops
from change_definitions import XGROUP_MERGES, REQUESTED_BY

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
)
logger = logging.getLogger(__name__)


def get_pfam_index_for_tgroup(conn, t_id):
    """Build a lookup of pfam_acc -> f_id for all active F-groups in a T-group.

    Policy: no two active F-groups under the same T-group should share
    the same pfam_acc. This index is used to detect merge targets.
    """
    with conn.cursor(cursor_factory=__import__('psycopg2').extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT id::text AS f_id, pfam_acc, name
            FROM ecod_rep.cluster
            WHERE parent::text = %s AND type = 'F' AND is_deprecated = false
            ORDER BY id::text
        """, (t_id,))
        index = {}
        for row in cur.fetchall():
            if row['pfam_acc']:
                index[row['pfam_acc']] = row
        return index


def plan_merge(conn, merge_def):
    """Plan a single X-group merge. Returns action plan (list of dicts)."""
    change_id = merge_def['id']
    source_t = merge_def['source_t']
    target_t = merge_def['target_t']
    plan = []

    print(f"\n--- Planning Change {change_id}: {merge_def['description']} ---")
    print(f"  Source T-group: {source_t}")
    print(f"  Target T-group: {target_t}")

    # Verify target T-group exists
    target_t_cluster = ops.verify_cluster_exists(conn, target_t, 'T')
    if not target_t_cluster:
        print(f"  ERROR: Target T-group {target_t} not found!")
        return None
    if target_t_cluster['is_deprecated']:
        print(f"  ERROR: Target T-group {target_t} is deprecated!")
        return None

    # Build pfam_acc index for the target T-group to detect merge targets
    pfam_index = get_pfam_index_for_tgroup(conn, target_t)

    for fmap in merge_def['fgroup_mapping']:
        source_f = fmap['source_f']
        pfam_name = fmap['pfam']
        pfam_acc = fmap.get('pfam_acc')

        # Verify source F-group
        source_cluster = ops.verify_fgroup_exists(conn, source_f)
        if not source_cluster:
            print(f"  WARNING: Source F-group {source_f} not found, skipping")
            continue
        if source_cluster['is_deprecated']:
            print(f"  WARNING: Source F-group {source_f} already deprecated, skipping")
            continue

        # Use actual pfam_acc from DB if not specified in definition
        if not pfam_acc:
            pfam_acc = source_cluster.get('pfam_acc')

        # Count domains
        rep_domains = ops.get_rep_domains_in_fgroup(conn, source_f)
        commons_count = ops.count_fgroup_members(conn, source_f, 'ecod_commons')

        # Determine target F-group:
        # 1. If explicitly specified in mapping, use it (already validated)
        # 2. If pfam_acc matches an existing F-group in target T-group, MERGE
        # 3. Otherwise, create new
        target_f = fmap.get('target_f')
        merge_reason = None

        if target_f:
            # Explicit target specified - verify it exists
            target_cluster = ops.verify_fgroup_exists(conn, target_f)
            if not target_cluster or target_cluster['is_deprecated']:
                print(f"  WARNING: Specified target F-group {target_f} invalid, will auto-detect")
                target_f = None
            else:
                merge_reason = "explicit"

        if target_f is None and pfam_acc:
            # Auto-detect: check if target T-group already has this pfam_acc
            match = pfam_index.get(pfam_acc)
            if match:
                target_f = match['f_id']
                merge_reason = f"pfam_acc match ({pfam_acc})"
                print(f"  AUTO-MERGE: {source_f} ({pfam_acc}) -> {target_f} "
                      f"({match['name']}) [same pfam_acc]")

        action = {
            'source_f': source_f,
            'source_name': source_cluster['name'],
            'pfam_name': pfam_name,
            'pfam_acc': pfam_acc,
            'target_f': target_f,  # None means create new
            'merge_reason': merge_reason,
            'target_t': target_t,
            'rep_count': len(rep_domains),
            'rep_domains': rep_domains,
            'commons_count': commons_count,
        }
        plan.append(action)

        if target_f:
            print(f"  {source_f} ({pfam_name}): {len(rep_domains)} reps, "
                  f"{commons_count} total -> MERGE into {target_f} [{merge_reason}]")
        else:
            print(f"  {source_f} ({pfam_name}): {len(rep_domains)} reps, "
                  f"{commons_count} total -> CREATE NEW")

    # Plan deprecation of source hierarchy
    plan_deprecations = []
    for level, group_id in [
        ('F', None),  # handled per-fgroup above
        ('T', merge_def['source_t']),
        ('H', merge_def['source_h']),
        ('X', merge_def['source_x']),
    ]:
        if group_id:
            cluster = ops.verify_cluster_exists(conn, group_id, level)
            if cluster and not cluster['is_deprecated']:
                plan_deprecations.append((level, group_id))
                print(f"  Will deprecate {level}-group {group_id}")

    return {
        'change_id': change_id,
        'merge_def': merge_def,
        'fgroup_actions': plan,
        'deprecations': plan_deprecations,
    }


def execute_merge(conn, plan, dry_run=True):
    """Execute a single X-group merge."""
    change_id = plan['change_id']
    merge_def = plan['merge_def']
    target_t = merge_def['target_t']
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    results = {
        'change_id': change_id,
        'fgroups_created': [],
        'fgroups_merged_into': [],
        'domains_reassigned_rep': 0,
        'domains_reassigned_commons': 0,
        'fgroups_deprecated': [],
        'hierarchy_deprecated': [],
        'errors': [],
    }

    justification_base = (
        f"Curator change {change_id}: {merge_def['description']}. "
        f"Merge {merge_def['source_x']} -> {target_t}. "
        f"Batch: {REQUESTED_BY}_{timestamp}"
    )

    for action in plan['fgroup_actions']:
        source_f = action['source_f']
        target_f = action['target_f']

        try:
            # Step 1: Create target F-group if needed, or merge into existing
            if target_f is None:
                # No matching F-group in target T-group -> create new
                if dry_run:
                    print(f"  [DRY RUN] Would create new F-group under {target_t} "
                          f"for {action['pfam_name']} ({action['pfam_acc']})")
                    target_f = f"{target_t}.NEW"
                else:
                    target_f, req_id = ops.create_fgroup(
                        conn, target_t,
                        name=action['pfam_name'],
                        pfam_acc=action['pfam_acc'],
                        justification=justification_base,
                    )
                    results['fgroups_created'].append(target_f)
                    print(f"  Created F-group {target_f} ({action['pfam_name']})")
            else:
                # Merging into existing F-group (same pfam_acc already exists)
                reason = action.get('merge_reason', 'specified')
                if dry_run:
                    print(f"  [DRY RUN] Will MERGE {source_f} into existing "
                          f"{target_f} [{reason}]")
                else:
                    results['fgroups_merged_into'].append(target_f)
                    print(f"  Merging {source_f} into existing {target_f} [{reason}]")

            # Step 2: Move rep domains in ecod_rep
            # Create a single change request for this F-group migration
            request_id = None
            if not dry_run:
                request_id = ops.create_change_request(
                    conn, 'rename', 'F',
                    original_id=source_f,
                    new_id=target_f,
                    new_name=f"Merge {source_f} -> {target_f}",
                    justification=justification_base,
                )
                ops.approve_change_request(conn, request_id)

            for domain in action['rep_domains']:
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
                print(f"  [DRY RUN] Would reassign {action['commons_count']} "
                      f"ecod_commons domains from {source_f} -> {target_f}")
            else:
                count = ops.reassign_commons_domains(
                    conn, source_f, target_f, justification_base,
                )
                results['domains_reassigned_commons'] += count
                print(f"  Reassigned {count} ecod_commons domains -> {target_f}")

            # Step 4: Deprecate source F-group
            if dry_run:
                print(f"  [DRY RUN] Would deprecate F-group {source_f}")
            else:
                # Verify source F-group is now empty
                remaining = ops.count_fgroup_members(conn, source_f, 'ecod_rep')
                if remaining > 0:
                    msg = (f"Source F-group {source_f} still has {remaining} "
                           f"rep domains after reassignment!")
                    results['errors'].append(msg)
                    print(f"  WARNING: {msg}")
                else:
                    ops.deprecate_group(conn, source_f, 'F',
                                        justification=justification_base)
                    results['fgroups_deprecated'].append(source_f)
                    print(f"  Deprecated F-group {source_f}")

            # Commit after each F-group move
            if not dry_run:
                conn.commit()

        except Exception as e:
            msg = f"Error processing {source_f}: {e}"
            results['errors'].append(msg)
            logger.error(msg, exc_info=True)
            if not dry_run:
                conn.rollback()

    # Step 5: Deprecate source T-group, H-group, X-group (bottom-up)
    # Only proceed if no errors in F-group processing
    if results['errors']:
        print(f"  SKIPPING hierarchy deprecation due to {len(results['errors'])} error(s)")
    else:
        for level, group_id in plan['deprecations']:
            try:
                if dry_run:
                    print(f"  [DRY RUN] Would deprecate {level}-group {group_id}")
                else:
                    ops.deprecate_group(conn, group_id, level,
                                        justification=justification_base)
                    results['hierarchy_deprecated'].append((level, group_id))
                    print(f"  Deprecated {level}-group {group_id}")
                    conn.commit()
            except Exception as e:
                msg = f"Error deprecating {level}-group {group_id}: {e}"
                results['errors'].append(msg)
                logger.error(msg, exc_info=True)
                if not dry_run:
                    conn.rollback()

    return results


def verify_merge(conn, merge_def, results):
    """Verify a merge completed correctly."""
    change_id = merge_def['id']
    print(f"\n--- Verification for Change {change_id} ---")

    # Check source groups are deprecated
    for level, group_id in [
        ('X', merge_def['source_x']),
        ('H', merge_def['source_h']),
        ('T', merge_def['source_t']),
    ]:
        cluster = ops.verify_cluster_exists(conn, group_id, level)
        if cluster:
            status = "DEPRECATED" if cluster['is_deprecated'] else "ACTIVE"
            print(f"  {level}-group {group_id}: {status}")

    # Check source F-groups are deprecated
    for fmap in merge_def['fgroup_mapping']:
        source_f = fmap['source_f']
        cluster = ops.verify_fgroup_exists(conn, source_f)
        if cluster:
            status = "DEPRECATED" if cluster['is_deprecated'] else "ACTIVE"
            rep_count = ops.count_fgroup_members(conn, source_f, 'ecod_rep')
            commons_count = ops.count_fgroup_members(conn, source_f, 'ecod_commons')
            print(f"  F-group {source_f}: {status}, "
                  f"reps={rep_count}, commons={commons_count}")

    # Check newly created target F-groups
    for new_f in results.get('fgroups_created', []):
        cluster = ops.verify_fgroup_exists(conn, new_f)
        if cluster:
            rep_count = ops.count_fgroup_members(conn, new_f, 'ecod_rep')
            commons_count = ops.count_fgroup_members(conn, new_f, 'ecod_commons')
            print(f"  NEW F-group {new_f}: reps={rep_count}, commons={commons_count}")


def main():
    parser = argparse.ArgumentParser(
        description='Implement X-group merge changes (1A, 1B, 1C)'
    )
    parser.add_argument('--dry-run', action='store_true', default=True,
                        help='Preview changes without executing (default)')
    parser.add_argument('--execute', action='store_true',
                        help='Execute changes (overrides --dry-run)')
    parser.add_argument('--change', type=str, default=None,
                        help='Execute only a specific change (e.g., 1C)')
    parser.add_argument('--verify-only', action='store_true',
                        help='Only run verification, no changes')

    args = parser.parse_args()
    dry_run = not args.execute

    # Filter merges if specific change requested
    merges = XGROUP_MERGES
    if args.change:
        merges = [m for m in merges if m['id'] == args.change]
        if not merges:
            print(f"Error: Change '{args.change}' not found. "
                  f"Available: {[m['id'] for m in XGROUP_MERGES]}")
            sys.exit(1)

    conn = ops.get_db_connection()

    try:
        for merge_def in merges:
            # Plan
            plan = plan_merge(conn, merge_def)
            if plan is None:
                print(f"Skipping change {merge_def['id']} due to planning errors")
                continue

            if args.verify_only:
                verify_merge(conn, merge_def, {})
                continue

            # Execute
            ops.print_change_summary(
                merge_def['id'],
                merge_def['description'],
                [f"Source: {merge_def['source_x']} -> Target T: {merge_def['target_t']}",
                 f"F-groups to move: {len(plan['fgroup_actions'])}",
                 f"Hierarchy to deprecate: {len(plan['deprecations'])} groups"],
                dry_run=dry_run,
            )

            results = execute_merge(conn, plan, dry_run)

            # Summary
            print(f"\n--- Results for Change {merge_def['id']} ---")
            print(f"  F-groups created: {results['fgroups_created']}")
            print(f"  F-groups merged into: {results['fgroups_merged_into']}")
            print(f"  Rep domains reassigned: {results['domains_reassigned_rep']}")
            print(f"  Commons domains reassigned: {results['domains_reassigned_commons']}")
            print(f"  F-groups deprecated: {results['fgroups_deprecated']}")
            print(f"  Hierarchy deprecated: {results['hierarchy_deprecated']}")
            if results['errors']:
                print(f"  ERRORS: {results['errors']}")

            # Verify
            if not dry_run:
                verify_merge(conn, merge_def, results)

    finally:
        conn.close()


if __name__ == '__main__':
    main()
