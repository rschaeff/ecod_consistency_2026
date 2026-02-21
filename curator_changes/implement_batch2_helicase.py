#!/usr/bin/env python3
"""
Implement batch 2 helicase split:
  B2_5: Split F:3930.1.1.1 (Helicase_C,RIG-I_C) into:
    - F:3930.1.1.2 (RIG-I_C, PF18119)
    - F:2004.1.1.30 (Helicase_C, PF00271)

Some domains will contain only one Pfam hit (reclassified, not split).
Domains that have both hits are split into two new domains.

The neighboring DEAD domain (F:2004.1.1.29) may need boundary adjustment
when the C-terminal discontinuous segment moves to the Helicase_C domain.

Correctly-split examples already exist in PDBs 7tnx, 8dvr, 8g7t.

Usage:
    python implement_batch2_helicase.py --dry-run
    python implement_batch2_helicase.py --execute
    python implement_batch2_helicase.py --analyze-only
"""

import argparse
import logging
import re
import sys
from datetime import datetime

import boundary_methods as bm
import curator_ops as ops
from change_definitions import REQUESTED_BY
from change_definitions_batch2 import HELICASE_RIGI_SPLIT

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Pfam details
RIGI_PFAM = 'PF18119'
RIGI_NAME = 'RIG-I_C'
HELICASE_PFAM = 'PF00271'
HELICASE_NAME = 'Helicase_C'


def next_domain_id(conn, base_domain_id):
    """Generate the next available domain_id for a protein.

    For PDB domains like 'e7tnxA3', increments trailing number -> 'e7tnxA4'.
    For UniProt domains like 'Q83C83_nD2', increments -> 'Q83C83_nD3'.
    Checks all existing domain IDs (including obsolete) for conflicts.
    """
    # PDB pattern
    m = re.match(r'^(e\w{4}[A-Za-z0-9]+?)(\d+)$', base_domain_id)
    if m:
        prefix = m.group(1)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT domain_id FROM ecod_commons.domains
                WHERE domain_id ~ %s
            """, (f'^{re.escape(prefix)}\\d+$',))
            existing = [r[0] for r in cur.fetchall()]
        max_num = int(m.group(2))
        for eid in existing:
            em = re.match(r'^' + re.escape(prefix) + r'(\d+)$', eid)
            if em:
                max_num = max(max_num, int(em.group(1)))
        return f"{prefix}{max_num + 1}"

    # UniProt _nD pattern
    m = re.match(r'^(.+_nD)(\d+)$', base_domain_id)
    if m:
        prefix = m.group(1)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT domain_id FROM ecod_commons.domains
                WHERE domain_id LIKE %s
            """, (f'{prefix}%',))
            existing = [r[0] for r in cur.fetchall()]
        max_num = int(m.group(2))
        for eid in existing:
            em = re.match(r'^' + re.escape(prefix) + r'(\d+)$', eid)
            if em:
                max_num = max(max_num, int(em.group(1)))
        return f"{prefix}{max_num + 1}"

    # UniProt _F1_nD pattern (with family number)
    m = re.match(r'^(.+_F\d+_nD)(\d+)$', base_domain_id)
    if m:
        prefix = m.group(1)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT domain_id FROM ecod_commons.domains
                WHERE domain_id LIKE %s
            """, (f'{prefix}%',))
            existing = [r[0] for r in cur.fetchall()]
        max_num = int(m.group(2))
        for eid in existing:
            em = re.match(r'^' + re.escape(prefix) + r'(\d+)$', eid)
            if em:
                max_num = max(max_num, int(em.group(1)))
        return f"{prefix}{max_num + 1}"

    return f"{base_domain_id}_2"


def analyze_helicase_domains(conn, cfg):
    """Analyze all domains in F:3930.1.1.1 using HMMER to classify as
    RIG-I_C (PF18119), Helicase_C (PF00271), or both."""
    source_f = cfg['source_f']
    pfam_accs = [RIGI_PFAM, HELICASE_PFAM]
    pfam_names = [RIGI_NAME, HELICASE_NAME]
    exclude_pdbs = cfg.get('exclude_pdbs', [])

    print(f"\n--- Analyzing domains in {source_f} (Helicase_C,RIG-I_C) ---")
    print(f"  HMMER: {RIGI_NAME} ({RIGI_PFAM}) + {HELICASE_NAME} ({HELICASE_PFAM})")
    print(f"  Exclude PDBs (already correct): {exclude_pdbs}")

    commons_domains = ops.get_commons_domains_in_fgroup(conn, source_f)
    rep_domains = ops.get_rep_domains_in_fgroup(conn, source_f)

    print(f"  Domains: {len(commons_domains)} commons, {len(rep_domains)} reps")

    split_plans = []
    counts = {'SPLIT': 0, 'RIGI_ONLY': 0, 'HELICASE_ONLY': 0, 'NO_HIT': 0, 'EXCLUDED': 0}

    for domain in commons_domains:
        domain_id = domain['domain_id']
        domain_range = domain['range_definition']
        domain_length = domain['sequence_length'] or 0
        is_rep = any(r['ecod_domain_id'] == domain_id for r in rep_domains)

        # Check if PDB is in exclude list
        pdb = domain_id[1:5] if domain_id.startswith('e') else None
        if pdb and pdb in exclude_pdbs:
            counts['EXCLUDED'] += 1
            continue

        # Get HMMER boundaries
        hmmer_hits = bm.get_hmmer_boundaries_from_db(conn, domain_id, pfam_accs)
        source = 'db'
        if not hmmer_hits:
            seq = bm.extract_domain_sequence(
                conn, domain_id, domain['protein_id'], domain_range)
            if seq:
                hmmer_hits = bm.run_hmmscan_for_domain(seq, pfam_names, domain_id, use_ga=True)
                source = 'hmmscan'
            else:
                source = 'no_seq'

        has_rigi = RIGI_PFAM in hmmer_hits
        has_helicase = HELICASE_PFAM in hmmer_hits

        products = []
        if has_rigi:
            hit = hmmer_hits[RIGI_PFAM]
            abs_result = bm.domain_local_to_absolute(
                hit['env_start'], hit['env_end'], domain_range)
            if abs_result:
                rng = bm.format_absolute_range(abs_result[0], abs_result[1])
                products.append({
                    'name': RIGI_NAME, 'pfam_acc': RIGI_PFAM,
                    'range': rng,
                    'length': hit['env_end'] - hit['env_start'] + 1,
                    'target_f': cfg['targets']['rigi_c']['f_group'],
                })

        if has_helicase:
            hit = hmmer_hits[HELICASE_PFAM]
            abs_result = bm.domain_local_to_absolute(
                hit['env_start'], hit['env_end'], domain_range)
            if abs_result:
                rng = bm.format_absolute_range(abs_result[0], abs_result[1])
                products.append({
                    'name': HELICASE_NAME, 'pfam_acc': HELICASE_PFAM,
                    'range': rng,
                    'length': hit['env_end'] - hit['env_start'] + 1,
                    'target_f': cfg['targets']['helicase_c']['f_group'],
                })

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
            'products': products,
            'valid': len(products) > 0,
        }

        n = len(products)
        if n == 2:
            status = "SPLIT"
            counts['SPLIT'] += 1
        elif n == 1:
            pname = products[0]['name']
            status = f"RECLASS({pname})"
            if pname == RIGI_NAME:
                counts['RIGI_ONLY'] += 1
            else:
                counts['HELICASE_ONLY'] += 1
        else:
            status = "NO_HIT"
            counts['NO_HIT'] += 1

        rep_flag = " [REP]" if is_rep else ""
        prod_strs = [f"{p['name']}:{p['range']}({p['length']}aa)" for p in products]
        print(f"  {domain_id}{rep_flag}: {domain_range} ({domain_length}aa) -> "
              f"{' + '.join(prod_strs) if prod_strs else '--'} [{status}] [{source}]")

        split_plans.append(plan)

    print(f"\n  Summary: {counts['SPLIT']} SPLIT, {counts['RIGI_ONLY']} RIG-I_C only, "
          f"{counts['HELICASE_ONLY']} Helicase_C only, {counts['NO_HIT']} NO_HIT, "
          f"{counts['EXCLUDED']} excluded")

    return split_plans


def execute_helicase_split(conn, cfg, split_plans, dry_run=True):
    """Execute the Helicase_C,RIG-I_C split.

    Domains with HMMER hits are split/reclassified to their target F-groups.
    NO_HIT domains (no RIG-I_C or Helicase_C detected) are moved to the .0
    pseudo-group in T:3930.1.1, preserving their original ranges.
    """
    source_f = cfg['source_f']
    pseudo_f = '3930.1.1.0'  # .0 pseudo-group for unclassifiable domains
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    justification = f"Curator change {cfg['id']}: {cfg['description']} [{timestamp}]"

    rigi_target = cfg['targets']['rigi_c']['f_group']
    helicase_target = cfg['targets']['helicase_c']['f_group']

    print(f"\n{'='*70}")
    print(f"Change {cfg['id']}: {cfg['description']}")
    print(f"Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")
    print(f"{'='*70}")
    print(f"  Source: {source_f}")
    print(f"  Targets: RIG-I_C -> {rigi_target}, Helicase_C -> {helicase_target}")
    print(f"  NO_HIT fallback: {pseudo_f}")

    results = {
        'domains_split': 0,
        'domains_reclassed': 0,
        'domains_to_pseudo': 0,
        'new_domains_created': 0,
        'errors': [],
    }

    for plan in split_plans:
        domain_id = plan['domain_id']
        products = plan['products']
        n_products = len(products)

        try:
            # --- NO_HIT: move to .0 pseudo-group ---
            if not plan['valid']:
                if dry_run:
                    print(f"  [DRY RUN] PSEUDO {domain_id}: "
                          f"{plan['original_range']} -> {pseudo_f}")
                    results['domains_to_pseudo'] += 1
                    continue

                ops.reassign_commons_domain_by_pk(
                    conn, plan['assignment_id'], pseudo_f,
                    justification=f"No RIG-I_C/Helicase_C hit: {justification}")
                print(f"  PSEUDO {domain_id} -> {pseudo_f}")
                results['domains_to_pseudo'] += 1
                conn.commit()
                continue

            # --- RECLASS: single product, just reassign ---
            if n_products == 1:
                prod = products[0]
                if dry_run:
                    print(f"  [DRY RUN] RECLASS {domain_id}: "
                          f"{prod['name']} -> {prod['target_f']}")
                    results['domains_reclassed'] += 1
                    continue

                ops.reassign_commons_domain_by_pk(
                    conn, plan['assignment_id'], prod['target_f'],
                    justification=f"Reclassified as {prod['name']}: {justification}")
                print(f"  RECLASS {domain_id} -> {prod['target_f']} ({prod['name']})")
                results['domains_reclassed'] += 1

                # Handle ecod_rep domain
                if plan['is_rep']:
                    rep = ops.get_domain_from_ecod_rep(conn, domain_id)
                    if rep:
                        ops.reassign_domain_fgroup(
                            conn, rep['uid'], prod['target_f'],
                            justification=f"Reclassified as {prod['name']}: {justification}")
                        print(f"  Reassigned rep {domain_id} -> {prod['target_f']}")

                conn.commit()
                continue

            # --- SPLIT: two products, deprecate-and-recreate ---
            if dry_run:
                print(f"  [DRY RUN] SPLIT {domain_id}:")
                for prod in products:
                    print(f"    {prod['name']}: {prod['range']} "
                          f"({prod['length']}aa) -> {prod['target_f']}")
                results['domains_split'] += 1
                results['new_domains_created'] += n_products
                continue

            # Handle ecod_rep domain
            if plan['is_rep']:
                rep = ops.get_domain_from_ecod_rep(conn, domain_id)
                if rep:
                    ops.delete_domain_from_ecod_rep(
                        conn, rep['uid'], domain_id,
                        justification=f"Split: {justification}")
                    print(f"  Deleted rep {domain_id} from ecod_rep")

            # Create split products
            new_pks = []
            for i, prod in enumerate(products):
                if i == 0:
                    new_domain_id = domain_id
                else:
                    new_domain_id = next_domain_id(conn, domain_id)

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
                    f"Split from {domain_id} ({prod['name']}): {justification}")
                new_pks.append(new_pk)
                results['new_domains_created'] += 1
                print(f"  Created {new_domain_id} (uid={new_ecod_uid}, "
                      f"{prod['name']}, {prod['range']}) -> {prod['target_f']}")

            # Obsolete original
            product_names = '/'.join(p['name'] for p in products)
            ops.obsolete_commons_domain(
                conn, plan['domain_pk'],
                reason=f"Split into {product_names}: {justification}",
                superseded_by_pk=new_pks[0] if new_pks else None)

            results['domains_split'] += 1
            conn.commit()

        except Exception as e:
            msg = f"Error processing {domain_id}: {e}"
            results['errors'].append(msg)
            logger.error(msg, exc_info=True)
            conn.rollback()

    # Deprecate source F-group
    if not dry_run:
        remaining_rep = ops.count_fgroup_members(conn, source_f, 'ecod_rep')
        remaining_commons = ops.count_fgroup_members(conn, source_f, 'ecod_commons')
        if remaining_rep == 0 and remaining_commons == 0:
            ops.deprecate_group(conn, source_f, 'F', justification=justification)
            print(f"  Deprecated F-group {source_f}")
            conn.commit()
        else:
            print(f"  Source {source_f} still has {remaining_rep} reps, "
                  f"{remaining_commons} commons - not deprecating")
    elif dry_run:
        print(f"  [DRY RUN] Would deprecate F-group {source_f}")

    print(f"\n  Results: {results['domains_split']} split, "
          f"{results['domains_reclassed']} reclassified, "
          f"{results['domains_to_pseudo']} to pseudo-group, "
          f"{results['new_domains_created']} new domains created")
    if results['errors']:
        for e in results['errors']:
            print(f"  ERROR: {e}")

    return results


def main():
    parser = argparse.ArgumentParser(
        description='Implement Helicase_C,RIG-I_C split (B2_5)')
    parser.add_argument('--dry-run', action='store_true', default=True)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--analyze-only', action='store_true')
    args = parser.parse_args()
    dry_run = not args.execute

    conn = ops.get_db_connection()
    try:
        cfg = HELICASE_RIGI_SPLIT
        split_plans = analyze_helicase_domains(conn, cfg)

        if args.analyze_only:
            return

        results = execute_helicase_split(conn, cfg, split_plans, dry_run)

    finally:
        conn.close()


if __name__ == '__main__':
    main()
