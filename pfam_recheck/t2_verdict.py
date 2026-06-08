#!/usr/bin/env python3
"""Validate the 674 tranche-2 propagation candidates (plain/provisional commons reps).
Fresh --cut_ga scan -> domain Pfam architecture (top-hit-per-region, >=50% of hit in domain)
-> best-matching F-group in commons_f's T-group -> verdict vs commons_f (the repless target)."""
import csv, sys
from collections import defaultdict
import psycopg2, psycopg2.extras
sys.path.insert(0, '.')
WD = "/home/rschaeff/work/ecod_consistency_2026/pfam_recheck"
DOMTBL = f"{WD}/t2_674.domtbl"
INP = f"{WD}/t2_674_input.tsv"
ARCH_FRAC = 0.50; OVERLAP_KILL = 0.50; MIN_FRAC = 0.60
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
        except: continue
        if a>b:a,b=b,a
        segs.append((a,b))
    return segs
def seg_len(s): return sum(b-a+1 for a,b in s)
def ov(s,lo,hi): return sum(max(0,min(b,hi)-max(a,lo)+1) for a,b in s)
def jac(a,b): return len(a&b)/len(a|b) if (a or b) else 0.0

def load_domtbl(p):
    raw=defaultdict(list)
    for ln in open(p):
        if ln.startswith('#') or not ln.strip(): continue
        f=ln.split()
        if len(f) < 22: continue
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

def main():
    hits=load_domtbl(DOMTBL)
    cn=psycopg2.connect(**CONN); cur=cn.cursor()
    cur.execute("SELECT id, parent, pfam_acc FROM ecod_rep.cluster WHERE type='F'")
    fg_pf={}; by_t=defaultdict(list); fg_parent={}
    for cid,par,pa in cur.fetchall():
        s={p.strip() for p in (pa or '').split(',') if p.strip()}
        fg_pf[cid]=s; by_t[par].append(cid); fg_parent[cid]=par
    cn.close()

    rows=[]; summ=defaultdict(int)
    for ln in open(INP):
        f=ln.rstrip('\n').split('\t')
        if len(f)<9: continue
        commons_f, commons_pf, ecod_uid, dom, pid, rng, old_f, is_reassign, rep_type = f[:9]
        segs=parse_segs(rng); dlen=seg_len(segs) or 1
        # architecture set: top-hit-per-region Pfams >=50% of hit inside domain
        D=set(); dom_pf=None; best_cov=0
        bestsingle=None
        for h in hits.get(pid,[]):
            hl=h['et']-h['ef']+1; o=ov(segs,h['ef'],h['et'])
            if hl>0 and o>=ARCH_FRAC*hl: D.add(h['pf'])
            frac=o/dlen
            if frac>=MIN_FRAC and (bestsingle is None or frac>bestsingle[1]): bestsingle=(h['pf'],frac)
        parent=fg_parent.get(commons_f)
        cands=by_t.get(parent,[]) if parent else [commons_f]
        newS=fg_pf.get(commons_f,set()); oldS=fg_pf.get(old_f,set()) if old_f else set()
        if not D and not bestsingle:
            v='no_arch'
        else:
            exact=[c for c in cands if fg_pf.get(c)==D and D]
            if exact: best=set(exact)
            else:
                js={c:jac(D,fg_pf.get(c,set())) for c in cands}
                bj=max(js.values()) if js else 0
                best={c for c,x in js.items() if x==bj and x>=0.5}
            # fall back to single dominant if arch gave nothing
            if not best and bestsingle:
                dp=bestsingle[0]
                best={c for c in cands if dp in fg_pf.get(c,set())}
            if not best: v='unresolved'
            elif commons_f in best and old_f not in best: v='supports_commons'
            elif old_f and old_f in best and commons_f not in best: v='supports_old'
            elif commons_f in best and old_f in best: v='ambiguous_both'
            else: v='points_other'
        summ[v]+=1
        rows.append(dict(commons_f=commons_f, ecod_uid=ecod_uid, domain_id=dom, rep_type=rep_type,
            is_reassign=is_reassign, old_f=old_f, commons_f_pfam=commons_pf,
            domain_arch=','.join(sorted(D)), verdict=v))
    fo=f"{WD}/t2_verdicts_20260608.csv"
    with open(fo,'w',newline='') as fh:
        w=csv.DictWriter(fh,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(f"674 tranche-2 verdicts (fresh --cut_ga + architecture match):")
    for k in sorted(summ,key=lambda k:-summ[k]): print(f"  {k:20s} {summ[k]}")
    sc=[r for r in rows if r['verdict']=='supports_commons']
    print(f"\n  supports_commons (validated -> propagate): {len(sc)}")
    from collections import Counter
    print("  of those, reassign vs create:", dict(Counter(('reassign' if r['is_reassign']=='t' else 'create') for r in sc)))
    print(f"\nwritten: {fo}")

if __name__=='__main__': main()
