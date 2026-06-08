#!/usr/bin/env python3
"""Build tranche-2 clean propagation inputs: 213 non-stranding reassign + 39 create.
Stranding excludes ALL supports_commons reassign movers from the remaining-reps check."""
import csv
import psycopg2
WD="/home/rschaeff/work/ecod_consistency_2026/pfam_recheck"
cn=psycopg2.connect(host="dione",port=45000,dbname="ecod_protein",user="ecod"); cur=cn.cursor()

sc=[r for r in csv.DictReader(open(f"{WD}/t2_verdicts_20260608.csv")) if r['verdict']=='supports_commons']
reassign=[r for r in sc if r['is_reassign']=='t']
create=[r for r in sc if r['is_reassign']=='f']
movers=tuple(int(r['ecod_uid']) for r in reassign)

# current f_id + deprecation per reassign mover
cur.execute("""SELECT d.ecod_uid, d.f_id::text, c.is_deprecated
               FROM ecod_rep.domain d LEFT JOIN ecod_rep.cluster c ON c.id=d.f_id
               WHERE d.ecod_uid = ANY(%s)""", (list(movers),))
info={u:(f,dep) for u,f,dep in cur.fetchall()}
# remaining reps per old_f excluding ALL movers
cur.execute("""SELECT d.f_id::text, count(*) FROM ecod_rep.domain d
               WHERE (d.manual_rep OR d.provisional_manual_rep) AND NOT (d.ecod_uid = ANY(%s))
               GROUP BY d.f_id""", (list(movers),))
remain=dict(cur.fetchall())

clean=[]; strand=[]
for r in reassign:
    u=int(r['ecod_uid']); old_f,dep=info.get(u,(None,None))
    if old_f is None or dep or remain.get(old_f,0)>0: clean.append(r)
    else: strand.append(r)

with open(f"{WD}/t2_reassign_clean.csv","w",newline="") as fh:
    w=csv.writer(fh); w.writerow(['ecod_uid','new_f_id'])
    for r in clean: w.writerow([r['ecod_uid'], r['commons_f']])
with open(f"{WD}/t2_strand_hold.csv","w",newline="") as fh:
    w=csv.writer(fh); w.writerow(['ecod_uid','commons_f','old_f'])
    for r in strand: w.writerow([r['ecod_uid'], r['commons_f'], info[int(r['ecod_uid'])][0]])

# create reps full data
cuids=[int(r['ecod_uid']) for r in create]
cur.execute("""SELECT dm.ecod_uid, dm.domain_id, p.source_id, p.source_type, dm.range_definition
               FROM ecod_commons.domains dm JOIN ecod_commons.proteins p ON p.id=dm.protein_id
               WHERE dm.ecod_uid = ANY(%s)""", (cuids,))
cd={u:(dom,src,st,rng) for u,dom,src,st,rng in cur.fetchall()}
cmap={int(r['ecod_uid']):r['commons_f'] for r in create}
def strip(r): return r.split(':',1)[1] if ':' in r else r
with open(f"{WD}/t2_create.csv","w",newline="") as fh:
    w=csv.writer(fh); w.writerow(['ecod_uid','f_id','ecod_domain_id','ecod_source_id','seqid_range','dtype'])
    for u in cuids:
        dom,src,st,rng=cd[u]
        w.writerow([u, cmap[u], dom, src, strip(rng),
                    'experimental structure' if st=='pdb' else 'computed structural model'])
cn.close()
print(f"reassign clean (non-stranding): {len(clean)}")
print(f"reassign stranding (held): {len(strand)}")
print(f"create: {len(create)}")
print(f"clean propagation total: {len(clean)+len(create)}")
