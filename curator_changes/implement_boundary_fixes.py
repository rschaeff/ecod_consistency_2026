#!/usr/bin/env python3
"""
Implement domain boundary correction changes (3A, 3B).

Change 3A: Trim e6bmsD1 from D:79-240 to D:79-156 (ecod_commons only)
Change 3B: Fix over-extended OSCP N-terminal domain boundaries in 563.1.1

Usage:
    python implement_boundary_fixes.py --dry-run
    python implement_boundary_fixes.py --execute
    python implement_boundary_fixes.py --execute --change 3A
    python implement_boundary_fixes.py --analyze-3b  # Show over-extended domains in 563.1.1
"""

import argparse
import logging
import re
import sys
from datetime import datetime

import boundary_methods as bm
import curator_ops as ops
from change_definitions import BOUNDARY_CORRECTIONS, REQUESTED_BY

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
)
logger = logging.getLogger(__name__)


def parse_range_length(range_str):
    """Parse a range string and compute total length.

    Handles multi-segment ranges like 'A:10-50,A:60-100'.
    Returns total residue count.
    """
    total = 0
    for part in range_str.split(','):
        part = part.strip()
        match = re.match(r'([A-Za-z0-9]*):?(\d+)-(\d+)', part)
        if match:
            start = int(match.group(2))
            end = int(match.group(3))
            total += end - start + 1
    return total


# ============================================================
# Change 3A: Single domain boundary trim
# ============================================================

def execute_3a(conn, correction, dry_run=True):
    """Execute Change 3A: trim e6bmsD1 boundary."""
    domain_id = correction['domain_id']
    current_range = correction['current_range']
    new_range = correction['new_range']
    f_group = correction['f_group']
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    results = {
        'change_id': '3A',
        'domain_updated': False,
        'errors': [],
    }

    justification = (
        f"Curator change 3A: {correction['description']}. "
        f"Trim {domain_id} from {current_range} to {new_range}. "
        f"Batch: {REQUESTED_BY}_{timestamp}"
    )

    print(f"\n--- Change 3A: Trim {domain_id} ---")

    # Look up domain in ecod_commons
    commons_domain = ops.get_domain_from_ecod_commons(conn, domain_id)
    if not commons_domain:
        msg = f"Domain {domain_id} not found in ecod_commons"
        results['errors'].append(msg)
        print(f"  ERROR: {msg}")
        return results

    actual_range = commons_domain['range_definition']
    actual_length = commons_domain['sequence_length']
    new_length = parse_range_length(new_range)

    print(f"  Current: range={actual_range}, length={actual_length}")
    print(f"  New:     range={new_range}, length={new_length}")

    # Verify domain is NOT in ecod_rep (it's AUTO_NONREP)
    rep_domain = ops.get_domain_from_ecod_rep(conn, domain_id)
    if rep_domain:
        print(f"  NOTE: Domain IS in ecod_rep (uid={rep_domain['uid']}), "
              f"will also update ecod_rep")

    if dry_run:
        print(f"  [DRY RUN] Would deprecate domain {domain_id} (ecod_uid={commons_domain['ecod_uid']})")
        print(f"  [DRY RUN] Would create replacement: {new_range} ({new_length}aa)")
        if rep_domain:
            print(f"  [DRY RUN] Would delete old ecod_rep entry and add replacement")
        return results

    try:
        # Deprecate old ecod_commons domain and create replacement
        new_pk, new_ecod_uid = ops.deprecate_and_recreate_domain(
            conn, commons_domain['id'], new_range, new_length,
            f_group, justification,
        )
        print(f"  Deprecated ecod_uid={commons_domain['ecod_uid']}, "
              f"created replacement ecod_uid={new_ecod_uid}: "
              f"{domain_id} -> {new_range} ({new_length}aa)")
        results['domain_updated'] = True

        # If also in ecod_rep, delete old and add replacement
        if rep_domain:
            ops.delete_domain_from_ecod_rep(
                conn, rep_domain['uid'], domain_id,
                justification=f"Range update (deprecate+recreate): {justification}",
            )
            new_uid = ops.add_domain_to_ecod_rep(
                conn, domain_id, rep_domain['f_id'],
                justification=justification,
                manual_rep=rep_domain['manual_rep'],
                provisional_manual_rep=rep_domain['provisional_manual_rep'],
            )
            print(f"  ecod_rep: deleted uid={rep_domain['uid']}, "
                  f"added uid={new_uid} with range {new_range}")

        conn.commit()

    except Exception as e:
        msg = f"Error updating {domain_id}: {e}"
        results['errors'].append(msg)
        logger.error(msg, exc_info=True)
        conn.rollback()

    return results


# ============================================================
# Change 3B: Systematic boundary fixes for 563.1.1
# ============================================================

def analyze_3b(conn, correction):
    """Analyze domains in 563.1.1 for over-extended boundaries."""
    f_group_prefix = correction['f_group']  # "563.1.1"
    ref_length = correction['reference_length']  # 105
    max_expected = correction['max_expected_length']  # 150
    curator_domains = correction['curator_specified_domains']

    print(f"\n--- Analyzing 563.1.1 domains for over-extended boundaries ---")
    print(f"  Reference length (e1abvA1): {ref_length} aa")
    print(f"  Max expected length: {max_expected} aa")

    # Get all F-groups under this T-group
    from psycopg2.extras import RealDictCursor as RDC
    with conn.cursor(cursor_factory=RDC) as cur:
        cur.execute("""
            SELECT id::text AS f_id, name, is_deprecated
            FROM ecod_rep.cluster
            WHERE parent::text = %s AND type = 'F' AND is_deprecated = false
            ORDER BY id::text
        """, (f_group_prefix,))
        fgroups = cur.fetchall()

    print(f"  Active F-groups under {f_group_prefix}: {len(fgroups)}")

    all_over_extended = []

    for fg in fgroups:
        f_id = fg['f_id']
        domains = ops.get_commons_domains_in_fgroup(conn, f_id)

        over_extended = [
            d for d in domains
            if d['sequence_length'] and d['sequence_length'] > max_expected
        ]

        if over_extended:
            print(f"\n  F-group {f_id} ({fg['name']}): "
                  f"{len(over_extended)}/{len(domains)} over-extended")
            for d in over_extended:
                curator_flag = " ** CURATOR" if d['domain_id'] in curator_domains else ""
                print(f"    {d['domain_id']}: {d['range_definition']} "
                      f"({d['sequence_length']}aa){curator_flag}")
                all_over_extended.append({
                    'domain_id': d['domain_id'],
                    'domain_pk': d['domain_pk'],
                    'ecod_uid': d['ecod_uid'],
                    'f_group_id': f_id,
                    'range_definition': d['range_definition'],
                    'sequence_length': d['sequence_length'],
                    'excess': d['sequence_length'] - ref_length,
                    'is_curator_specified': d['domain_id'] in curator_domains,
                })

    print(f"\n  Total over-extended domains: {len(all_over_extended)}")
    print(f"  Curator-specified: {sum(1 for d in all_over_extended if d['is_curator_specified'])}")

    return all_over_extended


def execute_3b(conn, correction, over_extended, dry_run=True):
    """Execute Change 3B: fix over-extended boundaries using pairwise alignment."""
    ref_domain_id = correction['reference_domain']
    ref_length = correction['reference_length']
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    results = {
        'change_id': '3B',
        'domains_updated': 0,
        'domains_skipped': 0,
        'low_confidence': [],
        'errors': [],
    }

    justification = (
        f"Curator change 3B: {correction['description']}. "
        f"Trim by alignment to {ref_domain_id} (~{ref_length}aa). "
        f"Batch: {REQUESTED_BY}_{timestamp}"
    )

    # Get reference sequence for pairwise alignment
    ref_seq = bm.extract_domain_sequence(conn, ref_domain_id)
    if not ref_seq:
        msg = f"Could not extract reference sequence for {ref_domain_id}"
        results['errors'].append(msg)
        print(f"  ERROR: {msg}")
        return results

    print(f"\n--- Executing Change 3B: Boundary fixes for 563.1.1 ---")
    print(f"  Reference: {ref_domain_id} ({len(ref_seq)}aa)")
    print(f"  Using pairwise alignment to determine C-terminal trim point")
    print(f"  Candidates: {len(over_extended)} over-extended domains")

    for domain_info in over_extended:
        domain_id = domain_info['domain_id']
        current_range = domain_info['range_definition']
        current_length = domain_info['sequence_length']

        # Extract domain sequence and align to reference
        query_seq = bm.extract_domain_sequence(conn, domain_id)
        if not query_seq:
            print(f"  SKIP {domain_id}: could not extract sequence")
            results['domains_skipped'] += 1
            continue

        new_range, new_length, aln = bm.compute_cterminal_trim(
            ref_seq, query_seq, current_range)

        if new_range is None:
            ref_cov = f"{aln['ref_coverage']:.0%}" if aln else "N/A"
            print(f"  SKIP {domain_id}: {current_range} ({current_length}aa) "
                  f"[low ref coverage {ref_cov}]")
            results['domains_skipped'] += 1
            if aln:
                results['low_confidence'].append({
                    'domain_id': domain_id,
                    'range': current_range,
                    'length': current_length,
                    'ref_coverage': aln['ref_coverage'],
                    'score': aln['score'],
                })
            continue

        ref_cov = f"{aln['ref_coverage']:.0%}" if aln else "?"
        if dry_run:
            print(f"  [DRY RUN] {domain_id}: {current_range} ({current_length}aa) -> "
                  f"{new_range} ({new_length}aa) [ref_cov={ref_cov}]")
            results['domains_updated'] += 1
            continue

        try:
            # Check if domain is in ecod_rep
            rep_domain = ops.get_domain_from_ecod_rep(conn, domain_id)

            # Deprecate old ecod_commons domain and create replacement
            # domain_info['domain_pk'] is the ecod_commons.domains.id
            new_pk, new_ecod_uid = ops.deprecate_and_recreate_domain(
                conn, domain_info['domain_pk'], new_range, new_length,
                domain_info['f_group_id'], justification,
            )

            # If also in ecod_rep, delete old and add replacement
            if rep_domain:
                ops.delete_domain_from_ecod_rep(
                    conn, rep_domain['uid'], domain_id,
                    justification=f"Boundary trim (deprecate+recreate): {justification}",
                )
                new_uid = ops.add_domain_to_ecod_rep(
                    conn, domain_id, rep_domain['f_id'],
                    justification=justification,
                    manual_rep=rep_domain['manual_rep'],
                    provisional_manual_rep=rep_domain['provisional_manual_rep'],
                )
                print(f"  {domain_id}: {current_range} -> {new_range} "
                      f"(ecod_rep uid={new_uid} + ecod_commons ecod_uid={new_ecod_uid})")
            else:
                print(f"  {domain_id}: {current_range} -> {new_range} "
                      f"(ecod_commons ecod_uid={new_ecod_uid})")

            results['domains_updated'] += 1
            conn.commit()

        except Exception as e:
            msg = f"Error updating {domain_id}: {e}"
            results['errors'].append(msg)
            logger.error(msg, exc_info=True)
            conn.rollback()

    return results


def main():
    parser = argparse.ArgumentParser(
        description='Implement domain boundary corrections (3A, 3B)'
    )
    parser.add_argument('--dry-run', action='store_true', default=True,
                        help='Preview changes without executing (default)')
    parser.add_argument('--execute', action='store_true',
                        help='Execute changes (overrides --dry-run)')
    parser.add_argument('--change', type=str, default=None,
                        help='Execute only a specific change (3A or 3B)')
    parser.add_argument('--analyze-3b', action='store_true',
                        help='Only analyze 563.1.1 domains, no changes')

    args = parser.parse_args()
    dry_run = not args.execute

    conn = ops.get_db_connection()

    try:
        for correction in BOUNDARY_CORRECTIONS:
            if args.change and correction['id'] != args.change:
                continue

            if correction['id'] == '3A':
                if args.analyze_3b:
                    continue

                ops.print_change_summary(
                    '3A', correction['description'],
                    [f"Domain: {correction['domain_id']}",
                     f"Range: {correction['current_range']} -> {correction['new_range']}"],
                    dry_run=dry_run,
                )
                results = execute_3a(conn, correction, dry_run)

                print(f"\n--- Results for Change 3A ---")
                print(f"  Domain updated: {results['domain_updated']}")
                if results['errors']:
                    print(f"  ERRORS: {results['errors']}")

            elif correction['id'] == '3B':
                # Always analyze first
                over_extended = analyze_3b(conn, correction)

                if args.analyze_3b:
                    continue

                if not over_extended:
                    print("  No over-extended domains found")
                    continue

                ops.print_change_summary(
                    '3B', correction['description'],
                    [f"Over-extended domains: {len(over_extended)}",
                     f"Reference: {correction['reference_domain']} ({correction['reference_length']}aa)",
                     f"Method: pairwise alignment to reference",
                     f"Curator-specified: {correction['curator_specified_domains']}"],
                    dry_run=dry_run,
                )

                results = execute_3b(conn, correction, over_extended, dry_run)

                print(f"\n--- Results for Change 3B ---")
                print(f"  Domains updated: {results['domains_updated']}")
                print(f"  Domains skipped: {results['domains_skipped']}")
                if results.get('low_confidence'):
                    print(f"  Low-confidence skips ({len(results['low_confidence'])}):")
                    for lc in results['low_confidence'][:10]:
                        print(f"    {lc['domain_id']}: {lc['range']} "
                              f"(ref_cov={lc['ref_coverage']:.0%})")
                    if len(results['low_confidence']) > 10:
                        print(f"    ... and {len(results['low_confidence']) - 10} more")
                if results['errors']:
                    print(f"  ERRORS: {results['errors']}")

    finally:
        conn.close()


if __name__ == '__main__':
    main()
