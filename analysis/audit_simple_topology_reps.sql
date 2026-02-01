-- AUDIT QUERY: Identify all simple_topology provisional representatives in ecod_rep
-- Purpose: Find provisional manual reps that should be reviewed/disqualified
-- Date: 2026-01-31

-- This query requires joining ecod_rep.domain with classification sources
-- to retrieve the 'judge' value for each provisional representative.

-- Step 1: Create temporary view of all provisional-only reps
-- (provisional_manual_rep = true AND manual_rep IS NOT true)

WITH provisional_reps AS (
    SELECT
        d.uid,
        d.ecod_domain_id,
        d.f_id,
        d.t_id,
        d.type,
        d.ecod_source_id,
        c.name as f_group_name,
        c.pfam_acc
    FROM ecod_rep.domain d
    LEFT JOIN ecod_rep.cluster c ON d.f_id = c.id
    WHERE d.provisional_manual_rep = true
    AND (d.manual_rep IS NULL OR d.manual_rep = false)
),

-- Step 2: Get judge from swissprot (domain_id format: ACC_nDX)
swissprot_judges AS (
    SELECT
        domain_id,
        judge,
        length,
        'swissprot' as source
    FROM swissprot.domain
),

-- Step 3: Get judge from proteomes (need to construct key from unp_acc + domain_id)
proteomes_judges AS (
    SELECT
        unp_acc || '_' || domain_id as domain_key,
        judge,
        length,
        'proteomes' as source
    FROM proteomes.domain
),

-- Step 4: Get judge from public.domain (key is ecod_source_id + '_' + ecod_domain_id)
public_judges AS (
    SELECT
        ecod_source_id || '_' || ecod_domain_id as domain_key,
        dpam_judge as judge,
        length,
        ecod_version,
        'public' as source
    FROM public.domain
    WHERE ecod_source_id IS NOT NULL
    AND ecod_domain_id IS NOT NULL
),

-- Step 5: Parse ecod_domain_id to create lookup keys
-- Format: ACC_F1_nD1 -> simple_key: ACC_nD1, public_key: ACC_F1_nD1
parsed_reps AS (
    SELECT
        pr.*,
        -- Extract ACC from ACC_F1_nD1 or ACC_nD1 pattern
        CASE
            WHEN pr.ecod_domain_id ~ '^.+_F[0-9]+_nD[0-9]+$' THEN
                regexp_replace(pr.ecod_domain_id, '_F[0-9]+_nD', '_nD')
            ELSE pr.ecod_domain_id
        END as simple_key,
        pr.ecod_domain_id as public_key
    FROM provisional_reps pr
),

-- Step 6: Join to get judge values
rep_with_judge AS (
    SELECT
        pr.uid,
        pr.ecod_domain_id,
        pr.f_id,
        pr.t_id,
        pr.type,
        pr.f_group_name,
        pr.pfam_acc,
        COALESCE(sw.judge, prot.judge, pub.judge,
            CASE WHEN pr.ecod_domain_id LIKE 'e%' THEN 'PDB' ELSE 'NOT_FOUND' END
        ) as judge,
        COALESCE(sw.source, prot.source, pub.source,
            CASE WHEN pr.ecod_domain_id LIKE 'e%' THEN 'pdb' ELSE 'unknown' END
        ) as classification_source,
        COALESCE(sw.length, prot.length, pub.length) as classified_length,
        pub.ecod_version
    FROM parsed_reps pr
    LEFT JOIN swissprot_judges sw ON pr.simple_key = sw.domain_id
    LEFT JOIN proteomes_judges prot ON pr.simple_key = prot.domain_key
    LEFT JOIN public_judges pub ON pr.public_key = pub.domain_key
)

-- Final output: All provisional reps with simple_topology classification
SELECT
    r.ecod_domain_id,
    r.f_id,
    SUBSTRING(r.f_id FROM '^[0-9]+\.[0-9]+') as h_group,
    r.t_id,
    r.type as domain_type,
    r.judge,
    r.classification_source,
    r.classified_length,
    r.pfam_acc,
    r.f_group_name,
    r.ecod_version
FROM rep_with_judge r
WHERE r.judge = 'simple_topology'
ORDER BY
    SUBSTRING(r.f_id FROM '^[0-9]+\.[0-9]+'),  -- H-group
    r.f_id;


-- SUMMARY STATISTICS QUERY
-- Run separately to get counts by H-group

/*
SELECT
    SUBSTRING(f_id FROM '^[0-9]+\.[0-9]+') as h_group,
    COUNT(*) as simple_topology_prov_reps,
    COUNT(DISTINCT pfam_acc) FILTER (WHERE pfam_acc IS NOT NULL) as affected_pfams,
    STRING_AGG(DISTINCT classification_source, ', ') as sources
FROM (
    -- Use the same CTE logic as above
    ...
) sub
WHERE judge = 'simple_topology'
GROUP BY SUBSTRING(f_id FROM '^[0-9]+\.[0-9]+')
ORDER BY simple_topology_prov_reps DESC;
*/
