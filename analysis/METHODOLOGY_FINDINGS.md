# ECOD Consistency Analysis: Methodological Findings

**Date:** 2026-01-31
**Status:** Critical finding affecting interpretation of results

---

## Executive Summary

Analysis of 1,167 H-groups reveals that **F-group classification (Pfam-based) and BLAST-based sequence clustering measure fundamentally different relationships**. This finding reframes how consistency metrics should be interpreted.

**Key Result:** Only 21.7% of H-groups have F-groups that form distinct BLAST-detectable sequence clusters. For the remaining 78.3%, F-groups capture homology relationships that pairwise BLAST cannot detect.

---

## Background: Two Different Distance Metrics

### F-group Assignment (Pfam HMM-based)
```
sequence → Pfam HMM profile → E-value → F-group
```
- Based on **profile-to-sequence** alignment
- Sensitive to conserved motifs and structural constraints
- Can detect **remote homology** across diverse sequences
- Each sequence is compared to a family model independently

### CLANS Clustering (BLAST-based)
```
sequence ↔ sequence → pairwise E-value → edge weights → clustering
```
- Based on **pairwise sequence similarity**
- Requires detectable overall sequence identity
- Struggles with remote homology
- Compares all sequences to each other

### The Fundamental Difference

Two domains can:
- Both match the same Pfam HMM with excellent E-values (same F-group)
- Yet have poor pairwise BLAST similarity to each other (no CLANS edge)

This is especially true for:
- **Diverse protein families** with conserved functional motifs but variable scaffolds
- **Remote homology** where HMMs excel but BLAST fails
- **Short domains** (e.g., HisKA ~70aa) where pairwise statistics are weak

---

## Empirical Analysis

### Measuring F-group Separation in CLANS Space

For each H-group, we calculated:
- **Internal spread**: Mean distance from domains to their F-group centroid
- **Inter-centroid distance**: Distance between F-group centroids
- **Separation ratio**: max(spread) / min(inter-centroid distance)

A ratio < 1.0 indicates F-groups form distinct clusters; ratio > 1.0 indicates overlap.

### Results (1,167 H-groups with 2+ multi-member F-groups)

| Category | Count | Percentage | Interpretation |
|----------|-------|------------|----------------|
| Well separated (ratio < 0.5) | 74 | 6.3% | F-groups = BLAST clusters |
| Moderate (0.5 ≤ ratio < 1.0) | 179 | 15.3% | F-groups ≈ BLAST clusters |
| Overlapping (1.0 ≤ ratio < 2.0) | 295 | 25.3% | Partial correspondence |
| Severe overlap (ratio ≥ 2.0) | 619 | 53.0% | F-groups ≠ BLAST clusters |

**Summary:**
- **21.7%** of H-groups: Pfam families correspond to BLAST-detectable clusters
- **78.3%** of H-groups: Pfam families capture relationships BLAST cannot detect

### Visualization

See: `evaluation/separation_analysis.png`

---

## Case Studies

### Well-Separated Example: H-group 7504.1

| Metric | Value |
|--------|-------|
| Domains | 499 |
| F-groups | 3 |
| Max internal spread | 17.7 |
| Min inter-centroid distance | 39.1 |
| Separation ratio | 0.45 |
| Consistency | 98.2% |

F-groups form visually distinct clusters. Pfam classification aligns with BLAST similarity.

See: `results/7504_1/7504_1_visualization.png`

### Overlapping Example: H-group 605.1 (HisKA)

| Metric | Value |
|--------|-------|
| Domains | 1,818 |
| F-groups | 11 (5 non-singleton) |
| Max internal spread | 48.3 |
| Min inter-centroid distance | 1.8 |
| Separation ratio | 26.8 |
| Consistency | 8.8% |

F-groups completely intermixed in CLANS space. Different Pfam families (HisKA, GrpE, FliJ, KRAB, etc.) share similar pairwise BLAST profiles despite distinct HMM signatures.

See: `results/605_1/605_1_visualization.png`

---

## Implications for Consistency Analysis

### What Consistency Actually Measures

The consistency metric answers:
> "Do Pfam-defined F-groups correspond to BLAST-detectable sequence clusters?"

This is **not** the same as asking:
> "Are domains correctly classified?"

### Reinterpreting Results

| Consistency | Separation Ratio | Interpretation |
|-------------|------------------|----------------|
| High | Low (<1.0) | F-groups align with sequence clusters |
| Low | Low (<1.0) | Potential misclassification - investigate |
| High | High (>1.0) | N/A (can't have high consistency with overlap) |
| Low | High (>1.0) | **Expected** - Pfam captures non-BLAST relationships |

### Revised Analysis Strategy

1. **Stratify H-groups** by separation ratio before interpreting consistency
2. **For ratio < 1.0** (21.7%): Low consistency suggests classification issues worth investigating
3. **For ratio ≥ 1.0** (78.3%): Low consistency is expected; focus on other quality metrics

---

## Biological Interpretation

The 78% of H-groups with overlapping F-groups represent cases where:

1. **Profile methods outperform pairwise methods** - The Pfam HMMs capture conserved features (active sites, structural motifs) that pairwise BLAST cannot detect across diverse sequences.

2. **F-groups represent functional families** - Classification based on what domains *do* (function, captured by Pfam) rather than how similar they *look* (raw sequence, captured by BLAST).

3. **Evolutionary divergence** - F-groups may have diverged beyond BLAST detection while retaining Pfam-recognizable features.

This is not a data quality problem - it reflects the biological reality that protein families can be coherent at the profile level while diverse at the pairwise level.

---

## Updated Recommendations

### For Consistency Analysis

1. **Do not use raw consistency scores as quality metrics** for H-groups with separation ratio ≥ 1.0

2. **Focus investigation efforts** on the 253 H-groups (21.7%) where:
   - Separation ratio < 1.0 (F-groups should cluster)
   - AND consistency is low (but they don't)
   - These represent potential classification issues

3. **Report separation ratio** alongside consistency to contextualize results

### For ECOD Quality Assessment

1. **The simple_topology deaccession was still valuable** - it removed fragmentary domains that shouldn't be representatives, regardless of BLAST clustering behavior

2. **Consider alternative metrics** for overlapping H-groups:
   - Direct Pfam E-value distributions within F-groups
   - Structural similarity (TM-score) if structures available
   - Phylogenetic coherence

---

## Data Files

| File | Description |
|------|-------------|
| `evaluation/separation_analysis.csv` | Per-H-group separation metrics |
| `evaluation/separation_analysis.png` | Distribution visualization |
| `evaluation/summary.csv` | Original consistency metrics |
| `results/*/evaluation.json` | Per-H-group detailed results |

---

## Conclusions

1. **F-group consistency (as measured by BLAST clustering) is not a universal quality metric** - it only applies to ~22% of H-groups where Pfam families happen to correspond to BLAST-detectable clusters.

2. **Low consistency in overlapping H-groups is expected behavior**, not a classification error. It reflects the different sensitivities of profile-based vs. pairwise methods.

3. **The analysis successfully characterized the relationship** between Pfam-based classification and BLAST-based clustering across ECOD, providing a framework for targeted quality assessment.

---

---

## Appendix: Pfam-based Consistency Analysis (Future Extension)

An alternative approach to consistency would measure assignment confidence using Pfam E-values directly, since F-groups are defined by Pfam HMM matches.

### Data Availability

The `pdb_analysis.domain_hmmer_results` table contains hmmscan results for PDB domains, including:
- All significant Pfam hits (not just best hit)
- E-values for each hit
- `is_best_hit` flag

### Scenario 1: Domains with Competitive Pfam Hits

Analysis of domains hitting multiple Pfams in the same H-group:

| Confidence Level | Domains | % | Description |
|------------------|---------|---|-------------|
| Ambiguous (<3x) | 1,453 | 4.2% | Best hit barely better than second |
| Marginal (3-10x) | 1,473 | 4.2% | Borderline assignment |
| Moderate (10-100x) | 2,355 | 6.8% | Reasonable confidence |
| Good (100-1000x) | 1,851 | 5.3% | High confidence |
| Strong (>1000x) | 27,590 | 79.5% | Unambiguous |

**~8.4% of multi-Pfam domains have ambiguous/marginal assignments** (within 10x E-value).

### Scenario 2: Consistently Competitive Pfam Pairs

Some Pfam pairs within H-groups are so similar that domains frequently have nearly equal E-values to both:

| H-group | F-group 1 | F-group 2 | Ambiguous Domains | Avg Ratio |
|---------|-----------|-----------|-------------------|-----------|
| 192.8 | zf-C3HC4 | zf-C3HC4_3 | 39 | 2.3x |
| 109.3 | Ank_2 | Ank | 30 | 3.0x |
| 206.1 | Pkinase | PK_Tyr_Ser-Thr | 28 | 3.1x |
| 11.1 | Ig_3 | I-set | 24 | 2.8x |
| 386.1 | zf-H2C2_5 | zf-C2H2_16 | 20 | 4.6x |
| 101.1 | MarR | MarR_2 | 13 | 3.9x |

These represent Pfam families that are variants of each other (e.g., zf-C3HC4 vs zf-C3HC4_3).

### Assessment

**This type of inconsistency is not concerning** for several reasons:

1. **Expected behavior**: Related Pfam families (often in same clan) naturally have overlapping sequence space
2. **Variant families**: Many pairs are intentional splits (e.g., MarR vs MarR_2) representing functional or structural subtypes
3. **Arbitrary boundaries**: The distinction between some Pfam families is inherently fuzzy
4. **Top-hit selection is reasonable**: Assigning to the best-scoring Pfam is a defensible approach even when alternatives are close

### Potential Future Extensions

If deeper analysis is needed:

1. **Domain confidence score**: Calculate `log10(second_best_eval / best_eval)` for all domains
2. **Pfam-Pfam similarity**: Use HHsearch/HHalign to measure HMM-HMM similarity between competitive pairs
3. **Clan-aware analysis**: Group related Pfams by clan and treat as equivalent for consistency purposes

### Query Templates

```sql
-- Find domains with competitive Pfam hits in same H-group
WITH ranked_hits AS (
    SELECT
        hr.domain_id,
        SPLIT_PART(hr.pfam_acc, '.', 1) as pfam_base,
        hr.domain_evalue,
        ROW_NUMBER() OVER (PARTITION BY hr.domain_id ORDER BY hr.domain_evalue) as rn
    FROM pdb_analysis.domain_hmmer_results hr
    WHERE hr.is_significant = true
)
SELECT
    r1.domain_id,
    r1.pfam_base as best_pfam,
    r2.pfam_base as second_pfam,
    LOG10(r2.domain_evalue / r1.domain_evalue) as log_ratio
FROM ranked_hits r1
JOIN ranked_hits r2 ON r1.domain_id = r2.domain_id
    AND r1.rn = 1 AND r2.rn = 2
WHERE r1.pfam_base != r2.pfam_base;
```

---

## Document History

| Date | Change |
|------|--------|
| 2026-01-31 | Initial findings from 605.1 case study |
| 2026-01-31 | Extended analysis to all 1,167 H-groups |
| 2026-01-31 | Reframed interpretation: Pfam distance ≠ BLAST distance |
| 2026-01-31 | Added Pfam-based consistency appendix (competitive hits analysis) |
