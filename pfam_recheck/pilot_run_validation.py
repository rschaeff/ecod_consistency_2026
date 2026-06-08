#!/usr/bin/env python3
"""Pilot non-circular validation: per mover, run pyecod-mini with --exclude-self
and --exclude-fgroups <old_f>, then map re-derived domains -> v294 F-group and verdict.
Uses --exclude-fgroups (one id) instead of the driver's giant exclude_domains list
(which exceeds csv field limits for big F-groups)."""
import csv, subprocess, tempfile, os
import xml.etree.ElementTree as ET

WD = "/home/rschaeff/work/ecod_consistency_2026"
SUMDIR = f"{WD}/rep_validation/ecod_weekly_20260608/summaries"
OUTDIR = f"{WD}/rep_validation/partitions"; os.makedirs(OUTDIR, exist_ok=True)
LOOKUP = f"{WD}/pfam_recheck/v294_classification_lookup.tsv"
PILOT = f"{WD}/pfam_recheck/pilot_driver_input.tsv"
PYECOD = "/home/rschaeff/.local/bin/pyecod-mini"

# load v294 domain_id -> f_group
print("loading v294 lookup...")
v294 = {}
with open(LOOKUP) as fh:
    for ln in fh:
        p = ln.rstrip("\n").split("\t")
        if len(p) >= 5 and p[4]:
            v294[p[0]] = p[4]
print(f"  {len(v294):,} entries")

rows = list(csv.DictReader(open(PILOT), delimiter="\t"))
print(f"validating {len(rows)} pilot movers\n")
out = []
for r in rows:
    dom, pdb, ch, old_f, commons_f = r["domain_id"], r["pdb_id"], r["chain_id"], r["old_f"], r["commons_f"]
    pc = f"{pdb}_{ch}"
    summ = f"{SUMDIR}/{pc}.summary.xml"
    outxml = f"{OUTDIR}/{pc}.excl.xml"
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as tf:
        tf.write((old_f or "") + "\n"); fgfile = tf.name
    cmd = [PYECOD, pc, "--summary-xml", summ, "--output", outxml, "--exclude-self"]
    if old_f:
        cmd += ["--exclude-fgroups", fgfile]
    res = subprocess.run(cmd, capture_output=True, text=True)
    os.unlink(fgfile)
    rederived, n = [], 0
    masked = ""
    try:
        root = ET.parse(outxml).getroot()
        for d in root.findall(".//domain"):
            n += 1
            ref = d.get("reference_ecod_domain_id")
            f = v294.get(ref) if ref else None
            if f:
                rederived.append(f)
        st = root.find(".//statistics")
        m = root.find(".//parameters")
    except Exception as e:
        out.append(dict(domain_id=dom, query=pc, old_f=old_f, commons_f=commons_f,
                        n_domains=0, rederived_f="", verdict="error", note=str(e)[:60]))
        print(f"  {dom} ({pc}): ERROR {str(e)[:50]}")
        continue
    rd = set(rederived)
    if n == 0:
        verdict = "unclassified"
    elif commons_f in rd:
        verdict = "supports_commons"
    elif old_f in rd:
        verdict = "supports_old"
    else:
        verdict = "other"
    out.append(dict(domain_id=dom, query=pc, old_f=old_f, commons_f=commons_f,
                    n_domains=n, rederived_f=";".join(sorted(rd)), verdict=verdict, note=""))
    print(f"  {dom} ({pc}): {verdict}  [{n} dom; rederived={';'.join(sorted(rd)) or '-'}]")

with open(f"{WD}/pfam_recheck/pilot_validation_20260608.tsv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(out[0].keys()), delimiter="\t"); w.writeheader(); w.writerows(out)
from collections import Counter
print("\n=== verdict summary ===")
for k, v in Counter(r["verdict"] for r in out).most_common():
    print(f"  {k}: {v}")
