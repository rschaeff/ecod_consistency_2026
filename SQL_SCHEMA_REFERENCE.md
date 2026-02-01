# ECOD Database SQL Schema Reference

## Connection Details

```python
import os
import psycopg2
conn = psycopg2.connect(
    host='dione',
    port=45000,
    user='ecod',
    dbname='ecod_protein',
    password=os.environ['DB_PASSWORD']  # Set via .env file
)
```

## Core Tables

### 1. `domain` - All ECOD Domains (PDB + AFDB)

**Row count**: ~3.7M domains

Primary table containing all classified domains from both experimental structures (PDB) and computed models (AlphaFold DB).

| Column | Type | Description |
|--------|------|-------------|
| `uid` | int | Primary key |
| `ecod_uid` | int | ECOD unique identifier (joins to `ecod_tmp_hier`) |
| `ecod_domain_id` | varchar | Domain identifier (e.g., "e8bhiE2", "Q80Y24_F1_nD1") |
| `ecod_source_id` | varchar | Source structure ID (PDB code or UniProt_F1) |
| `ecod_chain_id` | varchar | Chain identifier |
| `ecod_seqid_range` | varchar | Residue range (e.g., "A:1-100" or "67-265") |
| `length` | int | Domain length in residues |
| `type` | enum | "experimental structure" or "computed structural model" |
| `hit_ecod_domain_id` | varchar | Reference domain used for classification |
| `hit_ecod_domain_uid` | int | UID of reference domain |
| `ecod_version` | varchar | ECOD version (e.g., "develop290") |

**Notes**:
- PDB domains: `ecod_domain_id` starts with "e" (e.g., "e8bhiE2")
- AFDB domains: `ecod_domain_id` is "nD1", "nD2", etc.; full ID is `ecod_source_id` + `ecod_domain_id`
- Many columns are NULL for non-representative domains

---

### 2. `ecod_tmp_hier` - ECOD Hierarchy Mapping

**Row count**: ~2M entries

Maps domains to their classification hierarchy (X → H → T → F groups).

| Column | Type | Description |
|--------|------|-------------|
| `id` | int | Primary key |
| `ecod_uid` | int | Foreign key to `domain.ecod_uid` |
| `ecod_domain_id` | varchar | Domain identifier |
| `pf_id` | varchar | **F-group ID with family number** (e.g., "377.1.1.5") |
| `f_id` | varchar | T-group ID (e.g., "377.1.1") |
| `h_id` | varchar | H-group ID (e.g., "377.1") |
| `x_id` | varchar | X-group ID (e.g., "377") |
| `a_id` | varchar | Architecture ID (e.g., "a.3") |
| `domain_type` | varchar | "experimental structure" or "computed structural model" |

**Important**:
- `pf_id` contains the full F-group ID (X.H.T.F format)
- `f_id` contains the T-group ID (X.H.T format) - naming is confusing!
- `pf_id` can be NULL for domains not assigned to a specific F-group

**Common Joins**:
```sql
-- Get domain with classification
SELECT d.*, h.pf_id, h.f_id, h.h_id
FROM domain d
JOIN ecod_tmp_hier h ON d.ecod_uid = h.ecod_uid
WHERE h.h_id = '377.1';
```

---

### 3. `ecod_rep.domain` - Representative Domains

**Row count**: ~35K domains

Contains manually curated representative domains for each classification group.

| Column | Type | Description |
|--------|------|-------------|
| `uid` | int | Primary key |
| `ecod_uid` | int | ECOD unique identifier |
| `ecod_domain_id` | varchar | Domain identifier |
| `ecod_source_id` | varchar | Source structure ID |
| `seqid_range` | varchar | Residue range |
| `t_id` | varchar | T-group ID |
| `f_id` | varchar | F-group ID (may be NULL) |
| `type` | varchar | Structure type |
| `manual_rep` | bool | Is manually curated representative |
| `provisional_manual_rep` | bool | Provisional representative status |
| `ecod_representative_domain_id` | varchar | Reference domain ID |

**Usage**: Query this table when you need only representative domains, not all members.

---

### 4. `ecod_rep.cluster` - Classification Groups (F/T/H/X)

**Row count**: ~30K entries

Defines the ECOD classification hierarchy with group names and metadata.

| Column | Type | Description |
|--------|------|-------------|
| `id` | varchar | Group ID (e.g., "377.1.1.5", "377.1.1", "377.1") |
| `type` | char | "F", "T", "H", or "X" |
| `name` | varchar | Group name (e.g., "LIM", "WD40", "Beta propeller") |
| `parent` | varchar | Parent group ID |
| `pfam_acc` | varchar | Associated Pfam accession |
| `comment` | text | Curator comments |
| `is_deprecated` | bool | Deprecation status |

**Usage**:
```sql
-- Get F-group names
SELECT id, name FROM ecod_rep.cluster
WHERE id LIKE '377.1.1.%' AND type = 'F';

-- Get H-group info
SELECT * FROM ecod_rep.cluster WHERE id = '377.1';
```

---

### 5. `reference_domain` - Reference/Template Domains

**Row count**: ~846K domains

Contains reference domains used for classification, with additional metadata.

| Column | Type | Description |
|--------|------|-------------|
| `uid` | int | Primary key |
| `ecod_uid` | int | ECOD unique identifier |
| `ecod_domain_id` | varchar | Domain identifier |
| `length` | int | Domain length |
| `domain_ecod_type` | int | Domain type code |
| `is_manrep` | bool | Manual representative flag |
| `is_f70/f40/f99` | bool | Clustering representative flags |

---

### 6. `protein` - Source Proteins

**Row count**: ~1.9M proteins

Information about source proteins (PDB chains and UniProt entries).

| Column | Type | Description |
|--------|------|-------------|
| `uid` | int | Primary key |
| `source` | varchar | "pdb" or "af2_db" |
| `source_id` | varchar | Identifier (PDB code or UniProt_F1) |
| `unp_acc` | varchar | UniProt accession |
| `length` | int | Protein length |
| `protein_res_range` | varchar | Full residue range |
| `classified_res_range` | varchar | Classified residue range |

---

## Common Query Patterns

### Get all domains in an H-group with F-group info
```sql
SELECT
    d.ecod_domain_id,
    d.ecod_source_id,
    d.length,
    d.ecod_seqid_range,
    d.type,
    h.pf_id as f_group_id,
    h.f_id as t_group_id,
    h.h_id as h_group_id,
    c.name as f_group_name
FROM domain d
JOIN ecod_tmp_hier h ON d.ecod_uid = h.ecod_uid
LEFT JOIN ecod_rep.cluster c ON h.pf_id = c.id
WHERE h.h_id = '377.1'
  AND d.length IS NOT NULL;
```

### Get F-group statistics
```sql
SELECT
    h.pf_id,
    c.name,
    COUNT(*) as domain_count,
    AVG(d.length) as mean_length,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY d.length) as median_length
FROM domain d
JOIN ecod_tmp_hier h ON d.ecod_uid = h.ecod_uid
LEFT JOIN ecod_rep.cluster c ON h.pf_id = c.id
WHERE h.h_id = '5.1'
  AND d.length IS NOT NULL
  AND h.pf_id IS NOT NULL
GROUP BY h.pf_id, c.name
ORDER BY domain_count DESC;
```

### Get all domains for a specific protein
```sql
SELECT
    d.ecod_domain_id,
    d.length,
    d.ecod_seqid_range,
    COALESCE(h.pf_id, h.f_id) as classification
FROM domain d
JOIN ecod_tmp_hier h ON d.ecod_uid = h.ecod_uid
WHERE d.ecod_source_id = 'Q80Y24_F1'
ORDER BY d.ecod_seqid_range;
```

### Find length outliers in an F-group
```sql
WITH fgroup_stats AS (
    SELECT
        h.pf_id,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY d.length) as median_len,
        STDDEV(d.length) as stddev_len
    FROM domain d
    JOIN ecod_tmp_hier h ON d.ecod_uid = h.ecod_uid
    WHERE h.pf_id = '377.1.1.5'
      AND d.length IS NOT NULL
    GROUP BY h.pf_id
)
SELECT
    d.ecod_domain_id,
    d.ecod_source_id,
    d.length,
    d.ecod_seqid_range,
    d.type,
    s.median_len,
    d.length / s.median_len as ratio_to_median
FROM domain d
JOIN ecod_tmp_hier h ON d.ecod_uid = h.ecod_uid
CROSS JOIN fgroup_stats s
WHERE h.pf_id = '377.1.1.5'
  AND d.length > 2 * s.median_len
ORDER BY d.length DESC;
```

### Count domains by source type
```sql
SELECT
    h.h_id,
    d.type,
    COUNT(*) as count
FROM domain d
JOIN ecod_tmp_hier h ON d.ecod_uid = h.ecod_uid
WHERE h.h_id IN ('5.1', '11.1', '377.1')
GROUP BY h.h_id, d.type
ORDER BY h.h_id, d.type;
```

---

## Key Relationships

```
domain.ecod_uid ──────────────┬──► ecod_tmp_hier.ecod_uid
                              │
                              └──► ecod_rep.domain.ecod_uid

ecod_tmp_hier.pf_id ──────────────► ecod_rep.cluster.id (F-group)
ecod_tmp_hier.f_id ───────────────► ecod_rep.cluster.id (T-group)
ecod_tmp_hier.h_id ───────────────► ecod_rep.cluster.id (H-group)

protein.uid ◄─────────────────────► protein_domain.protein_id
domain.uid ◄──────────────────────► protein_domain.domain_id
```

---

## ECOD Classification Hierarchy

```
X-group (Architecture)     e.g., "377" - Similar overall shape
  └── H-group (Homology)   e.g., "377.1" - LIM zinc-binding domain
        └── T-group        e.g., "377.1.1" - Same topology
              └── F-group  e.g., "377.1.1.5" - LIM family
```

**ID Format**: `X.H.T.F` (e.g., "377.1.1.5")
- X-group: single number
- H-group: X.H
- T-group: X.H.T
- F-group: X.H.T.F

---

## Notes on Column Naming

**Confusing naming in `ecod_tmp_hier`**:
- `pf_id` = F-group ID (X.H.T.F format) - "pf" likely means "precise family"
- `f_id` = T-group ID (X.H.T format) - NOT the F-group!

Always use `pf_id` when you want the F-group classification.

---

## Domain ID Conventions

| Source | Domain ID Pattern | Example |
|--------|-------------------|---------|
| PDB | e{pdb_code}{chain}{domain_num} | e8bhiE2 |
| AFDB | nD{num} (with source_id) | Q80Y24_F1_nD1 |

For AFDB domains, combine `ecod_source_id` + "_" + `ecod_domain_id` to get full identifier.

---

## Version Information

- Current ECOD version: develop290+
- AlphaFold DB version: v6 (as of 2026)
- Database updated: Ongoing development

---

*Document created: 2026-02-01*
*For ECOD consistency analysis project*
