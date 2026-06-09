\set ON_ERROR_STOP on
BEGIN;
-- STEP 1: flag reps in commons to match ecod_rep (forward sync). Reps get is_representative=true,
-- representative_domain_id=NULL (version_consistency CHECK).
WITH er AS (SELECT ecod_uid, bool_or(manual_rep) mr, bool_or(provisional_manual_rep) pr
            FROM ecod_rep.domain WHERE manual_rep OR provisional_manual_rep GROUP BY ecod_uid)
UPDATE ecod_commons.domains dm
SET is_manual_representative=er.mr, is_provisional_representative=er.pr,
    is_representative=true, representative_domain_id=NULL
FROM er WHERE dm.ecod_uid=er.ecod_uid AND dm.is_obsolete IS NOT TRUE
  AND (dm.is_representative IS DISTINCT FROM true OR dm.is_manual_representative IS DISTINCT FROM er.mr
       OR dm.is_provisional_representative IS DISTINCT FROM er.pr OR dm.representative_domain_id IS NOT NULL);
-- STEP 2: point NULL-pointer non-reps at their F-group's rep (one rep per F-group: manual>prov>uid).
WITH rep_per_fgroup AS (
  SELECT DISTINCT ON (er.f_id) er.f_id::text AS fid, dm.id AS rep_id
  FROM ecod_rep.domain er JOIN ecod_commons.domains dm ON dm.ecod_uid=er.ecod_uid AND dm.is_obsolete IS NOT TRUE
  WHERE er.manual_rep OR er.provisional_manual_rep
  ORDER BY er.f_id, er.manual_rep DESC, er.provisional_manual_rep DESC, er.ecod_uid )
UPDATE ecod_commons.domains dm
SET representative_domain_id = rp.rep_id
FROM ecod_commons.f_group_assignments fga
JOIN rep_per_fgroup rp ON rp.fid = fga.f_group_id
WHERE fga.domain_id = dm.id AND dm.is_obsolete IS NOT TRUE
  AND NOT (dm.is_manual_representative OR dm.is_provisional_representative)
  AND dm.is_representative IS NOT TRUE AND dm.representative_domain_id IS NULL
  AND dm.id <> rp.rep_id;
-- verification
SELECT 'reps now flagged in commons' q, count(*) FROM ecod_commons.domains dm
  JOIN ecod_rep.domain er ON er.ecod_uid=dm.ecod_uid AND (er.manual_rep OR er.provisional_manual_rep)
  WHERE dm.is_obsolete IS NOT TRUE AND dm.is_representative;
SELECT 'nonreps still NULL-pointer in repped fgroup' q, count(*) FROM ecod_commons.domains dm
  JOIN ecod_commons.f_group_assignments fga ON fga.domain_id=dm.id
  WHERE dm.is_obsolete IS NOT TRUE AND NOT dm.is_representative AND dm.representative_domain_id IS NULL
    AND EXISTS (SELECT 1 FROM ecod_rep.domain er WHERE er.f_id::text=fga.f_group_id AND (er.manual_rep OR er.provisional_manual_rep));
SELECT 'CHECK violations (reps w/ non-null ptr)' q, count(*) FROM ecod_commons.domains WHERE is_representative AND representative_domain_id IS NOT NULL;
-- ROLLBACK;
COMMIT;
