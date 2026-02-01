# Deaccession Plan: Simple Topology Provisional Representatives

**Date:** 2026-01-31
**Author:** ECOD Consistency Pipeline
**Target Release:** v293.1 (current development)
**Scope:** 574 simple_topology provisional representatives across 122 H-groups

---

## Executive Summary

This plan outlines the procedure to deaccession simple_topology provisional representatives from ecod_rep while preserving the full audit trail using the existing hierarchy change request system.

---

## Background

The deficiency report (DEFICIENCY_REPORT_605.1.md) identified 574 F-groups with `simple_topology` provisional representatives that should be disqualified. These fall into two categories:

1. **Singleton F-groups (majority):** The simple_topology domain is the only member → deprecate the F-group
2. **Multi-member F-groups:** Other domains exist → demote provisional rep, optionally promote a qualified replacement

---

## Audit Trail Mechanisms

The ecod_rep schema provides these audit mechanisms:

| Table | Purpose |
|-------|---------|
| `hierarchy_change_request` | Tracks all change requests with status workflow |
| `hierarchy_change_history` | Records implemented changes with old/new JSONB snapshots |
| `cluster_changelog` | Automatic trigger-based logging of all cluster changes |
| `domain_modification_log` | Tracks domain attribute changes (provisional_manual_rep) |
| `domain_assignment_log` | Tracks F-group reassignments |

### Key Functions

| Function | Purpose |
|----------|---------|
| `create_hierarchy_change_request()` | Creates pending request |
| `approve_hierarchy_change_request()` | Approves request |
| `implement_deprecate_group()` | Deprecates F-group with full audit |
| `implement_set_provisional_rep()` | Changes provisional_manual_rep with logging |
| `implement_reassign_f_group()` | Moves domain to new F-group with logging |

---

## Deaccession Categories

### Category A: Singleton F-groups (Deprecate)

**Criteria:** F-group has exactly one domain, which is the simple_topology provisional rep.

**Action:** Deprecate the F-group entirely.

**Workflow:**
1. Create deprecation request via `create_hierarchy_change_request()`
2. Approve request via `approve_hierarchy_change_request()`
3. Implement via `implement_deprecate_group()`

**Result:**
- `cluster.is_deprecated = TRUE`
- `cluster.deprecated_release_id` set to current release
- Comment updated with deprecation justification
- Full JSONB snapshot in `hierarchy_change_history`
- Automatic entry in `cluster_changelog` via trigger

### Category B: Multi-member F-groups with Qualified Replacement

**Criteria:** F-group has >1 domain, and at least one non-simple_topology domain exists that can serve as representative.

**Action:** Demote simple_topology provisional rep, promote qualified replacement.

**Workflow:**
1. Create domain_update request for demoting current provisional rep
2. Create domain_update request for promoting new representative
3. Approve and implement both requests

**Result:**
- Old rep: `provisional_manual_rep = FALSE` logged in `domain_modification_log`
- New rep: `provisional_manual_rep = TRUE` logged in `domain_modification_log`

### Category C: Multi-member F-groups without Qualified Replacement

**Criteria:** F-group has >1 domain, but all domains are simple_topology or otherwise unqualified.

**Action:** Flag for manual review. Potentially deprecate F-group if all members are fragments.

---

## Implementation Steps

### Phase 1: Analysis and Classification

```sql
-- Classify F-groups by member count and replacement availability
WITH simple_topo_fgroups AS (
    SELECT DISTINCT f_id
    FROM simple_topology_provisional_reps  -- from TSV data
),
fgroup_members AS (
    SELECT
        d.f_id,
        COUNT(*) as member_count,
        COUNT(*) FILTER (WHERE d.provisional_manual_rep = TRUE) as prov_rep_count,
        -- Check ecod_commons for qualified replacements
        BOOL_OR(
            EXISTS (
                SELECT 1 FROM swissprot.domain sd
                WHERE sd.uid = d.ecod_uid
                AND sd.classification IN ('good_domain', 'high_confidence')
            )
        ) as has_qualified_replacement
    FROM ecod_rep.domain d
    WHERE d.f_id IN (SELECT f_id FROM simple_topo_fgroups)
    GROUP BY d.f_id
)
SELECT
    f_id,
    member_count,
    CASE
        WHEN member_count = 1 THEN 'A_SINGLETON_DEPRECATE'
        WHEN has_qualified_replacement THEN 'B_REPLACE_REP'
        ELSE 'C_MANUAL_REVIEW'
    END as category
FROM fgroup_members;
```

### Phase 2: Batch Processing Script

```python
#!/usr/bin/env python3
"""
Deaccession simple_topology provisional representatives with full audit trail.
"""

import psycopg2
from psycopg2.extras import RealDictCursor

JUSTIFICATION_TEMPLATE = """
Simple topology domains should not serve as provisional manual representatives.
Classification: {classification}
HHpred probability: {hhpred_prob}
DPAM probability: {dpam_prob}
Domain length: {length} aa (expected: {expected_length} aa for H-group)
Reference: DEFICIENCY_REPORT_605.1.md
"""

def create_deprecation_request(conn, f_id, justification, requested_by='consistency_pipeline'):
    """Create a hierarchy change request for F-group deprecation."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT ecod_rep.create_hierarchy_change_request(
                p_request_type := 'deprecate',
                p_group_type := 'F',
                p_original_id := %s,
                p_justification := %s,
                p_requested_by := %s
            )
        """, (f_id, justification, requested_by))
        return cur.fetchone()[0]

def approve_and_implement_deprecation(conn, request_id, reviewed_by='consistency_pipeline'):
    """Approve and implement a deprecation request."""
    with conn.cursor() as cur:
        # Approve
        cur.execute("""
            SELECT ecod_rep.approve_hierarchy_change_request(%s, %s)
        """, (request_id, reviewed_by))

        # Implement
        cur.execute("""
            SELECT ecod_rep.implement_hierarchy_change(%s)
        """, (request_id,))

        return cur.fetchone()[0]

def demote_provisional_rep(conn, domain_uid, request_id, changed_by='consistency_pipeline'):
    """Demote a provisional representative with audit logging."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT ecod_rep.implement_set_provisional_rep(
                p_domain_uid := %s,
                p_new_value := FALSE,
                p_request_id := %s,
                p_changed_by := %s
            )
        """, (domain_uid, request_id, changed_by))

def promote_new_rep(conn, domain_uid, request_id, changed_by='consistency_pipeline'):
    """Promote a new provisional representative with audit logging."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT ecod_rep.implement_set_provisional_rep(
                p_domain_uid := %s,
                p_new_value := TRUE,
                p_request_id := %s,
                p_changed_by := %s
            )
        """, (domain_uid, request_id, changed_by))
```

### Phase 3: Execution Order

1. **Pre-flight checks:**
   - Verify current development release is v293.1
   - Backup current cluster and domain states
   - Validate all 574 F-groups exist and are not already deprecated

2. **Category A (Singletons):**
   - Process in batches of 50
   - Create, approve, and implement deprecation requests
   - Verify each deprecation in `cluster_changelog`

3. **Category B (Replacements):**
   - For each F-group, identify best replacement candidate:
     - Prefer `good_domain` classification
     - Prefer longer domains (closer to H-group mean)
     - Prefer PDB domains over AFDB
   - Demote current rep, promote replacement
   - Log both changes

4. **Category C (Manual Review):**
   - Generate review report for curator attention
   - Hold for manual decision

5. **Post-processing:**
   - Update release statistics via `update_release_statistics()`
   - Generate summary report

---

## Rollback Procedure

If issues are discovered:

1. **Identify affected requests:**
   ```sql
   SELECT id, original_id, status
   FROM ecod_rep.hierarchy_change_request
   WHERE justification LIKE '%DEFICIENCY_REPORT_605.1%'
   AND status = 'implemented';
   ```

2. **Reverse deprecations:**
   ```sql
   UPDATE ecod_rep.cluster
   SET is_deprecated = FALSE,
       deprecated_release_id = NULL
   WHERE id IN (
       SELECT original_id FROM ecod_rep.hierarchy_change_request
       WHERE justification LIKE '%DEFICIENCY_REPORT_605.1%'
   );
   ```

3. **Log rollback in comments**

---

## Validation Queries

### Verify deprecations logged correctly
```sql
SELECT
    hcr.id as request_id,
    hcr.original_id as f_id,
    hcr.status,
    hch.operation,
    hch.changed_at
FROM ecod_rep.hierarchy_change_request hcr
JOIN ecod_rep.hierarchy_change_history hch ON hch.change_request_id = hcr.id
WHERE hcr.justification LIKE '%simple_topology%';
```

### Verify domain modifications logged
```sql
SELECT
    dml.domain_uid,
    dml.modification_type,
    dml.old_value,
    dml.new_value,
    dml.timestamp
FROM ecod_rep.domain_modification_log dml
WHERE dml.justification LIKE '%simple_topology%'
ORDER BY dml.timestamp;
```

### Verify cluster_changelog entries
```sql
SELECT
    operation,
    record_id,
    old_values->>'is_deprecated' as was_deprecated,
    new_values->>'is_deprecated' as now_deprecated,
    changed_at
FROM ecod_rep.cluster_changelog
WHERE record_id IN (
    SELECT original_id FROM ecod_rep.hierarchy_change_request
    WHERE justification LIKE '%simple_topology%'
);
```

---

## Summary Statistics (Expected)

| Category | Count | Action |
|----------|-------|--------|
| A: Singleton deprecations | ~450 | Deprecate F-group |
| B: Rep replacements | ~100 | Demote/promote |
| C: Manual review | ~24 | Flag for curator |
| **Total** | **574** | |

---

## Appendix: Database Connection

```
Host: dione
Port: 45000
Database: ecod_protein
User: ecod
Schema: ecod_rep
Current Release: v293.1 (development)
```

---

## Document History

| Date | Author | Change |
|------|--------|--------|
| 2026-01-31 | Consistency Pipeline | Initial plan |
