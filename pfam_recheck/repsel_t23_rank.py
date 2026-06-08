#!/usr/bin/env python3
"""Tier-2/3 ranker prototype. For each multi-member repless F-group, rank its candidate domains and
pick the best provisional rep. Lexicographic key (all 'higher is better'):
  1. concordant (domain Pfam intersects F-group pfam_acc)   [gate]
  2. source experimental (PDB) > computed
  3. HMM coverage of the best in-pfam_acc match (completeness/faithfulness)
  4. domain match score (match strength)
  5. sequence_length (fuller domain)
  6. -ecod_uid (stable tiebreak)
If no candidate in a group is concordant -> flag the F-group (pfam_acc/membership suspect)."""
import csv
from collections import defaultdict
WD="/home/rschaeff/work/ecod_consistency_2026/pfam_recheck"
DOMTBL=f"{WD}/repsel_t23.domtbl"; INP=f"{WD}/repsel_t23_input.tsv"; KILL=0.50

def load(p):
    raw=defaultdict(list)
    for ln in open(p):
        if ln.startswith('#') or not ln.strip(): continue
        f=ln.split()
        if len(f)<22: continue
        raw[f[3]].append(dict(pf=f[1].split('.')[0],tlen=int(f[2]),score=float(f[13]),
                              hf=int(f[15]),ht=int(f[16]),ef=int(f[19]),et=int(f[20])))
    res={}
    for q,h in raw.items():
        kept=[]
        for x in sorted(h,key=lambda z:-z['score']):
            hl=x['et']-x['ef']+1; drop=False
            for k in kept:
                if min(x['et'],k['et'])-max(x['ef'],k['ef'])+1>=KILL*hl: drop=True; break
            if not drop: kept.append(x)
        res[q]=kept
    return res

SRC={'pdb':2}
def srank(s): return SRC.get(s,1)

def main():
    H=load(DOMTBL)
    groups=defaultdict(list); pfa={}
    for ln in open(INP):
        f=ln.rstrip('\n').split('\t')
        if len(f)<9: continue
        fid,pfam,gsize,uid,dom,srcid,st,sl,did=f[:9]
        pfa[fid]=pfam
        P={x.strip() for x in pfam.split(',') if x.strip()}
        kept=H.get(uid,[])
        D={h['pf'] for h in kept}
        inP=[h for h in kept if h['pf'] in P]
        conc=len(inP)>0
        best=max(inP,key=lambda h:h['score']) if inP else None
        hmmcov=((best['ht']-best['hf']+1)/best['tlen']) if best else 0.0
        mscore=best['score'] if best else 0.0
        try: sli=int(sl)
        except: sli=0
        complete=1 if hmmcov>=0.8 else 0   # completeness outranks source: a full AF2 beats a fragment PDB
        groups[fid].append(dict(ecod_uid=uid,domain_id=dom,source_id=srcid,source=st,seqlen=sli,
            member_pfams=','.join(sorted(D)),concordant=conc,hmm_cov=round(hmmcov,3),
            match_score=mscore,key=(1 if conc else 0,complete,srank(st),hmmcov,mscore,sli,-int(uid))))
    picks=[]
    for fid,cands in groups.items():
        cands.sort(key=lambda c:c['key'],reverse=True)
        pick=cands[0]; runner=cands[1] if len(cands)>1 else None
        n_pdb=sum(1 for c in cands if c['source']=='pdb')
        n_conc=sum(1 for c in cands if c['concordant'])
        picks.append(dict(fid=fid,pfam_acc=pfa[fid],n_cand=len(cands),n_pdb=n_pdb,n_concordant=n_conc,
            pick_uid=pick['ecod_uid'],pick_domain=pick['domain_id'],pick_source=pick['source'],
            pick_seqlen=pick['seqlen'],pick_concordant=pick['concordant'],pick_hmm_cov=pick['hmm_cov'],
            pick_pfams=pick['member_pfams'],
            runner_source=(runner['source'] if runner else ''),runner_uid=(runner['ecod_uid'] if runner else ''),
            group_flag=('NO_CONCORDANT_CANDIDATE' if n_conc==0 else '')))
    with open(f"{WD}/repsel_t23_picks_20260608.csv",'w',newline='') as fh:
        w=csv.DictWriter(fh,fieldnames=list(picks[0].keys())); w.writeheader(); w.writerows(picks)
    from collections import Counter
    good=[p for p in picks if not p['group_flag']]
    print(f"Tier-2/3 ranker prototype: {len(picks)} multi-member F-groups\n")
    print(f"  groups with a concordant pick: {len(good)}/{len(picks)} = {100*len(good)/len(picks):.0f}%")
    print(f"  groups flagged (no concordant candidate): {len(picks)-len(good)}")
    print(f"  pick source: {dict(Counter(p['pick_source'] for p in good))}")
    haspdb=[p for p in good if p['n_pdb']>0]
    pdbchosen=[p for p in haspdb if p['pick_source']=='pdb']
    print(f"  of {len(haspdb)} groups WITH a PDB candidate, picked the PDB: {len(pdbchosen)} ({100*len(pdbchosen)/max(1,len(haspdb)):.0f}%)")
    print(f"  median pick HMM coverage: {sorted(p['pick_hmm_cov'] for p in good)[len(good)//2]:.2f}")
    print(f"\n  written: {WD}/repsel_t23_picks_20260608.csv")

if __name__=='__main__': main()
