#!/usr/bin/env python3
"""
Composite-aware (architecture) rule, prototyped on the 266 REVIEW movers that
involve a composite Pfam F-group.

Instead of a single dominant Pfam >=60% of the domain, collect the domain's
ARCHITECTURE = the set of top-hit-per-region Pfams substantially inside the
domain (>=ARCH_FRAC of the hit envelope lies in the domain). Then match that
SET against each F-group's Pfam combination in the T-group (Jaccard; exact-set
match preferred). Resolve to commons_f / old_f / other when there is a clear
best match.
"""
import csv
from collections import defaultdict
import psycopg2, psycopg2.extras

WD = "/home/rschaeff/work/ecod_consistency_2026/pfam_recheck"
DOMTBL = f"{WD}/mover_pfam.domtbl"          # fresh scan of all 456 mover proteins
FRESH  = f"{WD}/fresh_verdicts_20260605.csv"
OVERLAP_KILL = 0.50    # top-hit-per-region resolution
ARCH_FRAC    = 0.50    # a Pfam is in the architecture if >=50% of its hit envelope lies in the domain
J_MIN        = 0.50    # minimum Jaccard for the best match to count as "resolved"
CONN = dict(host="dione", port=45000, dbname="ecod_protein", user="ecod")

def parse_segs(rng):
    segs=[]
    for part in rng.split(','):
        part=part.strip()
        if not part: continue
        if ':' in part: part=part.split(':',1)[1]
        if '-' in part.lstrip('-'):
            i=part.rindex('-'); a,b=part[:i],part[i+1:]
        else: a=b=part
        try: a,b=int(a),int(b)
        except ValueError: continue
        if a>b: a,b=b,a
        segs.append((a,b))
    return segs
def ov(s,lo,hi): return sum(max(0,min(b,hi)-max(a,lo)+1) for a,b in s)

def load_domtbl(path):
    raw=defaultdict(list)
    with open(path) as fh:
        for line in fh:
            if line.startswith('#') or not line.strip(): continue
            f=line.split()
            raw[f[3]].append(dict(pf=f[1].split('.')[0],score=float(f[13]),ef=int(f[19]),et=int(f[20])))
    res={}
    for q,hits in raw.items():
        kept=[]
        for h in sorted(hits,key=lambda x:-x['score']):
            hl=h['et']-h['ef']+1; drop=False
            for k in kept:
                inter=min(h['et'],k['et'])-max(h['ef'],k['ef'])+1
                if inter>0 and inter>=OVERLAP_KILL*hl: drop=True; break
            if not drop: kept.append(h)
        res[q]=kept
    return res

def jac(a,b):
    if not a and not b: return 0.0
    return len(a&b)/len(a|b)

def main():
    hits=load_domtbl(DOMTBL)
    fresh={}
    with open(FRESH) as fh:
        for r in csv.DictReader(fh): fresh[int(r['ecod_uid'])]=r['verdict'].strip()

    cn=psycopg2.connect(**CONN); cur=cn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
      WITH repless AS (SELECT c.id FROM ecod_rep.cluster c WHERE c.type='F' AND c.is_deprecated IS NOT TRUE
        AND NOT EXISTS (SELECT 1 FROM ecod_rep.domain d WHERE d.f_id=c.id AND (d.manual_rep OR d.provisional_manual_rep))),
      cand AS (SELECT dom.ecod_uid, dom.protein_id, dom.domain_id, dom.range_definition, r.id AS commons_f
               FROM repless r JOIN ecod_commons.f_group_assignments fga ON fga.f_group_id=r.id
               JOIN ecod_commons.domains dom ON dom.id=fga.domain_id AND dom.is_obsolete IS NOT TRUE
               WHERE dom.is_manual_representative)
      SELECT cand.*, er.f_id AS old_f, er.t_id FROM cand JOIN ecod_rep.domain er ON er.ecod_uid=cand.ecod_uid
    """)
    movers=cur.fetchall()
    cur.execute("SELECT id, parent AS t_parent, pfam_acc FROM ecod_rep.cluster WHERE type='F'")
    fg_pfams={}; by_t=defaultdict(list)
    for c in cur.fetchall():
        pf={p.strip() for p in (c['pfam_acc'] or '').split(',') if p.strip()}
        fg_pfams[c['id']]=pf; by_t[c['t_parent']].append(c['id'])
    cn.close()

    REVIEW={'ambiguous_both','no_dominant_pfam'}
    out=[]; summ=defaultdict(int)
    for m in movers:
        if fresh.get(m['ecod_uid']) not in REVIEW: continue
        segs=parse_segs(m['range_definition'])
        D=set()
        for h in hits.get(str(m['protein_id']),[]):
            hl=h['et']-h['ef']+1
            if hl>0 and ov(segs,h['ef'],h['et'])>=ARCH_FRAC*hl: D.add(h['pf'])
        old_f,new_f,t=m['old_f'],m['commons_f'],m['t_id']
        oldS,newS=fg_pfams.get(old_f,set()),fg_pfams.get(new_f,set())
        # best matching F-group(s) in the T-group; exact set-match wins
        cand_fs=by_t.get(t,[])
        exact=[f for f in cand_fs if fg_pfams.get(f,set())==D and D]
        if exact:
            best=set(exact); best_j=1.0
        else:
            js={f:jac(D,fg_pfams.get(f,set())) for f in cand_fs}
            best_j=max(js.values()) if js else 0.0
            best={f for f,v in js.items() if v==best_j and v>=J_MIN}
        if not D:                                   v='comp_no_arch'
        elif not best:                              v='comp_unresolved (best J<%.2f)'%J_MIN
        elif new_f in best and old_f not in best:   v='comp_supports_commons'
        elif old_f in best and new_f not in best:   v='comp_supports_old'
        elif new_f in best and old_f in best:       v='comp_ambiguous_both'
        else:                                       v='comp_points_other'
        summ[v]+=1
        out.append(dict(ecod_uid=m['ecod_uid'], domain_id=m['domain_id'], prev_verdict=fresh[m['ecod_uid']],
            t_id=t, old_f=old_f, old_pfam=','.join(sorted(oldS)), commons_f=new_f, new_pfam=','.join(sorted(newS)),
            domain_arch=','.join(sorted(D)), j_old=round(jac(D,oldS),2), j_commons=round(jac(D,newS),2),
            best_match=';'.join(sorted(best)), exact_match=bool(exact), comp_verdict=v))

    out.sort(key=lambda r:(r['comp_verdict'], r['domain_id']))
    fo=f"{WD}/composite_rule_20260605.csv"
    with open(fo,'w',newline='') as fh:
        w=csv.DictWriter(fh,fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)

    tot=len(out)
    resolved=sum(n for k,n in summ.items() if k in
                 ('comp_supports_commons','comp_supports_old','comp_points_other'))
    print(f"composite-aware rule on {tot} REVIEW movers (ARCH_FRAC={ARCH_FRAC}, J_MIN={J_MIN})\n")
    for k in sorted(summ,key=lambda k:-summ[k]): print(f"  {k:32s} {summ[k]:4d}")
    print(f"\n  RESOLVED (commons/old/other): {resolved}/{tot} ({100*resolved//tot}%)")
    # split resolution by prior verdict
    byp=defaultdict(lambda: defaultdict(int))
    for r in out: byp[r['prev_verdict']][r['comp_verdict']]+=1
    print("\n  by prior verdict:")
    for pv in byp:
        res=sum(byp[pv][k] for k in byp[pv] if k in ('comp_supports_commons','comp_supports_old','comp_points_other'))
        print(f"    {pv:18s}: {res}/{sum(byp[pv].values())} resolved")
    print(f"\nwritten: {fo}")

if __name__=='__main__':
    main()
