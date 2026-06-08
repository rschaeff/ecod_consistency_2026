#!/usr/bin/env python3
"""Relaxed-Pfam recovery for the 236 tranche-2 no-arch/ambiguous reps.
Re-scan WITHOUT --cut_ga; for each, test whether commons_f's distinguishing Pfam(s)
(N - O, the commons Pfams not in the rep's current old_f) hit the domain region.
above GA -> supports_commons; sub-GA -> borderline; absent -> unresolved (structural)."""
import csv
from collections import defaultdict
WD="/home/rschaeff/work/ecod_consistency_2026/pfam_recheck"
DOMTBL=f"{WD}/t2_674_relaxed.domtbl"; GA=f"{WD}/pfam_ga.tsv"
VERD=f"{WD}/t2_verdicts_20260608.csv"; INP=f"{WD}/t2_674_input.tsv"
HIT=0.50
def segs(r):
    o=[]
    for p in r.split(','):
        p=p.strip()
        if not p: continue
        if ':' in p: p=p.split(':',1)[1]
        if '-' in p.lstrip('-'):
            i=p.rindex('-'); a,b=p[:i],p[i+1:]
        else: a=b=p
        try: a,b=int(a),int(b)
        except: continue
        if a>b:a,b=b,a
        o.append((a,b))
    return o
def ov(s,lo,hi): return sum(max(0,min(b,hi)-max(a,lo)+1) for a,b in s)

def main():
    ga={}
    for ln in open(GA):
        a,v=ln.split('\t')
        try: ga[a]=float(v)
        except: pass
    H=defaultdict(list)
    for ln in open(DOMTBL):
        if ln.startswith('#') or not ln.strip(): continue
        f=ln.split()
        if len(f)<22: continue
        H[f[3]].append((f[1].split('.')[0],float(f[13]),int(f[19]),int(f[20])))
    # input: commons_f, commons_f_pfam, ecod_uid, domain_id, protein_id, range, old_f, is_reassign, rep_type
    inp={}
    for ln in open(INP):
        f=ln.rstrip('\n').split('\t')
        if len(f)<9: continue
        inp[f[2]]=dict(commons_f=f[0], commons_pf=f[1], domain_id=f[3], pid=f[4], rng=f[5], old_f=f[6])
    # old_f pfam: need cluster pfam_acc; pull from input commons_pf for commons; for old, query? use a small DB call.
    import psycopg2
    cn=psycopg2.connect(host="dione",port=45000,dbname="ecod_protein",user="ecod"); cur=cn.cursor()
    cur.execute("SELECT id, pfam_acc FROM ecod_rep.cluster WHERE type='F'")
    fgpf={cid:{p.strip() for p in (pa or '').split(',') if p.strip()} for cid,pa in cur.fetchall()}
    cn.close()

    rows=[]; summ=defaultdict(int)
    targets=[r for r in csv.DictReader(open(VERD)) if r['verdict'] in ('no_arch','ambiguous_both')]
    for t in targets:
        u=t['ecod_uid']; d=inp.get(u)
        if not d: continue
        seg=segs(d['rng'])
        N=fgpf.get(d['commons_f'],set()); O=fgpf.get(d['old_f'],set()) if d['old_f'] else set()
        Q=(N-O) or N
        best=None
        for q in Q:
            for (pf,sc,ef,et) in H.get(d['pid'],[]):
                if pf!=q: continue
                hl=et-ef+1
                if hl>0 and ov(seg,ef,et)>=HIT*hl:
                    g=ga.get(q); delta=(sc-g) if g is not None else None
                    if best is None or sc>best[1]: best=(q,sc,g,delta)
        if best is None: v='unresolved (commons Pfam absent)'
        elif best[3] is not None and best[2] is not None and best[1]>=best[2]: v='supports_commons (>=GA)'
        else: v='borderline (sub-GA)'
        summ[v]+=1
        rows.append(dict(ecod_uid=u, domain_id=d['domain_id'], commons_f=d['commons_f'],
            prior=t['verdict'], best_Q=(best[0] if best else ''),
            score=(round(best[1],1) if best else ''), GA=(best[2] if best else ''),
            delta=(round(best[3],1) if best and best[3] is not None else ''), relaxed_verdict=v))
    fo=f"{WD}/t2_relaxed_verdicts_20260608.csv"
    with open(fo,'w',newline='') as fh:
        w=csv.DictWriter(fh,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(f"relaxed recovery on {len(rows)} no-arch/ambiguous reps:")
    for k in sorted(summ,key=lambda k:-summ[k]): print(f"  {k:32s} {summ[k]}")
    rec=summ.get('supports_commons (>=GA)',0)
    print(f"\n  recovered to supports_commons (>=GA): {rec}")
    print(f"  borderline (sub-GA, curator judgment): {summ.get('borderline (sub-GA)',0)}")
    print(f"\nwritten: {fo}")
if __name__=='__main__': main()
