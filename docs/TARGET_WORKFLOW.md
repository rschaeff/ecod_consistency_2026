# Target Workflow: F-group Consistency Analysis Pipeline

## Overview

This document describes the complete pipeline for identifying and validating potential F-group classification inconsistencies in ECOD. The pipeline progressively filters candidates through geometric analysis, structural alignment, and automated scoring before presenting high-confidence cases to curators for review.

## Pipeline Summary

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ECOD Database                                │
│                    (~920K domains, ~13K F-groups)                   │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 1: CLANS Embedding                                           │
│  - Select H-groups with ≥2 F-groups (~1,471)                       │
│  - Extract F70 cluster representatives                              │
│  - Run CLANS force-directed layout per H-group                      │
│  - Output: 3D coordinates labeled by F-group                        │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 2: Geometric Consistency Analysis                            │
│  - Compute F-group centroids                                        │
│  - Calculate domain-to-centroid distances                           │
│  - Flag domains with distance_ratio > 1.0                           │
│  - Output: Ranked list of inconsistent domains                      │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 3: FoldMason Structural Alignment                            │
│  - For each flagged domain + its F-group members                    │
│  - Retrieve structure files (PDB/mmCIF)                             │
│  - Run FoldMason multiple structure alignment                       │
│  - Output: MSA (AA + 3Di) with per-residue LDDT scores              │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 4: Automated Alignment Analysis                              │
│  - Parse LDDT scores per domain                                     │
│  - Detect boundary issues (terminal LDDT drops)                     │
│  - Identify core vs. peripheral regions                             │
│  - Score confidence in inconsistency diagnosis                      │
│  - Output: Annotated candidates with evidence                       │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 5: Curator Review                                            │
│  - Filter to high-confidence candidates                             │
│  - Present with supporting visualizations                           │
│  - Curator determines: reclassify / fix boundary / keep / merge     │
│  - Output: Curation decisions                                       │
└─────────────────────────────────────────────────────────────────────┘
```

## Stage 1: CLANS Embedding

### Purpose
Embed F-group representatives in a geometric space where sequence similarity determines proximity.

### Input
- H-groups with ≥2 F-groups (from `ecod_commons.f_group_assignments`)
- F70 cluster representatives (from `ecod_commons.cluster_representatives`)
- Domain sequences (from `ecod_commons.domain_sequences`)

### Process
1. For each qualifying H-group:
   - Extract all F70 representatives for member F-groups
   - Generate FASTA with F-group labels in headers
   - Run CLANS: all-vs-all BLAST → force-directed layout
2. Execute as SLURM array job (~1,471 jobs)

### Output
- `.clans` files with 3D coordinates per domain
- Domains labeled by F-group membership

### Implementation Status
✅ Implemented: `generate_jobs.py`, `submit_jobs.py`, `run_clans_job.sh`

## Stage 2: Geometric Consistency Analysis

### Purpose
Identify domains that don't cluster with their assigned F-group.

### Input
- CLANS output files (coordinates + F-group labels)

### Process
1. Parse coordinates and F-group assignments
2. Compute centroid for each F-group
3. For each domain:
   - Calculate distance to own F-group centroid
   - Calculate distance to all other F-group centroids
   - Compute distance_ratio = own_dist / nearest_other_dist
   - Compute silhouette coefficient
4. Flag domains with distance_ratio > 1.0 as inconsistent

### Output
- Per-domain: distance_ratio, silhouette, is_consistent flag
- Per-F-group: consistency_rate, mean_silhouette
- Per-H-group: overall metrics, list of inconsistent domains
- Triage report ranking H-groups by severity

### Implementation Status
✅ Implemented: `parse_clans.py`, `evaluate_consistency.py`, `evaluate_all.py`

## Stage 3: FoldMason Structural Alignment

### Purpose
Structurally align inconsistent domains with their F-group to assess whether the inconsistency reflects a structural problem.

### Input
- Inconsistent domains from Stage 2
- Structure files for flagged domain + F-group members
- Structure source: PDB/mmCIF files (local or fetched)

### Process
1. For each inconsistent domain:
   - Retrieve structure file for the domain
   - Retrieve structure files for other F-group members (or representatives)
   - Run FoldMason `easy-msa`:
     ```bash
     foldmason easy-msa structures/ output_prefix tmp/
     ```
2. Produces:
   - Amino acid alignment (`_aa.fa`)
   - 3Di alignment (`_3di.fa`)
   - LDDT scores per residue

### Output
- Multiple structure alignment for each flagged domain's F-group context
- Per-residue LDDT quality scores
- HTML visualization (optional)

### Implementation Status
⬜ Not yet implemented

### Considerations
- May need to limit F-group members aligned (use representatives)
- Structure retrieval strategy (local cache vs. fetch)
- Handling domains without available structures

## Stage 4: Automated Alignment Analysis

### Purpose
Programmatically analyze FoldMason output to distinguish boundary issues from true misclassifications.

### Input
- FoldMason alignments (AA + 3Di)
- LDDT scores per residue per domain

### Process
1. **Parse LDDT profiles**:
   - Extract per-residue LDDT for each domain
   - Identify regions of high/low structural conservation

2. **Detect boundary issues**:
   - Terminal LDDT drop: Low scores at N/C termini suggest extended boundaries
   - Internal LDDT drop: May indicate insertion or structural divergence
   - Compare domain length to F-group median

3. **Identify core regions**:
   - Regions with consistently high LDDT across members = structural core
   - Flagged domain's LDDT in core regions indicates true membership

4. **Score confidence**:
   - High core LDDT + low terminal LDDT → Boundary issue (fixable)
   - Low core LDDT → Possible misclassification
   - Normal LDDT throughout → Geometric outlier but structurally similar

5. **Cross-reference**:
   - Check if domain is provisional representative
   - Check for existing cross-boundary pairs in curation system
   - Note if domain has unusual length

### Output
- Per-domain diagnosis:
  - `boundary_issue`: N-terminal / C-terminal / both / none
  - `core_lddt_score`: Average LDDT in core regions
  - `confidence`: High / Medium / Low
  - `recommended_action`: review_boundary / review_classification / likely_ok
- Supporting evidence for each diagnosis

### Implementation Status
⬜ Not yet implemented

## Stage 5: Curator Review

### Purpose
Present high-confidence candidates to human curators for final decision.

### Input
- Filtered candidates from Stage 4
- Supporting evidence (alignments, LDDT profiles, cross-references)

### Process
1. **Filter candidates**:
   - Exclude low-confidence cases
   - Prioritize by severity (distance_ratio, core LDDT)
   - Group by H-group for efficient review

2. **Present evidence**:
   - Domain identification and current classification
   - CLANS embedding visualization (domain position relative to F-groups)
   - FoldMason alignment with LDDT highlighting
   - Recommended action with rationale

3. **Curator decisions**:
   - **Reclassify**: Move domain to different F-group
   - **Fix boundary**: Adjust domain range definition
   - **Keep**: Domain is correctly classified (distant homolog)
   - **Merge F-groups**: F-groups should be combined
   - **Flag for expert**: Escalate to domain expert

### Output
- Curation decisions logged
- Feedback loop: decisions inform future analysis priorities

### Implementation Status
⬜ Not yet implemented (may integrate with pyecod_vis)

## Data Flow Summary

| Stage | Input | Output | Scale |
|-------|-------|--------|-------|
| 1. CLANS | ~858K F70 reps | 1,471 embeddings | ~1,471 jobs |
| 2. Consistency | Embeddings | Flagged domains | ? domains |
| 3. FoldMason | Flagged + F-group structures | MSAs + LDDT | ? alignments |
| 4. Analysis | MSAs + LDDT | Scored candidates | ? candidates |
| 5. Curation | High-confidence candidates | Decisions | ? reviews |

Scale at each stage depends on consistency rate observed.

## Resource Requirements

### Compute
- Stage 1: SLURM cluster, ~2 hours per job, 4 cores, 8GB RAM
- Stage 3: FoldMason alignment, scales with F-group size

### Storage
- FASTA files: ~500MB estimated
- CLANS output: ~2GB estimated
- FoldMason alignments: TBD (depends on Stage 2 results)

### Database
- Read access to ecod_commons, ecod_rep, ecod_curation schemas
- Queries for representatives, sequences, structures, cross-boundary pairs

## Success Criteria

1. **Coverage**: All 1,471 H-groups with ≥2 F-groups evaluated
2. **Sensitivity**: Known problem cases (from curation system) detected
3. **Specificity**: Reasonable false-positive rate in curator review
4. **Actionability**: Candidates come with clear evidence and recommended actions
5. **Efficiency**: Pipeline reduces curator workload vs. manual review

## Dependencies

- CLANS Python implementation: `~/dev/claude_clans/CLANS`
- FoldMason: `~/src/foldmason/bin/foldmason`
- ECOD database: `dione:45000`
- SLURM cluster for parallel execution
- Structure files: PDB/mmCIF access

## Next Steps

1. ✅ Stage 1-2 implemented and tested
2. ⬜ Run Stage 1 on full dataset
3. ⬜ Analyze Stage 2 results to estimate Stage 3 scale
4. ⬜ Implement Stage 3 (FoldMason integration)
5. ⬜ Implement Stage 4 (alignment analysis)
6. ⬜ Design Stage 5 interface (curator review)
