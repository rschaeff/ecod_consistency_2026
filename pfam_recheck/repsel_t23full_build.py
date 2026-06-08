#!/usr/bin/env python3
"""Tier-2/3 full: rank all multi-member live repless F-groups, pick best provisional rep, pre-flight,
and build the create batch. Ranker key: concordant -> complete(HMMcov>=0.8) -> PDB -> coverage ->
score -> length. Pre-flight excludes ecod_domain_id collisions and already-in-ecod_rep (defer);
flags no-concordant groups and low-coverage (<0.5) picks."""
import csv, psycopg2
from collections import defaultdict, Counter
WD="/home/rschaeff/work/ecod_consistency_2026/pfam_recheck"
DOMTBL=f"{WD}/repsel_t23full.domtbl"; INP=f"{WD}/repsel_t23full_input.tsv"; KILL=0.50
SRC={'pdb':2}
def srank(s): return SRC.get(s,1)
def strip(r): return ','.join(s.split(':',1)[1] if ':' in s else s for s in r.split(','))
def dtype(st): return 'experimental structure' if st=='pdb' else 'computed structural model'

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
            hl=x['et']-x['ef']+1
            if not any(min(x['et'],k['et'])-max(x['ef'],k['ef'])+1>=KILL*hl for k in kept): kept.append(x)
        res[q]=kept
    return res

def main():
    H=load(DOMTBL); groups=defaultdict(list); pfa={}; meta={}
    for ln in open(INP):
        f=ln.rstrip('\n').split('\t')
        if len(f)<8: continue
        fid,pfam,uid,dom,srcid,st,sl,did=f[:8]
        pfa[fid]=pfam; meta[uid]=dict(domain_id=dom,source_id=srcid,source=st)
        P={x.strip() for x in pfam.split(',') if x.strip()}
        kept=H.get(uid,[]); inP=[h for h in kept if h['pf'] in P]
        conc=len(inP)>0; best=max(inP,key=lambda h:h['score']) if inP else None
        cov=((best['ht']-best['hf']+1)/best['tlen']) if best else 0.0
        try: sli=int(sl)
        except: sli=0
        complete=1 if cov>=0.8 else 0
        groups[fid].append(dict(uid=uid,source=st,hmm_cov=cov,
            key=(1 if conc else 0,complete,srank(st),cov,(best['score'] if best else 0),sli,-int(uid))))
    # pick best per group
    picks={}
    for fid,c in groups.items():
        c.sort(key=lambda z:z['key'],reverse=True)
        picks[fid]=c[0]
    n_conc={fid:sum(1 for z in c if z['key'][0]==1) for fid,c in groups.items()}
    # pre-flight the picked uids
    puids=[int(picks[f]['uid']) for f in picks]
    cn=psycopg2.connect(host="dione",port=45000,dbname="ecod_protein",user="ecod"); cur=cn.cursor()
    cur.execute("SELECT dm.ecod_uid, dm.range_definition FROM ecod_commons.domains dm WHERE dm.ecod_uid = ANY(%s)",(puids,))
    rng={u:r for u,r in cur.fetchall()}
    cur.execute("SELECT ecod_uid FROM ecod_rep.domain WHERE ecod_uid = ANY(%s)",(puids,))
    in_rep={u for (u,) in cur.fetchall()}
    pdoms=[meta[picks[f]['uid']]['domain_id'] for f in picks]
    cur.execute("SELECT ecod_domain_id FROM ecod_rep.domain WHERE ecod_domain_id = ANY(%s)",(pdoms,))
    coll={d for (d,) in cur.fetchall()}; cn.close()

    creates=[]; deferred=[]; flagged=[]
    for fid,pk in picks.items():
        u=int(pk['uid']); m=meta[pk['uid']]
        if n_conc[fid]==0:
            flagged.append((fid,pfa[fid],'NO_CONCORDANT_CANDIDATE')); continue
        if u in in_rep: deferred.append((fid,u,m['domain_id'],'already_in_ecod_rep')); continue
        if m['domain_id'] in coll: deferred.append((fid,u,m['domain_id'],'ecod_domain_id_collision')); continue
        lowcov='low_coverage' if pk['hmm_cov']<0.5 else ''
        creates.append(dict(ecod_uid=u,f_id=fid,ecod_domain_id=m['domain_id'],ecod_source_id=m['source_id'],
            seqid_range=strip(rng.get(u,'')),dtype=dtype(m['source']),flag=lowcov))
    with open(f"{WD}/repsel_t23full_create.csv","w",newline="") as fh:
        w=csv.writer(fh); w.writerow(['ecod_uid','f_id','ecod_domain_id','ecod_source_id','seqid_range','dtype'])
        for r in creates: w.writerow([r['ecod_uid'],r['f_id'],r['ecod_domain_id'],r['ecod_source_id'],r['seqid_range'],r['dtype']])
    with open(f"{WD}/repsel_t23full_deferred.csv","w",newline="") as fh:
        w=csv.writer(fh); w.writerow(['fid','ecod_uid','ecod_domain_id','reason']); w.writerows(deferred)
    with open(f"{WD}/repsel_t23full_flagged.csv","w",newline="") as fh:
        w=csv.writer(fh); w.writerow(['fid','pfam_acc','reason']); w.writerows(flagged)
    with open(f"{WD}/repsel_t23full_lowcov.csv","w",newline="") as fh:
        w=csv.writer(fh); w.writerow(['ecod_uid','f_id','hmm_cov'])
        for r in creates:
            if r['flag']=='low_coverage': w.writerow([r['ecod_uid'],r['f_id'],round(picks[r['f_id']]['hmm_cov'],3)])
    print(f"Tier-2/3 full: {len(groups)} multi-member live F-groups")
    print(f"  CREATE (clean picks): {len(creates)}  (of which low-coverage flagged: {sum(1 for r in creates if r['flag'])})")
    print(f"  deferred: {len(deferred)} ({dict(Counter(d[3] for d in deferred))})")
    print(f"  flagged no-concordant: {len(flagged)}")
    print(f"  pick source (creates): {dict(Counter(r['dtype'] for r in creates))}")

if __name__=='__main__': main()
