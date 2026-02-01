# Simple Topology Deaccession - Pre-Execution Report

**Date:** 2026-01-31
**Status:** Ready for Review

---

## Executive Summary

Analysis of 574 simple_topology provisional representatives is complete. The cases have been classified and appropriate actions identified:

| Category | Count | Action | Script |
|----------|-------|--------|--------|
| **A1: True Singletons** | 382 | Deprecate F-group | `batch_deprecate_a1.py` |
| **A2: With Replacement** | 51 | Replace provisional rep | `batch_replace_a2.py` |
| **A2: Manual Review** | 139 | Curator decision needed | - |
| **Data Inconsistency** | 2 | Investigate | - |
| **Total** | **574** | | |

---

## Category A1: Singleton F-groups (382)

### Description
F-groups where:
- 1 representative domain in `ecod_rep.domain`
- 1 domain assigned in `ecod_commons.f_group_assignments`
- Representative is `simple_topology` classification

### Action
**Deprecate the F-group** via hierarchy change request system.

### Audit Trail
Each deprecation creates:
1. `hierarchy_change_request` entry (type='deprecate', status workflow)
2. `hierarchy_change_history` entry with JSONB before/after snapshots
3. `cluster_changelog` entry via automatic trigger
4. Comment appended to `ecod_rep.cluster.comment` with justification

### Script
```bash
# Dry run (preview changes)
python batch_deprecate_a1.py --dry-run

# Execute
python batch_deprecate_a1.py --execute --batch-size 50
```

### Sample F-groups to be deprecated
| F-group | H-group | Domain | Pfam | Source |
|---------|---------|--------|------|--------|
| 1008.1.1.47 | 1008.1 | P40573_F1_nD2 | PF07716 | swissprot |
| 101.1.1.254 | 101.1 | K7KTF9_F1_nD3 | PF03789 | proteomes |
| 101.1.1.255 | 101.1 | G5EBU4_F1_nD2 | PF12171 | swissprot |
| 605.1.1.114 | 605.1 | A0A0R0KYT6_F1_nD1 | PF11152 | proteomes |
| 605.1.1.116 | 605.1 | Q9HBM0_F1_nD1 | PF12632 | swissprot |

---

## Category A2: Multi-member F-groups (190 total)

### With Replacement Candidates (51)

F-groups where a `good_domain` member exists to replace the `simple_topology` rep.

#### Action
**Replace provisional representative**:
1. Demote current `simple_topology` rep (`provisional_manual_rep = FALSE`)
2. Promote `good_domain` candidate (`provisional_manual_rep = TRUE`)
3. If candidate not in `ecod_rep.domain`, add it first

#### Audit Trail
Each replacement creates:
1. `hierarchy_change_request` entry (type='domain_update')
2. `domain_modification_log` entries for demote and promote operations

#### Script
```bash
# Dry run
python batch_replace_a2.py --dry-run

# Execute
python batch_replace_a2.py --execute --batch-size 50
```

#### Top replacements by impact
| F-group | Assigned | Current Rep | New Rep | HH prob |
|---------|----------|-------------|---------|---------|
| 192.8.1.210 | 124 | P08730_F1_nD1 | A0A2R8VHP3_F1_nD3 | 0.98 |
| 192.8.1.211 | 26 | K7N091_F1_nD1 | C1H1Q6_F1_nD1 | 0.97 |
| 5086.1.1.87 | 15 | Q9VJY8_F1_nD1 | U7PU40_F1_nD1 | 0.21 |
| 3755.3.1.281 | 13 | P49455_F1_nD1 | P49455_F1_nD1* | 0.99 |
| 3755.3.1.283 | 12 | Q8BHN1_F1_nD1 | A0A0G2QC39_F1_nD1 | 0.99 |

*Same domain exists in both swissprot (simple_topology) and proteomes (good_domain)

---

### Without Replacement Candidates (139) - MANUAL REVIEW

F-groups where no `good_domain` member exists among assigned domains.

#### Options for curator:
1. **Deprecate anyway** - Assigned domains lose F-group until reassigned elsewhere
2. **Keep as-is** - Accept simple_topology rep for now
3. **Find alternative** - Manual search for suitable representative

#### Top cases by assigned domain count
| F-group | Assigned | H-group | Pfam | Description |
|---------|----------|---------|------|-------------|
| 3749.1.1.5 | 17 | 3749.1 | PF25983 | No good_domain in any source |
| 109.26.1.7 | 13 | 109.26 | PF00096 | Zinc finger, all simple_topology |
| 375.1.1.178 | 13 | 375.1 | PF24747 | No good_domain in any source |
| 3297.1.1.11 | 12 | 3297.1 | PF01486 | No good_domain in any source |
| 304.9.1.72 | 10 | 304.9 | PF00096 | Zinc finger, all simple_topology |
| 604.1.1.91 | 10 | 604.1 | PF00096 | Zinc finger, all simple_topology |
| 3922.1.1.127 | 9 | 3922.1 | PF05911 | No good_domain in any source |

**Note:** Many PF00096 (Zn-finger, C2H2 type) cases - this may be a systematic issue with small repeat domains.

---

## Data Files

| File | Description |
|------|-------------|
| `classification_results.tsv` | Full classification of all 574 F-groups |
| `a2_replacement_analysis.tsv` | A2 F-groups with replacement analysis |
| `batch_deprecate_a1.py` | Script for A1 deprecation |
| `batch_replace_a2.py` | Script for A2 replacement |
| `deprecation_results.tsv` | Output from deprecation script |
| `replacement_results.tsv` | Output from replacement script |

---

## Recommended Execution Order

### Phase 1: A1 Singleton Deprecations (382)
```bash
cd /home/rschaeff/work/ecod_consistency_2026/prov_rep_daccession

# Verify dry run
python batch_deprecate_a1.py --dry-run

# Execute
python batch_deprecate_a1.py --execute --batch-size 50
```

### Phase 2: A2 Replacements (51)
```bash
# Verify dry run
python batch_replace_a2.py --dry-run

# Execute
python batch_replace_a2.py --execute --batch-size 50
```

### Phase 3: Manual Review (139)
- Generate curator report
- Decision needed per F-group

---

## Validation Queries (Post-Execution)

### Verify A1 deprecations
```sql
SELECT COUNT(*)
FROM ecod_rep.cluster c
JOIN ecod_rep.hierarchy_change_request hcr ON hcr.original_id = c.id::text
WHERE hcr.justification LIKE '%simple_topology_deaccession%'
AND hcr.request_type = 'deprecate'
AND c.is_deprecated = TRUE;
```

### Verify A2 replacements
```sql
SELECT COUNT(*)
FROM ecod_rep.domain_modification_log dml
WHERE dml.justification LIKE '%simple_topology_replacement%';
```

### Check for any failures
```sql
SELECT *
FROM ecod_rep.hierarchy_change_request
WHERE justification LIKE '%simple_topology%'
AND status = 'failed';
```

---

## Impact Summary

| Metric | Before | After |
|--------|--------|-------|
| F-groups with simple_topology prov reps | 574 | 139 (manual review only) |
| Domains affected by deprecation | 382 | 0 (all singletons) |
| Domains affected by replacement | 799 | 0 (reps swapped, assignments unchanged) |

---

## Approval Required

Before execution, please confirm:

- [ ] A1 deprecations (382 F-groups) approved
- [ ] A2 replacements (51 F-groups) approved
- [ ] A2 manual review (139 F-groups) - decision deferred or specific action

---

## Document History

| Date | Author | Change |
|------|--------|--------|
| 2026-01-31 | Consistency Pipeline | Initial pre-execution report |
