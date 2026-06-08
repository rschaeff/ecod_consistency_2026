#!/usr/bin/env python3
"""Tier-1 rep-selection pilot: for each single-member repless F-group, does the sole member's
Pfam architecture match the F-group's pfam_acc? Measures the concordance rate that calibrates
the validation gate."""
import csv
from collections import defaultdict, Counter
WD="/home/rschaeff/work/ecod_consistency_2026/pfam_recheck"
DOMTBL=f"{WD}/repsel_pilot.domtbl"; INP=f"{WD}/repsel_pilot_input.tsv"
ARCH=0.50; KILL=0.50; DOM=0.60

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
def slen(s): return sum(b-a+1 for a,b in s)
def ov(s,lo,hi): return sum(max(0,min(b,hi)-max(a,lo)+1) for a,b in s)

def load(p):
    raw=defaultdict(list)
    for ln in open(p):
        if ln.startswith('#') or not ln.strip(): continue
        f=ln.split()
        if len(f)<22: continue
        raw[f[3]].append(dict(pf=f[1].split('.')[0],score=float(f[13]),ef=int(f[19]),et=int(f[20])))
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
    scanned=set(hits.keys())  # proteins present in scan output (had >=1 hit)
    # proteins actually in the FASTA (scanned even if 0 hits):
    infasta=set()
    for ln in open(f"{WD}/repsel_pilot_proteins.fasta"):
        if ln.startswith('>'): infasta.add(ln[1:].strip())
    rows=[]; summ=Counter()
    for ln in open(INP):
        f=ln.rstrip('\n').split('\t')
        if len(f)<8: continue
        fid,pfam,uid,dom,pid,rng,src,sl=f[:8]
        P={x.strip() for x in pfam.split(',') if x.strip()}
        seg=segs(rng); dl=slen(seg) or 1
        if pid not in infasta:
            v='protein_missing'; D=set(); dompf=''
        else:
            D=set(); dompf=None; best=0
            for h in hits.get(pid,[]):
                hl=h['et']-h['ef']+1; o=ov(seg,h['ef'],h['et'])
                if hl>0 and o>=ARCH*hl: D.add(h['pf'])
                if o/dl>=DOM and o/dl>best: best=o/dl; dompf=h['pf']
            if not D: v='no_pfam_member'
            elif D==P: v='concordant_exact'
            elif P and P<=D: v='concordant_contains'
            elif dompf in P: v='concordant_dominant'
            elif P & D: v='partial_overlap'
            else: v='discordant'
        summ[v]+=1
        rows.append(dict(fid=fid,pfam_acc=pfam,ecod_uid=uid,domain_id=dom,source=src,seqlen=sl,
                         member_arch=','.join(sorted(D)),dominant=dompf or '',verdict=v))
    with open(f"{WD}/repsel_pilot_verdicts_20260608.csv",'w',newline='') as fh:
        w=csv.DictWriter(fh,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(f"Tier-1 pilot: {len(rows)} single-member repless F-groups\n")
    conc=sum(summ[k] for k in ('concordant_exact','concordant_contains','concordant_dominant'))
    scannable=len(rows)-summ['protein_missing']
    for k in ('concordant_exact','concordant_contains','concordant_dominant','partial_overlap',
              'discordant','no_pfam_member','protein_missing'):
        if summ[k]: print(f"  {k:22s} {summ[k]}")
    print(f"\n  CONCORDANT (gate-pass): {conc}/{scannable} scannable = {100*conc/scannable:.0f}%")
    print(f"  would FLAG for curator (discordant/no_pfam): {summ['discordant']+summ['no_pfam_member']+summ['partial_overlap']}")
    print(f"  protein not in sequence table: {summ['protein_missing']}")
    print(f"\n  written: {WD}/repsel_pilot_verdicts_20260608.csv")

if __name__=='__main__': main()
