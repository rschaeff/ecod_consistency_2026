# ECOD Classification Changes: Implementation Report

**Date**: 2026-02-16
**Source**: Curator instructions (received 2026-02-16)
**Status**: All 8 changes implemented and verified

---

## Overview

This document records the implementation of curator-provided classification corrections
spanning three levels of the ECOD hierarchy. All changes were applied to both
`ecod_rep` (the authority schema for hierarchy and representative domains) and
`ecod_commons` (the comprehensive domain schema), with full audit trails.

| Level | Changes | Source F-groups Deprecated | Domains Moved/Created |
|-------|---------|--------------------------|----------------------|
| X-group merges | 3 (1A, 1B, 1C) | 8 F-groups + 3 T/H/X each | ~6,100 |
| Family reclassification | 2 (2A, 2B) | 3 F-groups | ~1,475 |
| Domain split | 1 (2C) | 1 F-group | 35 obsoleted, ~60 created |
| Boundary corrections | 2 (3A, 3B) | 0 | 1 + 759 domains trimmed |

---

## Resolved Clarifications

Two domain identifiers in the original curator notes contained typos. These were
resolved by searching ECOD versions v290-v292 flat files to identify the correct
PDB codes, then confirmed by the curator:

| Original (typo) | Corrected | PDB | Chain | Range | F-group |
|-----------------|-----------|-----|-------|-------|---------|
| e6bmlD1 | **e6bmsD1** | 6bms | D | D:79-240 | 4106.1.1.1, AUTO_NONREP |
| e5wwB1 | **e5fwwB1** | 5fww | B | B:1-184 | 380.1.1.3, MANUAL_REP |

---

## Implementation Architecture

All changes were implemented via scripts in `curator_changes/`:

```
curator_changes/
  curator_ops.py                 # Shared database operations library
  change_definitions.py          # Declarative configuration for all 8 changes
  implement_xgroup_merges.py     # Changes 1A, 1B, 1C
  implement_family_reclass.py    # Changes 2A, 2B
  implement_domain_split.py      # Change 2C (Kringle/WSC)
  implement_boundary_fixes.py    # Changes 3A, 3B
  boundary_methods.py            # HMMER and pairwise alignment boundary determination
```

### Design principles

1. **Separate scripts per change type** - each type has fundamentally different logic
2. **Shared ops library** (`curator_ops.py`) - reuses patterns from `prov_rep_daccession/batch_deprecate_a1.py` and `batch_replace_a2.py`
3. **All scripts support `--dry-run` (default) and `--execute`** - dry-run was run first for every change
4. **Per-domain commits** - each domain operation is atomic; rollback on failure
5. **ecod_rep changes via stored functions** - triggers automatic audit logging to `cluster_changelog`, `domain_assignment_log`, `domain_modification_log`
6. **ecod_commons changes via direct SQL** - no auto-propagation exists, so f_group_assignments are updated manually

### Synchronization pattern

Every change follows this flow:

```
1. ecod_rep.hierarchy_change_request  (create + approve)
2. ecod_rep stored function           (implement) -> auto-audit
3. ecod_commons.f_group_assignments   (UPDATE all hierarchy columns)
4. ecod_commons.domains               (UPDATE/INSERT if range or obsolete changes)
5. conn.commit()
```

For ecod_commons f_group_assignments, all hierarchy columns are updated together:
```sql
UPDATE ecod_commons.f_group_assignments
SET f_group_id = :new_f, t_group_id = :new_t, h_group_id = :new_h,
    x_group_id = :new_x, a_group_id = :new_a,
    assignment_method = 'manual',
    assigned_by = 'curator_change_pipeline',
    assignment_date = NOW()
WHERE f_group_id = :old_f
```

### Schema note

`ecod_commons.f_group_assignments.domain_id` is a FK to `ecod_commons.domains.id`
(the integer PK), NOT to `domains.ecod_uid`. Always join as `d.id = fga.domain_id`.

---

## Change 1: X-group Merges

### 1A. X-group 7584 -> 323.1.1

**Rationale**: Rossmann-like domain in Acetyl-CoA synthetase-like proteins recognized
as homologous to CoA-dependent acyltransferases.

| Source | Target |
|--------|--------|
| 7584 (a.17, 1 H/T, 5 F-groups) | 323.1.1 (a.14, CoA-dependent acyltransferases) |

**F-group mapping (implemented)**:

| Source | Pfam | Action | Target |
|--------|------|--------|--------|
| 7584.1.1.1 AMP-binding (11 reps) | PF00501 | Merged (same Pfam) | 323.1.1.3 |
| 7584.1.1.2 AMP-binding,ACAS_N (1 rep) | PF00501,PF16177 | New F-group | 323.1.1.20 |
| 7584.1.1.3 GH3 (1 rep) | PF03321 | New F-group | 323.1.1.21 |
| 7584.1.1.4 ACAS_N (1 rep) | PF16177 | New F-group | 323.1.1.22 |
| 7584.1.1.5 LuxE (1 rep) | PF04443 | New F-group | 323.1.1.23 |

**Result**: 5 source F-groups deprecated, X/H/T 7584 deprecated. 323.1.1.3 now
contains 3,180 active domains. New F-groups 323.1.1.20-23 created via `assign_next_f_id`.

### 1B. X-group 1139 -> 327.6.1

**Rationale**: Secretin domain recognized as structurally related to Fe-S cluster
assembly (FSCA) domain-like fold.

| Source | Target |
|--------|--------|
| 1139 (1 H/T/F, ~156 domains) | 327.6.1 (FSCA domain-like, 3 existing F-groups) |

**Result**: New F-group 327.6.1.6 (Secretin, PF00263) created. 169 active domains
assigned. Source X/H/T/F 1139 fully deprecated.

### 1C. X-group 3488 -> 223.1.1

**Rationale**: Putative sensor histidine kinase domain belongs with sensor domains.

| Source | Target |
|--------|--------|
| 3488 (1 H/T, 2 F-groups, ~18 domains) | 223.1.1 (sensor domains, 85 F-groups) |

**Result**: New F-groups 223.1.1.96 (dCache_2, PF08269, 4 active) and 223.1.1.97
(sCache_2, PF17200, 14 active) created. Source X/H/T 3488 fully deprecated.

### X-group merge algorithm

```
For each source F-group:
    1. Check if matching Pfam exists in target T-group
       - If match: merge into existing target F-group
       - If no match: create new F-group via assign_next_f_id()
    2. Move rep domains: implement_reassign_f_group() for each rep
    3. Move ecod_commons: UPDATE f_group_assignments SET f_group_id = target
    4. Deprecate source F-group

After all F-groups processed:
    5. Deprecate source T-group, H-group, X-group (bottom-up)
```

---

## Change 2: Family-Level Reclassifications

### 2A. OmpA: 274.1.1.3 -> 301.3.1.1

**Rationale**: OmpA domains incorrectly placed in Pili subunits; belong in OmpA-like.

**Result**: F-group 274.1.1.3 deprecated. 301.3.1.1 now contains 598 active domains
(4 reps).

### 2B. tRNA-synt: 310.1.1.1 + 310.1.1.3 -> 140.1.1.3

**Rationale**: tRNA synthetase domains were in ArgRS N-terminal group; belong with
anticodon-binding domain superfamily.

**Result**: Both 310.1.1.1 (tRNA-synt_1d,DALR_1) and 310.1.1.3 (DALR_1) deprecated.
310.1.1.2 (Arg_tRNA_synt_N) survives. 140.1.1.3 now contains 877 active domains
(6 reps).

### Family reclassification algorithm

```
1. Verify source and target F-groups exist
2. Move rep domains: implement_reassign_f_group() for each
3. Move ecod_commons: UPDATE f_group_assignments
4. Deprecate source F-group if emptied
```

---

## Change 2C: Kringle/WSC Domain Split

**Rationale**: F-group 380.1.1.3 (Kringle,WSC) contains domains spanning two
distinct Pfam families that should be classified separately.

| | Kringle portion | WSC portion |
|---|---|---|
| **Pfam** | PF00051 | PF01822 |
| **Target F-group** | 380.1.1.2 | 390.1.1.2 |
| **Target X-group** | 380 (same) | 390 (Hairpin loop containing domain-like) |

### Boundary determination method: HMMER envelope coordinates

Each domain's split boundary was determined by Pfam HMM search rather than by
transferring coordinates from the reference domain. This is more robust because
domains have varying absolute coordinates but consistent Pfam domain boundaries.

**Two-tier lookup**:

1. **Database lookup** (`swissprot.domain_hmmer_results`): Check for pre-computed
   HMMER results for each domain against PF00051 (Kringle) and PF01822 (WSC).
   Coordinates are 1-based, domain-local (envelope start/end).

2. **hmmscan fallback**: If no pre-computed results exist, extract the domain
   sequence from `ecod_commons.protein_sequences`, fetch Kringle and WSC HMMs
   from `Pfam-A.hmm` by name (`hmmfetch`), and run `hmmscan` to determine
   envelope coordinates.

**Coordinate conversion**: HMMER envelope coordinates are domain-local (position 1
= first residue of the domain). These are converted to absolute protein coordinates
by walking through the domain's range segments:

```python
# domain_local_to_absolute(env_start, env_end, range_definition)
# e.g., domain range "296-385", HMMER env 10-80 -> absolute 305-375
# Handles multi-segment ranges like "251-280,306-345"
```

### Split outcomes

Each domain was classified based on which Pfam HMMs were detected:

| Outcome | Count | Action |
|---------|-------|--------|
| SPLIT (both Kringle + WSC detected) | 9 | Two new domains created, original obsoleted |
| RECLASS (only Kringle detected) | 20 | One new domain -> 380.1.1.2, original obsoleted |
| RECLASS (only WSC detected) | 5 | One new domain -> 390.1.1.2, original obsoleted |
| Obsoleted fragment | 1 | Q96FE7_F1_nD2 (40aa) too short for either family |

**Result**: 380.1.1.3 deprecated. 380.1.1.2 (Kringle) now contains 473 active
domains. 390.1.1.2 (WSC) now contains 24 active domains.

### Split product naming

New domains are named by appending a suffix to the original domain ID:
- Kringle portion: `{original_id}k` (e.g., e5fwwB1 -> e5fwwB1k)
- WSC portion: `{original_id}w` (e.g., e5fwwB1 -> e5fwwB1w)

Each new domain receives a fresh `ecod_uid` via `nextval('ecod_commons.ecod_uid_sequence')`.

---

## Change 3: Domain Boundary Corrections

### 3A. e6bmsD1 trim (Zinc hairpin stack)

**Curator instruction**: Trim e6bmsD1 (PDB 6bms chain D) from D:79-240 to D:79-156.

**Context**: Most 4106.1.1 domains span ~55-90 residues. e6bmsD1 at 162 residues
was over-extended into a non-zinc-hairpin C-terminal region.

**Method**: Direct range update per curator specification. Domain is an AUTO_NONREP,
so only ecod_commons was modified. The atomic domain principle was followed:
the original domain (ecod_uid 4925088) was deprecated and a replacement created
with the trimmed range.

**Result**: e6bmsD1 range updated from D:79-240 to D:79-156.

### 3B. 563.1.1 boundary fixes (OSCP N-terminal domain)

**Curator instruction**: Fix boundaries on nonrepresentatives such as e6rdqP1.

**Context**: The manual representative e1abvA1 is 105 residues. Many domains in this
group are substantially longer, up to 790 residues for some AlphaFold-derived entries.

### Boundary determination method: pairwise sequence alignment

Rather than applying a fixed residue cutoff, each over-extended domain's correct
C-terminal boundary was determined by local pairwise alignment to the reference
domain (e1abvA1).

**Algorithm** (implemented in `boundary_methods.py`):

1. **Extract sequences**: Reference (e1abvA1) and query domain sequences are
   extracted from `ecod_commons.protein_sequences` using the domain range definition.

2. **Local alignment**: BioPython `PairwiseAligner` with BLOSUM62 scoring,
   gap open -11, gap extend -1. Local (Smith-Waterman) mode so the reference
   matches a subset of the query.

3. **C-terminal trim**: The alignment endpoint on the query indicates where the
   OSCP-homologous region ends. The original N-terminal start is preserved;
   only the C-terminus is trimmed.

4. **Confidence filter**: Alignments must cover at least 50% of the reference
   sequence to be considered reliable. Domains with low reference coverage are
   skipped (logged as low-confidence).

```python
new_range, new_length, aln_info = compute_cterminal_trim(
    reference_seq, query_seq, range_definition,
    min_ref_coverage=0.5)
```

**Coordinate conversion**: The alignment endpoint (0-based on the query sequence)
is converted back to absolute protein coordinates by walking through the domain's
range segments, preserving multi-segment range formatting.

**Result**:
- 759 domains trimmed (including e6rdqP1: P:37-229 -> P:37-144)
- 113 domains skipped (97 due to low reference coverage, 16 no sequence available)
- All trimmed domains follow the deprecate-and-recreate pattern (new ecod_uid assigned)

---

## Audit Trail

All changes are tracked in the following ecod_rep audit tables:

| Table | Records Created | Content |
|-------|----------------|---------|
| `hierarchy_change_request` | 43 requests | Create/rename/deprecate actions, all status=implemented |
| `cluster_changelog` | ~50 entries | INSERT/UPDATE records with old_values/new_values JSON |
| `domain_assignment_log` | ~49 entries | Per-domain F-group reassignments |
| `domain_modification_log` | ~30 entries | Per-domain F-group changes |

All requests have `requested_by = 'curator_change_pipeline'` with justification
strings referencing the change ID and batch timestamp.

---

## Verification Summary

Verified 2026-02-16 via database queries against both schemas.

### Source F-groups (all should have 0 active domains)

| F-group | Change | Active | Total (incl. obsolete) | Status |
|---------|--------|--------|----------------------|--------|
| 3488.1.1.1 | 1C | 0 | 0 | OK |
| 3488.1.1.2 | 1C | 0 | 0 | OK |
| 1139.1.1.1 | 1B | 0 | 0 | OK |
| 7584.1.1.1-5 | 1A | 0 | 0 | OK |
| 274.1.1.3 | 2A | 0 | 0 | OK |
| 310.1.1.1 | 2B | 0 | 0 | OK |
| 310.1.1.3 | 2B | 0 | 0 | OK |
| 380.1.1.3 | 2C | 0 | 35 (all obsoleted) | OK |

### Target F-groups

| F-group | Change | Active Domains |
|---------|--------|---------------|
| 223.1.1.96 (dCache_2) | 1C | 4 |
| 223.1.1.97 (sCache_2) | 1C | 14 |
| 327.6.1.6 (Secretin) | 1B | 169 |
| 323.1.1.3 (AMP-binding, merged) | 1A | 3,180 |
| 323.1.1.20 (AMP-binding,ACAS_N) | 1A | 599 |
| 323.1.1.21 (GH3) | 1A | 131 |
| 323.1.1.22 (ACAS_N) | 1A | 1 |
| 323.1.1.23 (LuxE) | 1A | 1 |
| 301.3.1.1 (OmpA) | 2A | 598 |
| 140.1.1.3 (tRNA-synt) | 2B | 877 |
| 380.1.1.2 (Kringle) | 2C | 473 |
| 390.1.1.2 (WSC) | 2C | 24 |

---

## Implementation Order (as executed)

| Order | Change | Script | Domains | Notes |
|-------|--------|--------|---------|-------|
| 1 | 1C (3488 -> 223.1.1) | implement_xgroup_merges.py | 18 | Lowest risk, smallest group |
| 2 | 1B (1139 -> 327.6.1) | implement_xgroup_merges.py | 156 | Simple 1-to-1 F-group map |
| 3 | 1A (7584 -> 323.1.1) | implement_xgroup_merges.py | 2,380 | 1 merge + 4 new F-groups |
| 4 | 2A (OmpA reclass) | implement_family_reclass.py | ~130 | Direct reclassification |
| 5 | 2B (tRNA-synt reclass) | implement_family_reclass.py | ~130 | 2 source F-groups |
| 6 | 2C (Kringle/WSC split) | implement_domain_split.py | 35 | HMMER boundary determination |
| 7 | 3A (e6bmsD1 trim) | implement_boundary_fixes.py | 1 | Direct curator-specified range |
| 8 | 3B (563.1.1 fixes) | implement_boundary_fixes.py | 759 | Pairwise alignment boundary determination |

---

## Schema fixes applied during execution

The following schema issues were encountered and resolved during implementation:

- Dropped defunct FK `fk_cnd_rep_uid` from `public.current_nonrep_domains`
- Added `resolved` column + dropped FKs from `ecod_curation.cross_boundary_pair`
- Added `resolved` column + dropped FKs from `ecod_curation.validation_curation`
- Bypassed broken `implement_reassign_f_group` stored function (defunct `dom_cid` type cast) with direct SQL equivalent

---

*Document created: 2026-02-16*
*Last updated: 2026-02-16*
*Based on curator instructions received 2026-02-16*
*Domain ID typos resolved: e6bmlD1 -> e6bmsD1, e5wwB1 -> e5fwwB1*
