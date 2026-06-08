#!/usr/bin/env python3
"""Build clean propagation for the 190 relaxed-recovered supports_commons reps (fresh DB state,
post-252-commit). Split reassign (rep in ecod_rep) vs create; exclude stranding."""
import csv, psycopg2
WD="/home/rschaeff/work/ecod_consistency_2026/pfam_recheck"
cn=psycopg2.connect(host="dione",port=45000,dbname="ecod_protein",user="ecod"); cur=cn.cursor()

rec=[r for r in csv.DictReader(open(f"{WD}/t2_relaxed_verdicts_20260608.csv"))
     if r['relaxed_verdict']=='supports_commons (>=GA)']
uids=[int(r['ecod_uid']) for r in rec]
cmap={int(r['ecod_uid']):r['commons_f'] for r in rec}

# current ecod_rep state
cur.execute("""SELECT d.ecod_uid, d.f_id::text, c.is_deprecated
               FROM ecod_rep.domain d LEFT JOIN ecod_rep.cluster c ON c.id=d.f_id
               WHERE d.ecod_uid = ANY(%s)""", (uids,))
in_ecod={u:(f,dep) for u,f,dep in cur.fetchall()}
movers=[u for u in uids if u in in_ecod]   # reassign candidates
create_uids=[u for u in uids if u not in in_ecod]
# remaining reps per f_id excluding ALL recovered movers
cur.execute("""SELECT d.f_id::text, count(*) FROM ecod_rep.domain d
               WHERE (d.manual_rep OR d.provisional_manual_rep) AND NOT (d.ecod_uid = ANY(%s))
               GROUP BY d.f_id""", (movers,))
remain=dict(cur.fetchall())

clean=[]; strand=[]
for u in movers:
    old_f,dep=in_ecod[u]
    if old_f is None or dep or remain.get(old_f,0)>0: clean.append(u)
    else: strand.append(u)

with open(f"{WD}/t2_recover_reassign.csv","w",newline="") as fh:
    w=csv.writer(fh); w.writerow(['ecod_uid','new_f_id'])
    for u in clean: w.writerow([u, cmap[u]])
# create reps full data
cur.execute("""SELECT dm.ecod_uid, dm.domain_id, p.source_id, p.source_type, dm.range_definition
               FROM ecod_commons.domains dm JOIN ecod_commons.proteins p ON p.id=dm.protein_id
               WHERE dm.ecod_uid = ANY(%s)""", (create_uids,))
cd={u:(dom,src,st,rng) for u,dom,src,st,rng in cur.fetchall()}
def strip(r): return r.split(':',1)[1] if ':' in r else r
with open(f"{WD}/t2_recover_create.csv","w",newline="") as fh:
    w=csv.writer(fh); w.writerow(['ecod_uid','f_id','ecod_domain_id','ecod_source_id','seqid_range','dtype'])
    for u in create_uids:
        dom,src,st,rng=cd[u]
        w.writerow([u, cmap[u], dom, src, strip(rng), 'experimental structure' if st=='pdb' else 'computed structural model'])
cn.close()
print(f"recovered total: {len(uids)}")
print(f"  reassign clean (non-stranding): {len(clean)}")
print(f"  reassign stranding (held): {len(strand)}")
print(f"  create: {len(create_uids)}")
print(f"  clean propagation: {len(clean)+len(create_uids)}")
