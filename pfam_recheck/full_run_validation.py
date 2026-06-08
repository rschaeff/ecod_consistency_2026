#!/usr/bin/env python3
"""Full non-circular validation of all 456 movers via Partitioner (loads reference once).
Per mover: partition with exclude_self + exclude_fgroups[old_f]; map re-derived domains
-> v294 F-group; verdict vs commons_f/old_f; cross-check vs Pfam final_class."""
import sys, csv, os
import xml.etree.ElementTree as ET
sys.path.insert(0, "/home/rschaeff/dev/pyecod_mini/src")
from pyecod_mini.api import Partitioner
from pyecod_mini.cli.config import PyEcodMiniConfig

WD = "/home/rschaeff/work/ecod_consistency_2026"
SUMDIR = f"{WD}/rep_validation_full/ecod_weekly_20260608/summaries"
OUTDIR = f"{WD}/rep_validation_full/partitions"; os.makedirs(OUTDIR, exist_ok=True)
LOOKUP = f"{WD}/pfam_recheck/v294_classification_lookup.tsv"
MOVERS = f"{WD}/pfam_recheck/movers_driver_input.tsv"
REVIEW = f"{WD}/pfam_recheck/movers_curator_review_20260605.csv"
csv.field_size_limit(sys.maxsize)

print("loading v294 lookup...")
v294 = {}
with open(LOOKUP) as fh:
    for ln in fh:
        p = ln.rstrip("\n").split("\t")
        if len(p) >= 5 and p[4]:
            v294[p[0]] = p[4]
print(f"  {len(v294):,} entries")

fc = {r["domain_id"]: r["final_class"] for r in csv.DictReader(open(REVIEW))}
movers = list(csv.DictReader(open(MOVERS), delimiter="\t"))
print(f"{len(movers)} movers")

cfg = PyEcodMiniConfig()
part = Partitioner()
part.load_references(
    domain_definitions_file=str(cfg.domain_definitions_file),
    reference_lengths_file=str(cfg.domain_lengths_file),
    protein_lengths_file=str(cfg.protein_lengths_file),
)
print("references loaded; partitioning...")

def concordance(struct, fclass):
    if struct == "supports_commons" and fclass == "APPLY": return "agree"
    if struct == "supports_old" and fclass == "HOLD": return "agree"
    if struct in ("other",) and fclass == "REROUTE": return "agree"
    if struct == "unclassified": return "no_evidence"
    return "check"

out = []
for i, m in enumerate(movers):
    dom, pdb, ch, old_f, commons_f = m["domain_id"], m["pdb_id"], m["chain_id"], m["old_f"], m["commons_f"]
    pc = f"{pdb}_{ch}"
    summ = f"{SUMDIR}/{pc}.summary.xml"
    outxml = f"{OUTDIR}/{dom}.excl.xml"
    rec = dict(domain_id=dom, query=pc, old_f=old_f, commons_f=commons_f,
               n_domains=0, rederived_f="", struct_verdict="error",
               final_class=fc.get(dom, ""), concordance="", note="")
    if not os.path.exists(summ):
        rec["note"] = "no summary"; out.append(rec); continue
    try:
        part.partition(summary_xml=summ, output_xml=outxml, pdb_id=pdb, chain_id=ch,
                       exclude_self=True, exclude_fgroups=[old_f] if old_f else None)
        root = ET.parse(outxml).getroot()
        rederived = []
        n = 0
        for d in root.findall(".//domain"):
            n += 1
            ref = d.get("reference_ecod_domain_id")
            f = v294.get(ref) if ref else None
            if f: rederived.append(f)
        rd = set(rederived)
        if n == 0: v = "unclassified"
        elif commons_f in rd: v = "supports_commons"
        elif old_f in rd: v = "supports_old"
        else: v = "other"
        rec.update(n_domains=n, rederived_f=";".join(sorted(rd)), struct_verdict=v,
                   concordance=concordance(v, fc.get(dom, "")))
    except Exception as e:
        rec["note"] = str(e)[:80]
    out.append(rec)
    if (i + 1) % 50 == 0: print(f"  {i+1}/{len(movers)}")

part.close()
with open(f"{WD}/pfam_recheck/full_validation_20260608.tsv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(out[0].keys()), delimiter="\t"); w.writeheader(); w.writerows(out)

from collections import Counter
print("\n=== struct verdict ===")
for k, n in Counter(r["struct_verdict"] for r in out).most_common(): print(f"  {k}: {n}")
print("\n=== struct verdict x Pfam final_class ===")
xt = Counter((r["struct_verdict"], r["final_class"]) for r in out)
for (s, f), n in sorted(xt.items()): print(f"  {s:17} x {f:8} : {n}")
print("\n=== concordance ===")
for k, n in Counter(r["concordance"] for r in out).most_common(): print(f"  {k}: {n}")
