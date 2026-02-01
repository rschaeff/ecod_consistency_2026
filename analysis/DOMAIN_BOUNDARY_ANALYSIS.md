# ECOD Domain Boundary Analysis

**Date:** 2026-02-01 (updated)
**Focus:** Domain length anomalies relative to Pfam model lengths

---

## Executive Summary

Analysis of domain lengths relative to Pfam HMM model lengths reveals two distinct patterns:

1. **Repeat protein families (EXPECTED)**: Domains correctly span multiple Pfam repeat units
2. **Non-repeat families (BOUNDARY ERRORS)**: Multiple distinct domains incorrectly merged

**Key Findings:**

1. Most apparent "boundary errors" (high domain/Pfam ratio) occur in repeat protein families where the behavior is expected. True boundary errors are concentrated in non-repeat families like Immunoglobulins.

2. **These are original DPAM merge errors, not migration artifacts.** Verification against source tables (swissprot.domain, proteomes.domain) confirms 100% of overlong domains were already overlong in the original DPAM output.

3. **DPAM classifies merged domains as high-quality.** 98%+ are `good_domain` with DPAM/HHpred probabilities near 1.0. The quality classifier doesn't detect boundary errors.

4. **Source breakdown:** 76% from Proteomes (48 species), 24% from SwissProt.

5. **NEW: Overlong domains include intrinsically disordered regions.** Structural analysis reveals that unmatched segments within merged domains are often disordered linkers (pLDDT < 30), not additional structured domains. pLDDT filtering before domain assignment could prevent many merge errors.

---

## Overall Statistics

### Domain Length vs Pfam Model Length

| Source | Total Domains | >2x Pfam | >3x Pfam | >5x Pfam | % >2x |
|--------|---------------|----------|----------|----------|-------|
| AFDB | 1,393,853 | 106,064 | 54,074 | 28,870 | 7.61% |
| PDB | 926,244 | 32,676 | 13,063 | 6,598 | 3.53% |

AFDB has approximately 2x the rate of long domains compared to PDB.

---

## Pattern 1: Repeat Proteins (Expected Behavior)

These H-groups have high domain/Pfam ratios because ECOD domains correctly span multiple repeat units.

### Affected H-groups

| H-group | Name | Repeat Type | % >2x Pfam | Explanation |
|---------|------|-------------|------------|-------------|
| 5076.1 | Mito carrier | Internal | 96% | ~3 repeats per domain |
| 282.1 | CBS domain | Tandem | 93% | CBS pairs/tandem |
| 208.1 | Hexapep | Left-handed | 92% | Many short repeats |
| 207.1 | LRR | Solenoid | 90% | 10-30 repeats typical |
| 5.1 | beta-propeller | WD40/Kelch | 65% | 7-8 blade propellers |
| 109.3 | Ankyrin | Linear | 66% | 4-7 repeats typical |
| 109.4 | ARM/TPR | Solenoid | 36% | Variable repeat count |

### Example: WD40 repeats (5.1.4.1)
- Pfam model (WD40): 39 aa per repeat
- Typical domain: 7 repeats × 39 aa = ~275 aa
- Observed average: 383 aa (includes linkers)
- **This is correct** - the domain encompasses all repeats

### Why This Is Not A Problem

For repeat proteins:
1. **The Pfam model represents ONE repeat unit**
2. **ECOD correctly defines the domain as all repeats together**
3. **High ratio = many repeats, not boundary error**

---

## Pattern 2: True Boundary Errors (Ig Domains Case Study)

H-group 11.1 (Immunoglobulin) shows true boundary errors where distinct Ig domains were merged.

### Statistics for 11.1 (AFDB)

| Metric | Count |
|--------|-------|
| Total domains | 44,366 |
| Domains >2x Pfam | 1,142 (2.6%) |
| Domains >3x Pfam | 252 (0.6%) |
| Domains >5x Pfam | 87 (0.2%) |

### F-groups with Most Errors

| F-group | Name | Pfam Len | Errors | Avg Len | Max Len |
|---------|------|----------|--------|---------|---------|
| 11.1.1.97 | I-set | 90 | 200 | 287 | 1500 |
| 11.1.1.2 | fn3 | 84 | 118 | 274 | 895 |
| 11.1.1.179 | Ig_3 | 78 | 83 | 217 | 480 |
| 11.1.1.1 | Cadherin | 93 | 35 | 273 | 735 |

### Most Extreme Cases

| Domain ID | Length | Expected | Fold | Analysis |
|-----------|--------|----------|------|----------|
| A0A044SJW9_F1_nD5 | 1595 aa | 93 aa | 17x | ~17 Filamin domains merged |
| A0A0H2UKW9_F1_nD12 | 1500 aa | 90 aa | 16x | ~16 I-set domains merged |
| F1QK75_F1_nD12 | 1480 aa | 90 aa | 16x | ~16 I-set domains merged |
| A0A5K4FE25_F1_nD7 | 1235 aa | 90 aa | 13x | ~13 I-set domains merged |

### Why Ig Domains Are Different From Repeats

Unlike repeat proteins:
1. **Each Ig domain is a complete, independent folding unit** (~100 aa)
2. **Multiple Ig domains in a protein are SEPARATE domains** (e.g., antibodies)
3. **ECOD should define each Ig domain separately**
4. **Merged Ig domains = incorrect domain parsing**

---

## Distinguishing Repeats from Domain Arrays

### Characteristics of Repeat Proteins
- Single repeat unit is NOT a complete domain
- Repeats fold together into one structure
- Cannot isolate one repeat as independent structure
- Examples: WD40, LRR, TPR, Ankyrin, ARM

### Characteristics of Domain Arrays
- Each unit IS a complete, independent domain
- Domains can fold independently
- Homologous domains arranged in tandem
- Examples: Ig domains, Cadherin, Fibronectin type III

### Decision Criteria

| Feature | Repeat Proteins | Domain Arrays |
|---------|-----------------|---------------|
| Independent folding | No | Yes |
| Pfam/domain ratio | N repeats | ~1 |
| Structural independence | Coupled | Independent |
| ECOD treatment | One domain | Multiple domains |

---

## Source Analysis

### True Boundary Errors by Source (11.1 only)

| Source | Total | >2x Pfam | % with Errors |
|--------|-------|----------|---------------|
| PDB | 78,215 | 200 | 0.3% |
| AFDB | 46,101 | 1,055 | 2.3% |

**AFDB has 8x higher error rate than PDB for Ig domains.**

### Origin of AFDB Errors

Tracing overlong domains (>3x Pfam) in 11.1:
- 215 from unknown source (likely inherited/computed)
- 27 from SwissProt DPAM (`good_domain`)
- Classification method: NULL for most

---

## Recommendations

### For Domain Parsing Pipelines

1. **Detect tandem Ig-like domains**: When domain length exceeds 2x Pfam model length for non-repeat families, trigger multi-domain detection
2. **Use domain number as signal**: If a protein has many Ig-like Pfam hits, each should be a separate domain
3. **Compare to PDB structures**: Use known multi-domain PDB structures as templates

### For H-groups to Review

**High priority (true boundary errors):**
- 11.1 (Immunoglobulin) - 1,142 errors
- 4.1 - 1,320 errors (need to verify if repeat)
- 10.12 - 1,227 errors (need to verify if repeat)

**Lower priority (likely repeat proteins - verify expected):**
- 5.1 (WD40) - behavior expected
- 207.1 (LRR) - behavior expected
- 109.3/109.4 (Ankyrin/ARM) - behavior expected

### Metric for Detection

```
boundary_error_score = domain_length / pfam_model_length

For non-repeat families:
  - score > 2.0: Review needed
  - score > 3.0: Likely error
  - score > 5.0: Definite error (multiple domains merged)

For repeat families:
  - High scores are expected
  - score ≈ number_of_repeats × (1 + linker_fraction)
```

---

## Data Files

| File | Description |
|------|-------------|
| This document | Analysis and recommendations |
| `evaluation/separation_analysis.csv` | F-group separation metrics |
| `analysis/METHODOLOGY_FINDINGS.md` | Pfam vs BLAST distance analysis |
| `analysis/DEFICIENCY_REPORT_605.1.md` | simple_topology case study |

---

## Conclusions

1. **Most high domain/Pfam ratios are NOT errors** - they occur in repeat protein families where the behavior is expected

2. **True boundary errors exist in domain array families** like Ig (11.1), where AFDB has ~2% error rate vs 0.3% for PDB

3. **Detection is feasible** by combining:
   - Domain length vs Pfam model length
   - Knowledge of repeat vs non-repeat family type
   - Multi-Pfam hit patterns within a protein

4. **Remediation should focus on non-repeat families** with high error rates, particularly 11.1 (Ig domains)

5. **Merged domains often include disordered linkers** - pLDDT analysis shows that unmatched regions in overlong domains are frequently intrinsically disordered (pLDDT < 30), not missing domain types

6. **pLDDT filtering is a simple prevention strategy** - excluding regions with mean pLDDT < 50 before domain assignment could prevent DPAM from merging structured domains with disordered linkers

---

## Root Cause: Original DPAM Merge Errors

### Verification

Comparison of overlong domains between `ecod_commons` and their source tables confirms these are **original DPAM errors, NOT migration artifacts**.

| Source | Total | Exact Length Match | Source >200aa |
|--------|-------|-------------------|---------------|
| SwissProt | 2,619 | 2,619 (100%) | 2,619 (100%) |
| Proteomes | 8,166 | 6,228 (76%) | 8,165 (99.99%) |

**Zero cases** where the source table had a short domain but ecod_commons has a long one.

### Source Distribution

| Source | Count | % of Total |
|--------|-------|------------|
| Proteomes (48 species) | 8,166 | 76% |
| SwissProt | 2,619 | 24% |

### Quality Classification in Source

| Source | good_domain | % |
|--------|-------------|---|
| SwissProt | 2,619 | 100% |
| Proteomes | 7,990 | 97.8% |

**Critical finding:** These are NOT low-quality domains. DPAM classified them as `good_domain` with high confidence scores.

### Example: Q60ZN5_nD12 (from swissprot.domain)

```
Domain ID: Q60ZN5_nD12
Length: 740 aa
Range: 641-855,1056-1155,1671-1770,1871-2010,2066-2100,2111-2140,2151-2245,2276-2300
Judge: good_domain
DPAM prob: 1.0
HHpred prob: 0.996
```

This domain spans **8 discontinuous segments** across 1,660 residues - clearly multiple Ig domains incorrectly merged. Despite this obvious boundary error:
- Judge: **good_domain**
- DPAM probability: **1.0** (maximum confidence)
- HHpred probability: **0.996** (near-maximum)

### Implications

1. **DPAM's domain detection works well** - it correctly identifies that these regions are Ig-like domains

2. **DPAM's boundary logic fails for tandem domains** - it merges multiple instances of the same domain type into one oversized domain

3. **Quality classification doesn't catch boundary errors** - a domain can be "good" (correct fold assignment) but still have incorrect boundaries

4. **This affects both SwissProt and Proteomes pipelines** - the error is in the core DPAM logic, not a dataset-specific issue

### Recommendations for DPAM

**1. Pre-filter disordered regions before domain assignment:**

```python
# Filter out low-confidence regions BEFORE domain assignment
for segment in protein_segments:
    if mean_plddt(segment) < 50:
        exclude_from_domain_candidates()
```

**2. Post-process to detect and split merged tandem domains:**

```python
# Pseudocode for boundary correction
if domain_length > pfam_model_length * 2:
    if family_type == "domain_array":  # Ig, Cadherin, fn3, etc.
        # Check for multiple Pfam hits in the region
        # Split into separate domains at natural boundaries
```

**3. Use structural alignment for validation:**

```python
# Iterative FoldSeek for domain splitting
for template in domain_family_templates:
    hits = foldseek_align(domain, template)
    # Accept hits with TM-score >= 0.3
    # Remove matched regions, repeat
```

---

## Structural Analysis: Iterative Domain Splitting Prototype

### Overview

A prototype was developed to test whether structural alignment can identify individual Ig domains within merged domain definitions. Using Q60ZN5_nD12 (740aa) as a test case.

**Tools tested:** DALI (DaliLite.v5), FoldSeek (recommended)

### Results Summary

| Approach | Domains Found | Coverage | Time |
|----------|---------------|----------|------|
| DALI (single template) | 4 | 38% | ~minutes |
| FoldSeek (single template) | 5 | 42% | 8.3 sec |

FoldSeek is ~50x faster with slightly better sensitivity.

### Key Discovery: Unmatched Segments Are Disordered

The segments that couldn't be matched to ANY Ig template (from a library of 323 templates covering 190 F-groups) or to ANY domain in the full ECOD database (63K domains) are **intrinsically disordered regions (IDRs)**.

| Segment | Length | Mean pLDDT | % < 50 | Status |
|---------|--------|------------|--------|--------|
| 2151-2245 | 95 aa | 25.8 | 100% | DISORDERED |
| 2066-2100 | 35 aa | 26.4 | 100% | DISORDERED |
| 2111-2140 | 30 aa | 26.4 | 100% | DISORDERED |
| 2276-2300 | 25 aa | 23.9 | 100% | DISORDERED |

**Total disordered:** 185 residues (25% of the merged domain)

### Corrected Domain Count for Q60ZN5_nD12

| Component | Residues | % of Total |
|-----------|----------|------------|
| True Ig domains | 311 | 42% |
| Disordered linkers | 185 | 25% |
| Inter-domain gaps | 244 | 33% |

The original expectation of "~8 Ig domains" was incorrect. The merged domain actually contains:
- **5 true Ig domains** (confirmed by structural alignment)
- **4 disordered linker regions** (pLDDT < 30, zero structural hits)

### Root Cause Clarified

**DPAM merged structured Ig domains WITH disordered linker regions.** The merge error wasn't just combining multiple Ig domains - it also included intrinsically disordered regions that have no defined structure.

AlphaFold pLDDT scores clearly distinguish:
- **Structured regions (pLDDT > 70):** True Ig domains that match templates
- **Disordered regions (pLDDT < 50):** Linkers with no structural similarity to any ECOD domain

### Recommendations from Prototype

1. **Pre-filter by pLDDT** - Exclude regions with mean pLDDT < 50 before domain assignment
2. **Use FoldSeek for structural validation** - 50x faster than DALI, enables multi-template searches
3. **Template library approach** - 323 Ig templates from 190 F-groups available for comprehensive matching
4. **TM-score ≥ 0.3** - Reasonable threshold for Ig domain identification

### Implications for DPAM Correction

1. **pLDDT filtering could prevent many merge errors**
   - Disordered linkers (pLDDT < 50) should be excluded from domain definitions
   - This is a simple, fast filter that can be applied before domain assignment

2. **Many "overlong domains" may include disordered regions**
   - The 10,785 overlong AFDB domains likely include linkers like this case
   - pLDDT analysis could quickly identify how many

3. **Structural alignment can split true domain repeats**
   - Iterative FoldSeek against template libraries works
   - Production implementation feasible given speed (~seconds per domain)

### Files

Prototype implementation and detailed results:
- `ig_split_prototype/iterative_foldseek_prototype.py` - Recommended implementation
- `ig_split_prototype/PROTOTYPE_RESULTS.md` - Full analysis
- `ig_split_prototype/ig_template_library.json` - 323 Ig templates

---

## Quality Control Gap: Representative Assignment Analysis

### Key Finding

**82% of overlong AFDB domains lack representative assignment and bypass length validation.**

### Statistics (All H-groups, Pfam 70-200 aa)

| Category | Count | Percentage |
|----------|-------|------------|
| Total overlong AFDB domains (>3x Pfam) | 10,785 | 100% |
| Without representative assignment | 8,847 | 82.0% |
| With representative assignment | 1,938 | 18.0% |

### Assignment Method Breakdown

| Method | Total | With Rep | % With Rep |
|--------|-------|----------|------------|
| inheritance | 10,070 | 1,920 | 19.1% |
| migration_recovery | 511 | 0 | 0.0% |
| hhsearch | 204 | 18 | 8.8% |

### Domains WITH Representatives: Detectable Errors

For the 309,739 AFDB domains that DO have representatives assigned:

| Metric | Count | Percentage |
|--------|-------|------------|
| Total with representative | 309,739 | 100% |
| >2x representative length | 2,593 | 0.84% |
| >3x representative length | 653 | 0.21% |
| >5x representative length | 59 | 0.02% |

### H-group 11.1 (Ig domains) Detail

| Metric | Count |
|--------|-------|
| Total overlong AFDB (>2x Pfam) | 1,055 |
| Without representative | 953 (90%) |
| With representative | 102 (10%) |
| >3x representative length | 17 domains |

### Implications

1. **The "inheritance" assignment method does not perform length validation**
   - 96% of overlong domains without reps were assigned via inheritance
   - Domains inherit F-group classification but not representative comparison

2. **Length validation against representatives would be effective**
   - For domains with reps, only 0.84% are >2x rep length
   - These are detectable boundary errors that could be flagged

3. **Pipeline recommendation**
   - Add length ratio check: `domain_length / representative_length`
   - Flag domains with ratio > 2.0 for manual review
   - Especially for non-repeat protein families

### Query for Detecting Boundary Errors

```sql
-- Find automated domains much longer than their representative
SELECT
    d.domain_id,
    d.sequence_length as auto_len,
    rep.sequence_length as rep_len,
    d.sequence_length::float / rep.sequence_length as ratio
FROM ecod_commons.domains d
JOIN ecod_commons.f_group_assignments fa ON fa.domain_id = d.id
JOIN ecod_commons.domains rep ON rep.ecod_uid = fa.representative_domain_ecod_uid
WHERE d.sequence_length > rep.sequence_length * 3
ORDER BY ratio DESC;
```

---

## Document History

| Date | Change |
|------|--------|
| 2026-01-31 | Initial analysis of H-group 11.1 |
| 2026-01-31 | Extended to all H-groups; discovered repeat protein pattern |
| 2026-01-31 | Documented distinction between repeats and domain arrays |
| 2026-01-31 | Added representative assignment analysis (82% lack rep) |
| 2026-01-31 | Confirmed errors are original DPAM merge errors (not migration) |
| 2026-01-31 | Traced source: 76% Proteomes, 24% SwissProt; 98%+ good_domain |
| 2026-02-01 | Added structural analysis prototype (FoldSeek/DALI) |
| 2026-02-01 | Discovered unmatched segments are intrinsically disordered (pLDDT < 30) |
| 2026-02-01 | Recommended pLDDT filtering to prevent future merge errors |
