#!/usr/bin/env python3
"""
Implement batch 2 merge changes:
  B2_1: TLC/ELO/TMEM120 unification (new X-group + merge 11 F-groups -> 3)
  B2_2: VSG + HpHbR X-group merge (merge 3633 into 1189, rename, move to a.7)

Usage:
    python implement_batch2_merges.py --dry-run
    python implement_batch2_merges.py --execute
    python implement_batch2_merges.py --execute --change B2_1
"""

import argparse
import logging
import sys
from datetime import datetime

import curator_ops as ops
from change_definitions import REQUESTED_BY
from change_definitions_batch2 import (
    TLC_ELO_TMEM120_UNIFICATION,
    VSG_HPBHR_MERGE,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)


# ============================================================
# Change B2_1: TLC/ELO/TMEM120 unification
# ============================================================

def execute_tlc_elo_unification(conn, dry_run=True):
    """Create new X-group and merge 11 F-groups into 3."""
    cfg = TLC_ELO_TMEM120_UNIFICATION
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    justification = f"Curator change {cfg['id']}: {cfg['description']} [{timestamp}]"

    print(f"\n{'='*70}")
    print(f"Change {cfg['id']}: {cfg['description']}")
    print(f"Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")
    print(f"{'='*70}")

    # Step 1: Create new X/H/T hierarchy (or find existing if restarting)
    new_hierarchy = None
    if dry_run:
        print(f"  [DRY RUN] Would create X/H/T '{cfg['new_xgroup_name']}' under {cfg['a_group']}")
    else:
        # Check if already created
        from psycopg2.extras import RealDictCursor
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id::text AS x_id FROM ecod_rep.cluster
                WHERE type = 'X' AND name = %s AND is_deprecated = false
            """, (cfg['new_xgroup_name'],))
            existing_x = cur.fetchone()
        if existing_x:
            x_id = existing_x['x_id']
            new_hierarchy = {
                'x_id': x_id,
                'h_id': f"{x_id}.1",
                't_id': f"{x_id}.1.1",
            }
            print(f"  X/H/T already exists: X:{x_id} (reusing)")
        else:
            new_hierarchy = ops.create_xht_hierarchy(
                conn, cfg['new_xgroup_name'], cfg['a_group'], justification,
            )
            conn.commit()
            print(f"  Created X:{new_hierarchy['x_id']} H:{new_hierarchy['h_id']} "
                  f"T:{new_hierarchy['t_id']} ('{cfg['new_xgroup_name']}')")

    new_t_id = new_hierarchy['t_id'] if new_hierarchy else 'NEW'

    # Step 2: For each family, create unified F-group and merge sources
    for family in cfg['families']:
        fname = family['name']
        pfam_acc = family['pfam_acc']
        prov_rep = family['prov_manual_rep']
        sources = family['source_fgroups']

        print(f"\n  --- F: {fname} ({pfam_acc}) ---")
        print(f"  Merging {len(sources)} source F-groups, prov. rep: {prov_rep}")

        # Create the target F-group (or find existing if restarting)
        target_f = None
        if dry_run:
            print(f"  [DRY RUN] Would create F-group '{fname}' under T:{new_t_id}")
            target_f = f"{new_t_id}.NEW"
        else:
            # Check if already created (idempotent restart)
            from psycopg2.extras import RealDictCursor
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT id::text AS f_id FROM ecod_rep.cluster
                    WHERE parent = %s AND type = 'F' AND name = %s
                      AND is_deprecated = false
                """, (new_t_id, fname))
                existing = cur.fetchone()
            if existing:
                target_f = existing['f_id']
                print(f"  F-group {target_f} ({fname}) already exists, reusing")
            else:
                target_f, req_id = ops.create_fgroup(
                    conn, new_t_id, name=fname, pfam_acc=pfam_acc,
                    justification=justification,
                )
                conn.commit()
                print(f"  Created F-group {target_f} ({fname})")

        # Move each source F-group's domains into the new target
        for source_f in sources:
            source = ops.verify_fgroup_exists(conn, source_f)
            if not source:
                print(f"  WARNING: Source {source_f} not found, skipping")
                continue
            if source['is_deprecated']:
                print(f"  WARNING: Source {source_f} already deprecated, skipping")
                continue

            rep_domains = ops.get_rep_domains_in_fgroup(conn, source_f)
            commons_count = ops.count_fgroup_members(conn, source_f, 'ecod_commons')

            if dry_run:
                print(f"  [DRY RUN] {source_f}: {len(rep_domains)} reps, "
                      f"{commons_count} commons -> {target_f}")
                continue

            # Create change request for this migration
            request_id = ops.create_change_request(
                conn, 'rename', 'F',
                original_id=source_f, new_id=target_f,
                new_name=f"Merge {source_f} -> {target_f}",
                justification=justification,
            )
            ops.approve_change_request(conn, request_id)

            # Move reps
            for domain in rep_domains:
                ops.reassign_domain_fgroup(conn, domain['uid'], target_f, request_id)

            # Move commons
            count = ops.reassign_commons_domains(conn, source_f, target_f, justification)

            # Deprecate source F-group
            remaining = ops.count_fgroup_members(conn, source_f, 'ecod_rep')
            if remaining == 0:
                ops.deprecate_group(conn, source_f, 'F', justification=justification)
                print(f"  {source_f}: moved {len(rep_domains)} reps + {count} commons, deprecated")
            else:
                print(f"  WARNING: {source_f} still has {remaining} reps after move!")

            conn.commit()

        # Set provisional manual rep
        if not dry_run:
            _set_provisional_manual_rep(conn, target_f, prov_rep)
            conn.commit()
            print(f"  Set provisional manual rep: {prov_rep}")

    # Step 3: Check if any source parent T/H/X groups are now empty and deprecate
    if not dry_run:
        _deprecate_emptied_parents(conn, cfg, justification)

    print(f"\n  Change {cfg['id']} {'preview' if dry_run else 'execution'} complete.")


def _set_provisional_manual_rep(conn, f_id, rep_domain_id):
    """Set one domain as provisional_manual_rep, clear it on others."""
    rep_domains = ops.get_rep_domains_in_fgroup(conn, f_id)
    with conn.cursor() as cur:
        for d in rep_domains:
            is_prov = d['ecod_domain_id'] == rep_domain_id
            cur.execute("""
                UPDATE ecod_rep.domain
                SET provisional_manual_rep = %s
                WHERE uid = %s
            """, (is_prov, d['uid']))
            if is_prov:
                logger.info("Set provisional_manual_rep on %s (uid=%d)",
                            rep_domain_id, d['uid'])


def _deprecate_emptied_parents(conn, cfg, justification):
    """Check and deprecate parent T/H/X groups emptied by the unification."""
    all_sources = []
    for family in cfg['families']:
        all_sources.extend(family['source_fgroups'])

    # Collect unique parent hierarchies
    seen_parents = set()
    for source_f in all_sources:
        hier = ops.get_hierarchy_ids_for_fgroup(conn, source_f)
        if hier:
            key = (hier['t_id'], hier['h_id'], hier['x_id'])
            seen_parents.add(key)

    for t_id, h_id, x_id in seen_parents:
        # Check if T-group has any active F-groups left
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM ecod_rep.cluster
                WHERE parent = %s AND type = 'F' AND is_deprecated = false
            """, (t_id,))
            active_f = cur.fetchone()[0]

        if active_f == 0:
            for level, gid in [('T', t_id), ('H', h_id), ('X', x_id)]:
                cluster = ops.verify_cluster_exists(conn, gid, level)
                if cluster and not cluster['is_deprecated']:
                    # Check that all children are deprecated before deprecating parent
                    with conn.cursor() as cur:
                        cur.execute("""
                            SELECT COUNT(*) FROM ecod_rep.cluster
                            WHERE parent = %s AND is_deprecated = false
                        """, (gid,))
                        active_children = cur.fetchone()[0]
                    if active_children == 0:
                        ops.deprecate_group(conn, gid, level, justification=justification)
                        print(f"  Deprecated {level}-group {gid}")
                        conn.commit()
                    else:
                        print(f"  {level}-group {gid} still has {active_children} active children")
        else:
            print(f"  T-group {t_id} still has {active_f} active F-groups, keeping")


# ============================================================
# Change B2_2: VSG + HpHbR merge
# ============================================================

def execute_vsg_merge(conn, dry_run=True):
    """Merge X-group 3633 into 1189, rename, move to a.7."""
    cfg = VSG_HPBHR_MERGE
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    justification = f"Curator change {cfg['id']}: {cfg['description']} [{timestamp}]"

    print(f"\n{'='*70}")
    print(f"Change {cfg['id']}: {cfg['description']}")
    print(f"Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")
    print(f"{'='*70}")

    # Step 1: Move F-groups from 3633.1.1 into 1189.1.1
    for fmap in cfg['fgroup_mapping']:
        source_f = fmap['source_f']
        source = ops.verify_fgroup_exists(conn, source_f)
        if not source or source['is_deprecated']:
            print(f"  WARNING: Source {source_f} not found or deprecated, skipping")
            continue

        rep_domains = ops.get_rep_domains_in_fgroup(conn, source_f)
        commons_count = ops.count_fgroup_members(conn, source_f, 'ecod_commons')

        if dry_run:
            print(f"  [DRY RUN] {source_f} ({fmap['pfam']}): {len(rep_domains)} reps, "
                  f"{commons_count} commons -> new F under {cfg['target_t']}")
            continue

        # Create new F-group under target T-group
        target_f, req_id = ops.create_fgroup(
            conn, cfg['target_t'], name=fmap['pfam'],
            pfam_acc=fmap['pfam_acc'], justification=justification,
        )
        print(f"  Created {target_f} ({fmap['pfam']})")

        # Create change request for migration
        request_id = ops.create_change_request(
            conn, 'rename', 'F',
            original_id=source_f, new_id=target_f,
            new_name=f"Merge {source_f} -> {target_f}",
            justification=justification,
        )
        ops.approve_change_request(conn, request_id)

        # Move reps
        for domain in rep_domains:
            ops.reassign_domain_fgroup(conn, domain['uid'], target_f, request_id)

        # Move commons
        count = ops.reassign_commons_domains(conn, source_f, target_f, justification)

        # Deprecate source
        remaining = ops.count_fgroup_members(conn, source_f, 'ecod_rep')
        if remaining == 0:
            ops.deprecate_group(conn, source_f, 'F', justification=justification)
            print(f"  Moved {len(rep_domains)} reps + {count} commons, deprecated {source_f}")
        else:
            print(f"  WARNING: {source_f} still has {remaining} reps!")

        conn.commit()

    # Step 2: Deprecate source X/H/T 3633
    if not dry_run:
        for level, gid in [('T', cfg['source_t']),
                           ('H', cfg['source_h']),
                           ('X', cfg['source_x'])]:
            cluster = ops.verify_cluster_exists(conn, gid, level)
            if cluster and not cluster['is_deprecated']:
                ops.deprecate_group(conn, gid, level, justification=justification)
                print(f"  Deprecated {level}-group {gid}")
                conn.commit()
    else:
        print(f"  [DRY RUN] Would deprecate T:{cfg['source_t']}, "
              f"H:{cfg['source_h']}, X:{cfg['source_x']}")

    # Step 3: Rename 1189 X/H/T
    if dry_run:
        print(f"  [DRY RUN] Would rename X/H/T 1189 to '{cfg['new_name']}'")
    else:
        for level, gid in [('X', cfg['target_x']),
                           ('H', f"{cfg['target_x']}.1"),
                           ('T', cfg['target_t'])]:
            ops.rename_group(conn, gid, level, cfg['new_name'], justification)
            print(f"  Renamed {level}-group {gid}")
        conn.commit()

    # Step 4: Move X-group 1189 to a.7 (alpha bundles)
    if dry_run:
        print(f"  [DRY RUN] Would move X:{cfg['target_x']} to A:{cfg['new_a_group']}")
    else:
        count = ops.reassign_xgroup_architecture(
            conn, cfg['target_x'], cfg['new_a_group'], justification,
        )
        conn.commit()
        print(f"  Moved X:{cfg['target_x']} to A:{cfg['new_a_group']} "
              f"({count} commons assignments updated)")

    print(f"\n  Change {cfg['id']} {'preview' if dry_run else 'execution'} complete.")


# ============================================================
# Verification
# ============================================================

def verify_b2_1(conn):
    """Verify TLC/ELO/TMEM120 unification."""
    cfg = TLC_ELO_TMEM120_UNIFICATION
    print(f"\n--- Verification: {cfg['id']} ---")

    # Check all source F-groups are deprecated
    all_sources = []
    for family in cfg['families']:
        all_sources.extend(family['source_fgroups'])
    for sf in all_sources:
        cluster = ops.verify_fgroup_exists(conn, sf)
        if cluster:
            status = "DEPRECATED" if cluster['is_deprecated'] else "ACTIVE"
            count = ops.count_fgroup_members(conn, sf, 'ecod_commons')
            print(f"  Source {sf}: {status}, commons={count}")

    # Check target F-groups exist and have domains
    # (we don't know the IDs yet, so search by name under new X-group)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id::text, name, pfam_acc, is_deprecated
            FROM ecod_rep.cluster
            WHERE name IN ('TRAM_LAG1_CLN8', 'ELO', 'TMPIT')
              AND type = 'F' AND is_deprecated = false
            ORDER BY id::text
        """)
        for row in cur.fetchall():
            count = ops.count_fgroup_members(conn, row[0], 'ecod_commons')
            print(f"  Target {row[0]} ({row[1]}): commons={count}")


def verify_b2_2(conn):
    """Verify VSG/HpHbR merge."""
    cfg = VSG_HPBHR_MERGE
    print(f"\n--- Verification: {cfg['id']} ---")

    # Source hierarchy should be deprecated
    for level, gid in [('X', cfg['source_x']),
                       ('H', cfg['source_h']),
                       ('T', cfg['source_t'])]:
        cluster = ops.verify_cluster_exists(conn, gid, level)
        if cluster:
            status = "DEPRECATED" if cluster['is_deprecated'] else "ACTIVE"
            print(f"  Source {level}:{gid}: {status}")

    # Target X-group name
    target = ops.verify_cluster_exists(conn, cfg['target_x'], 'X')
    if target:
        print(f"  Target X:{cfg['target_x']}: name='{target['name']}'")
        print(f"    parent={target['parent_id']} (should be {cfg['new_a_group']})")

    # Count domains in target T-group F-groups
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id::text, name, pfam_acc
            FROM ecod_rep.cluster
            WHERE parent = %s AND type = 'F' AND is_deprecated = false
            ORDER BY id::text
        """, (cfg['target_t'],))
        for row in cur.fetchall():
            count = ops.count_fgroup_members(conn, row[0], 'ecod_commons')
            reps = len(ops.get_rep_domains_in_fgroup(conn, row[0]))
            print(f"  F:{row[0]} ({row[1]}): reps={reps}, commons={count}")


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description='Implement batch 2 merge changes (B2_1, B2_2)')
    parser.add_argument('--dry-run', action='store_true', default=True)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--change', type=str, default=None,
                        help='Execute only B2_1 or B2_2')
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    dry_run = not args.execute

    conn = ops.get_db_connection()
    try:
        if args.verify_only:
            if not args.change or args.change == 'B2_1':
                verify_b2_1(conn)
            if not args.change or args.change == 'B2_2':
                verify_b2_2(conn)
            return

        if not args.change or args.change == 'B2_1':
            execute_tlc_elo_unification(conn, dry_run)
            if not dry_run:
                verify_b2_1(conn)

        if not args.change or args.change == 'B2_2':
            execute_vsg_merge(conn, dry_run)
            if not dry_run:
                verify_b2_2(conn)

    finally:
        conn.close()


if __name__ == '__main__':
    main()
