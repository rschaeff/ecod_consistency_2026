#!/usr/bin/env python3
"""
Pfam-evidence reconciliation for the 456 manual-rep "movers".

Goal: independently decide, with ecod_rep as authority, where each manual-rep
domain SHOULD sit at the F-group level -- using the stored Pfam-A v38.2 hmmscan
(ecod_commons.protein_pfam_hits) rather than trusting the v294 migration's
commons assignments.

For each domain:
  - parse its seqid range (possibly discontinuous)
  - for every Pfam hit on its protein, compute overlap with the domain residues
  - keep Pfams covering >= 60% of the DOMAIN length ("significant")
  - dominant = highest domain-coverage (tie-break: bitscore)
  - map the dominant Pfam to F-group(s) within the domain's T-group via cluster.pfam_acc
  - verdict: does the evidence point to the commons target (new_f), the current
    ecod_rep group (old_f), some other F-group, or is it unresolved?
"""
import csv, sys
import psycopg2, psycopg2.extras

MIN_FRAC = 0.60
CONN = dict(host="dione", port=45000, dbname="ecod_protein", user="ecod")  # password via ~/.pgpass

def parse_segs(rng):
    """'A:1-437' / '1-71,150-200' / 'A:1-71,A:90-120' -> [(1,437)] etc (seqid coords)."""
    segs = []
    for part in rng.split(','):
        part = part.strip()
        if not part:
            continue
        if ':' in part:
            part = part.split(':', 1)[1]
        if '-' in part.lstrip('-'):
            # split on last '-' to tolerate a leading sign (seqid should be positive though)
            i = part.rindex('-')
            a, b = part[:i], part[i+1:]
        else:
            a = b = part
        try:
            a, b = int(a), int(b)
        except ValueError:
            continue
        if a > b:
            a, b = b, a
        segs.append((a, b))
    return segs

def seg_len(segs):
    return sum(b - a + 1 for a, b in segs)

def overlap(segs, lo, hi):
    """residues of [lo,hi] (a Pfam envelope) covered by the domain segments."""
    tot = 0
    for a, b in segs:
        tot += max(0, min(b, hi) - max(a, lo) + 1)
    return tot

def main():
    cn = psycopg2.connect(**CONN)
    cur = cn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # 1. the 456 movers
    cur.execute("""
      WITH repless AS (
        SELECT c.id FROM ecod_rep.cluster c
        WHERE c.type='F' AND c.is_deprecated IS NOT TRUE
          AND NOT EXISTS (SELECT 1 FROM ecod_rep.domain d
             WHERE d.f_id=c.id AND (d.manual_rep OR d.provisional_manual_rep))
      ),
      cand AS (
        SELECT dom.id AS commons_did, dom.ecod_uid, dom.protein_id, dom.domain_id,
               dom.range_definition, dom.sequence_length, r.id AS commons_f
        FROM repless r
        JOIN ecod_commons.f_group_assignments fga ON fga.f_group_id=r.id
        JOIN ecod_commons.domains dom ON dom.id=fga.domain_id AND dom.is_obsolete IS NOT TRUE
        WHERE dom.is_manual_representative
      )
      SELECT cand.*, er.f_id AS old_f, er.t_id
      FROM cand JOIN ecod_rep.domain er ON er.ecod_uid=cand.ecod_uid
    """)
    movers = cur.fetchall()

    prot_ids = sorted({m['protein_id'] for m in movers})

    # 2. all Pfam hits for those proteins
    cur.execute("""
      SELECT protein_id, pfam_acc_short, pfam_name, env_from, env_to, bitscore
      FROM ecod_commons.protein_pfam_hits
      WHERE protein_id = ANY(%s)
    """, (prot_ids,))
    hits_by_prot = {}
    for h in cur.fetchall():
        hits_by_prot.setdefault(h['protein_id'], []).append(h)

    # 3. F-group -> pfam set, plus parent T and deprecation, for resolution
    cur.execute("""
      SELECT id, parent AS t_parent, pfam_acc, is_deprecated, name
      FROM ecod_rep.cluster WHERE type='F'
    """)
    fg_pfams, fg_parent, fg_dep, fg_name = {}, {}, {}, {}
    by_tgroup = {}   # t_id -> list of f_id
    for c in cur.fetchall():
        pf = set()
        if c['pfam_acc']:
            pf = {p.strip() for p in c['pfam_acc'].split(',') if p.strip()}
        fg_pfams[c['id']] = pf
        fg_parent[c['id']] = c['t_parent']
        fg_dep[c['id']] = c['is_deprecated']
        fg_name[c['id']] = c['name']
        by_tgroup.setdefault(c['t_parent'], []).append(c['id'])

    rows = []
    summ = {}
    for m in movers:
        segs = parse_segs(m['range_definition'])
        dlen = seg_len(segs) or (m['sequence_length'] or 0)
        hits = hits_by_prot.get(m['protein_id'], [])

        # best (max coverage) per Pfam short acc
        best = {}  # pfam_short -> (frac, bitscore, name)
        for h in hits:
            ov = overlap(segs, h['env_from'], h['env_to'])
            frac = ov / dlen if dlen else 0.0
            cur_best = best.get(h['pfam_acc_short'])
            if cur_best is None or frac > cur_best[0] or (frac == cur_best[0] and h['bitscore'] > cur_best[1]):
                best[h['pfam_acc_short']] = (frac, h['bitscore'], h['pfam_name'])

        significant = {p: v for p, v in best.items() if v[0] >= MIN_FRAC}
        # dominant = highest frac, tie-break bitscore
        dom_pf = None
        if significant:
            dom_pf = max(significant.items(), key=lambda kv: (kv[1][0], kv[1][1]))[0]

        old_f, new_f, t_id = m['old_f'], m['commons_f'], m['t_id']
        old_pf = fg_pfams.get(old_f, set())
        new_pf = fg_pfams.get(new_f, set())

        # which F-groups in this T-group carry the dominant Pfam?
        implied = []
        if dom_pf:
            for f in by_tgroup.get(t_id, []):
                if dom_pf in fg_pfams.get(f, set()):
                    implied.append(f)

        if dom_pf is None:
            verdict = 'no_dominant_pfam'
        else:
            in_new = dom_pf in new_pf
            in_old = dom_pf in old_pf
            if in_new and not in_old:
                verdict = 'supports_commons'
            elif in_old and not in_new:
                verdict = 'supports_old_ecod_rep'
            elif in_new and in_old:
                verdict = 'ambiguous_both'
            elif implied:
                verdict = 'points_to_other_fgroup'
            else:
                verdict = 'pfam_has_no_fgroup_here'

        summ[verdict] = summ.get(verdict, 0) + 1
        dv = best.get(dom_pf) if dom_pf else None
        rows.append(dict(
            ecod_uid=m['ecod_uid'], domain_id=m['domain_id'], t_id=t_id,
            old_f=old_f, old_f_pfam=','.join(sorted(old_pf)) or '',
            commons_f=new_f, new_f_pfam=','.join(sorted(new_pf)) or '',
            dom_len=dlen,
            dominant_pfam=dom_pf or '', dominant_name=(dv[2] if dv else ''),
            dominant_cov_pct=(round(dv[0]*100, 1) if dv else ''),
            dominant_bitscore=(dv[1] if dv else ''),
            n_significant_pfams=len(significant),
            verdict=verdict,
            pfam_implied_fgroups=';'.join(implied),
        ))

    out = "/home/rschaeff/work/ecod_consistency_2026/pfam_reconcile_movers_20260605.csv"
    with open(out, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"movers analyzed: {len(rows)}   (>=60% domain coverage threshold)")
    print(f"written: {out}\n")
    print("VERDICT SUMMARY")
    for k in sorted(summ, key=lambda k: -summ[k]):
        print(f"  {k:28s} {summ[k]:4d}")
    cn.close()

if __name__ == '__main__':
    main()
