# Beta Propeller H-group Remediation

**Date:** 2026-02-01
**Status:** Context gathering complete, analysis phase

---

## Problem Statement

The beta propeller H-group in ECOD is subdivided into T-groups primarily by **blade count**. Years of automated assignment have blurred these T-group distinctions, requiring systematic remediation.

---

## Objectives

1. Restore accurate T-group classification based on blade count
2. Identify and correct domain boundary errors (contamination from adjacent repeats)
3. Handle edge cases appropriately (partial propellers, multi-chain assemblies)

---

## Key Complications

### A. Contamination from Adjacent Repeat Domains

Beta propellers frequently occur near other repeat domains in eukaryotic proteins. This proximity can lead to:
- Non-propeller repeat sequences incorrectly included in propeller domain definitions
- Blade count misassignment due to contaminating repeats
- Ambiguous boundaries between propeller and adjacent domains

**Examples of adjacent repeat types:**
- WD40 repeats near LRR domains
- Kelch propellers near BTB domains
- Other solenoid repeats

### B. Partial/Open Propellers

Traditional view: Beta propellers are "closed" repeats where N- and C-termini are spatially proximal, completing the circular arrangement.

Reality: Some propellers are partial or open:
- Incomplete blade sets (e.g., 6.5 blades instead of 7)
- "Velcro" closure where terminal blades interdigitate (N-C distance ~20-25 Å even in "closed" propellers)
- Genuinely open propellers with exposed edges

**Implications:**
- Blade counting becomes ambiguous
- T-group assignment less clear-cut
- May need sub-classification for open vs. closed variants

### C. Multi-Subunit Propellers

Some beta propellers form from multiple distinct protein chains:
- Each chain contributes partial blades
- Complete propeller only exists in quaternary structure
- Single-chain analysis shows incomplete/unusual blade count

**Confirmed Example: T-group 5.1.10 (12-bladed)**
- PDB 4uzr: Dodecameric assembly (12 copies of ~72 aa chain)
- Each chain is OPEN topology (N-C distance ~40 Å)
- Individual ECOD domains represent single chains, not complete propeller
- Complete 12-bladed propeller only exists in biological assembly

---

## Approach

### Phase 1: Context Gathering (Complete)
- [x] Document ECOD beta propeller H-group organization
- [x] Count representatives per T-group
- [x] Identify provisional/manual representatives
- [x] Understand current classification criteria

### Phase 2: Analysis (Current)
- [ ] Identify misclassified domains (blade count vs. T-group mismatch)
- [ ] Detect contamination cases (domain length anomalies, non-propeller regions)
- [ ] Catalog partial propeller cases
- [ ] Flag multi-chain propeller instances

### Phase 3: Remediation Strategy
- [ ] Define structural criteria for blade counting
- [ ] Develop automated validation pipeline
- [ ] Establish review queue for edge cases
- [ ] Plan representative reassignment

### Phase 4: Implementation
- [ ] Correct T-group assignments
- [ ] Fix domain boundaries
- [ ] Update representatives
- [ ] Document exceptions and special cases

---

## ECOD Beta Propeller Organization

### H-group Information
- **H-group ID:** 5.1
- **H-group name:** beta-propeller
- **Total domains:** 29,214
- **Total T-groups:** 13
- **Total F-groups:** 392

### T-group Summary

| T-group | Name/Description | Blade Count | Domains | F-groups | Reps | Manual | Provisional |
|---------|------------------|-------------|---------|----------|------|--------|-------------|
| 5.1.1 | 4-bladed | 4 | 338 | 2 | 6 | 6 | 1 |
| 5.1.2 | 5-bladed | 5 | 1,512 | 26 | 41 | 28 | 23 |
| 5.1.3 | 6-bladed | 6 | 7,020 | 113 | 147 | 118 | 100 |
| 5.1.4 | 7-bladed | 7 | 17,206 | 174 | 241 | 187 | 140 |
| 5.1.5 | 8-bladed | 8 | 2,530 | 50 | 60 | 47 | 48 |
| 5.1.6 | deteriorated | varies | 3 | 1 | 1 | 1 | 0 |
| 5.1.7 | 10-bladed | 10 | 166 | 3 | 2 | 1 | 1 |
| 5.1.8 | putative conserved lipoprotein | varies | 38 | 3 | 3 | 3 | 2 |
| 5.1.9 | ABC toxin B component | varies | 16 | 2 | 3 | 1 | 2 |
| 5.1.10 | 12-bladed | 12 | 82 | 4 | 10 | 9 | 4 |
| 5.1.11 | 9-bladed | 9 | 205 | 9 | 10 | 9 | 8 |
| 5.1.12 | PERK/Ire1 luminal domains | varies | 78 | 4 | 6 | 4 | 3 |
| 5.1.13 | DCAF15 propeller | varies | 20 | 1 | 1 | 1 | 0 |
| **TOTAL** | | | **29,214** | **392** | **531** | **415** | **332** |

### Domain Source Distribution

| T-group | PDB Domains | AFDB Domains | Total |
|---------|-------------|--------------|-------|
| 5.1.1 | 131 | 207 | 338 |
| 5.1.2 | 903 | 609 | 1,512 |
| 5.1.3 | 2,810 | 4,210 | 7,020 |
| 5.1.4 | 6,780 | 10,426 | 17,206 |
| 5.1.5 | 1,147 | 1,383 | 2,530 |
| 5.1.6 | 2 | 1 | 3 |
| 5.1.7 | 31 | 135 | 166 |
| 5.1.8 | 2 | 36 | 38 |
| 5.1.9 | 14 | 2 | 16 |
| 5.1.10 | 12 | 70 | 82 |
| 5.1.11 | 32 | 173 | 205 |
| 5.1.12 | 20 | 58 | 78 |
| 5.1.13 | 9 | 11 | 20 |

---

## Length Analysis and Potential Misclassifications

### Key Insight: F-group-Specific Baselines Required

**Universal blade-size assumptions are invalid.** Different propeller families have fundamentally different blade architectures:

- **GH68 (Glyco_hydro_68)**: 5-bladed but ~80-100 aa per blade → 400-500 aa total
- **WD40**: 7-bladed with ~45 aa per blade → 300-350 aa total
- **Fungal lectins**: Can be trimeric assemblies where each chain is ~87 aa

Comparing all 5-bladed propellers to "150-300 aa expected" produces false positives.

### F-group-Specific Outlier Analysis

Using F-group median as baseline (outliers = >1.5x or <0.5x median):

| T-group | Total | Too Long | Too Short | % Long | % Short |
|---------|-------|----------|-----------|--------|---------|
| 5.1.1 (4-blade) | 332 | 3 | 9 | 0.9% | 2.7% |
| 5.1.2 (5-blade) | 1,433 | 65 | 64 | 4.5% | 4.5% |
| 5.1.3 (6-blade) | 6,585 | 37 | 387 | 0.6% | 5.9% |
| 5.1.4 (7-blade) | 15,047 | 442 | 979 | 2.9% | 6.5% |
| 5.1.5 (8-blade) | 2,272 | 85 | 219 | 3.7% | 9.6% |
| 5.1.7 (10-blade) | 162 | 48 | 44 | 29.6% | 27.2% |
| 5.1.10 (12-blade) | 79 | 9 | 3 | 11.4% | 3.8% |
| 5.1.11 (9-blade) | 193 | 16 | 62 | 8.3% | 32.1% |

**Note:** With F-group-specific baselines, 5.1.2 drops from "70% problematic" to "4.5% outliers" - most "too long" domains were normal for their family.

### Problem Categories Identified

#### 1. Multi-Chain Assemblies (Short PDB Domains)

F-groups where >20% of PDB domains are <50% of median - likely trimeric/oligomeric:

| F-group | Name | Median | PDB Count | Short PDB | % Short |
|---------|------|--------|-----------|-----------|---------|
| 5.1.3.21 | Fungal_lectin | 300 | 280 | 169 | 60.4% |
| 5.1.4.62 | PROPPIN | 350 | 61 | 21 | 34.4% |

**Example:** PDB 3zw1 (Fungal_lectin) - 87 aa chains form trimeric assembly

#### 2. Multi-Domain Merges (Long Domains with Discontinuous Ranges)

Domains >2x F-group median with multiple segments:

| Domain | Length | Median | Ratio | Segments |
|--------|--------|--------|-------|----------|
| A0A3Q0KPF9_F1_nD1 | 1,175 | 325 | 3.6x | 4 segments (320+360+175+320 aa) |
| A0A1C1CUU3_F1_nD1 | 690 | 190 | 3.6x | 3 segments with gaps |
| Q6CNR4_nD2 | 1,135 | 378 | 3.0x | 3 segments |

**Pattern:** Each segment is ~propeller-sized, gaps are linkers/insertions

#### 3. High-Variance F-groups

| F-group | Name | Total | Median | Outliers | % |
|---------|------|-------|--------|----------|---|
| 5.1.7.2 | Sortilin-Vps10 | 152 | 520 | 92 | 60% |
| 5.1.11.1 | eIF2A | 177 | 375 | 78 | 44% |
| 5.1.4.1 | WD40 | 7,892 | 345 | 654 | 8.3% |

These need individual investigation - may contain mixed populations.

---

## Special-Case T-groups

These T-groups don't have standard blade-count classifications:

| T-group | Name | Notes |
|---------|------|-------|
| 5.1.6 | deteriorated | Degraded propeller folds |
| 5.1.8 | NT01CX_1156 lipoprotein | Putative, unusual topology |
| 5.1.9 | ABC toxin B component | Specific functional class |
| 5.1.12 | PERK/Ire1 luminal domains | ER stress sensor domains |
| 5.1.13 | DCAF15 propeller | Specific protein family |

---

## Database Queries

### Primary Tables Used
- `ecod_rep.cluster` - Hierarchy names, Pfam annotations
- `ecod_commons.f_group_assignments` - Domain-to-hierarchy mapping
- `ecod_commons.domains` - Domain details, lengths, representatives

### Key Query: T-group Statistics
```sql
SELECT
    fa.t_group_id,
    COUNT(DISTINCT fa.domain_id) as domain_count,
    COUNT(DISTINCT fa.f_group_id) as f_group_count,
    COUNT(DISTINCT CASE WHEN d.is_representative THEN d.id END) as total_reps,
    COUNT(DISTINCT CASE WHEN d.is_manual_representative THEN d.id END) as manual_reps,
    COUNT(DISTINCT CASE WHEN d.is_provisional_representative THEN d.id END) as provisional_reps
FROM ecod_commons.f_group_assignments fa
JOIN ecod_commons.domains d ON fa.domain_id = d.id
WHERE fa.h_group_id = '5.1'
GROUP BY fa.t_group_id
ORDER BY fa.t_group_id
```

---

## Structural Investigation

### Multi-Chain Assembly Analysis (4uzr, T-group 5.1.10)

**Structure:** Pyrococcus horikoshii Ph1500 (PDB 4uzr)
- **Assembly:** Dodecameric (12 copies of same chain)
- **Chain length:** ~142 residues total, ECOD domain covers 72-143
- **N-C terminus distance:** ~40 Å (OPEN topology)
- **Conclusion:** Individual chains are open fragments; complete 12-bladed propeller only exists in biological assembly

### Standard Propeller Analysis (1erj, WD40)

- **N-C terminus distance:** ~21.5 Å
- **Note:** Even "closed" propellers have moderately distant termini due to velcro closure

### Topology Metrics

| Category | N-C Distance | Interpretation |
|----------|--------------|----------------|
| Closed (velcro) | 15-25 Å | Standard complete propeller |
| Intermediate | 25-35 Å | Possibly partial or unusual |
| Open | >35 Å | Multi-chain or partial fragment |

---

## Methodology

### Blade Detection: Not Feasible

**Tested:** FoldSeek iterative alignment using single-blade templates (~48 aa)

**Result:** Failed - blades too short for reliable structural matching.

**Alternatives rejected:**
- Pfam blade models: Considered unreliable by Pfam team
- HHrepID: Sequence-based, doesn't leverage structure

### Whole-Propeller Splitting: VALIDATED

**Tested:** FoldSeek iterative alignment using whole-propeller templates (~300-400 aa)

**Result:** Successfully identifies individual propeller domains within merged definitions.

| Test Case | Original | Domains Found | Coverage | TM-scores |
|-----------|----------|---------------|----------|-----------|
| Q9BZH6 (WDR11) | 885 aa | 2 | 74.4% | 0.50-0.76 |
| Q4DHX3 (UTP12) | 985 aa | 3 | 79.5% | 0.44-0.68 |
| P57737 (Coronin-7) | 855 aa | 2 | 84.7% | 0.70-0.82 |

**Key findings:**
- Correctly identifies 2-3 propellers per merged domain
- Linker regions (60-150 aa) properly excluded
- Each detected domain is ~300-400 aa (appropriate for 7-bladed WD40)
- TM-scores 0.4-0.8 indicate confident matches

### Implementation

Script: `iterative_propeller_split.py`

```bash
# Basic usage
python iterative_propeller_split.py merged_domain.pdb wd40_template.pdb

# With JSON output for batch processing
python iterative_propeller_split.py target.pdb template.pdb --json --cleanup

# Adjustable parameters
python iterative_propeller_split.py target.pdb template.pdb \
    --min-tmscore 0.3 \
    --min-length 100 \
    --min-remaining 100
```

**Algorithm:**
1. Run FoldSeek against whole-propeller template
2. If significant hit (TM ≥ 0.3, aligned ≥ 100 aa): record region, mask residues
3. Repeat until no more hits or too few residues remain
4. Return list of detected propeller domains with boundaries

---

## Remediation Strategy

### Approach: Length-Based Triage

Since blade detection isn't feasible, focus on:
1. **Obvious outliers** - Domains with extreme length deviations from expected
2. **Contamination detection** - "Too long" domains likely contain non-propeller regions
3. **Multi-chain flagging** - Short domains in assembly-forming T-groups
4. **Manual review queue** - Borderline cases for curator attention

### Priority Targets (F-group-Specific)

| Priority | Category | Criteria | Est. Count | Action |
|----------|----------|----------|------------|--------|
| HIGH | Multi-domain merges | >2x F-group median + discontinuous | ~200 | Split like Ig prototype |
| HIGH | Sortilin-Vps10 (5.1.7.2) | 60% outlier rate | ~90 | Investigate family |
| MEDIUM | eIF2A (5.1.11.1) | 44% outlier rate, bimodal | ~78 | Characterize populations |
| LOW | Assembly components | Fungal_lectin short PDBs | ~170 | Document as assembly chains |
| INFO | 5.1.10 (12-bladed) | Multi-chain by design | 82 | No action, representation issue |

### What We Can Fix

1. **Boundary trimming** - Remove obvious non-propeller extensions (like Ig prototype)
2. **T-group reassignment** - Move domains to correct blade-count group when length clearly indicates error
3. **Contamination splitting** - Separate propeller from adjacent repeat domains

### What We Cannot Fix (Without Blade Detection)

1. **Ambiguous blade counts** - 6 vs 7 blades when length is borderline
2. **Partial propellers** - Cannot determine if 5.5 vs 6 blades
3. **Unusual blade sizes** - Some families have non-standard blade lengths

---

## Next Steps

### Immediate Actions
1. **Batch process merge candidates**: Run `iterative_propeller_split.py` on 298 candidates
2. **Generate correction proposals**: For domains where splitting succeeds (TM > 0.4)
3. **Investigate Sortilin-Vps10 (5.1.7.2)**: Why 60% outlier rate?

### Batch Processing Pipeline

```bash
# 1. Download structures for merge candidates
for uniprot in $(cat merge_candidates.txt); do
    curl -s "https://alphafold.ebi.ac.uk/files/AF-${uniprot}-F1-model_v6.pdb" \
        -o structures/${uniprot}.pdb
done

# 2. Run splitting on each
for pdb in structures/*.pdb; do
    python iterative_propeller_split.py $pdb wd40_template.pdb \
        --json --cleanup >> split_results.jsonl
done

# 3. Filter high-confidence splits
jq 'select(.domains_found | length > 1) | select(.coverage_pct > 70)' \
    split_results.jsonl > corrections.jsonl
```

### Template Library (To Build)

| T-group | Blades | Template Needed | Example PDB |
|---------|--------|-----------------|-------------|
| 5.1.4 | 7 | WD40 | 1gxr |
| 5.1.3 | 6 | Kelch/6-blade | TBD |
| 5.1.5 | 8 | 8-blade | TBD |
| 5.1.2 | 5 | 5-blade | TBD |

### Deliverables
1. **Split results**: JSON output for 298 merge candidates
2. **Correction proposals**: New domain boundaries for successful splits
3. **F-group characterization**: Document expected lengths per family
4. **Assembly documentation**: Flag Fungal_lectin, PROPPIN, 5.1.10 as assembly-derived

### Files

| File | Description |
|------|-------------|
| `iterative_propeller_split.py` | Main splitting script |
| `multi_domain_merge_candidates.csv` | 298 candidates for splitting |
| `wd40_template.pdb` | 7-bladed WD40 template (1gxr) |
| `REMEDIATION_PLAN.md` | This document |

---

## References

- ECOD classification methodology
- Beta propeller structural biology literature
- Related: Ig domain remediation prototype (../ig_split_prototype/)
