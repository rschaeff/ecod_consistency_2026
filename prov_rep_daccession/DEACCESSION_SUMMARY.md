# Simple Topology Provisional Representative Deaccession Summary

**Date:** 2026-01-31
**Reference:** DEFICIENCY_REPORT_605.1.md

## Overview

Systematic deaccession of 574 F-groups with simple_topology provisional representatives that should not serve as provisional manual representatives.

## Categories Processed

| Category | Description | Count | Action |
|----------|-------------|-------|--------|
| A1 | Singleton F-groups (1 rep, 1 assignment) | 382 | Deprecate |
| A2 with replacement | Multi-member F-groups with good_domain candidate | 51 | Replace rep |
| A2 no replacement | Multi-member F-groups without replacement | 139 | Deprecate |
| B (excluded) | Multi-rep F-groups | 2 | Manual review |
| **Total** | | **574** | |

## Execution Results

### A1 Singleton Deprecation
- **Script:** `batch_deprecate_a1.py`
- **F-groups deprecated:** 382
- **Domains reassigned to .0:** 382

### A2 Replacement (with good_domain candidate)
- **Script:** `batch_replace_a2.py`
- **Successful replacements:** 50
- **Skipped (already complete):** 0
- **Failed:** 1
  - `3755.3.1.19` - FK constraint violation (domain referenced in cross_boundary_pair table)

### A2 No-Replacement Deprecation
- **Script:** `batch_deprecate_a2_no_replacement.py`
- **F-groups deprecated:** 139
- **Domains reassigned to .0:** 447

## Final Totals

| Metric | Count |
|--------|-------|
| F-groups deprecated | 521 |
| F-groups with replaced rep | 50 |
| Domains reassigned to .0 pseudo F-groups | 829 |
| New domains added to ecod_rep | 36 |
| Domains promoted as provisional rep | 7 |
| Hierarchy change requests | 521 |

## Outstanding Issues

### 1. F-group 3755.3.1.19 - Left As-Is (No Action Needed)
- **Current rep:** Q8N2N9_F1_nD3 (ecod_uid: 3542511)
- **Situation:** Domain classified as simple_topology via swissprot but as good_domain via proteomes (HH=0.983, DPAM=0.996)
- **Cause:** Different DPAM versions used for swissprot vs proteomes classifications
- **Cross-boundary issue:** Domain shares 87% sequence identity with Q5JPF3_F1_nD2 (X-group 5046) - separate curation concern
- **Resolution:** No deaccession needed. Domain is valid; classification discrepancy due to DPAM version differences.

### 2. Category B F-groups (2 total)
- Multi-representative F-groups excluded from batch processing
- Require individual manual review

## Scripts and Output Files

| File | Description |
|------|-------------|
| `batch_deprecate_a1.py` | A1 singleton deprecation script |
| `batch_replace_a2.py` | A2 replacement script |
| `batch_deprecate_a2_no_replacement.py` | A2 no-replacement deprecation script |
| `classification_results.tsv` | F-group classification output |
| `a2_replacement_analysis.tsv` | A2 replacement candidate analysis |
| `deprecation_results.tsv` | A1 deprecation results |
| `replacement_results_retry.tsv` | A2 replacement results (final) |
| `deprecation_a2_no_replacement_results.tsv` | A2 no-replacement results |

## Audit Trail

All changes were tracked through:
- `ecod_rep.hierarchy_change_request` - F-group deprecation requests
- `ecod_rep.domain_modification_log` - Domain additions and promotions
- `ecod_rep.cluster_changelog` - Automatic cluster change logging (via triggers)
- `ecod_commons.f_group_assignments.notes` - Domain reassignment annotations
