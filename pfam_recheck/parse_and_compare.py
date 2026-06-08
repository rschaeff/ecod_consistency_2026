#!/usr/bin/env python3
"""
Re-derive the mover verdicts from a FRESH hmmscan --cut_ga run (full protein
sequence), applying current policy: TOP HIT PER REGION (resolve overlapping
family hits, keep best-scoring), then >=60%-of-domain overlap -> dominant Pfam
-> F-group -> verdict. Compare against the stored-protein_pfam_hits result.
"""
import csv, re, sys
import psycopg2, psycopg2.extras

MIN_FRAC = 0.60
OVERLAP_KILL = 0.50   # a lower-scoring hit overlapping a kept hit by >=50% of its own length is dropped
WD = "/home/rschaeff/work/ecod_consistency_2026"
DOMTBL = f"{WD}/pfam_recheck/mover_pfam.domtbl"
OLDCSV = f"{WD}/pfam_reconcile_movers_20260605.csv"
CONN = dict(host="dione", port=45000, dbname="ecod_protein", user="ecod")

def parse_segs(rng):
    segs = []
    for part in rng.split(','):
        part = part.strip()
        if not part:
            continue
        if ':' in part:
            part = part.split(':', 1)[1]
        if '-' in part.lstrip('-'):
            i = part.rindex('-'); a, b = part[:i], part[i+1:]
        else:
            a = b = part
        try:
            a, b = int(a), int(b)
        except ValueError:
            continue
        if a > b: a, b = b, a
        segs.append((a, b))
    return segs

def seg_len(segs): return sum(b-a+1 for a,b in segs)
def overlap(segs, lo, hi): return sum(max(0, min(b,hi)-max(a,lo)+1) for a,b in segs)

def load_domtbl(path):
    """protein_id(str) -> list of {pf_short, pf_name, score, ef, et} after top-hit-per-region resolution."""
    raw = {}
    with open(path) as fh:
        for line in fh:
            if line.startswith('#') or not line.strip():
                continue
            f = line.split()
            pf_name, pf_acc, query = f[0], f[1], f[3]
            score = float(f[13]); ef, et = int(f[19]), int(f[20])
            raw.setdefault(query, []).append(
                dict(pf_short=pf_acc.split('.')[0], pf_name=pf_name, score=score, ef=ef, et=et))
    resolved = {}
    for q, hits in raw.items():
        kept = []
        for h in sorted(hits, key=lambda x: -x['score']):
            hlen = h['et'] - h['ef'] + 1
            drop = False
            for k in kept:
                inter = min(h['et'], k['et']) - max(h['ef'], k['ef']) + 1
                if inter > 0 and inter >= OVERLAP_KILL * hlen:
                    drop = True; break
            if not drop:
                kept.append(h)
        resolved[q] = kept
    return resolved

def main():
    hits_by_prot = load_domtbl(DOMTBL)

    cn = psycopg2.connect(**CONN)
    cur = cn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
      WITH repless AS (
        SELECT c.id FROM ecod_rep.cluster c
        WHERE c.type='F' AND c.is_deprecated IS NOT TRUE
          AND NOT EXISTS (SELECT 1 FROM ecod_rep.domain d
             WHERE d.f_id=c.id AND (d.manual_rep OR d.provisional_manual_rep))
      ),
      cand AS (
        SELECT dom.ecod_uid, dom.protein_id, dom.domain_id, dom.range_definition,
               dom.sequence_length, r.id AS commons_f
        FROM repless r JOIN ecod_commons.f_group_assignments fga ON fga.f_group_id=r.id
        JOIN ecod_commons.domains dom ON dom.id=fga.domain_id AND dom.is_obsolete IS NOT TRUE
        WHERE dom.is_manual_representative
      )
      SELECT cand.*, er.f_id AS old_f, er.t_id
      FROM cand JOIN ecod_rep.domain er ON er.ecod_uid=cand.ecod_uid
    """)
    movers = cur.fetchall()

    cur.execute("SELECT id, parent AS t_parent, pfam_acc FROM ecod_rep.cluster WHERE type='F'")
    fg_pfams, by_tgroup = {}, {}
    for c in cur.fetchall():
        pf = {p.strip() for p in (c['pfam_acc'] or '').split(',') if p.strip()}
        fg_pfams[c['id']] = pf
        by_tgroup.setdefault(c['t_parent'], []).append(c['id'])
    cn.close()

    new_verdict = {}
    fresh_rows = []
    for m in movers:
        segs = parse_segs(m['range_definition'])
        dlen = seg_len(segs) or (m['sequence_length'] or 0)
        best = {}
        for h in hits_by_prot.get(str(m['protein_id']), []):
            ov = overlap(segs, h['ef'], h['et']); frac = ov/dlen if dlen else 0
            cb = best.get(h['pf_short'])
            if cb is None or frac > cb[0] or (frac == cb[0] and h['score'] > cb[1]):
                best[h['pf_short']] = (frac, h['score'], h['pf_name'])
        significant = {p: v for p, v in best.items() if v[0] >= MIN_FRAC}
        dom_pf = max(significant.items(), key=lambda kv: (kv[1][0], kv[1][1]))[0] if significant else None

        old_f, new_f, t_id = m['old_f'], m['commons_f'], m['t_id']
        in_new = dom_pf in fg_pfams.get(new_f, set()) if dom_pf else False
        in_old = dom_pf in fg_pfams.get(old_f, set()) if dom_pf else False
        implied = [f for f in by_tgroup.get(t_id, []) if dom_pf and dom_pf in fg_pfams.get(f, set())]

        if dom_pf is None:
            v = 'no_dominant_pfam'
        elif in_new and not in_old: v = 'supports_commons'
        elif in_old and not in_new: v = 'supports_old_ecod_rep'
        elif in_new and in_old:     v = 'ambiguous_both'
        elif implied:               v = 'points_to_other_fgroup'
        else:                       v = 'pfam_has_no_fgroup_here'
        new_verdict[m['ecod_uid']] = v
        dv = best.get(dom_pf) if dom_pf else None
        fresh_rows.append(dict(
            ecod_uid=m['ecod_uid'], domain_id=m['domain_id'], t_id=t_id,
            old_f=old_f or '', commons_f=new_f,
            dominant_pfam=dom_pf or '', dominant_name=(dv[2] if dv else ''),
            dominant_cov_pct=(round(dv[0]*100,1) if dv else ''),
            dominant_score=(dv[1] if dv else ''), verdict=v))

    fout = f"{WD}/pfam_recheck/fresh_verdicts_20260605.csv"
    with open(fout, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(fresh_rows[0].keys())); w.writeheader(); w.writerows(fresh_rows)
    print(f"fresh per-domain verdicts written: {fout}")

    # old verdicts
    old_verdict = {}
    with open(OLDCSV) as fh:
        for row in csv.DictReader(fh):
            old_verdict[int(row['ecod_uid'])] = row['verdict']

    order = ['supports_commons','ambiguous_both','no_dominant_pfam',
             'points_to_other_fgroup','supports_old_ecod_rep','pfam_has_no_fgroup_here']
    print("FRESH hmmscan --cut_ga (full protein, top-hit-per-region) verdict counts:")
    from collections import Counter
    nc = Counter(new_verdict.values())
    for k in order: print(f"  {k:26s} {nc.get(k,0):4d}   (stored: {Counter(old_verdict.values()).get(k,0)})")

    # agreement
    same = sum(1 for u in new_verdict if new_verdict[u] == old_verdict.get(u))
    print(f"\nverdict UNCHANGED: {same}/{len(new_verdict)}   CHANGED: {len(new_verdict)-same}")

    # focus: what happened to the 163 stored supports_commons
    sc = [u for u in old_verdict if old_verdict[u]=='supports_commons']
    moved = Counter(new_verdict[u] for u in sc)
    print("\nstored 'supports_commons' (163) -> fresh verdict:")
    for k,c in moved.most_common(): print(f"  {k:26s} {c}")

    # any NEW supports_commons that weren't before, or stored questioned that became supported
    flips = [(u, old_verdict.get(u), new_verdict[u]) for u in new_verdict
             if old_verdict.get(u) != new_verdict[u]]
    out = f"{WD}/pfam_recheck/verdict_changes_20260605.csv"
    with open(out, 'w', newline='') as fh:
        w = csv.writer(fh); w.writerow(['ecod_uid','stored_verdict','fresh_verdict'])
        w.writerows(sorted(flips, key=lambda x:(x[1] or '', x[2])))
    print(f"\nchanged rows written: {out}")

if __name__ == '__main__':
    main()
