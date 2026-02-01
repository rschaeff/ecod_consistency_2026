# Length Anomaly Investigation Summary

## Overview

This document summarizes the investigation of four high-priority H-groups identified by the full database length anomaly scan. These groups showed >70% "too long" anomaly rates, indicating systematic domain boundary problems.

**Investigation Date**: 2026-02-01

**Analysis Approach**:
1. Characterized F-group distributions within each H-group
2. Identified merge candidates (domains significantly longer than median)
3. Tested iterative FoldSeek splitting where applicable
4. Assessed remediation feasibility

---

## Executive Summary

| H-group | Name | Outliers | % Too Long | Merge Candidates | Remediation |
|---------|------|----------|------------|------------------|-------------|
| **377.1** | LIM domains | 2,257 | 88% | 58 | ✅ Iterative splitting works |
| **5050.1** | MFS transporters | 2,306 | 86% | 1,650 | ✅ Iterative splitting works |
| **108.1** | EF-hand domains | 1,935 | 81% | 781 | ⚠️ Metal-binding complexity |
| **386.1** | Zinc fingers | 5,032 | 74% | 1,179 | ⚠️ Metal-binding complexity |
| **11.1** | Immunoglobulin | 10,785+ | varies | ~1,000+ | ✅ Iterative splitting works |
| **5.1** | Beta propellers | 29,214 | varies | ~298 | ✅ Whole-propeller splitting works |

**Key Finding**: The H-groups fall into three distinct categories:
1. **Structural repeat domains** (LIM, MFS, Ig, beta propellers): Clear splitting boundaries, iterative FoldSeek works well
2. **Metal-binding domains** (EF-hand, zinc fingers): More complex, metal coordination affects domain definition
3. **Disordered region contamination** (Ig domains especially): DPAM merged structured domains with disordered linkers

---

## H-group 377.1: LIM Domains

### Domain Architecture
```
Single LIM domain: ~30-35 aa (double zinc finger motif)
ECOD median: 30-34 aa
Proteins often have 2-6 tandem LIM domains
```

### Investigation Results

| Metric | Value |
|--------|-------|
| Total domains | 7,162 |
| Outliers (>2x median) | 2,257 |
| Merge candidates (>60 aa) | 58 |
| PDB candidates | 10 |
| AFDB candidates | 48 |

### Length Distribution (LIM F-group 377.1.1.5)
- 83% in 20-39 aa range (single LIM)
- Outliers up to 258 aa (~7-8 LIM domains merged)

### Iterative Splitting Test
**Target**: Q80Y24_F1 (199 aa merged LIM domain)

| Domain | Residues | Length | TM-score |
|--------|----------|--------|----------|
| LIM 1 | 191-220 | 30 aa | 0.708 |
| LIM 2 | 125-160 | 36 aa | 0.680 |
| LIM 3 | 221-247 | 27 aa | 0.679 |
| LIM 4 | 116-183 | 32 aa | 0.479 |

**Coverage**: 62.8% (linker regions unmatched)
**Result**: ✅ Splitting works well

### Output Files
- Candidates: `/home/rschaeff/work/ecod_consistency_2026/lim_domain_test/lim_merge_candidates.csv`
- Splitting script: `/home/rschaeff/work/ecod_consistency_2026/lim_domain_test/iterative_lim_split.py`
- Template: PDB 2egq chain A (40 aa LIM domain)

---

## H-group 5050.1: MFS Transporters

### Domain Architecture
```
Full MFS transporter: ~450-500 aa (12 TM helices)
  ├── N-terminal half: ~200-220 aa (6 TM helices)
  ├── Cytoplasmic linker: ~50-80 aa
  └── C-terminal half: ~200-220 aa (6 TM helices)

ECOD treats each 6-TM bundle as a separate domain
```

### Investigation Results

| Metric | Value |
|--------|-------|
| Total domains | 10,334 |
| Outliers | 2,306 |
| Merge candidates (>400 aa) | 1,650 |
| PDB candidates | 0 (all properly split!) |
| AFDB candidates | 1,650 |

### Key Insight
- **All PDB structures** have MFS split into 2 domains (N and C halves)
- **All AFDB models** with full transporters have both halves merged
- This is a systematic AFDB classification issue

### Length Distribution (Sugar_tr F-group)
- 78% in 150-300 aa range (half-transporters)
- 21% in 400-600 aa range (full transporters, merged)

### Iterative Splitting Test
**Target**: A0A0D2ESK5_F1 (555 aa merged MFS domain)

| Domain | Residues | Length | TM-score |
|--------|----------|--------|----------|
| MFS-N | 37-252 | 216 aa | 0.603 |
| MFS-C | 328-521 | 194 aa | 0.610 |

**Coverage**: 73.9% (linker loop unmatched)
**Result**: ✅ Splitting works perfectly

### Output Files
- Candidates: `/home/rschaeff/work/ecod_consistency_2026/mfs_domain_test/mfs_merge_candidates.csv`
- Template: PDB 1pw4 chain A residues 4-225 (N-terminal MFS half)

---

## H-group 108.1: EF-hand Domains

### Domain Architecture
```
Single EF-hand motif: ~30-40 aa (helix-loop-helix, Ca²⁺ binding)
EF-hand pair (ECOD unit): ~70-90 aa (2 motifs)
Calmodulin-like: 2 pairs = 140-160 aa (4 EF-hands)
```

### Investigation Results

| Metric | Value |
|--------|-------|
| Total domains | 11,655 |
| Outliers | 1,935 |
| Merge candidates (>160 aa) | 781 |
| PDB candidates | 57 (7.3%) |
| AFDB candidates | 724 |

### Complexity Factors
⚠️ **Unlike LIM/MFS, PDB structures also have outliers**

This suggests inherent variability in EF-hand domain definitions due to:
1. **Ca²⁺-dependent stability**: Domain boundaries may shift with calcium occupancy
2. **Structural variability**: Helix geometry varies more than rigid folds
3. **No metal site tracking**: Classification doesn't explicitly consider Ca²⁺ positions

### Length Distribution
| Range | Count | Est. EF-hand Pairs |
|-------|-------|-------------------|
| 160-200 aa | 509 | ~2 pairs (borderline) |
| 200-300 aa | 195 | ~3 pairs |
| 300-400 aa | 23 | ~4-5 pairs |
| 400-500 aa | 50 | ~5-6 pairs |
| 500+ aa | 4 | 6+ pairs |

### Remediation Assessment
⚠️ **Iterative splitting may not be appropriate**
- The 160-200 aa candidates (509) might be legitimate 2-pair domains
- Focus remediation on larger outliers (>300 aa, 77 total)
- Consider domain definition includes metal binding context

### Output Files
- Candidates: `/home/rschaeff/work/ecod_consistency_2026/length_anomaly_analysis/efhand_merge_candidates.csv`

---

## H-group 386.1: Zinc Fingers (β-β-α)

### Domain Architecture
```
Single C2H2 zinc finger: ~25-30 aa
  - β-β-α topology
  - Zn²⁺ coordinated by 2 Cys + 2 His
  - Linker to next finger: ~5-7 aa

Proteins often have 3-15+ tandem zinc fingers
```

### Investigation Results

| Metric | Value |
|--------|-------|
| Total domains | 10,723 |
| Outliers | 5,032 |
| Merge candidates (>70 aa) | 1,179 |
| PDB candidates | 92 (7.8%) |
| AFDB candidates | 1,087 |

### Complexity Factors
⚠️ **Zinc fingers exist at the boundary of "structured domains"**

Key issues:
1. **Simple topology**: β-β-α is flagged by DPAM as potentially "too simple"
2. **Metal-dependent structure**: Without Zn²⁺, the motif is disordered
3. **Constitutive simplicity**: The simple topology IS the domain (not a fragment)

### Length Distribution (zf-C2H2)
- 63% in 25-49 aa range (1-2 zinc fingers)
- 26% in 50-74 aa range (2-3 zinc fingers)
- ~8% larger (3+ zinc fingers merged)

### PDB Validation
PDB structures with tandem zinc fingers ARE properly split:
- 1f2i: 12 zinc finger domains, avg 32 aa each
- TFIIIA (1tf3/1tf6): 9 fingers, each ~29-33 aa

### Remediation Assessment
⚠️ **Mixed approach needed**
- Large merges (>150 aa, 83 candidates) could be split
- Smaller candidates may reflect legitimate domain definitions
- Need to consider that "simple topology" is valid for metal-stabilized domains

### Output Files
- Candidates: `/home/rschaeff/work/ecod_consistency_2026/length_anomaly_analysis/zf_merge_candidates.csv`

---

## H-group 11.1: Immunoglobulin Domains

### Domain Architecture
```
Single Ig domain: ~90 aa (β-sandwich fold)
Proteins often have 2-12+ tandem Ig domains
DPAM frequently merges adjacent Ig domains + disordered linkers
```

### Investigation Results

| Metric | Value |
|--------|-------|
| Test case | Q60ZN5_nD12 (740 aa merged domain) |
| Expected domains | 8 (based on segments) |
| Actual Ig domains | 5 (confirmed by FoldSeek) |
| Disordered linkers | 4 regions (185 aa, 25% of total) |
| Template library | 323 templates from 190 F-groups |

### Key Discovery: Disordered Region Contamination

**Root cause of overlong Ig domain definitions:**
- DPAM merged structured Ig domains WITH disordered linker regions
- Linker regions have mean pLDDT < 30 (extremely low confidence)
- FoldSeek against entire ECOD database (63K domains) returns zero hits for linkers
- These are **not missing domains** - they are intrinsically disordered regions (IDRs)

### pLDDT Analysis of Unmatched Segments

| Segment | Length | Mean pLDDT | % Low | Status |
|---------|--------|------------|-------|--------|
| 2151-2245 | 95 aa | 25.8 | 100% | DISORDERED |
| 2066-2100 | 35 aa | 26.4 | 100% | DISORDERED |
| 2111-2140 | 30 aa | 26.4 | 100% | DISORDERED |
| 2276-2300 | 25 aa | 23.9 | 100% | DISORDERED |

### FoldSeek vs DALI Comparison

| Metric | DALI | FoldSeek |
|--------|------|----------|
| Domains found | 4 | 5 |
| Coverage | 38.4% | 42.0% |
| Time | ~minutes | 8.3 sec |
| Speed factor | 1x | ~50x faster |

### Recommendations

1. **Pre-filter by pLDDT** - Exclude regions with mean pLDDT < 50 before domain assignment
2. **Use FoldSeek** - 50x faster than DALI, slightly better sensitivity
3. **Multi-template library** - 323 Ig templates from 190 F-groups available
4. **TM-score ≥ 0.3** - Reasonable threshold for Ig domain identification

### Output Files
- Prototype results: `/home/rschaeff/work/ecod_consistency_2026/ig_split_prototype/PROTOTYPE_RESULTS.md`
- FoldSeek script: `/home/rschaeff/work/ecod_consistency_2026/ig_split_prototype/iterative_foldseek_prototype.py`
- Template library: `/home/rschaeff/work/ecod_consistency_2026/ig_split_prototype/ig_template_library.json`

---

## H-group 5.1: Beta Propellers

### Domain Architecture
```
Beta propeller: Circular arrangement of 4-12 "blades"
Each blade: ~40-50 aa (4-stranded β-sheet)
Total propeller: 150-600 aa depending on blade count
T-groups organized by blade count (4, 5, 6, 7, 8, 9, 10, 12)
```

### Investigation Results

| Metric | Value |
|--------|-------|
| Total domains | 29,214 |
| T-groups | 13 (organized by blade count) |
| F-groups | 392 |
| Multi-domain merge candidates | 298 |

### T-group Distribution

| T-group | Blades | Domains | F-groups | Outliers |
|---------|--------|---------|----------|----------|
| 5.1.1 | 4 | 338 | 2 | 3.6% |
| 5.1.2 | 5 | 1,512 | 26 | 9.0% |
| 5.1.3 | 6 | 7,020 | 113 | 6.5% |
| 5.1.4 | 7 | 17,206 | 174 | 9.4% |
| 5.1.5 | 8 | 2,530 | 50 | 13.3% |
| 5.1.7 | 10 | 166 | 3 | 56.8% |
| 5.1.10 | 12 | 82 | 4 | 15.2% |
| 5.1.11 | 9 | 205 | 9 | 40.4% |

### Key Insight: F-group-Specific Baselines Required

**Universal blade-size assumptions are invalid.** Different propeller families have fundamentally different blade architectures:
- **GH68 (Glyco_hydro_68)**: 5-bladed but ~80-100 aa per blade → 400-500 aa total
- **WD40**: 7-bladed with ~45 aa per blade → 300-350 aa total
- **Fungal lectins**: Trimeric assemblies where each chain is ~87 aa

### Problem Categories Identified

| Category | Description | Examples |
|----------|-------------|----------|
| Multi-chain assemblies | Short PDB domains that form oligomeric propellers | Fungal_lectin (60% short), 5.1.10 (12-bladed) |
| Multi-domain merges | >2x F-group median with discontinuous ranges | WDR11 (885aa→2 propellers), UTP12 (985aa→3 propellers) |
| High-variance F-groups | Bimodal length distributions | Sortilin-Vps10 (60% outliers), eIF2A (44% outliers) |

### Iterative Splitting Validation

**Tested:** FoldSeek with whole-propeller templates (~300-400 aa)

| Test Case | Original | Domains Found | Coverage | TM-scores |
|-----------|----------|---------------|----------|-----------|
| Q9BZH6 (WDR11) | 885 aa | 2 | 74.4% | 0.50-0.76 |
| Q4DHX3 (UTP12) | 985 aa | 3 | 79.5% | 0.44-0.68 |
| P57737 (Coronin-7) | 855 aa | 2 | 84.7% | 0.70-0.82 |

**Result:** ✅ Whole-propeller splitting works well (blade detection failed - blades too short)

### Special Cases

| T-group | Name | Issue |
|---------|------|-------|
| 5.1.6 | deteriorated | Degraded propeller folds |
| 5.1.10 | 12-bladed | Multi-chain assemblies (e.g., PDB 4uzr: 12 chains form complete propeller) |
| 5.1.8-9, 5.1.12-13 | Various | Specific functional classes, non-standard blade counts |

### Output Files
- Remediation plan: `/home/rschaeff/work/ecod_consistency_2026/beta_propeller_remediation/REMEDIATION_PLAN.md`
- Splitting script: `/home/rschaeff/work/ecod_consistency_2026/beta_propeller_remediation/iterative_propeller_split.py`
- Merge candidates: `/home/rschaeff/work/ecod_consistency_2026/beta_propeller_remediation/multi_domain_merge_candidates.csv`

---

## Metal-Binding Domains: Special Considerations

### Shared Characteristics

| Feature | EF-hands | Zinc Fingers |
|---------|----------|--------------|
| Metal ion | Ca²⁺ | Zn²⁺ |
| Topology | helix-loop-helix | β-β-α |
| Unit size | ~35-40 aa | ~25-30 aa |
| Stability source | Metal coordination | Metal coordination |
| Without metal | Unfolded/flexible | Unfolded/flexible |

### Why These Are Different from LIM/MFS

1. **PDB outliers exist**: 7-8% of PDB structures are also flagged
   - LIM: 10 PDB / 48 AFDB (17% PDB)
   - MFS: 0 PDB / 1,650 AFDB (0% PDB)
   - EF-hand: 57 PDB / 724 AFDB (7% PDB)
   - Zinc finger: 92 PDB / 1,087 AFDB (8% PDB)

2. **Domain definition is context-dependent**: Metal occupancy affects structure

3. **Simple topology is constitutive**: Not a sign of incompleteness

### Remediation Recommendations

**Tier 1: Clear candidates for splitting (high confidence)**
- MFS merged transporters (1,650) - all AFDB, all should be 2 domains
- Large LIM merges (58) - clear tandem arrays
- Ig merged domains with disordered linkers - pLDDT filtering + FoldSeek splitting
- Beta propeller multi-domain merges (298) - whole-propeller splitting validated

**Tier 2: Likely candidates for splitting**
- Large zinc finger merges (>150 aa, 83) - probably tandem arrays
- Large EF-hand merges (>300 aa, 77) - probably multi-lobe proteins
- High-variance propeller F-groups (Sortilin-Vps10, eIF2A) - need investigation

**Tier 3: Requires careful review**
- Medium zinc finger candidates (70-150 aa, 1,096) - may be legitimate
- Medium EF-hand candidates (160-300 aa, 704) - may be legitimate
- Multi-chain propeller assemblies - documentation, not correction

---

## Output File Summary

| H-group | File | Candidates |
|---------|------|------------|
| 377.1 (LIM) | `lim_domain_test/lim_merge_candidates.csv` | 58 |
| 5050.1 (MFS) | `mfs_domain_test/mfs_merge_candidates.csv` | 1,650 |
| 108.1 (EF-hand) | `length_anomaly_analysis/efhand_merge_candidates.csv` | 781 |
| 386.1 (Zinc finger) | `length_anomaly_analysis/zf_merge_candidates.csv` | 1,179 |
| 11.1 (Ig) | `ig_split_prototype/ig_template_library.json` | 323 templates |
| 5.1 (Beta propeller) | `beta_propeller_remediation/multi_domain_merge_candidates.csv` | 298 |

**Total merge candidates**: ~3,966 (plus Ig domains requiring pLDDT filtering)

---

## Next Steps

### Immediate Actions
1. **Batch process MFS candidates** (highest confidence, largest count)
   - Use iterative splitting with MFS half template
   - Expected: 1,650 → 3,300 domains

2. **Batch process LIM candidates** (validated approach)
   - Use iterative splitting with LIM template
   - Expected: 58 → ~200-350 domains

3. **Batch process beta propeller merge candidates** (validated approach)
   - Use `iterative_propeller_split.py` with WD40 template
   - Expected: 298 → ~600-900 domains
   - Build multi-template library for different blade counts

4. **Implement pLDDT filtering for Ig domains**
   - Pre-filter regions with mean pLDDT < 50
   - Apply FoldSeek multi-template splitting
   - Use 323-template Ig library

### Future Consideration
5. **Review metal-binding domain policy**
   - Should ECOD track metal binding sites?
   - Should domain definitions account for metal occupancy?
   - How to handle "simple but stable" topologies?

6. **Curate large EF-hand/zinc finger outliers**
   - Manual review of >300 aa EF-hands (77)
   - Manual review of >150 aa zinc fingers (83)

7. **Investigate high-variance propeller F-groups**
   - Sortilin-Vps10 (5.1.7.2): 60% outlier rate
   - eIF2A (5.1.11.1): 44% outlier rate, bimodal distribution
   - Document multi-chain assembly cases (Fungal_lectin, 5.1.10)

---

## Related Documents

- SQL Schema Reference: `/home/rschaeff/work/ecod_consistency_2026/SQL_SCHEMA_REFERENCE.md`
- Beta Propeller Remediation Plan: `/home/rschaeff/work/ecod_consistency_2026/beta_propeller_remediation/REMEDIATION_PLAN.md`
- Ig Domain Prototype Results: `/home/rschaeff/work/ecod_consistency_2026/ig_split_prototype/PROTOTYPE_RESULTS.md`
- Ig Domain Method Documentation: `/home/rschaeff/work/ecod_consistency_2026/ig_split_prototype/METHOD_DOCUMENTATION.md`
- Length Anomaly Detector: `/home/rschaeff/work/ecod_consistency_2026/length_anomaly_analysis/length_anomaly_detector.py`
- Full Scan Results: `/home/rschaeff/work/ecod_consistency_2026/length_anomaly_analysis/full_scan/`

---

*Document created: 2026-02-01*
*Analysis performed using ECOD database on dione:45000*
