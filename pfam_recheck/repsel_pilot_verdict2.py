#!/usr/bin/env python3
"""Tier-1 pilot v2 on DOMAIN sequences (header=ecod_uid). The sequence IS the domain, so any
cut_ga Pfam hit is the domain's Pfam -- concordance = does the F-group's pfam_acc appear in the
domain's hits."""
import csv
from collections import defaultdict, Counter
WD="/home/rschaeff/work/ecod_consistency_2026/pfam_recheck"
DOMTBL=f"{WD}/repsel_pilot_dom.domtbl"; INP=f"{WD}/repsel_pilot_input.tsv"
KILL=0.50; DOM=0.60

def load(p):
    raw=defaultdict(list)
    for ln in open(p):
        if ln.startswith('#') or not ln.strip(): continue
        f=ln.split()
        if len(f)<22: continue
        raw[f[3]].append(dict(pf=f[1].split('.')[0],score=float(f[13]),
                              qlen=int(f[5]),ef=int(f[19]),et=int(f[20])))
    res={}
    for q,h in raw.items():
        kept=[]
        for x in sorted(h,key=lambda z:-z['score']):
            hl=x['et']-x['ef']+1; drop=False
            for k in kept:
                inter=min(x['et'],k['et'])-max(x['ef'],k['ef'])+1
                if inter>0 and inter>=KILL*hl: drop=True; break
            if not drop: kept.append(x)
        res[q]=kept
    return res

def main():
    hits=load(DOMTBL)
    rows=[]; summ=Counter()
    for ln in open(INP):
        f=ln.rstrip('\n').split('\t')
        if len(f)<8: continue
        fid,pfam,uid,dom,pid,rng,src,sl=f[:8]
        P={x.strip() for x in pfam.split(',') if x.strip()}
        kept=hits.get(uid,[])
        D={h['pf'] for h in kept}
        dompf=None; best=0
        for h in kept:
            cov=(h['et']-h['ef']+1)/(h['qlen'] or 1)
            if cov>=DOM and cov>best: best=cov; dompf=h['pf']
        if not D: v='no_pfam_member'
        elif D==P: v='concordant_exact'
        elif P and P<=D: v='concordant_contains'
        elif dompf in P: v='concordant_dominant'
        elif P & D: v='partial_overlap'
        else: v='discordant'
        summ[v]+=1
        rows.append(dict(fid=fid,pfam_acc=pfam,ecod_uid=uid,domain_id=dom,source=src,seqlen=sl,
                         member_pfams=','.join(sorted(D)),dominant=dompf or '',verdict=v))
    with open(f"{WD}/repsel_pilot_verdicts2_20260608.csv",'w',newline='') as fh:
        w=csv.DictWriter(fh,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(f"Tier-1 pilot v2 (domain sequences): {len(rows)} single-member repless F-groups\n")
    conc=sum(summ[k] for k in ('concordant_exact','concordant_contains','concordant_dominant'))
    for k in ('concordant_exact','concordant_contains','concordant_dominant','partial_overlap',
              'discordant','no_pfam_member'):
        if summ[k]: print(f"  {k:22s} {summ[k]}")
    print(f"\n  CONCORDANT (gate-pass): {conc}/{len(rows)} = {100*conc/len(rows):.0f}%")
    print(f"  FLAG for curator/relaxed (partial+discordant+no_pfam): {summ['partial_overlap']+summ['discordant']+summ['no_pfam_member']}")
    print(f"  by source: {dict(Counter(r['source'] for r in rows))}")

if __name__=='__main__': main()
