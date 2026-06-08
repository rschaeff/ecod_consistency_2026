#!/usr/bin/env python3
"""
Relaxed-Pfam rescan analysis for the 149 subset-ambiguous movers.

Question per domain: the composite target adds Pfam(s) Q that the --cut_ga scan did
NOT find in the domain. Re-scanned WITHOUT --cut_ga (default E=10). For each missing
Q, is there ANY hit inside the domain region, and how does its best domain bitscore
compare to Q's gathering threshold (GA)?
  - no hit in region                -> Q_absent        (composite likely unwarranted)
  - hit, score < GA                 -> Q_sub_GA         (present but weak; composite plausible)
  - hit, score >= GA                -> Q_above_GA       (flag: cut_ga scan/overlap-resolution missed it)

NON-CIRCULAR: Pfam HMMs are independent of the ECOD query domains.
"""
import csv
from collections import defaultdict

WD = "/home/rschaeff/work/ecod_consistency_2026/pfam_recheck"
DOMTBL = f"{WD}/mover_pfam_relaxed.domtbl"
TARGETS = f"{WD}/subset_targets.tsv"     # ecod_uid domain_id old_f commons_f arch missing_Q
DOMINFO = f"{WD}/subset_dominfo.tsv"     # ecod_uid protein_id range_definition
GA = f"{WD}/pfam_ga.tsv"
HIT_IN_REGION = 0.50   # a Q hit counts as "in the domain" if >=50% of its envelope lies in the domain

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

def main():
    ga={}
    for line in open(GA):
        a,v=line.split('\t');
        try: ga[a]=float(v)
        except: pass
    dominfo={}
    for line in open(DOMINFO):
        f=line.rstrip('\n').split('\t')
        if len(f)<3: continue
        dominfo[f[0]]=(f[1], parse_segs(f[2]))
    # relaxed scan hits: protein_id -> list of (pf_short, score, evalue, ef, et)
    hits=defaultdict(list)
    for line in open(DOMTBL):
        if line.startswith('#') or not line.strip(): continue
        f=line.split()
        hits[f[3]].append((f[1].split('.')[0], float(f[13]), float(f[12]), int(f[19]), int(f[20])))

    rows=[]; summ=defaultdict(int)
    for line in open(TARGETS):
        if line.startswith('ecod_uid'): continue
        uid,dom,old_f,new_f,arch,missing=line.rstrip('\n').split('\t')
        pid,segs=dominfo.get(uid,(None,[]))
        Qs=[q for q in missing.split(',') if q]
        per_q=[]
        worst='Q_absent'   # aggregate (strongest evidence wins): above_GA > sub_GA > absent
        for Q in Qs:
            best=None
            for (pf,score,ev,ef,et) in hits.get(pid,[]):
                if pf!=Q: continue
                hlen=et-ef+1
                if hlen>0 and ov(segs,ef,et) >= HIT_IN_REGION*hlen:
                    if best is None or score>best[0]: best=(score,ev,ef,et)
            gth=ga.get(Q)
            if best is None:
                cls='absent'; sc=ev2=None; delta=None
            else:
                sc=best[0]; ev2=best[1]
                delta=(sc-gth) if gth is not None else None
                cls='above_GA' if (gth is not None and sc>=gth) else 'sub_GA'
            per_q.append((Q,cls,sc,gth,delta,ev2))
            if cls=='above_GA': worst='Q_above_GA'
            elif cls=='sub_GA' and worst!='Q_above_GA': worst='Q_sub_GA'
        summ[worst]+=1
        # pick representative Q detail (the strongest)
        rank={'above_GA':2,'sub_GA':1,'absent':0}
        pq=sorted(per_q,key=lambda x:rank[x[1]],reverse=True)[0] if per_q else ('', 'absent',None,None,None,None)
        rows.append(dict(ecod_uid=uid,domain_id=dom,old_f=old_f,commons_f=new_f,
            missing_Q=missing, verdict=worst,
            strongest_Q=pq[0], Q_class=pq[1],
            Q_score=(round(pq[2],1) if pq[2] is not None else ''),
            Q_GA=(pq[3] if pq[3] is not None else ''),
            Q_delta_vs_GA=(round(pq[4],1) if pq[4] is not None else ''),
            Q_evalue=(f'{pq[5]:.1e}' if pq[5] is not None else '')))
    fo=f"{WD}/relaxed_pfam_check_20260605.csv"
    with open(fo,'w',newline='') as fh:
        w=csv.DictWriter(fh,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

    n=len(rows)
    print(f"relaxed-Pfam rescan on {n} subset-ambiguous domains (HIT_IN_REGION>={HIT_IN_REGION})\n")
    for k in ('Q_absent','Q_sub_GA','Q_above_GA'):
        print(f"  {k:12s} {summ.get(k,0):4d}")
    # distribution of how-far-below-GA for sub_GA
    subs=[float(r['Q_delta_vs_GA']) for r in rows if r['verdict']=='Q_sub_GA' and r['Q_delta_vs_GA']!='']
    if subs:
        subs.sort()
        import statistics
        print(f"\n  sub_GA delta (score-GA, negative=below): min={subs[0]} median={round(statistics.median(subs),1)} max={subs[-1]}")
    print(f"\nwritten: {fo}")

if __name__=='__main__':
    main()
