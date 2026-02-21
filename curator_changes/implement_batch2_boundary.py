#!/usr/bin/env python3
"""
Implement batch 2 boundary fix:
  B2_4: KH_domain-like / MMR_HSR1 boundary correction in Der GTPase structures.

Shift the MMR/KH boundary ~35 residues C-terminal for 17 PDB domain pairs.
Uses HMMER (PF14714 KH_dom-like, PF01926 MMR_HSR1) to find the correct
KH start position, then extends MMR to cover the gap.

All 34 domains are ecod_commons only (no ecod_rep entries).
Each domain is deprecated and recreated with the corrected range.

Usage:
    python implement_batch2_boundary.py --dry-run
    python implement_batch2_boundary.py --execute
    python implement_batch2_boundary.py --analyze-only
"""

import argparse
import logging
import re
import sys
from datetime import datetime

import boundary_methods as bm
import curator_ops as ops
from change_definitions import REQUESTED_BY
from change_definitions_batch2 import KH_DOMAIN_BOUNDARY_FIX

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)


def analyze_boundary_pairs(conn, cfg):
    """Analyze all 17 KH/MMR domain pairs using HMMER to find correct boundaries."""
    pairs = cfg['pairs']
    kh_fgroup = cfg['kh_f_group']
    mmr_fgroup = cfg['mmr_f_group']

    # Pfam accessions and names
    kh_pfam = 'PF14714'
    mmr_pfam = 'PF01926'
    kh_name = 'KH_dom-like'
    mmr_name = 'MMR_HSR1'

    print(f"\n--- Analyzing {len(pairs)} KH/MMR domain pairs ---")
    print(f"  KH F-group: {kh_fgroup} ({kh_name}, {kh_pfam})")
    print(f"  MMR F-group: {mmr_fgroup} ({mmr_name}, {mmr_pfam})")
    print(f"  Reference: {cfg['reference']['domain']} "
          f"MMR={cfg['reference']['mmr_range']} KH={cfg['reference']['kh_range']}")

    plans = []

    for kh_id, mmr_id in pairs:
        # Look up both domains
        kh_info = ops.get_commons_assignment(conn, kh_id)
        mmr_info = ops.get_commons_assignment(conn, mmr_id)

        if not kh_info:
            print(f"  WARNING: KH domain {kh_id} not found, skipping pair")
            continue
        if not mmr_info:
            print(f"  WARNING: MMR domain {mmr_id} not found, skipping pair")
            continue

        kh_range = kh_info['range_definition']
        kh_len = kh_info['sequence_length'] or 0
        mmr_range = mmr_info['range_definition']
        mmr_len = mmr_info['sequence_length'] or 0

        # Run hmmscan on the KH domain to find where KH_dom-like actually starts
        kh_seq = bm.extract_domain_sequence(conn, kh_id)
        kh_hmmer = {}
        if kh_seq:
            kh_hmmer = bm.run_hmmscan_for_domain(kh_seq, [kh_name], kh_id)

        # Also run hmmscan on the MMR domain to find where MMR_HSR1 actually ends
        mmr_seq = bm.extract_domain_sequence(conn, mmr_id)
        mmr_hmmer = {}
        if mmr_seq:
            mmr_hmmer = bm.run_hmmscan_for_domain(mmr_seq, [mmr_name], mmr_id)

        # Determine new boundary from KH HMMER hit
        new_kh_start_local = None
        new_kh_range = None
        new_kh_len = None
        new_mmr_range = None
        new_mmr_len = None

        kh_hit = kh_hmmer.get(kh_pfam)
        if kh_hit:
            # KH HMMER envelope starts at position kh_hit['env_start'] in the
            # current KH domain sequence. Convert to absolute coordinates.
            kh_abs = bm.domain_local_to_absolute(
                kh_hit['env_start'], kh_hit['env_end'], kh_range)
            if kh_abs:
                new_kh_start_abs = kh_abs[0]  # (chain, position)
                new_kh_end_abs = kh_abs[1]
                new_kh_range = bm.format_absolute_range(new_kh_start_abs, new_kh_end_abs)
                new_kh_len = kh_hit['env_end'] - kh_hit['env_start'] + 1

                # MMR extends from its current start to one residue before new KH start
                new_mmr_end_pos = new_kh_start_abs[1] - 1
                mmr_segments = _parse_range(mmr_range)
                if mmr_segments:
                    first_chain = mmr_segments[0][0]
                    mmr_start = mmr_segments[0][1]
                    # Handle simple single-segment case
                    prefix = f"{first_chain}:" if first_chain else ""
                    new_mmr_range = f"{prefix}{mmr_start}-{new_mmr_end_pos}"
                    new_mmr_len = new_mmr_end_pos - mmr_start + 1

                    # For multi-segment MMR ranges, preserve early segments
                    # and extend the last one (or add a new continuation segment)
                    if len(mmr_segments) > 1:
                        new_mmr_parts = []
                        for chain, start, end in mmr_segments:
                            p = f"{chain}:{start}-{end}" if chain else f"{start}-{end}"
                            new_mmr_parts.append(p)
                        last_chain, last_start, last_end = mmr_segments[-1]
                        if last_end < new_mmr_end_pos:
                            # Extend last segment to cover the new boundary
                            p = f"{last_chain}:{last_start}-{new_mmr_end_pos}" if last_chain else f"{last_start}-{new_mmr_end_pos}"
                            new_mmr_parts[-1] = p
                        new_mmr_range = ','.join(new_mmr_parts)
                        new_mmr_len = sum(
                            _seg_len(s) for s in new_mmr_range.split(','))

        plan = {
            'kh_id': kh_id,
            'mmr_id': mmr_id,
            'kh_domain_pk': kh_info['domain_pk'],
            'mmr_domain_pk': mmr_info['domain_pk'],
            'kh_ecod_uid': kh_info['ecod_uid'],
            'mmr_ecod_uid': mmr_info['ecod_uid'],
            'kh_protein_id': kh_info.get('protein_id'),
            'mmr_protein_id': mmr_info.get('protein_id'),
            'old_kh_range': kh_range,
            'old_kh_len': kh_len,
            'old_mmr_range': mmr_range,
            'old_mmr_len': mmr_len,
            'new_kh_range': new_kh_range,
            'new_kh_len': new_kh_len,
            'new_mmr_range': new_mmr_range,
            'new_mmr_len': new_mmr_len,
            'kh_fgroup': kh_fgroup,
            'mmr_fgroup': mmr_fgroup,
            'valid': new_kh_range is not None and new_mmr_range is not None,
        }

        if plan['valid']:
            delta_kh = kh_len - new_kh_len if new_kh_len else 0
            delta_mmr = (new_mmr_len or 0) - mmr_len
            print(f"  {kh_id}/{mmr_id}: "
                  f"KH {kh_range}({kh_len}aa) -> {new_kh_range}({new_kh_len}aa) [{-delta_kh:+d}] | "
                  f"MMR {mmr_range}({mmr_len}aa) -> {new_mmr_range}({new_mmr_len}aa) [{delta_mmr:+d}]")
        else:
            print(f"  {kh_id}/{mmr_id}: HMMER failed to determine boundary")

        plans.append(plan)

    n_valid = sum(1 for p in plans if p['valid'])
    print(f"\n  Valid plans: {n_valid}/{len(plans)}")
    return plans


def _parse_range(range_str):
    """Parse range string to list of (chain, start, end) tuples."""
    segments = []
    for part in range_str.split(','):
        part = part.strip()
        # Try chain:start-end first (chain is letters only)
        m = re.match(r'([A-Za-z]+):(\d+)-(\d+)', part)
        if m:
            segments.append((m.group(1), int(m.group(2)), int(m.group(3))))
            continue
        # Then try start-end (no chain)
        m = re.match(r'(\d+)-(\d+)', part)
        if m:
            segments.append((None, int(m.group(1)), int(m.group(2))))
    return segments


def _seg_len(seg_str):
    """Compute length of a range segment like 'A:10-50' or '10-50'."""
    seg_str = seg_str.strip()
    m = re.match(r'[A-Za-z]+:(\d+)-(\d+)', seg_str)
    if m:
        return int(m.group(2)) - int(m.group(1)) + 1
    m = re.match(r'(\d+)-(\d+)', seg_str)
    if m:
        return int(m.group(2)) - int(m.group(1)) + 1
    return 0


def execute_boundary_fixes(conn, plans, dry_run=True):
    """Execute boundary corrections for all valid plans."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    cfg = KH_DOMAIN_BOUNDARY_FIX
    justification = f"Curator change {cfg['id']}: {cfg['description']} [{timestamp}]"

    print(f"\n{'='*70}")
    print(f"Change {cfg['id']}: {cfg['description']}")
    print(f"Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")
    print(f"{'='*70}")

    results = {
        'pairs_processed': 0,
        'domains_updated': 0,
        'errors': [],
    }

    for plan in plans:
        if not plan['valid']:
            print(f"  SKIP {plan['kh_id']}/{plan['mmr_id']}: no valid boundary")
            continue

        try:
            if dry_run:
                print(f"  [DRY RUN] {plan['kh_id']}: {plan['old_kh_range']} -> "
                      f"{plan['new_kh_range']} ({plan['new_kh_len']}aa)")
                print(f"  [DRY RUN] {plan['mmr_id']}: {plan['old_mmr_range']} -> "
                      f"{plan['new_mmr_range']} ({plan['new_mmr_len']}aa)")
                results['pairs_processed'] += 1
                results['domains_updated'] += 2
                continue

            # Deprecate-and-recreate KH domain
            new_kh_pk, new_kh_uid = ops.deprecate_and_recreate_domain(
                conn, plan['kh_domain_pk'],
                plan['new_kh_range'], plan['new_kh_len'],
                plan['kh_fgroup'], justification)
            print(f"  {plan['kh_id']}: {plan['old_kh_range']} -> "
                  f"{plan['new_kh_range']} (uid={new_kh_uid})")

            # Deprecate-and-recreate MMR domain
            new_mmr_pk, new_mmr_uid = ops.deprecate_and_recreate_domain(
                conn, plan['mmr_domain_pk'],
                plan['new_mmr_range'], plan['new_mmr_len'],
                plan['mmr_fgroup'], justification)
            print(f"  {plan['mmr_id']}: {plan['old_mmr_range']} -> "
                  f"{plan['new_mmr_range']} (uid={new_mmr_uid})")

            results['pairs_processed'] += 1
            results['domains_updated'] += 2
            conn.commit()

        except Exception as e:
            msg = f"Error fixing {plan['kh_id']}/{plan['mmr_id']}: {e}"
            results['errors'].append(msg)
            logger.error(msg, exc_info=True)
            conn.rollback()

    print(f"\n  Results: {results['pairs_processed']} pairs processed, "
          f"{results['domains_updated']} domains updated")
    if results['errors']:
        for e in results['errors']:
            print(f"  ERROR: {e}")

    return results


def main():
    parser = argparse.ArgumentParser(
        description='Implement KH_domain-like boundary fix (B2_4)')
    parser.add_argument('--dry-run', action='store_true', default=True)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--analyze-only', action='store_true')
    args = parser.parse_args()
    dry_run = not args.execute

    conn = ops.get_db_connection()
    try:
        cfg = KH_DOMAIN_BOUNDARY_FIX
        plans = analyze_boundary_pairs(conn, cfg)

        if args.analyze_only:
            return

        results = execute_boundary_fixes(conn, plans, dry_run)

    finally:
        conn.close()


if __name__ == '__main__':
    main()
