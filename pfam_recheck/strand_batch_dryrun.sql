-- Stranding batch DRY-RUN (#1 reassign 15 + #2 deprecate 6 + commons .0 rehome). DEFAULT ROLLBACK.
\set ON_ERROR_STOP on
BEGIN;

-- ---------- #1: reassign the 15 movers (all stranding except Lsr2) ----------
CREATE TEMP TABLE _r15(ecod_uid int, new_f_id text);
\copy _r15 FROM 'strand_reassign15.csv' WITH CSV HEADER
CREATE TEMP TABLE _r15w AS
  SELECT d.uid, d.ecod_uid, d.f_id::text AS old_f, r.new_f_id
  FROM _r15 r JOIN ecod_rep.domain d ON d.ecod_uid=r.ecod_uid;
DO $$
DECLARE r RECORD; v_req INT; n INT:=0;
BEGIN
  FOR r IN SELECT * FROM _r15w LOOP
    IF r.old_f IS NOT DISTINCT FROM r.new_f_id THEN CONTINUE; END IF;
    v_req := ecod_rep.create_domain_update_request(r.uid,'reassign_f_group',r.new_f_id,
      'v294 reconciliation (stranding): move rep to commons F-group; old group reseeded/deprecated','v294_strand');
    PERFORM ecod_rep.approve_hierarchy_change_request(v_req,'v294_strand','stranding batch');
    PERFORM ecod_rep.implement_domain_update(v_req);
    n:=n+1;
  END LOOP;
  RAISE NOTICE '#1 reassigned: %', n;
END $$;

-- ---------- #2: deprecate the 6 vacated/reconsider groups (ecod_rep) ----------
CREATE TEMP TABLE _dep(f_id text, t0_group text);
\copy _dep FROM 'strand_deprecate6.csv' WITH CSV HEADER
DO $$
DECLARE r RECORD; v_req INT; n INT:=0;
BEGIN
  FOR r IN SELECT * FROM _dep LOOP
    v_req := ecod_rep.create_hierarchy_change_request('deprecate','F', r.f_id, NULL, NULL, NULL,
      'v294 reconciliation (stranding): vacated/superseded F-group; contents rehomed to T-group .0 in commons',
      'v294_strand', NULL);
    PERFORM ecod_rep.approve_hierarchy_change_request(v_req,'v294_strand','stranding deprecate');
    PERFORM ecod_rep.implement_deprecate_group(v_req);
    n:=n+1;
  END LOOP;
  RAISE NOTICE '#2 deprecated: %', n;
END $$;

-- ---------- #2b: rehome remaining commons members to the T-group .0 ----------
WITH moved AS (
  UPDATE ecod_commons.f_group_assignments fa
  SET f_group_id = d.t0_group
  FROM _dep d WHERE fa.f_group_id = d.f_id
  RETURNING 1)
SELECT count(*) AS commons_members_rehomed_to_dot0 FROM moved;

-- ---------- verification ----------
SELECT count(*) AS r15_now_in_target FROM _r15w w JOIN ecod_rep.domain d ON d.uid=w.uid WHERE d.f_id::text=w.new_f_id;
SELECT count(*) AS groups_now_deprecated FROM ecod_rep.cluster WHERE id IN (SELECT f_id FROM _dep) AND is_deprecated;
SELECT count(*) AS commons_still_in_deprecated FROM ecod_commons.f_group_assignments WHERE f_group_id IN (SELECT f_id FROM _dep);

-- ROLLBACK;
COMMIT;
