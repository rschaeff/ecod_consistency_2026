\set ON_ERROR_STOP on
BEGIN;
CREATE TEMP TABLE _in(ecod_uid int, new_f_id text);
\copy _in FROM 'reassign_362_input.csv' WITH CSV HEADER
CREATE TEMP TABLE _work AS
  SELECT d.uid, d.ecod_uid, d.f_id::text AS old_f, i.new_f_id, d.manual_rep
  FROM _in i JOIN ecod_rep.domain d ON d.ecod_uid=i.ecod_uid;
SELECT count(*) AS work_rows, count(*) FILTER (WHERE manual_rep) AS manual_reps,
       count(*) FILTER (WHERE old_f IS NOT DISTINCT FROM new_f_id) AS already_in_target,
       count(*) FILTER (WHERE old_f IS NULL) AS fill_ins FROM _work;
DO $$
DECLARE r RECORD; v_req INT; n INT:=0; skip INT:=0;
BEGIN
  FOR r IN SELECT * FROM _work LOOP
    IF r.old_f IS NOT DISTINCT FROM r.new_f_id THEN skip:=skip+1; CONTINUE; END IF;
    v_req := ecod_rep.create_domain_update_request(r.uid,'reassign_f_group',r.new_f_id,
      'v294 reconciliation: Pfam-validated + structurally-confirmed/curator-cleared f_group reassignment','v294_reconcile');
    PERFORM ecod_rep.approve_hierarchy_change_request(v_req,'v294_reconcile','apply batch 2026-06-08');
    PERFORM ecod_rep.implement_domain_update(v_req);
    n:=n+1;
  END LOOP;
  RAISE NOTICE 'reassigned: %, skipped(already in target): %', n, skip;
END $$;
SELECT count(*) AS now_in_target FROM _work w JOIN ecod_rep.domain d ON d.uid=w.uid WHERE d.f_id::text=w.new_f_id;
SELECT count(*) AS assignment_log_rows FROM ecod_rep.domain_assignment_log WHERE requested_by='v294_reconcile';
-- ROLLBACK;
COMMIT;
