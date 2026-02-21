#!/usr/bin/env python3
"""
Implement batch 2 extraction changes:
  B2_3b: ATP-grasp_6 extraction to new X-group (simple F-group move)
  B2_3a: Cyanophycin_syn extraction to new X-group (with domain split)

B2_3b must run before B2_3a because 3a split products go into the
ATP-grasp_6 F-group created by 3b.

Usage:
    python implement_batch2_extractions.py --dry-run
    python implement_batch2_extractions.py --execute
    python implement_batch2_extractions.py --execute --change B2_3b
    python implement_batch2_extractions.py --analyze-only  # HMMER analysis for 3a
"""

import argparse
import logging
import re
import sys
from datetime import datetime

import boundary_methods as bm
import curator_ops as ops
from change_definitions import REQUESTED_BY
from change_definitions_batch2 import (
    ATP_GRASP_6_EXTRACTION,
    CYANOPHYCIN_SYN_EXTRACTION,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)


# ============================================================
# Domain naming helpers
# ============================================================

def next_domain_id_for_protein(conn, base_domain_id):
    """Generate the next available domain_id for a protein.

    For PDB domains like 'e7lg5A4', increments the trailing number -> 'e7lg5A5'.
    For UniProt domains like 'Q83C83_nD2', increments -> 'Q83C83_nD3'.

    Checks ecod_commons.domains for conflicts (including obsolete entries).
    """
    # PDB pattern: e{pdb}{chain}{num}
    m = re.match(r'^(e\w{4}[A-Za-z0-9]+?)(\d+)$', base_domain_id)
    if m:
        prefix, num = m.group(1), int(m.group(2))
        # Find max existing number for this prefix
        with conn.cursor() as cur:
            cur.execute("""
                SELECT domain_id FROM ecod_commons.domains
                WHERE domain_id ~ %s
                ORDER BY domain_id
            """, (f'^{re.escape(prefix)}\\d+$',))
            existing = [r[0] for r in cur.fetchall()]
        max_num = num
        for eid in existing:
            em = re.match(r'^' + re.escape(prefix) + r'(\d+)$', eid)
            if em:
                max_num = max(max_num, int(em.group(1)))
        return f"{prefix}{max_num + 1}"

    # UniProt pattern: {uniprot}_nD{num} or {uniprot}_F1_nD{num}
    m = re.match(r'^(.+_nD)(\d+)$', base_domain_id)
    if m:
        prefix, num = m.group(1), int(m.group(2))
        with conn.cursor() as cur:
            cur.execute("""
                SELECT domain_id FROM ecod_commons.domains
                WHERE domain_id LIKE %s
            """, (f'{prefix}%',))
            existing = [r[0] for r in cur.fetchall()]
        max_num = num
        for eid in existing:
            em = re.match(r'^' + re.escape(prefix) + r'(\d+)$', eid)
            if em:
                max_num = max(max_num, int(em.group(1)))
        return f"{prefix}{max_num + 1}"

    # Fallback: append _2
    return f"{base_domain_id}_2"


# ============================================================
# B2_3b: ATP-grasp_6 extraction (simple F-group move)
# ============================================================

def execute_atp_grasp_extraction(conn, dry_run=True):
    """Extract F:2003.1.10.18 (ATP-grasp_6) to new X-group under a.17."""
    cfg = ATP_GRASP_6_EXTRACTION
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    justification = f"Curator change {cfg['id']}: {cfg['description']} [{timestamp}]"

    print(f"\n{'='*70}")
    print(f"Change {cfg['id']}: {cfg['description']}")
    print(f"Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")
    print(f"{'='*70}")

    source_f = cfg['source_f']
    source = ops.verify_fgroup_exists(conn, source_f)
    if not source or source['is_deprecated']:
        print(f"  ERROR: Source {source_f} not found or deprecated")
        return None

    rep_domains = ops.get_rep_domains_in_fgroup(conn, source_f)
    commons_count = ops.count_fgroup_members(conn, source_f, 'ecod_commons')
    print(f"  Source: {source_f} ({source['name']})")
    print(f"    Reps: {len(rep_domains)}, Commons: {commons_count}")

    # Step 1: Create new X/H/T hierarchy
    new_hierarchy = None
    if dry_run:
        print(f"  [DRY RUN] Would create X/H/T '{cfg['new_xgroup_name']}' under {cfg['a_group']}")
    else:
        from psycopg2.extras import RealDictCursor
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id::text AS x_id FROM ecod_rep.cluster
                WHERE type = 'X' AND name = %s AND is_deprecated = false
            """, (cfg['new_xgroup_name'],))
            existing_x = cur.fetchone()
        if existing_x:
            x_id = existing_x['x_id']
            new_hierarchy = {'x_id': x_id, 'h_id': f"{x_id}.1", 't_id': f"{x_id}.1.1"}
            print(f"  X/H/T already exists: X:{x_id} (reusing)")
        else:
            new_hierarchy = ops.create_xht_hierarchy(
                conn, cfg['new_xgroup_name'], cfg['a_group'], justification)
            conn.commit()
            print(f"  Created X:{new_hierarchy['x_id']} H:{new_hierarchy['h_id']} "
                  f"T:{new_hierarchy['t_id']}")

    new_t_id = new_hierarchy['t_id'] if new_hierarchy else 'NEW'

    # Step 2: Create new F-group
    target_f = None
    if dry_run:
        print(f"  [DRY RUN] Would create F-group '{cfg['new_xgroup_name']}' under T:{new_t_id}")
        target_f = f"{new_t_id}.NEW"
    else:
        from psycopg2.extras import RealDictCursor
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id::text AS f_id FROM ecod_rep.cluster
                WHERE parent = %s AND type = 'F' AND name = %s AND is_deprecated = false
            """, (new_t_id, cfg['new_xgroup_name']))
            existing = cur.fetchone()
        if existing:
            target_f = existing['f_id']
            print(f"  F-group {target_f} already exists, reusing")
        else:
            target_f, req_id = ops.create_fgroup(
                conn, new_t_id, name=cfg['new_xgroup_name'],
                pfam_acc=cfg['pfam_acc'], justification=justification)
            conn.commit()
            print(f"  Created F-group {target_f}")

    # Step 3: Move domains
    if dry_run:
        print(f"  [DRY RUN] Would move {len(rep_domains)} reps + {commons_count} commons "
              f"from {source_f} -> {target_f}")
    else:
        request_id = ops.create_change_request(
            conn, 'rename', 'F', original_id=source_f, new_id=target_f,
            new_name=f"Extract {source_f} -> {target_f}", justification=justification)
        ops.approve_change_request(conn, request_id)

        for domain in rep_domains:
            ops.reassign_domain_fgroup(conn, domain['uid'], target_f, request_id)

        count = ops.reassign_commons_domains(conn, source_f, target_f, justification)
        print(f"  Moved {len(rep_domains)} reps + {count} commons from {source_f} -> {target_f}")
        conn.commit()

    # Step 4: Deprecate source
    if dry_run:
        print(f"  [DRY RUN] Would deprecate F-group {source_f}")
    else:
        remaining = ops.count_fgroup_members(conn, source_f, 'ecod_rep')
        if remaining == 0:
            ops.deprecate_group(conn, source_f, 'F', justification=justification)
            print(f"  Deprecated F-group {source_f}")
            conn.commit()
        else:
            print(f"  WARNING: {source_f} still has {remaining} reps!")

    print(f"\n  Change {cfg['id']} {'preview' if dry_run else 'execution'} complete.")
    return target_f


# ============================================================
# B2_3a: Cyanophycin_syn extraction + domain split
# ============================================================

def _reference_split(domain_range, ref_boundary):
    """Split a domain range at a reference boundary (domain-local position).

    Given domain range 'A:1-203' and ref_boundary=162, produces:
      product1: 'A:1-162' (162aa)
      product2: 'A:163-203' (41aa)

    Handles multi-segment ranges by walking through segments.
    Returns list of (range_str, length) tuples.
    """
    segments = []
    for part in domain_range.split(','):
        part = part.strip()
        m = re.match(r'([A-Za-z0-9]*):?(\d+)-(\d+)', part)
        if m:
            chain = m.group(1) if m.group(1) else None
            segments.append((chain, int(m.group(2)), int(m.group(3))))

    if not segments:
        return [(None, 0), (None, 0)]

    # Walk through segments to find absolute position of ref_boundary
    residues_consumed = 0
    split_chain = None
    split_abs_pos = None
    for chain, start, end in segments:
        seg_len = end - start + 1
        if residues_consumed + seg_len >= ref_boundary:
            offset = ref_boundary - residues_consumed
            split_abs_pos = start + offset - 1  # absolute position of last residue in product 1
            split_chain = chain
            break
        residues_consumed += seg_len

    if split_abs_pos is None:
        return [(domain_range, sum(e - s + 1 for _, s, e in segments)), (None, 0)]

    # Build product 1: domain start to split point
    p1_parts = []
    p1_len = 0
    for chain, start, end in segments:
        if chain == split_chain and end >= split_abs_pos:
            p1_end = min(end, split_abs_pos)
            prefix = f"{chain}:" if chain else ""
            p1_parts.append(f"{prefix}{start}-{p1_end}")
            p1_len += p1_end - start + 1
            break
        else:
            prefix = f"{chain}:" if chain else ""
            p1_parts.append(f"{prefix}{start}-{end}")
            p1_len += end - start + 1

    # Build product 2: split point + 1 to domain end
    p2_parts = []
    p2_len = 0
    past_split = False
    for chain, start, end in segments:
        if not past_split:
            if chain == split_chain and end >= split_abs_pos:
                if split_abs_pos + 1 <= end:
                    prefix = f"{chain}:" if chain else ""
                    p2_parts.append(f"{prefix}{split_abs_pos + 1}-{end}")
                    p2_len += end - split_abs_pos
                past_split = True
        else:
            prefix = f"{chain}:" if chain else ""
            p2_parts.append(f"{prefix}{start}-{end}")
            p2_len += end - start + 1

    p1_range = ','.join(p1_parts) if p1_parts else None
    p2_range = ','.join(p2_parts) if p2_parts else None

    return [(p1_range, p1_len), (p2_range, p2_len)]


def analyze_cyanophycin_domains(conn, cfg, atp_grasp_f):
    """Analyze domains in F:2007.3.1.5 for Cyanophycin/ATP-grasp split.

    Uses HMMER first, falls back to reference boundary (domain-local
    position 162/163) when HMMER can't detect the short ATP-grasp portion.
    """
    source_f = cfg['source_f']
    pfam_accs = [cfg['split_pfams']['cyanophycin'], cfg['split_pfams']['atp_grasp']]
    pfam_names = ['Cyanophycin_syn', 'ATP-grasp_6']

    # Reference boundary: domain-local position where cyanophycin ends
    ref_split = cfg['reference_split']
    # Parse reference cyanophycin range to get its length (= split boundary)
    ref_cyanophycin_range = ref_split['cyanophycin']
    m = re.match(r'[A-Za-z]*:?(\d+)-(\d+)', ref_cyanophycin_range)
    ref_boundary = int(m.group(2)) - int(m.group(1)) + 1  # 162

    print(f"\n--- Analyzing domains in {source_f} for split ---")
    print(f"  HMMER: {pfam_names[0]} ({pfam_accs[0]}) + {pfam_names[1]} ({pfam_accs[1]})")
    print(f"  Reference boundary: domain-local position {ref_boundary}")

    commons_domains = ops.get_commons_domains_in_fgroup(conn, source_f)
    rep_domains = ops.get_rep_domains_in_fgroup(conn, source_f)

    print(f"  Domains: {len(commons_domains)} commons, {len(rep_domains)} reps")

    split_plans = []

    for domain in commons_domains:
        domain_id = domain['domain_id']
        domain_range = domain['range_definition']
        domain_length = domain['sequence_length'] or 0
        is_rep = any(r['ecod_domain_id'] == domain_id for r in rep_domains)

        # Try HMMER first for both Pfams
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

        both_detected = (pfam_accs[0] in hmmer_hits and pfam_accs[1] in hmmer_hits)

        products = []
        if both_detected:
            # Use HMMER boundaries for both products
            for pfam_key, pfam_acc, pfam_name, target_f in [
                ('cyanophycin', pfam_accs[0], pfam_names[0], None),
                ('atp_grasp', pfam_accs[1], pfam_names[1], atp_grasp_f),
            ]:
                hit = hmmer_hits[pfam_acc]
                abs_result = bm.domain_local_to_absolute(
                    hit['env_start'], hit['env_end'], domain_range)
                if abs_result:
                    rng = bm.format_absolute_range(abs_result[0], abs_result[1])
                    length = hit['env_end'] - hit['env_start'] + 1
                    products.append({
                        'name': pfam_name, 'pfam_key': pfam_key,
                        'pfam_acc': pfam_acc, 'range': rng,
                        'length': length, 'target_f': target_f,
                    })
            source = f'{source}+hmmer'
        else:
            # Use reference boundary - compute the actual sequence length
            seq = bm.extract_domain_sequence(
                conn, domain_id, domain['protein_id'], domain_range)
            seq_len = len(seq) if seq else domain_length

            if seq_len >= ref_boundary + 10:
                # Domain is long enough to split at reference boundary
                (p1_range, p1_len), (p2_range, p2_len) = _reference_split(
                    domain_range, ref_boundary)
                if p1_range and p2_range and p1_len > 0 and p2_len > 0:
                    products = [
                        {'name': 'Cyanophycin_syn', 'pfam_key': 'cyanophycin',
                         'pfam_acc': pfam_accs[0], 'range': p1_range,
                         'length': p1_len, 'target_f': None},
                        {'name': 'ATP-grasp_6', 'pfam_key': 'atp_grasp',
                         'pfam_acc': pfam_accs[1], 'range': p2_range,
                         'length': p2_len, 'target_f': atp_grasp_f},
                    ]
                    source = f'{source}+ref_boundary'
                else:
                    source = f'{source}+ref_fail'
            elif seq_len > 0:
                # Domain too short to split - just reclassify as cyanophycin
                products = [
                    {'name': 'Cyanophycin_syn', 'pfam_key': 'cyanophycin',
                     'pfam_acc': pfam_accs[0], 'range': domain_range,
                     'length': seq_len, 'target_f': None},
                ]
                source = f'{source}+reclass_only'

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
        elif n == 1:
            status = f"RECLASS({products[0]['name']})"
        else:
            status = "NO_HIT"

        rep_flag = " [REP]" if is_rep else ""
        prod_strs = [f"{p['name']}:{p['range']}({p['length']}aa)" for p in products]
        print(f"  {domain_id}{rep_flag}: {domain_range} ({domain_length}aa) -> "
              f"{' + '.join(prod_strs) if prod_strs else '--'} [{status}] [{source}]")

        split_plans.append(plan)

    n_split = sum(1 for p in split_plans if len(p['products']) == 2)
    n_reclass = sum(1 for p in split_plans if len(p['products']) == 1)
    n_nohit = sum(1 for p in split_plans if not p['valid'])
    print(f"\n  Summary: {n_split} SPLIT, {n_reclass} RECLASS, {n_nohit} NO_HIT")

    return split_plans


def execute_cyanophycin_extraction(conn, cfg, atp_grasp_f, split_plans, dry_run=True):
    """Extract Cyanophycin_syn to new X-group and split domains."""
    source_f = cfg['source_f']
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    justification = f"Curator change {cfg['id']}: {cfg['description']} [{timestamp}]"

    print(f"\n{'='*70}")
    print(f"Change {cfg['id']}: {cfg['description']}")
    print(f"Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")
    print(f"{'='*70}")

    # Step 1: Create new X/H/T for Cyanophycin_syn
    cyanophycin_t = None
    if dry_run:
        print(f"  [DRY RUN] Would create X/H/T '{cfg['new_xgroup_name']}' under {cfg['a_group']}")
        cyanophycin_t = 'NEW'
    else:
        from psycopg2.extras import RealDictCursor
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id::text AS x_id FROM ecod_rep.cluster
                WHERE type = 'X' AND name = %s AND is_deprecated = false
            """, (cfg['new_xgroup_name'],))
            existing_x = cur.fetchone()
        if existing_x:
            x_id = existing_x['x_id']
            cyanophycin_t = f"{x_id}.1.1"
            print(f"  X/H/T already exists: X:{x_id} (reusing)")
        else:
            hierarchy = ops.create_xht_hierarchy(
                conn, cfg['new_xgroup_name'], cfg['a_group'], justification)
            cyanophycin_t = hierarchy['t_id']
            conn.commit()
            print(f"  Created X:{hierarchy['x_id']} T:{cyanophycin_t}")

    # Step 2: Create F-group for Cyanophycin_syn
    cyanophycin_f = None
    if dry_run:
        print(f"  [DRY RUN] Would create F-group '{cfg['new_xgroup_name']}' under T:{cyanophycin_t}")
        cyanophycin_f = f"{cyanophycin_t}.NEW"
    else:
        from psycopg2.extras import RealDictCursor
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id::text AS f_id FROM ecod_rep.cluster
                WHERE parent = %s AND type = 'F' AND name = %s AND is_deprecated = false
            """, (cyanophycin_t, cfg['new_xgroup_name']))
            existing = cur.fetchone()
        if existing:
            cyanophycin_f = existing['f_id']
            print(f"  F-group {cyanophycin_f} already exists, reusing")
        else:
            cyanophycin_f, req_id = ops.create_fgroup(
                conn, cyanophycin_t, name=cfg['new_xgroup_name'],
                pfam_acc=cfg['pfam_acc'], justification=justification)
            conn.commit()
            print(f"  Created F-group {cyanophycin_f}")

    # Set cyanophycin target in split plans
    for plan in split_plans:
        for prod in plan['products']:
            if prod['pfam_key'] == 'cyanophycin':
                prod['target_f'] = cyanophycin_f

    # Step 3: Process each domain
    results = {
        'domains_processed': 0,
        'domains_skipped': 0,
        'new_domains_created': 0,
        'errors': [],
    }

    rep_domains = ops.get_rep_domains_in_fgroup(conn, source_f)

    for plan in split_plans:
        if not plan['valid']:
            print(f"  SKIP {plan['domain_id']}: no HMMER hits")
            results['domains_skipped'] += 1
            continue

        products = plan['products']
        domain_id = plan['domain_id']
        n_products = len(products)

        try:
            if dry_run:
                label = "SPLIT" if n_products > 1 else "RECLASS"
                print(f"  [DRY RUN] {label} {domain_id}:")
                for prod in products:
                    print(f"    {prod['name']}: {prod['range']} ({prod['length']}aa) -> {prod['target_f']}")
                results['domains_processed'] += 1
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
            # N-terminal product reuses original domain_id
            # C-terminal product gets next available domain_id
            for i, prod in enumerate(products):
                if i == 0:
                    new_domain_id = domain_id  # N-terminal reuses original
                else:
                    new_domain_id = next_domain_id_for_protein(conn, domain_id)

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
            ops.obsolete_commons_domain(
                conn, plan['domain_pk'],
                reason=f"Split into {'/'.join(p['name'] for p in products)}: {justification}",
                superseded_by_pk=new_pks[0] if new_pks else None)

            results['domains_processed'] += 1
            conn.commit()

        except Exception as e:
            msg = f"Error splitting {domain_id}: {e}"
            results['errors'].append(msg)
            logger.error(msg, exc_info=True)
            conn.rollback()

    # Step 4: Deprecate source F-group
    if not dry_run and results['domains_skipped'] == 0:
        remaining = ops.count_fgroup_members(conn, source_f, 'ecod_rep')
        if remaining == 0:
            ops.deprecate_group(conn, source_f, 'F', justification=justification)
            print(f"  Deprecated F-group {source_f}")
            conn.commit()
        else:
            print(f"  Source {source_f} still has {remaining} reps, not deprecating")
    elif dry_run:
        print(f"  [DRY RUN] Would deprecate F-group {source_f}")

    print(f"\n  Results: {results['domains_processed']} processed, "
          f"{results['domains_skipped']} skipped, "
          f"{results['new_domains_created']} new domains")
    if results['errors']:
        print(f"  ERRORS: {results['errors']}")

    return results


# ============================================================
# Verification
# ============================================================

def verify_b2_3b(conn):
    """Verify ATP-grasp_6 extraction."""
    cfg = ATP_GRASP_6_EXTRACTION
    print(f"\n--- Verification: {cfg['id']} ---")

    source = ops.verify_fgroup_exists(conn, cfg['source_f'])
    if source:
        print(f"  Source {cfg['source_f']}: {'DEPRECATED' if source['is_deprecated'] else 'ACTIVE'}")

    # Find the new F-group by name
    with conn.cursor() as cur:
        cur.execute("""
            SELECT c.id::text, c.name, c.pfam_acc, c.parent::text
            FROM ecod_rep.cluster c
            WHERE c.name = %s AND c.type = 'F' AND c.is_deprecated = false
        """, (cfg['new_xgroup_name'],))
        for row in cur.fetchall():
            count = ops.count_fgroup_members(conn, row[0], 'ecod_commons')
            reps = len(ops.get_rep_domains_in_fgroup(conn, row[0]))
            print(f"  Target F:{row[0]} ({row[1]}): reps={reps}, commons={count}")


def verify_b2_3a(conn):
    """Verify Cyanophycin_syn extraction + split."""
    cfg = CYANOPHYCIN_SYN_EXTRACTION
    print(f"\n--- Verification: {cfg['id']} ---")

    source = ops.verify_fgroup_exists(conn, cfg['source_f'])
    if source:
        print(f"  Source {cfg['source_f']}: {'DEPRECATED' if source['is_deprecated'] else 'ACTIVE'}")

    with conn.cursor() as cur:
        cur.execute("""
            SELECT c.id::text, c.name, c.pfam_acc, c.parent::text
            FROM ecod_rep.cluster c
            WHERE c.name = %s AND c.type = 'F' AND c.is_deprecated = false
        """, (cfg['new_xgroup_name'],))
        for row in cur.fetchall():
            count = ops.count_fgroup_members(conn, row[0], 'ecod_commons')
            print(f"  Cyanophycin F:{row[0]}: {count} commons")

    # Check ATP-grasp_6 gained domains
    with conn.cursor() as cur:
        cur.execute("""
            SELECT c.id::text, c.name
            FROM ecod_rep.cluster c
            WHERE c.name = 'ATP-grasp_6' AND c.type = 'F' AND c.is_deprecated = false
        """)
        for row in cur.fetchall():
            count = ops.count_fgroup_members(conn, row[0], 'ecod_commons')
            print(f"  ATP-grasp F:{row[0]}: {count} commons (includes 3b + 3a split products)")


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description='Implement batch 2 extraction changes (B2_3a, B2_3b)')
    parser.add_argument('--dry-run', action='store_true', default=True)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--change', type=str, default=None,
                        help='Execute only B2_3a or B2_3b')
    parser.add_argument('--analyze-only', action='store_true',
                        help='Only analyze HMMER hits for B2_3a')
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    dry_run = not args.execute

    conn = ops.get_db_connection()
    try:
        if args.verify_only:
            if not args.change or args.change == 'B2_3b':
                verify_b2_3b(conn)
            if not args.change or args.change == 'B2_3a':
                verify_b2_3a(conn)
            return

        # B2_3b must run first
        atp_grasp_f = None
        if not args.change or args.change == 'B2_3b':
            atp_grasp_f = execute_atp_grasp_extraction(conn, dry_run)
            if not dry_run:
                verify_b2_3b(conn)

        # B2_3a needs the ATP-grasp_6 F-group from 3b
        if not args.change or args.change == 'B2_3a':
            # Find ATP-grasp_6 F-group if not just created
            if atp_grasp_f is None or dry_run:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT id::text FROM ecod_rep.cluster
                        WHERE name = 'ATP-grasp_6' AND type = 'F'
                          AND is_deprecated = false
                        ORDER BY id::text DESC LIMIT 1
                    """)
                    row = cur.fetchone()
                    if row:
                        atp_grasp_f = row[0]
                    else:
                        atp_grasp_f = 'PENDING_3B'

            print(f"\n  ATP-grasp_6 target F-group: {atp_grasp_f}")

            cfg = CYANOPHYCIN_SYN_EXTRACTION
            split_plans = analyze_cyanophycin_domains(conn, cfg, atp_grasp_f)

            if args.analyze_only:
                return

            results = execute_cyanophycin_extraction(
                conn, cfg, atp_grasp_f, split_plans, dry_run)

            if not dry_run:
                verify_b2_3a(conn)

    finally:
        conn.close()


if __name__ == '__main__':
    main()
