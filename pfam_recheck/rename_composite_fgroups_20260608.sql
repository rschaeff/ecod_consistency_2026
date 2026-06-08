-- =============================================================================
-- rename_composite_fgroups_20260608.sql
-- Second pass of the v294 migration --acc naming fix: COMPOSITE F-group names that
-- still carry a bare Pfam accession for component(s) whose name the migration could
-- not resolve (newer ECOD-seeded Pfams, e.g. PF29xxx). 408 active F-groups, all v293.1.
-- e.g. "LRR_6, PF29265" -> "LRR_6, LRR_CARMIL"; "PF29148, PF29151, PF29158" -> "YPP1_N, YPP1_middle, YPP1_C".
-- Per-token fix: only bare-accession tokens are replaced with their v38.2 family name;
-- all other (already-correct) tokens are preserved. All 408 resolve (0 unresolved).
-- Same audited pipeline as the single-Pfam pass (validated). DEFAULT ROLLBACK.
-- Input: fgroup_composite_rename_20260608.csv (f_id,current_name,correct_name,introduced_release)
-- =============================================================================
\set ON_ERROR_STOP on
\timing on
BEGIN;
CREATE TEMP TABLE _crename (f_id text, current_name text, correct_name text, introduced_release text);
\copy _crename FROM 'fgroup_composite_rename_20260608.csv' WITH CSV HEADER
SELECT count(*) AS rows_loaded FROM _crename;

DO $$
DECLARE r RECORD; v_req INTEGER; v_now TEXT; n INTEGER:=0; skip INTEGER:=0;
BEGIN
  FOR r IN SELECT * FROM _crename LOOP
    SELECT name INTO v_now FROM ecod_rep.cluster WHERE id::text = r.f_id;
    IF v_now IS DISTINCT FROM r.current_name THEN skip:=skip+1; CONTINUE; END IF;
    v_req := ecod_rep.create_hierarchy_change_request(
      'rename','F', r.f_id, NULL, r.current_name, r.correct_name,
      'Fix v294 migration --acc naming (composite): unresolved Pfam accession(s) in F-group name replaced with HMM family name',
      'pfam_name_fix', NULL);
    PERFORM ecod_rep.approve_hierarchy_change_request(v_req, 'pfam_name_fix', 'composite accession->family-name cleanup');
    PERFORM ecod_rep.implement_rename_group(v_req);
    n := n + 1;
  END LOOP;
  RAISE NOTICE 'renamed: %, skipped (drift): %', n, skip;
END $$;

-- verification
SELECT count(*) AS composite_acc_named_remaining FROM ecod_rep.cluster
WHERE type='F' AND is_deprecated IS NOT TRUE AND name ~ '(^|[, ])PF[0-9]{4,6}([, ]|$)';
SELECT id, name FROM ecod_rep.cluster WHERE id IN ('109.4.1.1575','207.1.1.161','101.1.10.48');

-- ROLLBACK;
COMMIT;
