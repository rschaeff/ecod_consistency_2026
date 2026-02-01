# Sources of ECOD Classification Inconsistency

## Overview

This document describes the known sources of classification inconsistency in ECOD and how they relate to the F-group consistency analysis pipeline.

## The Consistency Premise

A domain within an F-group should be closer to the centroid of its own F-group than to the centroid of any related F-group within the same H-group. Violations of this premise indicate potential classification issues.

## Sources of Inconsistency

### 1. Domain Boundary Issues ("Cantilevering")

**Description**: Domain boundaries are incorrectly extended or truncated, leading to classification artifacts.

**Origins**:
- **Automated boundary detection errors**: Algorithms may include/exclude regions incorrectly
- **PDB chain curation**: Curators may "fold in" partial domains at chain termini
- **Structural artifacts**: Low-resolution regions, disorder, or crystal contacts

**Propagation mechanism**:
1. A domain with incorrect boundaries becomes a representative
2. New domains are classified against this flawed representative
3. The boundary problem propagates through subsequent classifications
4. F-group accumulates domains with similar boundary issues

**Detection signals**:
- Unusual sequence length vs F-group median
- Poor structural alignment at N/C termini
- Low LDDT scores in terminal regions

### 2. Bona Fide Misclassifications

**Description**: Domains placed in incorrect groups despite correct boundaries.

**Origins**:
- **Duplicate groups**: Curator creates new X-group when suitable one existed
- **Classifier confusion**: Multiple valid classification targets
- **Evolutionary ambiguity**: Genuine borderline cases between families

**Detection signals**:
- Domain closer to another F-group centroid (distance ratio > 1.0)
- Bidirectional inconsistency between F-groups (merge candidates)
- Normal boundaries but poor centroid distance

### 3. Provisional Manual Representatives

**Description**: Automated domains serving as classification targets due to absence of curated representatives.

**Background**:
- ECOD uses manual representatives as classification targets
- Rule: A domain's manual representative must reside in the same F-group
- Problem: New F-groups have no manual representatives
- Solution: First automated domain becomes "provisional manual representative"

**Why this causes inconsistency**:

| Issue | Consequence |
|-------|-------------|
| No curation | Provisional rep may have poor boundaries or structural artifacts |
| Self-seeding | Provisional rep defines what the F-group "looks like" to classifiers |
| Quality variance | Selected by necessity, not quality |
| No structural review | May come from low-resolution structures |
| Boundary propagation | All subsequent domains inherit the flawed reference |

**The cascade**:
1. New F-group created → provisional rep assigned (possibly flawed)
2. Classifier uses provisional rep as target
3. New domains match the flawed rep → inherit its characteristics
4. F-group grows around the flawed seed
5. Eventually, good domains don't match well (appear inconsistent)
6. Or bad domains match the flawed boundary region (false positives)

## Representative Domain Types in ECOD

### Manual Representatives (Curated)
- **Location**: `ecod_rep.domains` with `is_manual_representative = true`
- **Selection**: Human-curated, high-quality exemplars
- **Purpose**: Serve as classification targets

### Provisional Manual Representatives
- **Location**: `ecod_rep.domains` with `is_provisional_representative = true`
- **Selection**: Automated, first domain in new F-group
- **Purpose**: Placeholder until manual curation occurs

### Cluster Representatives (Separate System)
- **Location**: `ecod_commons.cluster_representatives`
- **Selection**: CD-HIT clustering at F40/F70/F99 thresholds
- **Purpose**: Redundancy reduction for analysis, NOT classification
- **Note**: Generated after classification, not used for assignment

## Implications for Consistency Analysis

### Triage Strategy

When domains are flagged as inconsistent, determine root cause:

1. **Check if representative is provisional**
   - If yes, the representative itself may be the problem
   - Examine representative's boundaries and structure quality

2. **Compare domain boundaries to F-group consensus**
   - Outlier length suggests boundary issue
   - Normal length suggests classification issue

3. **Structural alignment analysis**
   - Use FoldMason to align F-group members
   - LDDT scores reveal which regions align poorly
   - Terminal LDDT drops indicate boundary problems

### Resolution Paths

| Root Cause | Resolution |
|------------|------------|
| Provisional rep with bad boundaries | Replace with better representative |
| Domain has extended boundaries | Trim domain boundaries |
| Domain has truncated boundaries | Extend domain boundaries |
| True misclassification | Reassign to correct F-group |
| F-groups should be merged | Merge F-groups |
| F-group should be split | Split F-group |

## Next Steps

1. Identify which F-groups rely on provisional manual representatives
2. For inconsistent domains, check representative quality
3. Use structural alignment (FoldMason) to analyze boundary issues
4. Prioritize F-groups with both inconsistency AND provisional reps
