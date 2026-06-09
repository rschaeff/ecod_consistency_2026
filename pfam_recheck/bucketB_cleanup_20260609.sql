\set ON_ERROR_STOP on
BEGIN;
CREATE TEMP TABLE _b(fid text);
INSERT INTO _b VALUES ('101.22.1.1'),('101.44.1.2'),('3488.1.1.3'),('3488.1.1.5'),('3633.1.1.4'),('7584.1.1.1'),('7584.1.1.10'),('7584.1.1.11'),('7584.1.1.8');
-- capture the leaked rep ecod_uids before demoting
CREATE TEMP TABLE _u AS SELECT DISTINCT d.ecod_uid FROM ecod_rep.domain d WHERE d.f_id::text IN (SELECT fid FROM _b) AND (d.manual_rep OR d.provisional_manual_rep);
-- 1. reconcile cluster_relation: drop deprecated T-groups (the live-branch gate leaked these)
DELETE FROM ecod_rep.cluster_relation cr USING ecod_rep.cluster tc WHERE tc.id=cr.t_id::text AND tc.is_deprecated;
-- 2. deprecate the 9 bucket-B F-groups (audited)
DO $$ DECLARE r RECORD; v_req INT; n INT:=0;
BEGIN FOR r IN SELECT fid FROM _b LOOP
  v_req := ecod_rep.create_hierarchy_change_request('deprecate','F', r.fid, NULL,NULL,NULL,
    'Orphan-reclassification cleanup (Pei/Schaeffer/Cong/Grishin 2025 Proteins): source F-group under a paper-deprecated H/T branch; our provisional rep was a cluster_relation leak','orphan_reclass_cleanup',NULL);
  PERFORM ecod_rep.approve_hierarchy_change_request(v_req,'orphan_reclass_cleanup','bucket B deprecate');
  PERFORM ecod_rep.implement_deprecate_group(v_req); n:=n+1;
END LOOP; RAISE NOTICE 'F-groups deprecated: %', n; END $$;
-- 3. demote the leaked provisional reps in ecod_rep
UPDATE ecod_rep.domain SET provisional_manual_rep=false WHERE ecod_uid IN (SELECT ecod_uid FROM _u) AND provisional_manual_rep;
-- 4. un-flag them in commons (forward sync: ecod_rep authoritative)
UPDATE ecod_commons.domains SET is_provisional_representative=false, is_representative=false WHERE ecod_uid IN (SELECT ecod_uid FROM _u);
-- verification
SELECT 'clrel_deprecated_remaining' q, count(*)::text v FROM ecod_rep.cluster_relation cr JOIN ecod_rep.cluster tc ON tc.id=cr.t_id::text WHERE tc.is_deprecated
UNION ALL SELECT 'bucketB_now_deprecated', count(*)::text FROM ecod_rep.cluster WHERE id IN (SELECT fid FROM _b) AND is_deprecated
UNION ALL SELECT 'leaked_reps_demoted (ecod_rep prov remaining)', count(*)::text FROM ecod_rep.domain WHERE ecod_uid IN (SELECT ecod_uid FROM _u) AND provisional_manual_rep
UNION ALL SELECT 'manual rep 101.44.1.3 still live+repped', (CASE WHEN EXISTS(SELECT 1 FROM ecod_rep.cluster WHERE id='101.44.1.3' AND is_deprecated IS NOT TRUE) THEN 'yes' ELSE 'NO' END)
UNION ALL SELECT 'repless active now', count(*)::text FROM ecod_rep.cluster c WHERE c.type='F' AND c.is_deprecated IS NOT TRUE AND NOT EXISTS (SELECT 1 FROM ecod_rep.domain d WHERE d.f_id=c.id AND (d.manual_rep OR d.provisional_manual_rep));
-- ROLLBACK;
COMMIT;
