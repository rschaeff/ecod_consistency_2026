#!/usr/bin/env python3
"""Tier-1 verdict + create-batch build. Gate: member Pfams (cut_ga, top-hit-per-region on the domain
sequence) intersect the F-group pfam_acc. PASS -> promote as provisional rep (create, or flag-set if
already in ecod_rep). no_pfam/discordant -> flag for relaxed/curator."""
import csv, psycopg2
from collections import defaultdict, Counter
WD="/home/rschaeff/work/ecod_consistency_2026/pfam_recheck"
DOMTBL=f"{WD}/repsel_t1.domtbl"; INP=f"{WD}/repsel_t1_input.tsv"; KILL=0.50

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
                if min(x['et'],k['et'])-max(x['ef'],k['ef'])+1>=KILL*hl: drop=True; break
            if not drop: kept.append(x)
        res[q]={x['pf'] for x in kept}
    return res
def strip(r): return ','.join(s.split(':',1)[1] if ':' in s else s for s in r.split(','))
DT={'pdb':'experimental structure'}
def dtype(st): return DT.get(st,'computed structural model')

def main():
    D=load(DOMTBL)
    rows=[]
    for ln in open(INP):
        f=ln.rstrip('\n').split('\t')
        if len(f)<9: continue
        fid,pfam,uid,dom,srcid,st,rng,iner,hasds=f[:9]
        P={x.strip() for x in pfam.split(',') if x.strip()}
        d=D.get(uid,set())
        if not d: v='no_pfam'
        elif P & d: v='PASS'
        else: v='discordant'
        rows.append(dict(fid=fid,pfam_acc=pfam,ecod_uid=uid,domain_id=dom,source_id=srcid,
            source_type=st,rng=rng,in_ecod_rep=(iner=='t'),member_pfams=','.join(sorted(d)),verdict=v))
    summ=Counter(r['verdict'] for r in rows)
    passes=[r for r in rows if r['verdict']=='PASS']
    creates=[r for r in passes if not r['in_ecod_rep']]
    iner=[r for r in passes if r['in_ecod_rep']]
    # current f_id of the in-ecod_rep ones
    if iner:
        cn=psycopg2.connect(host="dione",port=45000,dbname="ecod_protein",user="ecod"); cur=cn.cursor()
        cur.execute("SELECT ecod_uid,f_id::text FROM ecod_rep.domain WHERE ecod_uid = ANY(%s)",
                    ([int(r['ecod_uid']) for r in iner],))
        cf=dict(cur.fetchall()); cn.close()
        for r in iner: r['cur_f']=cf.get(int(r['ecod_uid']),'')
    with open(f"{WD}/repsel_t1_create.csv","w",newline="") as fh:
        w=csv.writer(fh); w.writerow(['ecod_uid','f_id','ecod_domain_id','ecod_source_id','seqid_range','dtype'])
        for r in creates: w.writerow([r['ecod_uid'],r['fid'],r['domain_id'],r['source_id'],strip(r['rng']),dtype(r['source_type'])])
    with open(f"{WD}/repsel_t1_inecodrep.csv","w",newline="") as fh:
        w=csv.writer(fh); w.writerow(['ecod_uid','f_id','cur_f','same_fgroup'])
        for r in iner: w.writerow([r['ecod_uid'],r['fid'],r.get('cur_f',''),r.get('cur_f','')==r['fid']])
    with open(f"{WD}/repsel_t1_flagged.csv","w",newline="") as fh:
        w=csv.DictWriter(fh,fieldnames=['fid','pfam_acc','ecod_uid','domain_id','source_type','member_pfams','verdict'])
        w.writeheader()
        for r in rows:
            if r['verdict']!='PASS': w.writerow({k:r[k] for k in w.fieldnames})
    print(f"Tier-1 verdict on {len(rows)} single-member groups:")
    for k,c in summ.most_common(): print(f"  {k:12s} {c}")
    print(f"\n  PASS -> promote: {len(passes)}  (create {len(creates)} + in_ecod_rep {len(iner)})")
    print(f"  flagged (no_pfam {summ['no_pfam']} + discordant {summ['discordant']}) -> relaxed/curator")
    print(f"  PASS by source: {dict(Counter(r['source_type'] for r in passes))}")

if __name__=='__main__': main()
