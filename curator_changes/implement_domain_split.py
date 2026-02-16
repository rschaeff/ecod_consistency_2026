#!/usr/bin/env python3
"""
Implement domain split change (2C: Kringle,WSC).

F-group 380.1.1.3 contains domains with two distinct structural regions
(Kringle + WSC) that should be classified separately:
  - Kringle portion -> 380.1.1.2
  - WSC portion -> 390.1.1.2

Algorithm:
  Phase 1: Determine split boundaries for all domains
    - Align each domain to the reference (e5fwwB1) to find Kringle/WSC boundary
    - Or use Pfam HMM boundaries (PF00051/PF01822)
  Phase 2: Validate products
    - Verify fragment sizes are reasonable
  Phase 3: Execute splits
    - For ecod_rep: reassign or create new domain entries
    - For ecod_commons: create new domains, assign to target F-groups,
      obsolete originals
  Phase 4: Deprecate source F-group 380.1.1.3

Usage:
    python implement_domain_split.py --dry-run
    python implement_domain_split.py --execute
    python implement_domain_split.py --analyze-only  # Just show domain analysis
"""

import argparse
import logging
import re
import sys
from datetime import datetime

import boundary_methods as bm
import curator_ops as ops
from change_definitions import DOMAIN_SPLITS, REQUESTED_BY

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
)
logger = logging.getLogger(__name__)


def compute_split_from_hmmer(domain_range, hmmer_hits, split_defs):
    """Compute split boundaries from HMMER envelope coordinates.

    Args:
        domain_range: original range string (e.g., '296-385')
        hmmer_hits: dict from get_hmmer_boundaries, mapping pfam_acc ->
                    {'env_start': int, 'env_end': int, ...}
                    Coordinates are 1-based, domain-local.
        split_defs: list of split target definitions from change_definitions,
                    each with 'pfam_acc' and 'name'.

    Returns:
        list of (range_str, length) tuples, one per split_def.
        Any entry may be (None, None) if that Pfam wasn't found.
    """
    results = []
    for split_def in split_defs:
        pfam_acc = split_def['pfam_acc']
        hit = hmmer_hits.get(pfam_acc)
        if not hit:
            results.append((None, None))
            continue

        env_start = hit['env_start']
        env_end = hit['env_end']
        length = env_end - env_start + 1

        # Convert domain-local to absolute coordinates
        abs_result = bm.domain_local_to_absolute(env_start, env_end, domain_range)
        if abs_result is None:
            results.append((None, None))
            continue

        abs_start, abs_end = abs_result
        range_str = bm.format_absolute_range(abs_start, abs_end)
        results.append((range_str, length))

    return results


def analyze_domains(conn, split_def):
    """Analyze all domains in the source F-group and plan splits using HMMER."""
    source_f = split_def['source_f']
    ref_domain_id = split_def['reference_domain']
    splits = split_def['splits']

    # Build Pfam name/acc lists from split definitions
    pfam_accs = [s['pfam_acc'] for s in splits]
    pfam_names = [s['name'] for s in splits]

    print(f"\n--- Analyzing domains in {source_f} ({split_def['source_f_name']}) ---")
    print(f"  Using HMMER boundaries: {', '.join(f'{n} ({a})' for n, a in zip(pfam_names, pfam_accs))}")

    # Get reference domain info
    ref_domain = ops.get_domain_from_ecod_commons(conn, ref_domain_id)
    if not ref_domain:
        print(f"  ERROR: Reference domain {ref_domain_id} not found!")
        return None

    print(f"  Reference: {ref_domain_id}, range={ref_domain['range_definition']}, "
          f"length={ref_domain['sequence_length']}")

    for s in splits:
        print(f"  {s['name']} ({s['pfam_acc']}) -> {s['target_f']}")

    # Get all domains in this F-group
    commons_domains = ops.get_commons_domains_in_fgroup(conn, source_f)
    rep_domains = ops.get_rep_domains_in_fgroup(conn, source_f)

    print(f"\n  Domains: {len(commons_domains)} in ecod_commons, "
          f"{len(rep_domains)} in ecod_rep")

    # Plan splits for each domain using HMMER
    split_plans = []
    hmmer_from_db = 0
    hmmer_from_scan = 0

    for domain in commons_domains:
        domain_range = domain['range_definition']
        domain_length = domain['sequence_length'] or 0
        domain_id = domain['domain_id']

        is_rep = any(r['ecod_domain_id'] == domain_id for r in rep_domains)

        # Get HMMER boundaries (DB first, then hmmscan fallback)
        hmmer_hits = bm.get_hmmer_boundaries_from_db(conn, domain_id, pfam_accs)
        source = 'db'
        if not hmmer_hits:
            seq = bm.extract_domain_sequence(
                conn, domain_id, domain['protein_id'], domain_range)
            if seq:
                hmmer_hits = bm.run_hmmscan_for_domain(seq, pfam_names, domain_id)
                source = 'hmmscan'
            else:
                source = 'no_seq'

        if source == 'db':
            hmmer_from_db += 1
        elif source == 'hmmscan':
            hmmer_from_scan += 1

        # Compute split ranges from HMMER hits
        split_results = compute_split_from_hmmer(domain_range, hmmer_hits, splits)

        plan = {
            'domain_id': domain_id,
            'domain_pk': domain['domain_pk'],
            'ecod_uid': domain['ecod_uid'],
            'protein_id': domain['protein_id'],
            'domain_version': domain['domain_version'],
            'original_range': domain_range,
            'original_length': domain_length,
            'assignment_id': domain['assignment_id'],
            'is_rep': is_rep,
            'hmmer_source': source,
            'hmmer_hits': hmmer_hits,
            'products': [],  # list of dicts with 'name', 'range', 'length', 'target_f', 'pfam_acc'
            'valid': False,
            'warnings': [],
        }

        # Build products: one per HMMER hit found (discard portions with no hit)
        range_strs = []
        for i, (s_def, (rng, length)) in enumerate(zip(splits, split_results)):
            name = s_def['name']
            if rng is not None:
                product = {
                    'name': name,
                    'range': rng,
                    'length': length,
                    'target_f': s_def['target_f'],
                    'pfam_acc': s_def['pfam_acc'],
                    'suffix': name[0].lower(),  # 'k' or 'w'
                }
                plan['products'].append(product)
                range_strs.append(f"{name}:{rng}({length}aa)")
                if length < 20:
                    plan['warnings'].append(f"{name} fragment very short ({length}aa)")
            else:
                range_strs.append(f"{name}:--")

        # Valid if at least one product
        plan['valid'] = len(plan['products']) > 0
        n_products = len(plan['products'])

        if n_products == len(splits):
            status = "SPLIT"
        elif n_products == 1:
            status = "RECLASS"
        else:
            status = "NO_HIT"

        if plan['warnings']:
            status += "/WARN"

        rep_flag = " [REP]" if is_rep else ""
        print(f"  {domain_id}{rep_flag}: {domain_range} ({domain_length}aa) -> "
              f"{' + '.join(range_strs)} [{status}] [{source}]")
        for w in plan['warnings']:
            print(f"    WARNING: {w}")

        split_plans.append(plan)

    print(f"\n  HMMER sources: {hmmer_from_db} from DB, {hmmer_from_scan} from hmmscan")

    return {
        'split_def': split_def,
        'ref_domain': ref_domain,
        'split_plans': split_plans,
        'rep_domains': rep_domains,
    }


def execute_split(conn, analysis, dry_run=True):
    """Execute domain splits based on HMMER-determined products.

    Each domain plan has a 'products' list with 0, 1, or 2 entries depending
    on which Pfam HMMs were detected. Domains with no products are skipped.
    Each product becomes a new domain assigned to its target F-group.
    The original domain is obsoleted regardless of product count.
    """
    split_def = analysis['split_def']
    source_f = split_def['source_f']
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Collect all target F-groups from split definitions
    all_targets = {s['target_f']: s['name'] for s in split_def['splits']}

    results = {
        'change_id': split_def['id'],
        'domains_processed': 0,
        'domains_skipped': 0,
        'new_domains_created': 0,
        'source_deprecated': False,
        'errors': [],
    }

    justification = (
        f"Curator change {split_def['id']}: Split {source_f} "
        f"({split_def['source_f_name']}). "
        f"Targets: {', '.join(f'{n} -> {f}' for f, n in all_targets.items())}. "
        f"Batch: {REQUESTED_BY}_{timestamp}"
    )

    # Verify all target F-groups exist
    for target_f, name in all_targets.items():
        cluster = ops.verify_fgroup_exists(conn, target_f)
        if not cluster:
            msg = f"Target F-group {target_f} ({name}) not found!"
            results['errors'].append(msg)
            print(f"  ERROR: {msg}")
            return results
        if cluster['is_deprecated']:
            msg = f"Target F-group {target_f} ({name}) is deprecated!"
            results['errors'].append(msg)
            print(f"  ERROR: {msg}")
            return results

    # Create tracking change request
    request_id = None
    if not dry_run:
        request_id = ops.create_change_request(
            conn, 'deprecate', 'F',
            original_id=source_f,
            justification=justification,
        )
        ops.approve_change_request(conn, request_id)

    # Process each domain
    for plan in analysis['split_plans']:
        if not plan['valid']:
            print(f"  SKIP {plan['domain_id']}: no HMMER hits")
            results['domains_skipped'] += 1
            continue

        products = plan['products']
        base_id = plan['domain_id']
        n_products = len(products)

        try:
            if dry_run:
                if n_products > 1:
                    label = "SPLIT"
                else:
                    label = "RECLASS"
                print(f"  [DRY RUN] {label} {base_id} ({plan['original_range']}):")
                for prod in products:
                    print(f"    {prod['name']}: {prod['range']} "
                          f"({prod['length']}aa) -> {prod['target_f']}")
                for w in plan['warnings']:
                    print(f"    WARNING: {w}")
                results['domains_processed'] += 1
                results['new_domains_created'] += n_products
                continue

            # Handle ecod_rep domain (the representative)
            if plan['is_rep']:
                rep_domain = ops.get_domain_from_ecod_rep(conn, base_id)
                if rep_domain:
                    product_names = '/'.join(p['name'] for p in products)
                    ops.delete_domain_from_ecod_rep(
                        conn, rep_domain['uid'], base_id,
                        justification=f"Split into {product_names}: {justification}",
                    )
                    print(f"  Deleted rep {base_id} from ecod_rep (split)")

            # Create new ecod_commons domain entries for each product
            new_pks = []
            for prod in products:
                suffix = prod['suffix']
                new_domain_id = f"{base_id}{suffix}"
                new_ecod_uid = ops.allocate_ecod_uid(conn)

                new_pk = ops.create_commons_domain(
                    conn,
                    ecod_uid=new_ecod_uid,
                    domain_id=new_domain_id,
                    range_definition=prod['range'],
                    sequence_length=prod['length'],
                    protein_id=plan['protein_id'],
                    domain_version=plan['domain_version'],
                )

                ops.create_commons_fgroup_assignment(
                    conn, new_pk, prod['target_f'],
                    f"Split from {base_id} ({prod['name']} portion): {justification}",
                )
                new_pks.append(new_pk)
                results['new_domains_created'] += 1
                print(f"  Created {new_domain_id} (ecod_uid={new_ecod_uid}, "
                      f"{prod['name']}, {prod['range']}) -> {prod['target_f']}")

            # Obsolete original domain
            product_names = '/'.join(p['name'] for p in products)
            ops.obsolete_commons_domain(
                conn, plan['domain_pk'],
                reason=f"Split into {product_names}: {justification}",
                superseded_by_pk=new_pks[0] if new_pks else None,
            )

            results['domains_processed'] += 1
            conn.commit()

        except Exception as e:
            msg = f"Error splitting {base_id}: {e}"
            results['errors'].append(msg)
            logger.error(msg, exc_info=True)
            conn.rollback()

    # Deprecate source F-group if all domains were processed
    if not dry_run and results['domains_skipped'] == 0:
        try:
            remaining = ops.count_fgroup_members(conn, source_f, 'ecod_rep')
            if remaining == 0:
                ops.deprecate_group(conn, source_f, 'F',
                                    justification=justification)
                results['source_deprecated'] = True
                print(f"  Deprecated F-group {source_f}")
                conn.commit()
            else:
                print(f"  Source {source_f} still has {remaining} reps, not deprecating")
        except Exception as e:
            msg = f"Error deprecating {source_f}: {e}"
            results['errors'].append(msg)
            logger.error(msg, exc_info=True)
    elif dry_run:
        print(f"  [DRY RUN] Would deprecate F-group {source_f}")

    return results


def main():
    parser = argparse.ArgumentParser(
        description='Implement domain split change (2C: Kringle,WSC)'
    )
    parser.add_argument('--dry-run', action='store_true', default=True,
                        help='Preview changes without executing (default)')
    parser.add_argument('--execute', action='store_true',
                        help='Execute changes (overrides --dry-run)')
    parser.add_argument('--analyze-only', action='store_true',
                        help='Only analyze domains, do not plan changes')

    args = parser.parse_args()
    dry_run = not args.execute

    conn = ops.get_db_connection()

    try:
        for split_def in DOMAIN_SPLITS:
            analysis = analyze_domains(conn, split_def)
            if analysis is None:
                print("Analysis failed, cannot proceed")
                continue

            if args.analyze_only:
                # Print summary statistics
                plans = analysis['split_plans']
                valid = sum(1 for p in plans if p['valid'])
                n_split = sum(1 for p in plans if len(p['products']) > 1)
                n_reclass = sum(1 for p in plans if len(p['products']) == 1)
                n_nohit = sum(1 for p in plans if not p['valid'])
                warned = sum(1 for p in plans if p['warnings'])
                print(f"\n  Summary: {len(plans)} domains total")
                print(f"    SPLIT (both hits): {n_split}")
                print(f"    RECLASS (one hit): {n_reclass}")
                print(f"    NO_HIT (skip):     {n_nohit}")
                print(f"    With warnings:     {warned}")
                continue

            # Summarize the plan
            plans = analysis['split_plans']
            n_split = sum(1 for p in plans if len(p['products']) > 1)
            n_reclass = sum(1 for p in plans if len(p['products']) == 1)
            n_nohit = sum(1 for p in plans if not p['valid'])

            target_lines = [
                f"{s['name']} -> {s['target_f']}" for s in split_def['splits']
            ]
            ops.print_change_summary(
                split_def['id'],
                f"Split {split_def['source_f']} ({split_def['source_f_name']})",
                target_lines + [
                    f"Domains: {len(plans)} total, "
                    f"{n_split} split, {n_reclass} reclass, {n_nohit} no hit",
                ],
                dry_run=dry_run,
            )

            results = execute_split(conn, analysis, dry_run)

            print(f"\n--- Results for Change {split_def['id']} ---")
            print(f"  Domains processed: {results['domains_processed']}")
            print(f"  Domains skipped: {results['domains_skipped']}")
            print(f"  New domains created: {results['new_domains_created']}")
            print(f"  Source deprecated: {results['source_deprecated']}")
            if results['errors']:
                print(f"  ERRORS:")
                for e in results['errors']:
                    print(f"    {e}")

    finally:
        conn.close()


if __name__ == '__main__':
    main()
