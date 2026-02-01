# Existing Curation-Based Inconsistency Detection

## Overview

The pyecod_vis system (`~/dev/pyecod_vis`) includes infrastructure for identifying classification inconsistencies during the curation workflow. This document describes that system for reference and potential integration with our CLANS-based consistency analysis.

## Database Schemas

### ecod_rep (Hierarchy Authority)

**Location**: `ecod_protein` database on `dione:45000`

**Purpose**: Contains the official ECOD hierarchy definitions and representative domains.

**Key Tables**:

| Table | Purpose |
|-------|---------|
| `ecod_rep.cluster` | Hierarchy definitions (T/H/X/F groups) |
| `ecod_rep.domain` | Representative domains with `manual_rep` flag |

**ecod_rep.cluster columns**:
- `id` (dom_cid) - Group identifier, e.g., "1.1.13.29" (F-group)
- `type` (ctype) - 'T', 'H', 'X', or 'F'
- `name` - Human-readable group name
- `parent` - Parent group reference

**ecod_rep.domain columns**:
- `ecod_domain_id` - e.g., "e8s9s71"
- `t_id`, `f_id` - Group references
- `manual_rep` (boolean) - True if curated manual representative
- `chain_id`, `seqid_range` - Domain definition

### ecod_curation (Staging/Curation)

**Purpose**: Temporary holding area for proteins undergoing curation, including cross-boundary validation.

**Key Tables**:

#### ecod_curation.protein
Tracks proteins through curation workflow:
- Status progression: `pending` → `in_progress` → `curated` → `accessioned`
- Metadata and accession tracking

#### ecod_curation.domain_assignment
Domain predictions and curator modifications:
- `flagged_as_representative` (boolean) - Domain should become a representative
- `flag_reason` (text) - Why it was flagged
- `curator_decision` - 'pending', 'accepted', 'modified', 'rejected', 'needs_expert'
- F-group assignment (required before accession)
- Links to best-match ecod_commons domains

#### ecod_curation.cross_boundary_pair
**Critical for inconsistency detection** - stores similarity pairs across family boundaries:
- `domain1_provisional_rep` (boolean) - First domain is provisional representative
- `domain2_provisional_rep` (boolean) - Second domain is provisional representative
- Similarity scores between domains in different families
- Used to identify potential misclassifications or merge candidates

#### ecod_curation.validation_curation
Tracks curation actions on validation issues:
- Links to cross_boundary_pair entries
- Records curator decisions on flagged pairs

#### Supporting Tables
- `domain_evidence` - BLAST/HHsearch evidence supporting assignments
- `curation_queue` - Prioritized proteins for curation
- `curation_decision_log` - Analytics on curator decisions
- `domain_boundary_history` - Audit trail of boundary modifications

### ecod_commons (Domain Authority)

**Purpose**: All active ECOD domains (PDB and AlphaFold).

**Representative flags**:
- `is_representative` (boolean) - General representative status
- `is_manual_representative` (boolean) - Explicitly curated representative
- `is_provisional_representative` (boolean) - Automated placeholder representative

## Cross-Boundary Pair Analysis

### What It Captures

The cross_boundary_pair table identifies domains that:
1. Reside in **different F-groups** (or higher-level groups)
2. Have **high sequence/structural similarity**
3. May indicate classification inconsistency

### Provisional Representative Flags

The `domain1_provisional_rep` and `domain2_provisional_rep` flags indicate when one or both domains in a high-similarity pair are provisional representatives. This is significant because:

- Provisional reps define F-group boundaries for classification
- High similarity between a provisional rep and a domain in another F-group suggests:
  - The provisional rep may be misclassified
  - The F-groups may need to be merged
  - Domain boundaries may be causing false similarity

### Validation Workflow

1. **Detection**: Cross-boundary pairs identified by similarity search
2. **Flagging**: Pairs with provisional reps flagged for review
3. **Curation**: Curator evaluates and decides:
   - `mask_from_search` - Remove from search libraries
   - `remove` - Remove from ECOD entirely
   - `reclassify` - Move to different F-group
   - `flag_review` - Escalate to expert review
4. **Resolution**: Changes applied during accession

## Problematic H-groups Tracking

### API Endpoint
`/api/curation/problematic-hgroups/:id`

### What It Tracks
- H-groups with high rates of `is_manual_rep = false` (relying on provisional reps)
- H-groups with high `low_confidence` assignment rates
- Representative usage patterns across the group
- Recommended representative adjustments

### Data Source
Joins:
- `ecod_rep.cluster` (H-group definitions)
- `ecod_curation.problematic_hgroups` (curation metadata)
- Reference domain usage statistics

## Relationship to CLANS-Based Analysis

### Complementary Approaches

| Aspect | Curation System | CLANS Analysis |
|--------|-----------------|----------------|
| **Timing** | During curation (prospective) | Post-classification (retrospective) |
| **Method** | Pairwise similarity | Embedding + centroid distance |
| **Scope** | Individual domain pairs | Entire F-group context |
| **Signal** | High cross-boundary similarity | Distance ratio to centroids |
| **Focus** | New domains entering ECOD | All existing domains |

### Potential Integration Points

1. **Cross-boundary pairs as validation**
   - CLANS flags domain X as inconsistent
   - Check if X appears in cross_boundary_pair table
   - If yes, curation system already identified this issue

2. **Provisional rep identification**
   - CLANS flags F-group with low consistency
   - Query ecod_commons for `is_provisional_representative = true`
   - Correlate inconsistency with provisional rep usage

3. **Prioritization**
   - Use cross_boundary_pair data to prioritize CLANS analysis
   - Focus on H-groups already flagged as problematic

## Querying Cross-Boundary Data

### Example: Find cross-boundary pairs for an H-group

```sql
SELECT
    cbp.domain1_id,
    cbp.domain2_id,
    cbp.domain1_provisional_rep,
    cbp.domain2_provisional_rep,
    f1.f_group_id as domain1_fgroup,
    f2.f_group_id as domain2_fgroup
FROM ecod_curation.cross_boundary_pair cbp
JOIN ecod_commons.f_group_assignments f1
    ON cbp.domain1_id = f1.domain_id
JOIN ecod_commons.f_group_assignments f2
    ON cbp.domain2_id = f2.domain_id
WHERE f1.h_group_id = '1.1'
   OR f2.h_group_id = '1.1';
```

### Example: Find provisional representatives in an F-group

```sql
SELECT
    d.id,
    d.domain_id,
    d.is_provisional_representative,
    d.is_manual_representative
FROM ecod_commons.domains d
JOIN ecod_commons.f_group_assignments f
    ON d.id = f.domain_id
WHERE f.f_group_id = '1.1.1.1'
    AND d.is_obsolete = false
    AND (d.is_provisional_representative = true
         OR d.is_manual_representative = true);
```

## Summary

The existing curation system approaches inconsistency detection from the **prospective** side - identifying issues as new domains enter ECOD. Key mechanisms:

1. **Cross-boundary pair detection** - Flags high-similarity pairs across F-group boundaries
2. **Provisional representative tracking** - Identifies when provisional reps are involved
3. **Problematic H-group monitoring** - Aggregates issues at the H-group level
4. **Validation workflow** - Structured process for curator review

Our CLANS-based analysis complements this by providing **retrospective** evaluation of the entire classification, using geometric embedding to identify domains that may have been missed by pairwise comparison.
