# ECOD Classification Changes: Batch 2 Implementation Report

**Date**: 2026-02-20
**Source**: Curator images in `jimin_list_2/`
**Status**: All 5 changes implemented and verified

---

## Overview

This document records the implementation of the second batch of curator-provided
classification corrections. Changes were applied to both `ecod_rep` (hierarchy +
representative domains) and `ecod_commons` (comprehensive domain assignments).

| # | Change | Domains Affected | Method |
|---|--------|-----------------|--------|
| 1 | TLC/ELO/TMEM120 unification | 11 reps, 14 commons | X-group create + F-group merge |
| 2 | VSG + HpHbR merge | 8 reps, 393 commons | X-group merge |
| 3a | Cyanophycin_syn extraction + split | 36 split -> 72 new | X-group create + domain split |
| 3b | ATP-grasp_6 extraction | 1 rep + 29 commons moved | X-group create + F-group move |
| 4 | KH/MMR boundary fix | 34 domains corrected | Deprecate-and-recreate |
| 5 | Helicase_C,RIG-I_C split | 146 domains processed | Split/reclass/pseudo-group |

---

## Implementation Architecture

Scripts in `curator_changes/`, building on the shared library from batch 1:

```
curator_changes/
  curator_ops.py                  # Shared database operations (batch 1+2)
  boundary_methods.py             # HMMER and alignment boundary determination
  change_definitions_batch2.py    # Declarative configuration for all batch 2 changes
  implement_batch2_merges.py      # Changes 1, 2
  implement_batch2_extractions.py # Changes 3a, 3b
  implement_batch2_boundary.py    # Change 4
  implement_batch2_helicase.py    # Change 5
```

All scripts support `--dry-run` (default), `--execute`, and `--analyze-only`.
HMMER searches use Pfam gathering thresholds (`--cut_ga`) for family classification.

---

## Change 1: TLC/ELO/TMEM120 Unification

Created new X-group **X:9000** ("TMEM120/ELO/TLC") under a.7 (alpha bundles),
with H:9000.1 and T:9000.1.1. Merged 11 scattered F-groups into 3 by Pfam:

| New F-group | Pfam | Sources | Reps | Commons |
|-------------|------|---------|------|---------|
| 9000.1.1.1 (TLC) | PF03798 | 7 F-groups | 7 | 8 |
| 9000.1.1.2 (ELO) | PF01151 | 2 F-groups | 2 | 3 |
| 9000.1.1.3 (TMEM120) | PF07851 | 2 F-groups | 2 | 3 |

All 11 source F-groups deprecated. Source X/H/T groups deprecated where emptied.

---

## Change 2: VSG + HpHbR X-group Merge

Merged X:3633 (Haptoglobin-hemoglobin receptor) into X:1189 (VSG N-terminal).
Renamed to "VSG (variant surface glycoprotein) N-terminal domain and
haptoglobin-hemoglobin receptor" at X/H/T levels. Reassigned architecture to
a.7 (alpha bundles).

| F-group | Pfam | Action | Reps | Commons |
|---------|------|--------|------|---------|
| 1189.1.1.1 (Trypan_glycop) | PF00913 | Stayed | 3 | 153 |
| 1189.1.1.2 (VSG_B) | PF13206 | Stayed | 1 | 117 |
| 1189.1.1.3 (GARP) | PF16731 | Moved from 3633 | 2 | 63 |
| 1189.1.1.4 (HpHbR) | PF20933 | Moved from 3633 | 1 | 59 |
| 1189.1.1.5 (ESAG1) | PF03238 | Moved from 3633 | 1 | 1 |

X/H/T 3633 fully deprecated.

---

## Change 3b: ATP-grasp_6 Extraction

Extracted F:2003.1.10.18 (ATP-grasp_6, PF18419) from X:2003 (Rossmann-like).

Created new hierarchy under a.17:
- X:9002 (ATP-grasp_6), H:9002.1, T:9002.1.1, F:9002.1.1.1

Moved 1 rep + 29 commons from F:2003.1.10.18 to F:9002.1.1.1.
Deprecated F:2003.1.10.18.

---

## Change 3a: Cyanophycin_syn Extraction + Domain Split

Extracted F:2007.3.1.5 (Cyanophycin_syn, PF18921) from X:2007 (Flavodoxin-like).
Each domain contains a C-terminal ATP-grasp_6 segment that was split off and
assigned to the new F:9002.1.1.1 (from change 3b).

Created new hierarchy under a.17:
- X:9003 (Cyanophycin_syn), H:9003.1, T:9003.1.1, F:9003.1.1.1

### Boundary determination

HMMER (PF18921) detected the Cyanophycin_syn portion in all 36 domains. However,
the C-terminal ATP-grasp_6 portion (PF18419) is only ~41 amino acids in these
domains -- too short for reliable HMMER detection even at E-value 10.

**Fallback**: A reference-based split was used. All 36 domains are from the same
cyanophycin synthetase protein family (PDBs 7lg5, 7lgj, 7lgq, 7txu, 7txv, 7wac,
7wad, 7wae, 7waf -- different chains/structures). The curator-specified reference
boundary (domain-local position 162) was applied deterministically:

- N-terminal (residues 1-162) -> Cyanophycin_syn (F:9003.1.1.1)
- C-terminal (residues 163-end) -> ATP-grasp_6 (F:9002.1.1.1)

The 41aa ATP-grasp products are consistent with existing ATP-grasp_6 domains
in F:9002.1.1.1, which range from 45-56aa.

### Domain naming

- N-terminal product reuses the original domain_id (e.g., `e7lg5A4`)
- C-terminal product gets the next available domain number with collision checks
  against all existing IDs including obsolete (e.g., `e7lg5A5`)

### Result

| Outcome | Count |
|---------|-------|
| Split (Cyanophycin + ATP-grasp) | 36 |
| New domains created | 72 |
| Originals obsoleted | 36 |

F:2007.3.1.5 deprecated. F:9003.1.1.1 (Cyanophycin_syn) has 36 active domains.
F:9002.1.1.1 (ATP-grasp_6) has 65 active domains (29 original + 36 split products).

---

## Change 4: KH_domain-like / MMR_HSR1 Boundary Fix

Corrected the KH_dom-like (PF14714) / MMR_HSR1 (PF01926) domain boundary in
17 Der GTPase PDB structures. The KH domain was over-extended ~35 residues into
the MMR region.

### Boundary determination

hmmscan with `--cut_ga` was run on each KH domain against PF14714 to find the
correct KH start position. The MMR domain was then extended to cover the gap
(MMR end = new KH start - 1).

No pre-existing HMMER hits were found in the database for these domains; all
boundaries were determined via hmmscan.

### Result

All 17 pairs (34 domains) corrected via deprecate-and-recreate:

| Metric | Before | After |
|--------|--------|-------|
| KH domain size | 113-123aa | 77-81aa |
| MMR domain size | 151-200aa | +31-39aa each |

All domains are ecod_commons only (no ecod_rep entries).

PDB pairs: 2hjg, 3j8g, 4dcs, 4dct, 4dcv, 5dn8, 5m7h, 5mbs, 6xrsA/B/C/D,
6yxx, 6yxy, 7am2, 7aoi, 9bs0.

---

## Change 5: Helicase_C,RIG-I_C Split

Deprecated F:3930.1.1.1 (Helicase_C,RIG-I_C). Its 146 domains were classified
by HMMER (PF18119 RIG-I_C, PF00271 Helicase_C, gathering thresholds) and
distributed to three destinations:

| Classification | Count | Destination |
|---------------|-------|-------------|
| SPLIT (both detected) | 32 | RIG-I_C -> F:3930.1.1.2, Helicase_C -> F:2004.1.1.30 |
| RIG-I_C only | 13 | Reassigned to F:3930.1.1.2 |
| Helicase_C only | 16 | Reassigned to F:2004.1.1.30 |
| NO_HIT (neither detected) | 85 | Moved to T:3930.1.1.0 (pseudo-group) |

The 1 ecod_rep domain (e3tmiA3) was among the SPLIT group: deleted from ecod_rep,
split into e3tmiA3 (RIG-I_C) + e3tmiA4 (Helicase_C).

Excluded PDBs 7tnx, 8dvr, 8g7t (already correctly split in DB).

### Split product naming

Same convention as Change 3a:
- N-terminal (RIG-I_C) reuses original domain_id
- C-terminal (Helicase_C) gets next available number with collision check

64 new domains created from 32 splits. 32 originals obsoleted.

### NO_HIT domain analysis

85 domains (all UniProt, 100-170aa, median 135aa) did not pass the Pfam gathering
threshold for either RIG-I_C (GA=23.20, model 141aa) or Helicase_C (GA=23.50,
model 110aa). Full Pfam-A scans revealed:

| Category | Count | Notes |
|----------|-------|-------|
| No Pfam hit at all | 77 | Structurally assigned but sequence-divergent |
| Dicer_PBD (PF20930) | 6 | F:3930.1.1.6 already exists for this family |
| SHOC1_ATPase (PF17825) | 2 | Different domain entirely |

All 85 were moved to the .0 pseudo-group (T:3930.1.1.0), which is an ecod_commons
convention for domains that belong to a T-group structurally but cannot be assigned
to a specific F-group. The .0 does not exist in ecod_rep.

### Result

F:3930.1.1.1 deprecated (0 ecod_rep domains, 32 obsolete commons).

| F-group | Active domains |
|---------|---------------|
| 3930.1.1.0 (pseudo) | 93 (8 pre-existing + 85 new) |
| 3930.1.1.2 (RIG-I_C) | 146 |
| 2004.1.1.30 (Helicase_C) | 3,918 |

---

## Verification Summary

### Source F-groups (all deprecated, 0 active domains)

| F-group | Change | Obsolete remaining | Status |
|---------|--------|-------------------|--------|
| 11 scattered F-groups | 1 | 0 | Deprecated |
| 3633.1.1.1-3 | 2 | 0 | Deprecated |
| 2003.1.10.18 | 3b | 0 | Deprecated |
| 2007.3.1.5 | 3a | 0 | Deprecated |
| 3930.1.1.1 | 5 | 32 (split originals) | Deprecated |

### New hierarchy created

| ID | Type | Name | Change |
|----|------|------|--------|
| X:9000 | X/H/T | TMEM120/ELO/TLC | 1 |
| X:9002 | X/H/T | ATP-grasp_6 | 3b |
| X:9003 | X/H/T | Cyanophycin_syn | 3a |

### Backups

Pre-implementation backups taken 2026-02-20:
- `backups/ecod_rep_backup_20260220.dump` (7.8MB)
- `backups/ecod_commons_backup_20260220.dump` (2.0GB)

---

## Implementation Order (as executed)

| Order | Change | Script | Domains | Notes |
|-------|--------|--------|---------|-------|
| 1 | B2_1 (TLC/ELO/TMEM120) | implement_batch2_merges.py | 14 | New X:9000 |
| 2 | B2_2 (VSG/HpHbR) | implement_batch2_merges.py | 393 | X-group merge + rename |
| 3 | B2_3b (ATP-grasp_6) | implement_batch2_extractions.py | 30 | New X:9002, prerequisite for 3a |
| 4 | B2_3a (Cyanophycin_syn) | implement_batch2_extractions.py | 36 -> 72 | New X:9003, reference-based split |
| 5 | B2_4 (KH/MMR boundary) | implement_batch2_boundary.py | 34 | hmmscan boundary determination |
| 6 | B2_5 (Helicase/RIG-I_C) | implement_batch2_helicase.py | 146 -> 210 | HMMER GA threshold, .0 fallback |

---

*Document created: 2026-02-20*
*Last updated: 2026-02-20*
*Based on curator images in jimin_list_2/*
