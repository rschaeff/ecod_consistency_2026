# ECOD Classification Change Plan

**Date**: 2026-02-16
**Source**: Curator instructions (received 2026-02-16)
**Status**: Draft - all items clarified, ready for review

---

## Overview

This document translates curator-provided classification corrections into a structured action plan. Changes span three levels of the ECOD hierarchy:

| Level | Changes | Domains Affected |
|-------|---------|------------------|
| X-group merges | 3 | ~2,554 |
| Family reclassification | 3 | ~5+ families |
| Domain boundary corrections | 2 | Individual domains + siblings |

---

## Resolved Clarifications

Two domain identifiers in the original curator notes contained typos, now confirmed:

| Original (typo) | Corrected | PDB | Chain | Current Range | F-group |
|-----------------|-----------|-----|-------|---------------|---------|
| e6bmlD1 | **e6bmsD1** | 6bms | D | D:79-240 | 4106.1.1.1 (Zinc hairpin stack), AUTO_NONREP |
| e5wwB1 | **e5fwwB1** | 5fww | B | B:1-184 | 380.1.1.3 (Kringle,WSC), MANUAL_REP |

---

## Change 1: X-group Merges

Three X-groups are to be dissolved and their contents merged into existing groups. In each case the source X-group is small and single-hierarchy (one H-group, one T-group, one F-group).

### 1A. X-group 7584 → X-group 323

**Rationale**: Rossmann-like domain in Acetyl-CoA synthetase-like proteins is recognized as homologous to CoA-dependent acyltransferases.

| | Source (7584) | Target (323) |
|---|---|---|
| **Name** | Rossmann-like domain in Acetyl-CoA synthetase-like proteins | CoA-dependent acyltransferases |
| **Architecture** | a.17 | a.14 |
| **Hierarchy** | 1 H-group, 1 T-group, 5 F-groups | 1 H-group, 1 T-group, 17 F-groups |
| **Domains** | ~2,380 | ~3,901 |

**Actions**:
1. Reassign all domains from 7584.1.1 F-groups into 323.1.1
2. Map source F-groups to target F-groups (note: 323.1.1 already contains an AMP-binding F-group 323.1.1.3, which overlaps with 7584.1.1.1 AMP-binding)
3. Retire X-group 7584, H-group 7584.1, T-group 7584.1.1

**F-group mapping** (requires curator input on whether to merge or create new F-groups):

| Source F-group | Pfam | Candidate Target | Action |
|----------------|------|------------------|--------|
| 7584.1.1.1 (AMP-binding, 11 domains) | PF00501 | 323.1.1.3 (AMP-binding, 3 domains) | Merge? |
| 7584.1.1.2 (AMP-binding,ACAS_N) | PF00501,PF16177 | 323.1.1.4 (AMP-binding,AMP-binding_C)? | New F-group? |
| 7584.1.1.3 (GH3, 1 domain) | PF16887 | -- | New F-group in 323.1.1 |
| 7584.1.1.4 (ACAS_N, 1 domain) | PF16177 | -- | New F-group in 323.1.1 |
| 7584.1.1.5 (LuxE, 1 domain) | PF02382 | -- | New F-group in 323.1.1 |

### 1B. X-group 1139 → T-group 327.6.1

**Rationale**: Secretin domain recognized as structurally related to Fe-S cluster assembly (FSCA) domain-like fold.

| | Source (1139) | Target (327.6.1) |
|---|---|---|
| **Name** | Secretin domain | Fe-S cluster assembly (FSCA) domain-like |
| **Parent X-group** | 1139 (standalone) | 327 (Alpha-lytic protease prodomain-like) |
| **Hierarchy** | 1 H/T/F | T-group with 3 F-groups |
| **Domains** | ~156 | ~45 |

**Actions**:
1. Create new F-group under T-group 327.6.1 for Secretin domains (e.g., 327.6.1.4 Secretin)
2. Reassign all 156 domains from 1139.1.1.1 → 327.6.1.4
3. Retire X-group 1139, H-group 1139.1, T-group 1139.1.1

### 1C. X-group 3488 → T-group 223.1.1

**Rationale**: Putative sensor histidine kinase domain recognized as belonging to the sensor domain superfamily.

| | Source (3488) | Target (223.1.1) |
|---|---|---|
| **Name** | Putative sensor histidine kinase domain | Sensor domains |
| **Parent X-group** | 3488 (standalone) | 223 (Profilin-like) |
| **Hierarchy** | 1 H/T, 2 F-groups | T-group with 85 F-groups |
| **Domains** | ~18 | ~2,458 |

**Actions**:
1. Map 3488.1.1.1 (dCache_2) and 3488.1.1.2 (sCache_2) into 223.1.1
2. Check if 223.1.1 already has dCache_2 or sCache_2 F-groups (if so, merge; if not, create new)
3. Reassign all 18 domains
4. Retire X-group 3488, H-group 3488.1, T-group 3488.1.1

---

## Change 2: Family-Level Reclassifications

Three sets of domains are to be moved from one F-group to another based on Pfam family membership.

### 2A. OmpA domains: 274.1.1 → 301.3.1

**Rationale**: OmpA-family domains were placed in the Pili subunits group but belong in the dedicated OmpA-like group.

| | Source | Target |
|---|---|---|
| **F-group** | 274.1.1 (Pili subunits) | 301.3.1 (OmpA-like) |
| **X-group** | 274 (Type IV pilin-like) | 301 (Bacillus chorismate mutase-like) |
| **Affected family** | 274.1.1.3 (OmpA, 1 rep: e6aeoA3) | 301.3.1.1 (OmpA, 472 domains) |

**Actions**:
1. Identify all domains in 274.1.1.3 (OmpA sub-family)
2. Reassign to 301.3.1.1 (existing OmpA F-group in target)
3. Retire 274.1.1.3 if emptied

**Impact**: Small - moving a handful of domains to a group that already contains the same Pfam family (PF00691).

### 2B. tRNA-synt_1d/DALR_1 domains: 310.1.1 → 140.1.1

**Rationale**: tRNA synthetase-related domains were placed in the ArgRS N-terminal domain group but belong with the anticodon-binding domain superfamily.

| | Source | Target |
|---|---|---|
| **F-group** | 310.1.1 (Arginyl-tRNA synthetase N-terminal) | 140.1.1 (Anticodon-binding domain) |
| **X-group** | 310 (ArgRS N-terminal) | 140 (same name as H/T) |
| **Affected families** | 310.1.1.1 (tRNA-synt_1d,DALR_1) and 310.1.1.3 (DALR_1) | 140.1.1.3 (tRNA-synt_1d,DALR_1, 4 reps) |

**Actions**:
1. Identify all domains in 310.1.1.1 and 310.1.1.3
2. Reassign to 140.1.1.3 (existing tRNA-synt_1d,DALR_1 family in target)
3. Retire emptied F-groups in 310.1.1
4. If 310.1.1 retains only Arg_tRNA_synt_N (310.1.1.2), the T-group survives

**Impact**: Small - target already has an exact Pfam-family match.

### 2C. Kringle,WSC split: 380.1.1.3 → 380.1.1.2 + 390.1.1

**Rationale**: F-group 380.1.1.3 (Kringle,WSC) contains domains with two distinct structural regions that should be classified separately. The Kringle portion belongs in the Kringle family, and the WSC portion belongs in the WSC family.

| | Kringle portion | WSC portion |
|---|---|---|
| **Target F-group** | 380.1.1.2 (Kringle) | 390.1.1.2 (WSC) |
| **Target X-group** | 380 (same) | 390 (Hairpin loop containing domain-like) |
| **Residue example** | 30-115 | 116-213 |

**Source**: F-group 380.1.1.3 (Kringle,WSC) - 1 rep domain, likely a small number of total members.

**Actions**:
1. For each domain in 380.1.1.3:
   - Split the domain range into Kringle region and WSC region (using the boundary pattern exemplified by the curator: ~residue 115-116)
   - Create a new domain entry for the Kringle portion → assign to 380.1.1.2
   - Create a new domain entry for the WSC portion → assign to 390.1.1.2
   - Retire the original merged domain
2. Retire F-group 380.1.1.3 after all members are split
3. Update representative status as needed in target F-groups

**Complexity**: Medium. This requires domain splitting (new domain entries), not just reclassification. Each domain needs its range recalculated. The curator-provided example (residues 30-115 / 116-213) serves as a template, but individual domains may have slightly different boundaries.

**Reference domain**: e5fwwB1 (PDB 5fww chain B, B:1-184, MANUAL_REP in 380.1.1.3). Curator specifies: residues 30-115 = Kringle, residues 116-213 = WSC.

---

## Change 3: Domain-Level Corrections

### 3A. Boundary trim in 4106.1.1 (Zinc hairpin stack)

**Curator instruction**: e6bmsD1 (PDB 6bms chain D) range D:79-240 → trim to approximately D:79-156

**Interpretation**: Trim the C-terminal boundary of a zinc hairpin stack domain, removing ~84 residues that likely belong to an adjacent domain or are unstructured.

**Actions**:
1. Update e6bmsD1 range from D:79-240 to approximately D:79-156
2. Check whether the trimmed region (157-240) constitutes a separate domain or is unstructured
3. Check other 4106.1.1 domains for similar over-extension (there are 14 PDB domains total in this group)

**Context**: Most 4106.1.1 domains span ~55-90 residues (e.g., e2dktA2: A:82-137). The e6bmsD1 domain at 162 residues is notably longer, consistent with the curator's assessment that it needs trimming.

### 3B. Boundary fixes in 563.1.1 (OSCP N-terminal domain)

**Curator instruction**: Fix boundaries on nonrepresentatives such as e6rdqP1.

**Current state of e6rdqP1**: Range P:37-229 (193 residues), F70 representative.

**Context**: The manual representative for 563.1.1 is e1abvA1 (A:1-105, 105 residues). Domain sizes in this group vary considerably:

| Size range | Examples | Notes |
|------------|----------|-------|
| ~100-120 aa | e1abvA1 (1-105), e4b2qW1 (11-120) | Consistent with OSCP N-terminal domain |
| ~150-170 aa | e5arhS1 (1-168), e5t4oL1 (3-162) | Moderately larger |
| ~190-230 aa | **e6rdqP1 (37-229)**, e6fkfd1 (71-249), e6tmiG1 (73-252) | Likely over-extended |

**Actions**:
1. Identify all 563.1.1 domains with ranges substantially longer than the manual representative (~105 aa)
2. Determine correct C-terminal boundary for e6rdqP1 and similar cases
3. Trim domain ranges to exclude non-OSCP regions
4. Reassess F70/F40 representative status after boundary corrections

**Scope**: At least 3-5 domains appear over-extended (>190 aa vs ~105 aa reference). A systematic review of all 200 domains in this group may be warranted.

---

## Implementation Priority

| Priority | Change | Complexity | Risk |
|----------|--------|------------|------|
| 1 | 1C. X-group 3488 → 223.1.1 | Low | Low (18 domains) |
| 2 | 1B. X-group 1139 → 327.6.1 | Low | Low (156 domains) |
| 3 | 2A. OmpA reclassification | Low | Low (handful of domains) |
| 4 | 2B. tRNA-synt reclassification | Low | Low |
| 5 | 3A. 4106.1.1 boundary trim (e6bmsD1) | Low | Low (single domain) |
| 6 | 3B. 563.1.1 boundary fixes | Medium | Medium (systematic review needed) |
| 7 | 1A. X-group 7584 → 323 | Medium | Medium (2,380 domains, F-group mapping) |
| 8 | 2C. Kringle,WSC split (e5fwwB1 + siblings) | High | Medium (domain splitting, new entries) |

---

## Database Operations Summary

Each change type requires different database operations:

### X-group merges (Changes 1A-1C)
```
UPDATE domain_level SET f_uid = <target_f_uid> WHERE f_uid = <source_f_uid>
-- Then cascade: retire source F-group, T-group, H-group, X-group
```

### Family reclassifications (Changes 2A-2B)
```
UPDATE domain_level SET f_uid = <target_f_uid> WHERE uid IN (<affected_domain_uids>)
-- Retire emptied source F-groups
```

### Domain splitting (Change 2C)
```
-- For each domain in 380.1.1.3:
INSERT INTO domain (...) VALUES (<kringle_portion>)   -- new domain
INSERT INTO domain (...) VALUES (<wsc_portion>)       -- new domain
UPDATE domain SET is_obsolete = true WHERE uid = <original_uid>
-- Assign new domains to respective F-groups
```

### Boundary corrections (Changes 3A-3B)
```
UPDATE domain SET domain_range = <new_range> WHERE uid = <domain_uid>
```

---

## Appendix: Full Hierarchy Context

### X-group 323 (merge target for 7584)
```
Architecture: a.14
X: 323 - CoA-dependent acyltransferases
  H: 323.1
    T: 323.1.1
      F: 323.1.1.1  2-oxoacid_dh (1 rep)
      F: 323.1.1.3  AMP-binding (3 reps)    ← potential merge target for 7584.1.1.1
      F: 323.1.1.4  AMP-binding,AMP-binding_C (1 rep)
      F: 323.1.1.7  Transferase (3 reps)
      F: 323.1.1.9  WS_DGAT_cat,WS_DGAT_C (3 reps)
      F: 323.1.1.10 Tri3 (2 reps)
      + 11 more F-groups (0-1 reps each)
```

### X-group 327 (merge target for 1139)
```
Architecture: a.9
X: 327 - Alpha-lytic protease prodomain-like (21 H-groups)
  ...
  H: 327.6 - Fe-S cluster assembly (FSCA) domain-like
    T: 327.6.1 (45 domains)
      F: 327.6.1.1 NifU
      F: 327.6.1.2 FeS_assembly_P (1 rep)
      F: 327.6.1.3 Germane (1 rep)
      F: 327.6.1.4 Secretin ← NEW (from 1139)
```

### X-group 223 (merge target for 3488)
```
Architecture: a.12
X: 223 - Profilin-like (11 H-groups)
  H: 223.1 - sensor domains
    T: 223.1.1 (2,458 domains, 85 F-groups)
      F: 223.1.1.3  GAF (3 reps)
      F: 223.1.1.14 PAS_4 (3 reps)
      F: 223.1.1.51 MCP-like_PDC_1 (3 reps)
      + 82 more F-groups
      ← NEW: dCache_2 and sCache_2 from 3488
```

---

*Document created: 2026-02-16*
*Based on curator instructions received 2026-02-16*
*Domain ID typos resolved 2026-02-16: e6bmlD1 → e6bmsD1, e5wwB1 → e5fwwB1*
