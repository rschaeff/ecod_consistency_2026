#!/usr/bin/env python3
"""
Pick a suggested PROVISIONAL representative for each stranded live old F-group.
Candidate = a remaining (non-mover, non-obsolete) commons member of the old group.
Confirm it belongs (fresh hmmscan dominant Pfam >=60% of domain matches the old
F-group's pfam_acc), then rank by quality:
  pfam-confirmed > pdb > non-discontinuous > single-domain protein > coverage > score
"""
import csv
from collections import defaultdict

WD = "/home/rschaeff/work/ecod_consistency_2026/pfam_recheck"
CAND = f"{WD}/reseed_candidates.csv"
DOMTBL = f"{WD}/reseed_pfam.domtbl"
MIN_FRAC = 0.60
OVERLAP_KILL = 0.50

def parse_segs(rng):
    segs = []
    for part in rng.split(','):
        part = part.strip()
        if not part: continue
        if ':' in part: part = part.split(':',1)[1]
        if '-' in part.lstrip('-'):
            i = part.rindex('-'); a,b = part[:i], part[i+1:]
        else: a=b=part
        try: a,b=int(a),int(b)
        except ValueError: continue
        if a>b: a,b=b,a
        segs.append((a,b))
    return segs
def seg_len(s): return sum(b-a+1 for a,b in s)
def ov(s,lo,hi): return sum(max(0,min(b,hi)-max(a,lo)+1) for a,b in s)

def load_domtbl(path):
    raw = defaultdict(list)
    with open(path) as fh:
        for line in fh:
            if line.startswith('#') or not line.strip(): continue
            f=line.split()
            raw[f[3]].append(dict(pf=f[1].split('.')[0], name=f[0], score=float(f[13]),
                                  ef=int(f[19]), et=int(f[20])))
    res={}
    for q,hits in raw.items():
        kept=[]
        for h in sorted(hits,key=lambda x:-x['score']):
            hlen=h['et']-h['ef']+1; drop=False
            for k in kept:
                inter=min(h['et'],k['et'])-max(h['ef'],k['ef'])+1
                if inter>0 and inter>=OVERLAP_KILL*hlen: drop=True; break
            if not drop: kept.append(h)
        res[q]=kept
    return res

def main():
    hits = load_domtbl(DOMTBL)
    cands = defaultdict(list)
    with open(CAND) as fh:
        for r in csv.DictReader(fh):
            r['_oldf_pfams'] = {p.strip() for p in r['oldf_pfam'].split(',') if p.strip()}
            segs = parse_segs(r['range_definition'])
            dlen = seg_len(segs) or int(r['sequence_length'] or 0)
            best=None
            for h in hits.get(r['protein_id'], []):
                frac = ov(segs,h['ef'],h['et'])/dlen if dlen else 0
                if best is None or frac>best[0] or (frac==best[0] and h['score']>best[1]):
                    best=(frac,h['score'],h['pf'],h['name'])
            r['_dom_pf']   = best[2] if best and best[0]>=MIN_FRAC else None
            r['_dom_name'] = best[3] if best and best[0]>=MIN_FRAC else ''
            r['_cov']      = round(best[0]*100,1) if best and best[0]>=MIN_FRAC else 0
            r['_score']    = best[1] if best and best[0]>=MIN_FRAC else 0
            r['_confirms'] = bool(r['_dom_pf'] and r['_dom_pf'] in r['_oldf_pfams'])
            cands[r['old_f']].append(r)

    def rank(r):
        return (r['_confirms'],
                r['source_type']=='pdb',
                r['is_discontinuous'] in ('f','False','false'),
                r['is_multidomain'] in ('f','False','false'),
                r['_cov'], r['_score'])

    print(f"{'old_f':12} {'oldf_pfam':16} {'#cand':5} {'#conf':5} | SUGGESTED REP")
    print('-'*120)
    out=[]
    for old_f in sorted(cands):
        cl = cands[old_f]
        nconf = sum(1 for r in cl if r['_confirms'])
        top = sorted(cl, key=rank, reverse=True)[0]
        oldf_pfam = cl[0]['oldf_pfam']
        flag = '' if top['_confirms'] and top['source_type']=='pdb' else \
               '  <-- predicted-only' if top['_confirms'] else '  <-- NO Pfam-confirmed candidate'
        print(f"{old_f:12} {oldf_pfam:16} {len(cl):5} {nconf:5} | "
              f"{top['domain_id']:14} {top['source_type']:4} len={top['sequence_length']:>4} "
              f"disc={top['is_discontinuous']:1} multidom={top['is_multidomain']:1} "
              f"dom_pfam={top['_dom_pf'] or '-'}/{top['_dom_name'] or '-'} cov={top['_cov']}% score={top['_score']}{flag}")
        out.append(dict(old_f=old_f, oldf_pfam=oldf_pfam, n_candidates=len(cl), n_confirmed=nconf,
                        suggested_ecod_uid=top['ecod_uid'], suggested_domain_id=top['domain_id'],
                        source_type=top['source_type'], seq_len=top['sequence_length'],
                        is_discontinuous=top['is_discontinuous'], is_multidomain=top['is_multidomain'],
                        dom_pfam=top['_dom_pf'] or '', dom_pfam_name=top['_dom_name'],
                        cov_pct=top['_cov'], score=top['_score'], pfam_confirmed=top['_confirms']))
    fo=f"{WD}/reseed_suggestions_20260605.csv"
    with open(fo,'w',newline='') as fh:
        w=csv.DictWriter(fh,fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
    print(f"\nwritten: {fo}")

if __name__=='__main__':
    main()
