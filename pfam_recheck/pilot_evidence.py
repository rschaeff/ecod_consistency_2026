#!/usr/bin/env python3
"""Generate domain_summary.xml evidence (BLAST+HHsearch, develop291) for the pilot movers,
by injecting them into a pyecod_prod WeeklyBatch (does NOT modify pyecod_prod)."""
import sys
sys.path.insert(0, "/home/rschaeff/dev/pyecod_prod/src")
from pyecod_prod.batch.weekly_batch import WeeklyBatch

BASE = "/home/rschaeff/work/ecod_consistency_2026/rep_validation"
SEQS = "/home/rschaeff/work/ecod_consistency_2026/pfam_recheck/pilot_seqs.tsv"

pilot = []
with open(SEQS) as fh:
    for ln in fh:
        f = ln.rstrip("\n").split("\t")
        if len(f) < 5:
            continue
        pilot.append(dict(uid=f[0], domain_id=f[1], pdb=f[2], chain=f[3], seq=f[4]))

batch = WeeklyBatch(release_date="20260608", pdb_status_dir="/tmp/none",
                    base_path=BASE, reference_version="develop291")
batch.create_batch()
for p in pilot:
    batch.manifest.add_chain(p["pdb"], p["chain"], p["seq"], len(p["seq"]))
batch.manifest.save()
print(f"chains added: {len(batch.manifest.data['chains'])}")

batch.generate_fastas()
print("FASTAs generated; submitting BLAST...")
batch.run_blast(partition="96GB", wait=True)
batch.process_blast_results()

need = batch.manifest.chains_needing_hhsearch()
print(f"chains needing HHsearch: {len(need)}")
if need:
    batch.run_hhsearch(partition="96GB", wait=True)
    batch.process_hhsearch_results()

batch.generate_summaries()
print(f"BATCH_PATH={batch.batch_path}")
print("DONE")
