# ECOD Representative Domain Deficiency Report

## Case Study: H-group 605.1 (HisKA α-hairpin dimer)

**Report Date:** 2026-01-31
**Prepared by:** ECOD Consistency Analysis Pipeline
**Classification:** Data Quality / Accession Policy

---

## Executive Summary

Analysis of H-group 605.1 reveals that **simple_topology domains are being accessioned into ecod_rep as provisional manual representatives**, leading to:
- Spurious singleton F-groups based on structural fragments
- False Pfam associations from partial domain matches
- Degraded clustering and consistency metrics

This report recommends policy changes to prevent simple_topology domains from serving as provisional representatives and improved tracking of representative domain origins.

---

## Background

### H-group 605.1: HisKA Domain

The HisKA domain (Histidine Kinase A) is a **constitutive α-hairpin dimer** structure with expected domain length of **70-90 amino acids** based on PDB manual representatives (mean: 73.7 aa, range: 66-89 aa).

### Discovery Context

During F-group consistency evaluation using CLANS clustering, H-group 605.1 showed:
- **1.2% consistency rate** (worst in dataset)
- **30.5% of domains completely isolated** (zero BLAST edges)
- Negative silhouette scores indicating poor cluster separation

Investigation traced the root cause to **fragmentary domain assignments** from automated DPAM classification.

---

## Findings

### 1. Source of Problematic Domains

Analysis of 1,922 domains in the 605.1 FASTA revealed:

| Source | Total | Short (<50aa) | % Short |
|--------|-------|---------------|---------|
| SwissProt | 401 | 19 | 4.7% |
| Proteomes (48 species) | 1,397 | 265 | 19.0% |
| AF2 Human | 27 | 22 | 81.5% |
| Other single-species DPAM | 57 | 36 | 63.2% |
| PDB | 40 | 3 | 7.5% |

**Key finding:** Short fragments correlate strongly with `simple_topology` classification:
- `simple_topology` domains: **37.3% are fragments** (<50 aa)
- `good_domain` domains: **0.3% are fragments**

### 2. Impact on BLAST Connectivity

| Source | Domains | Isolated (0 edges) | Mean Degree |
|--------|---------|-------------------|-------------|
| PDB | 40 | 0 (0.0%) | 122.2 |
| AlphaFold | 1,883 | 586 (31.1%) | 30.8 |

PDB domains cluster perfectly at all lengths. The isolation problem is specific to automated AFDB domain detection producing fragments too short for BLAST homology detection.

### 3. Provisional Representatives with simple_topology Classification

Seven F-groups in 605.1 have provisional manual representatives classified as `simple_topology`:

| F-group | Representative | Length | Pfam | Status |
|---------|---------------|--------|------|--------|
| 605.1.1.113 | A0A0R0LG38_F1_nD3 | 35 aa | PF12428 | 2 members |
| 605.1.1.114 | A0A0R0KYT6_F1_nD1 | 75 aa | PF11152 | **Singleton** |
| 605.1.1.116 | Q9HBM0_F1_nD1 | 60 aa | PF12632 | **Singleton** |
| 605.1.1.117 | A6NGG8_F1_nD1 | 90 aa | PF15449 | **Singleton** |
| 605.1.1.119 | A0A3Q0KH19_F1_nD1 | 40 aa | PF04201 | **Singleton** |
| 605.1.1.120 | A0A0S0WGS4_F1_nD1 | 30 aa | PF23670 | **Singleton** |
| 605.1.1.121 | Q7KRS9_F1_nD4 | 105 aa | PF23460 | **Singleton** |

**Six of seven are singleton F-groups** where the simple_topology domain is the only member.

### 4. Spurious Pfam Associations

Four Pfams are uniquely represented in ECOD only through these simple_topology F-groups:

| Pfam | Description | Pfam Length | ECOD Rep Length | Coverage |
|------|-------------|-------------|-----------------|----------|
| PF12428 | DUF3675 | 119 aa | 35 aa | 29% |
| PF15449 | Retinal protein | 1292 aa | 90 aa | **7%** |
| PF23460 | ZMYND8 coiled-coil | 65 aa | 105 aa | 162% |
| PF23670 | PIGBOS1-like | 54 aa | 30 aa | 56% |

**PF15449 is particularly egregious:** a 90 aa fragment matched to a 1292 aa Pfam represents a false positive structural match, not genuine homology.

### 5. H-group Structure

605.1 H-group statistics:
- **Total F-groups:** 55
- **Singleton F-groups:** 41 (74.5%)
- **F-groups with PDB manual reps:** 4
- **F-groups with AFDB provisional reps only:** 51

The proliferation of singleton F-groups suggests over-splitting driven by automated classification of structural fragments.

---

## Root Cause Analysis

### What is `simple_topology`?

The `simple_topology` judge classification indicates:
- Low HHpred probability (~0.18 vs ~0.61 for `good_domain`)
- Moderate DPAM probability (~0.83 vs ~0.96 for `good_domain`)
- Classification based primarily on **structural similarity** rather than sequence homology
- Often assigned to **partial structural matches** that capture secondary structure elements without complete domain architecture

### Why This Matters for HisKA

HisKA is an α-hairpin dimer (~75 aa). A single α-helix (~25-35 aa) can match the topology without representing a complete, functional domain. The `simple_topology` classifier cannot distinguish:
- Complete HisKA domain (two helices forming hairpin dimer)
- Single helix fragment (partial structural match)

### Pipeline Gap

The current accession pipeline permits `simple_topology` domains to:
1. Be assigned to new F-groups as representatives
2. Create singleton F-groups based on fragment matches
3. Establish Pfam associations from partial structural overlap

---

## Positive Finding: SwissProt Quality

SwissProt DPAM (the most recent AFDB accession) shows significantly better quality:
- Only **4.7% fragments** (<50 aa)
- Predominantly `good_domain` classification
- Only 19 short domains in 401 total

This suggests quality controls have improved for recent accessions, but legacy data from earlier DPAM runs (Proteomes, AF2 Human, single-species) contains problematic entries that were accessioned into ecod_rep.

---

## Recommendations

### Immediate Actions

1. **Policy Change:** Simple_topology domains should not serve as provisional manual representatives in ecod_rep.

2. **Remediation for 605.1:**
   - Deprecate 6 singleton F-groups with simple_topology reps
   - Promote Q69JV9_F1_nD2 (95 aa, good_domain) as rep for 605.1.1.113
   - Review and potentially remove 4 spurious Pfam associations

3. **Audit:** Identify all simple_topology provisional reps across ecod_rep for review.

### Systemic Improvements

4. **Provenance Tracking:** Implement explicit tracking of representative domain origins in ecod_rep:
   - Source pipeline (SwissProt DPAM, Proteomes DPAM, AF2 Human, etc.)
   - Classification judge (good_domain, simple_topology, low_confidence, partial_domain)
   - Accession date and version

5. **Validation Gates:** Add pre-accession checks:
   - Minimum domain length relative to Pfam family length
   - Minimum classification confidence (reject simple_topology for rep status)
   - Singleton F-group review before creation

6. **Consistency Integration:** Use CLANS-based consistency metrics as quality signal during accession, not just post-hoc evaluation.

---

## Impact Assessment

### If simple_topology reps are disqualified in 605.1:

| Metric | Before | After |
|--------|--------|-------|
| F-groups | 55 | 49 |
| Singleton F-groups | 41 | 35 |
| Unique Pfams lost | - | 1 legitimate (PF23460), 3 spurious |
| Expected consistency | 1.2% | Significantly improved |

### Broader Impact (Audit Completed)

Systematic review identified:

| Metric | Count |
|--------|-------|
| Total provisional-only reps in ecod_rep | 8,157 |
| `simple_topology` provisional reps | **574** (7.0%) |
| Affected H-groups | **122** |
| Associated Pfams | **444** |

**Top affected H-groups:**

| H-group | simple_topo F-groups | Consistency |
|---------|---------------------|-------------|
| 3755.3 | 96 | 1.8% |
| 192.8 | 57 | 5.9% |
| 3922.1 | 55 | 1.8% |
| 5086.1 | 35 | 5.6% |
| 101.1 | 25 | 2.8% |

Strong correlation: H-groups with many simple_topology provisional reps consistently appear among the worst performers for F-group consistency.

**Full audit data:** `analysis/simple_topology_prov_reps.tsv`

---

## Appendix: Data Sources

### Database Connection
```
Host: dione
Port: 45000
Database: ecod_protein
User: ecod
```

### Key Tables
- `ecod_rep.domain` - Representative domain definitions
- `ecod_rep.cluster` - F-group/T-group/H-group hierarchy with Pfam associations
- `ecod_commons.domains` - Full domain inventory
- `ecod_commons.f_group_assignments` - Domain to F-group mappings
- `swissprot.domain` - SwissProt DPAM classifications
- `proteomes.domain` - 48 Proteomes DPAM classifications
- `public.domain` - Other single-species DPAM classifications
- `ecod_commons.pfam_families` - Pfam family metadata

### Analysis Files
- `/home/rschaeff/work/ecod_consistency_2026/analysis/CONNECTIVITY_ANALYSIS.md`
- `/home/rschaeff/work/ecod_consistency_2026/evaluation/TRIAGE_REPORT.md`
- `/home/rschaeff/work/ecod_consistency_2026/results/605_1/605_1.clans`

---

## Addendum: Post-Deaccession Analysis (2026-01-31)

Following the deaccession of simple_topology provisional reps, 605.1 was re-analyzed.

### Results After Deaccession

| Metric | Before | After |
|--------|--------|-------|
| F-groups | 55 | 11 (excluding .0 pseudo-group) |
| Singleton F-groups | 41 | 6 |
| Consistency | 1.2% | 8.8% |

### Critical Finding: Pfam ≠ BLAST Distance

Despite cleanup, consistency remained low. Investigation revealed that **F-groups in 605.1 completely overlap in CLANS space**:

| Metric | Value |
|--------|-------|
| Max internal spread | 48.3 |
| Min inter-centroid distance | 1.8 |
| Separation ratio | 26.8 |

Different Pfam families (HisKA, GrpE, FliJ, KRAB, etc.) share similar pairwise BLAST profiles despite distinct HMM signatures. This is expected for:
- Small helical domains (~70-90 aa) with limited sequence diversity
- Diverse families where HMMs detect remote homology BLAST cannot

### Reinterpretation

The original low consistency in 605.1 was caused by **two distinct issues**:

1. **simple_topology fragmentary reps** (addressed by deaccession) - data quality issue
2. **Pfam families not forming BLAST clusters** (inherent to this H-group) - expected biological behavior

The deaccession successfully addressed issue #1. Issue #2 is not a problem - it reflects that profile-based classification captures relationships pairwise methods cannot.

### Broader Implications

Systematic analysis of 1,167 H-groups found:
- Only 21.7% have F-groups that form distinct BLAST clusters
- 78.3% (including 605.1) have overlapping F-groups
- Low consistency in overlapping H-groups is expected, not an error

See: `analysis/METHODOLOGY_FINDINGS.md`

---

## Document History

| Date | Author | Change |
|------|--------|--------|
| 2026-01-31 | Consistency Pipeline | Initial report |
| 2026-01-31 | Consistency Pipeline | Added full audit results (574 simple_topology reps across 122 H-groups) |
| 2026-01-31 | Consistency Pipeline | Added post-deaccession analysis and methodology finding |
