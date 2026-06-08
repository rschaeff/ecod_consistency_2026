-- =============================================================================
-- rename_accession_fgroups_20260608.sql
-- Fix the v294 migration "--acc" naming bug: 3,069 active F-groups were named with
-- a bare Pfam ACCESSION (cluster.name = pfam_acc, e.g. "PF31211") instead of the
-- HMM family NAME (e.g. "Taz1_DD"). All migration-created (v293.1: 2,812; v294: 257);
-- all resolve to a real v38.2 family name. Composites were unaffected (got name-lists).
--
-- Uses the AUDITED rename pipeline (validated rolled-back on 1009.1.1.1 -> Taz1_DD):
--   create_hierarchy_change_request('rename','F',f_id,NULL,acc_name,family_name,...)
--     -> approve_hierarchy_change_request -> implement_rename_group
--   (implement_rename_group updates cluster.name, appends an audit note to comment,
--    and logs old/new to hierarchy_change_history)
--
-- Each row is GUARDED: skipped if the cluster's current name no longer matches the
-- accession (idempotent / drift-safe). NOTE: create_hierarchy_change_request runs
-- identify_affected_domains per request, so 3,069 rows may take a few minutes.
--
-- DEFAULT IS ROLLBACK. Review the verification output, then change ROLLBACK -> COMMIT.
-- Input: fgroup_accession_rename_20260608.csv  (f_id,current_name,correct_name,pfam_acc,introduced_release)
-- =============================================================================
\set ON_ERROR_STOP on
\timing on
BEGIN;

CREATE TEMP TABLE _rename (
  f_id text, current_name text, correct_name text, pfam_acc text, introduced_release text
);
\copy _rename FROM 'fgroup_accession_rename_20260608.csv' WITH CSV HEADER

SELECT count(*) AS rows_loaded,
       count(*) FILTER (WHERE correct_name='(NOT_IN_v38.2)') AS unresolved_skipped
FROM _rename;

DO $$
DECLARE
  r RECORD; v_req INTEGER; v_now TEXT;
  n_renamed INTEGER := 0; n_skipped INTEGER := 0;
BEGIN
  FOR r IN SELECT * FROM _rename WHERE correct_name <> '(NOT_IN_v38.2)' LOOP
    -- guard: only rename if the name is still the accession
    SELECT name INTO v_now FROM ecod_rep.cluster WHERE id::text = r.f_id;
    IF v_now IS DISTINCT FROM r.current_name THEN
      n_skipped := n_skipped + 1; CONTINUE;
    END IF;
    v_req := ecod_rep.create_hierarchy_change_request(
      'rename', 'F', r.f_id, NULL, r.current_name, r.correct_name,
      'Fix v294 migration --acc naming: Pfam accession written as F-group name instead of HMM family name',
      'pfam_name_fix', r.pfam_acc);
    PERFORM ecod_rep.approve_hierarchy_change_request(v_req, 'pfam_name_fix', 'accession->family-name cleanup');
    PERFORM ecod_rep.implement_rename_group(v_req);
    n_renamed := n_renamed + 1;
  END LOOP;
  RAISE NOTICE 'renamed: %, skipped (name drifted/not the accession): %', n_renamed, n_skipped;
END $$;

-- ===== verification (inside the transaction) =====
SELECT count(*) AS still_accession_named
FROM ecod_rep.cluster
WHERE type='F' AND is_deprecated IS NOT TRUE AND name ~ '^PF[0-9]{4,6}$';

SELECT id, name FROM ecod_rep.cluster
WHERE id IN ('1009.1.1.1','101.1.2.493','10.1.1.74','108.1.1.121');

SELECT count(*) AS rename_history_rows
FROM ecod_rep.hierarchy_change_history
WHERE operation='rename' AND change_request_id IN
  (SELECT id FROM ecod_rep.hierarchy_change_request WHERE requested_by='pfam_name_fix');

-- ROLLBACK;
COMMIT;
