#!/usr/bin/env python3
"""Rank the 3 Archaea F-groups' members and emit the create rows. Same key as Tier-2/3:
concordant -> complete(HMMcov>=0.8) -> PDB -> coverage -> score -> length."""
import csv
from collections import defaultdict
WD="/home/rschaeff/work/ecod_consistency_2026/pfam_recheck"
DOMTBL=f"{WD}/repsel_archaea.domtbl"; INP=f"{WD}/repsel_archaea_input.tsv"; KILL=0.50
def srank(s): return 2 if s=='pdb' else 1
def strip(r): return ','.join(s.split(':',1)[1] if ':' in s else s for s in r.split(','))
def dtype(st): return 'experimental structure' if st=='pdb' else 'computed structural model'
def rlen(r):
    n=0
    for p in r.split(','):
        p=p.split(':',1)[1] if ':' in p else p
        if '-' in p.lstrip('-'):
            i=p.rindex('-')
            try: n+=int(p[i+1:])-int(p[:i])+1
            except: pass
    return n

def load(p):
    raw=defaultdict(list)
    for ln in open(p):
        if ln.startswith('#') or not ln.strip(): continue
        f=ln.split()
        if len(f)<22: continue
        raw[f[3]].append(dict(pf=f[1].split('.')[0],tlen=int(f[2]),score=float(f[13]),hf=int(f[15]),ht=int(f[16]),ef=int(f[19]),et=int(f[20])))
    res={}
    for q,h in raw.items():
        kept=[]
        for x in sorted(h,key=lambda z:-z['score']):
            hl=x['et']-x['ef']+1
            if not any(min(x['et'],k['et'])-max(x['ef'],k['ef'])+1>=KILL*hl for k in kept): kept.append(x)
        res[q]=kept
    return res

H=load(DOMTBL); groups=defaultdict(list)
for ln in open(INP):
    f=ln.rstrip('\n').split('\t')
    if len(f)<8: continue
    fid,pfam,uid,dom,srcid,st,rng,did=f[:8]
    P={x.strip() for x in pfam.split(',') if x.strip()}
    inP=[h for h in H.get(uid,[]) if h['pf'] in P]
    conc=len(inP)>0; best=max(inP,key=lambda h:h['score']) if inP else None
    cov=((best['ht']-best['hf']+1)/best['tlen']) if best else 0.0
    groups[fid].append(dict(uid=uid,dom=dom,srcid=srcid,st=st,rng=rng,conc=conc,cov=cov,
        key=(1 if conc else 0,1 if cov>=0.8 else 0,srank(st),cov,(best['score'] if best else 0),rlen(rng),-int(uid))))
rows=[]
for fid,c in groups.items():
    c.sort(key=lambda z:z['key'],reverse=True); pk=c[0]
    rows.append([pk['uid'],fid,pk['dom'],pk['srcid'],strip(pk['rng']),dtype(pk['st'])])
    print(f"  {fid:12s} {len(c):>3} cand -> {pk['dom']:18s} {pk['st']:5s} concordant={pk['conc']} cov={pk['cov']:.2f}")
with open(f"{WD}/repsel_archaea_create.csv","w",newline="") as fh:
    w=csv.writer(fh); w.writerow(['ecod_uid','f_id','ecod_domain_id','ecod_source_id','seqid_range','dtype']); w.writerows(rows)
print(f"create rows: {len(rows)}")
