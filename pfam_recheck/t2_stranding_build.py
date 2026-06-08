#!/usr/bin/env python3
"""Assemble the 107 held stranding movers (70 tranche-2 + 37 tranche-2b) and gather per-old_f
signals to bucket each stranded old F-group: deprecate / re-seed-from-commons-rep / rep-select-hold."""
import csv, psycopg2
WD="/home/rschaeff/work/ecod_consistency_2026/pfam_recheck"
cn=psycopg2.connect(host="dione",port=45000,dbname="ecod_protein",user="ecod"); cur=cn.cursor()

# committed reassign uids (already moved out, not stranding)
committed=set()
for fn in ('t2_reassign_clean.csv','t2_recover_reassign.csv','t2_create.csv','t2_recover_create.csv'):
    committed |= {int(r['ecod_uid']) for r in csv.DictReader(open(f"{WD}/{fn}"))}

# candidate supports_commons reassign movers: direct (t2_verdicts) + recovered (relaxed >=GA)
cand={}
for r in csv.DictReader(open(f"{WD}/t2_verdicts_20260608.csv")):
    if r['verdict']=='supports_commons' and r['is_reassign']=='t':
        cand[int(r['ecod_uid'])]=r['commons_f']
for r in csv.DictReader(open(f"{WD}/t2_relaxed_verdicts_20260608.csv")):
    if r['relaxed_verdict']=='supports_commons (>=GA)':
        cand[int(r['ecod_uid'])]=r['commons_f']   # may include create ones; filtered by ecod_rep below

held=[u for u in cand if u not in committed]
cur.execute("SELECT ecod_uid, f_id::text FROM ecod_rep.domain WHERE ecod_uid = ANY(%s)", (held,))
cur_f={u:f for u,f in cur.fetchall()}
held=[u for u in held if u in cur_f]   # must exist in ecod_rep (reassign, not create)

rows=[]
for u in held:
    old_f=cur_f[u]; commons_f=cand[u]
    # old_f signals
    cur.execute("""SELECT c.is_deprecated, c.name,
        (SELECT count(*) FROM ecod_rep.domain d WHERE d.f_id=c.id),
        (SELECT count(*) FROM ecod_rep.domain d WHERE d.f_id=c.id AND d.ecod_uid<>%s),
        (SELECT count(*) FROM ecod_rep.domain d WHERE d.f_id=c.id AND d.ecod_uid<>%s AND (d.manual_rep OR d.provisional_manual_rep))
        FROM ecod_rep.cluster c WHERE c.id=%s""", (u,u,old_f))
    dep,name,nrep_dom,nother_dom,nother_rep=cur.fetchone()
    # commons members of old_f + any available commons rep (non-mover)
    cur.execute("""SELECT count(*) ,
        count(*) FILTER (WHERE (dm.is_manual_representative OR dm.is_provisional_representative) AND dm.ecod_uid<>%s)
        FROM ecod_commons.f_group_assignments fga JOIN ecod_commons.domains dm ON dm.id=fga.domain_id
        WHERE fga.f_group_id=%s AND dm.is_obsolete IS NOT TRUE""", (u,old_f))
    n_commons, n_commons_rep_avail = cur.fetchone()
    rows.append(dict(ecod_uid=u, commons_f=commons_f, old_f=old_f, old_dep=dep, old_name=(name or ''),
        old_ecodrep_doms=nrep_dom, old_other_doms=nother_dom, old_other_reps=nother_rep,
        old_commons_members=n_commons, old_commons_rep_avail=n_commons_rep_avail))
cn.close()

# bucket
def bucket(r):
    if r['old_dep']: return 'old_already_deprecated'
    if r['old_other_reps']>0: return 'NOT_stranding(other rep exists)'
    if r['old_commons_rep_avail']>0: return 'reseed_from_commons_rep'
    if r['old_commons_members']>0 or r['old_other_doms']>0: return 'rep_select_hold'
    return 'deprecate_empty'
from collections import Counter
for r in rows: r['disposition']=bucket(r)
fo=f"{WD}/t2_stranding_107_disposition.csv"
with open(fo,'w',newline='') as fh:
    w=csv.DictWriter(fh,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print(f"held stranding movers: {len(rows)}")
for k,v in Counter(r['disposition'] for r in rows).most_common(): print(f"  {k:34s} {v}")
print(f"\nwritten: {fo}")
