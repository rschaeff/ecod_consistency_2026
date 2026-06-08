\set ON_ERROR_STOP on
BEGIN;
-- 107 ecod_rep stranding movers: pure reassign to Pfam-validated commons_f.
-- No deprecations (old_f stay as repless real F-groups for temporal stability); no commons writes.
CREATE TEMP TABLE _in(ecod_uid int, new_f_id text);
\copy _in FROM 't2_stranding107_input.csv' WITH CSV HEADER
CREATE TEMP TABLE _w AS SELECT d.uid, d.ecod_uid, d.f_id::text AS old_f, i.new_f_id FROM _in i JOIN ecod_rep.domain d ON d.ecod_uid=i.ecod_uid;
DO $$ DECLARE r RECORD; v INT; n INT:=0;
BEGIN FOR r IN SELECT * FROM _w LOOP
  IF r.old_f IS NOT DISTINCT FROM r.new_f_id THEN CONTINUE; END IF;
  v:=ecod_rep.create_domain_update_request(r.uid,'reassign_f_group',r.new_f_id,
     'v294 reconciliation tranche-2c: ecod_rep-stranding movers, Pfam-validated rep placement (old_f kept repless)','v294_t2c');
  PERFORM ecod_rep.approve_hierarchy_change_request(v,'v294_t2c','tranche2c stranding reassign');
  PERFORM ecod_rep.implement_domain_update(v); n:=n+1;
END LOOP; RAISE NOTICE 'reassigned: %', n; END $$;
SELECT count(*) AS reassign_in_target FROM _w w JOIN ecod_rep.domain d ON d.uid=w.uid WHERE d.f_id::text=w.new_f_id;
SELECT count(*) AS old_f_now_repless FROM (SELECT DISTINCT old_f FROM _w) x
  WHERE NOT EXISTS (SELECT 1 FROM ecod_rep.domain d WHERE d.f_id::text=x.old_f AND (d.manual_rep OR d.provisional_manual_rep));
SELECT count(*) AS repless_active_now FROM ecod_rep.cluster c WHERE c.type='F' AND c.is_deprecated IS NOT TRUE
  AND NOT EXISTS (SELECT 1 FROM ecod_rep.domain d WHERE d.f_id=c.id AND (d.manual_rep OR d.provisional_manual_rep));
-- ROLLBACK;
COMMIT;
