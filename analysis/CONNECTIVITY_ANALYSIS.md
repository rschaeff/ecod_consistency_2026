# ECOD F-group Consistency: BLAST Connectivity Analysis

**Date:** 2026-01-31
**Focus:** H-group 605.1 (HisKA domain family)

## Executive Summary

The low consistency rates observed in CLANS analysis are primarily caused by **fragmentary AlphaFold domain assignments** that are too short to produce BLAST edges, not by actual F-group heterogeneity.

## Key Finding: Source Type Determines Connectivity

### Overall Statistics for H-group 605.1

| Source | Domains | Isolated (0 edges) | Mean Degree |
|--------|---------|-------------------|-------------|
| PDB | 40 | 0 (0.0%) | 122.2 |
| AlphaFold | 1,883 | 586 (31.1%) | 30.8 |

**PDB domains have 0% isolation; AlphaFold has 31% isolation.**

### Sequence Length vs Connectivity (AlphaFold)

| Length | Domains | Isolated | % Isolated | Mean Degree |
|--------|---------|----------|------------|-------------|
| 0-30 aa | 131 | 101 | 77.1% | 0.3 |
| 30-50 aa | 211 | 128 | 60.7% | 0.7 |
| 50-75 aa | 622 | 160 | 25.7% | 38.5 |
| 75-100 aa | 514 | 104 | 20.2% | 49.7 |
| 100-150 aa | 297 | 69 | 23.2% | 20.9 |
| 150-500 aa | 107 | 24 | 22.4% | 20.4 |

### Sequence Length vs Connectivity (PDB)

| Length | Domains | Isolated | % Isolated | Mean Degree |
|--------|---------|----------|------------|-------------|
| 0-30 aa | 1 | 0 | 0.0% | 14.0 |
| 30-50 aa | 2 | 0 | 0.0% | 114.5 |
| 50-75 aa | 16 | 0 | 0.0% | 99.8 |
| 75-100 aa | 17 | 0 | 0.0% | 166.2 |
| 100-150 aa | 4 | 0 | 0.0% | 56.0 |

**Critical observation:** PDB domains cluster at ALL lengths, including short ones. The issue is specific to AlphaFold domain assignments.

## Interpretation

1. **HisKA is a ~100 aa domain.** Having 342 AlphaFold domains under 50 aa (18% of AFDB) indicates:
   - Domain boundary prediction errors in AlphaFold structure parsing
   - Incorrect F70 representative selection (fragments chosen as cluster reps)
   - Possible multi-domain protein splitting issues

2. **Short fragments cannot produce BLAST edges** at E-value threshold 1e-4, making them appear as isolated nodes that reduce consistency scores.

3. **PDB domains cluster perfectly** regardless of length, suggesting the underlying HisKA family is coherent - the problem is data quality, not biological heterogeneity.

## Edge Density Analysis

- Total sequences: 1,923
- Total BLAST edges (E < 1e-4): 31,487
- Maximum possible edges: 1,848,003
- **Edge density: 1.70%**

### Connectivity Distribution (All Sources)

| Category | Count | Percentage |
|----------|-------|------------|
| Isolated (0 edges) | 586 | 30.5% |
| Low (1-5 edges) | 836 | 43.5% |
| Medium (6-50 edges) | 145 | 7.5% |
| High (>50 edges) | 356 | 18.5% |

## F-group Distribution in 605.1

| F-group | Domains | Isolated | % Isolated | Mean Degree |
|---------|---------|----------|------------|-------------|
| 605.1.1.1 (HisKA) | 1,478 | 453 | 31% | 37.4 |
| 605.1.1.4 | 290 | 90 | 31% | 22.0 |
| 605.1.1.0 (provisional) | 105 | 28 | 27% | 5.1 |
| 605.1.1.2 | 35 | 12 | 34% | 15.5 |

All major F-groups show similar isolation rates (~30%), confirming this is a data quality issue affecting all F-groups equally, not F-group-specific problems.

## Database Connection Details

```
host: dione
port: 45000
user: ecod
database: ecod_protein
password: $DB_PASSWORD  # Set via .env file
```

## Key Tables and Columns

- `ecod_commons.proteins.source_type`: 'pdb' or 'afdb'
- `ecod_commons.domains`: links to proteins via protein_id
- `ecod_commons.f_group_assignments`: F-group assignments via domain_id
- `ecod_rep.domain.type`: 'experimental structure', 'computed structural model', or NULL

## Recommendations

### For Consistency Analysis

1. **Filter analysis by minimum sequence length** (>= 50 aa) to exclude fragments
2. **Consider separate metrics** for PDB vs AlphaFold domains
3. **Weight consistency scores** by edge density - low-connectivity H-groups may lack signal for meaningful clustering

### For ecod_rep Data Quality (See DEFICIENCY_REPORT_605.1.md)

4. **Policy Change:** `simple_topology` domains should not serve as provisional manual representatives
5. **Remediation:** Audit and address 574 existing simple_topology provisional reps across 122 H-groups
6. **Provenance Tracking:** Implement explicit tracking of representative domain origins:
   - Source pipeline (SwissProt DPAM, Proteomes DPAM, AF2 Human, single-species)
   - Classification judge
   - Accession date/version
7. **Validation Gates:** Add pre-accession checks for rep candidates:
   - Minimum domain length relative to expected family size
   - Minimum classification confidence
   - Review before singleton F-group creation

## Conclusions

The F-group consistency analysis revealed a significant data quality issue: **simple_topology domains from automated DPAM classification are being accessioned as provisional representatives**, creating:

1. Spurious singleton F-groups based on structural fragments
2. Isolated nodes that degrade clustering metrics
3. False Pfam associations from partial structural matches

**Key evidence:**
- 605.1 (HisKA): 1.2% consistency driven by 31% isolated AFDB fragments
- 574 simple_topology provisional reps identified across ecod_rep
- Strong correlation between simple_topology rep count and poor consistency

**Positive finding:** SwissProt DPAM (most recent accession) shows only 4.7% fragments, indicating quality controls have improved. The problem is concentrated in legacy Proteomes and single-species DPAM data.

**Path forward:** Address the simple_topology provisional rep issue as a data quality remediation separate from consistency analysis. Once addressed, re-run consistency evaluation to assess true F-group coherence.

## Source of Short Fragments (2026-01-31 Update)

### Primary Source: Proteomes `simple_topology` Classification

Matching FASTA domains by UniProt accession + domain number to source databases:

| Source | Matched | Short (<50aa) |
|--------|---------|---------------|
| Proteomes | 1,397 | 280 |
| SwissProt | 402 | 4 |
| Unmatched (PDB) | 124 | ~3 |

**Judge classification breakdown for matched domains:**

| Judge | Total | Short (<50aa) | % Short |
|-------|-------|---------------|---------|
| `good_domain` | 985 | 3 | 0.3% |
| `simple_topology` | **731** | **273** | **37.3%** |
| `low_confidence` | 71 | 4 | 5.6% |
| `partial_domain` | 12 | 4 | 33.3% |

### Complete Source Breakdown for 605.1 FASTA (1,922 domains)

| Source | Total | Short (<50aa) | % Short |
|--------|-------|---------------|---------|
| SwissProt | 401 | 19 | 4.7% |
| Proteomes (48 species) | 1,397 | 265 | 19.0% |
| AF2 Human | 27 | 22 | **81.5%** |
| Other single-species DPAM | 57 | 36 | **63.2%** |
| PDB | 40 | 3 | 7.5% |

### Short Fragment Sources

**Total short fragments: 345**

| Source | Short Count | % of Total Short |
|--------|-------------|------------------|
| Proteomes `simple_topology` | ~265 | 77% |
| AF2 Human | 22 | 6% |
| Other DPAM (dicdi, drome, orsyj, etc.) | 36 | 10% |
| SwissProt | 19 | 6% |
| PDB | 3 | 1% |

### Other Single-Species DPAM Breakdown

From `public.domain` table:
- dicdi_dpam_v5 (Dictyostelium): 21 domains
- drome_dpam_v5 (Drosophila): 9 domains
- orsyj_dpam_v5 (Rice): 9 domains
- yeast_dpam_v5: 8 domains
- haein_dpam_v5 (Haemophilus): 4 domains
- caeel_dpam_v5 (C. elegans): 3 domains
- Others: 3 domains

Judge distribution for other DPAM:
- `simple_topology`: 43 (75%)
- `low_confidence`: 11 (19%)
- `good_domain`: 2 (4%)
- `partial_domain`: 1 (2%)

### What is `simple_topology`?

The `simple_topology` judge indicates:
- Low HHpred probability (~0.18 vs 0.61 for `good_domain`)
- Moderate DPAM probability (~0.83 vs 0.96 for `good_domain`)
- Automated classification based primarily on structural similarity
- Often produces fragmentary domain assignments (~37% are <50 aa)

### SwissProt Quality

SwissProt-matched domains (401 total) are high quality:
- Only 19 domains under 50 aa (4.7%)
- Predominantly `good_domain` classification

### Domain Breakdown for 605.1 FASTA

| Category | Count | Short (<50aa) | Mean Length |
|----------|-------|---------------|-------------|
| SwissProt | 251 | 1 | 91.1 aa |
| AFDB long | 1,283 | 0 | 89.0 aa |
| AFDB short | 341 | 341 | 31.2 aa |
| PDB | 39 | 3 | 75.6 aa |

### Classification Method in ecod_commons

| Method | Source | Count | Mean Len | Short |
|--------|--------|-------|----------|-------|
| NULL | afdb | 2,266 | 79.3 | 358 |
| NULL | pdb | 235 | 74.1 | 0 |
| mini_pyecod | pdb | 43 | 81.3 | 1 |

## Next Steps

### Completed
- [x] Check if short fragments are from SwissProt automated classification → **NO, from Proteomes/single-species DPAM**
- [x] Trace fragment origins to classification source and judge
- [x] Audit simple_topology provisional reps across all ecod_rep → **574 identified**
- [x] Document 605.1 case study as deficiency report
- [x] Identify correlation between simple_topology reps and poor consistency

### Pending
- [ ] Policy decision on simple_topology provisional rep disqualification
- [ ] Remediation plan for 574 affected F-groups
- [ ] Pfam coverage impact analysis for unique Pfam associations
- [ ] Rerun consistency analysis after remediation
- [ ] Implement provenance tracking for future accessions

---

## Systematic Audit: simple_topology Provisional Representatives

Following the 605.1 case study, a full audit of ecod_rep was conducted.

### Scope of Problem

| Metric | Count |
|--------|-------|
| Total provisional-only reps in ecod_rep | 8,157 |
| `simple_topology` provisional reps | **574** (7.0%) |
| Affected H-groups | **122** |
| Associated Pfams at risk | **444** |

### Correlation with Consistency Metrics

**Top H-groups by simple_topology provisional rep count:**

| H-group | simple_topo F-groups | Consistency | In Worst Performers? |
|---------|---------------------|-------------|---------------------|
| 3755.3 | 96 | 1.8% | **Yes** (#5) |
| 192.8 | 57 | 5.9% | **Yes** (#27) |
| 3922.1 | 55 | 1.8% | **Yes** (#4) |
| 5086.1 | 35 | 5.6% | **Yes** (#25) |
| 101.1 | 25 | 2.8% | **Yes** (#11) |
| 386.1 | 10 | 1.7% | **Yes** (#3) |
| 605.1 | 7 | 1.2% | **Yes** (#1) |

**Strong correlation:** H-groups with many simple_topology provisional reps consistently appear among the worst performers for F-group consistency.

### Provisional Rep Classification Distribution

| Judge | Count | % of Total |
|-------|-------|------------|
| PDB | 4,757 | 58.3% |
| good_domain | 2,314 | 28.4% |
| simple_topology | 574 | 7.0% |
| low_confidence | 442 | 5.4% |
| partial_domain | 69 | 0.8% |

### Generated Audit Files

- `analysis/simple_topology_prov_reps.tsv` - Full list of 574 affected F-groups
- `analysis/audit_simple_topology_reps.sql` - SQL query template for database audit
- `analysis/DEFICIENCY_REPORT_605.1.md` - Detailed case study and recommendations

---

## Critical Finding: Pfam Distance ≠ BLAST Distance (2026-01-31)

**See full analysis:** `analysis/METHODOLOGY_FINDINGS.md`

### Discovery

After the simple_topology deaccession, 605.1 was re-analyzed. Despite cleanup, consistency remained low (8.8%). Investigation revealed that F-groups in 605.1 completely overlap in CLANS space - different Pfam families share similar BLAST profiles.

### Systematic Analysis

Analysis of 1,167 H-groups with 2+ multi-member F-groups:

| Category | Count | % | Description |
|----------|-------|---|-------------|
| Well separated | 74 | 6.3% | F-groups = BLAST clusters |
| Moderate | 179 | 15.3% | F-groups ≈ BLAST clusters |
| Overlapping | 295 | 25.3% | Partial correspondence |
| Severe overlap | 619 | 53.0% | F-groups ≠ BLAST clusters |

**Key Finding:** Only 21.7% of H-groups have F-groups that form distinct BLAST-detectable clusters. For 78.3%, F-groups capture relationships that pairwise BLAST cannot detect.

### Root Cause

F-group assignment and CLANS clustering measure fundamentally different distances:

| Method | Distance Measured |
|--------|-------------------|
| F-group (Pfam) | sequence → HMM profile |
| CLANS (BLAST) | sequence ↔ sequence |

Two domains can match the same Pfam HMM (same F-group) while having poor pairwise BLAST similarity (no CLANS edge). This is expected for diverse families with conserved motifs.

### Implications

1. **Consistency is not a universal quality metric** - only applicable to ~22% of H-groups
2. **Low consistency in overlapping H-groups is expected**, not an error
3. **simple_topology deaccession was still valuable** - removed fragmentary reps regardless of clustering behavior
4. **Future analysis should stratify** by separation ratio before interpreting consistency

### Updated Pending Tasks

- [x] ~~Rerun consistency analysis after remediation~~ → Completed; led to methodology finding
- [ ] Policy decision on simple_topology provisional rep disqualification
- [ ] Remediation plan for 574 affected F-groups
- [ ] Develop alternative quality metrics for overlapping H-groups
- [ ] Identify the 253 H-groups where consistency IS meaningful for targeted review

---

## Technical Notes

- CLANS parameters: E-value 1e-4, 500 rounds
- Edge density calculation: edges / (n*(n-1)/2)
- Silhouette scores negative due to isolated nodes having no cluster assignment
- Separation ratio = max(internal spread) / min(inter-centroid distance)
