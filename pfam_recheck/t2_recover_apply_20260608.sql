\set ON_ERROR_STOP on
BEGIN;
-- 122 reassign (relaxed-recovered supports_commons; provisional flag already set)
CREATE TEMP TABLE _in(ecod_uid int, new_f_id text);
\copy _in FROM 't2_recover_reassign.csv' WITH CSV HEADER
CREATE TEMP TABLE _w AS SELECT d.uid, d.ecod_uid, d.f_id::text AS old_f, i.new_f_id FROM _in i JOIN ecod_rep.domain d ON d.ecod_uid=i.ecod_uid;
DO $$ DECLARE r RECORD; v INT; n INT:=0;
BEGIN FOR r IN SELECT * FROM _w LOOP
  IF r.old_f IS NOT DISTINCT FROM r.new_f_id THEN CONTINUE; END IF;
  v:=ecod_rep.create_domain_update_request(r.uid,'reassign_f_group',r.new_f_id,
     'v294 reconciliation tranche-2b: relaxed-Pfam-recovered provisional-rep propagation','v294_t2b');
  PERFORM ecod_rep.approve_hierarchy_change_request(v,'v294_t2b','tranche2b reassign');
  PERFORM ecod_rep.implement_domain_update(v); n:=n+1;
END LOOP; RAISE NOTICE 'reassigned: %', n; END $$;
-- 31 create
CREATE TEMP TABLE _cr(ecod_uid int, f_id text, ecod_domain_id text, ecod_source_id text, seqid_range text, dtype text);
\copy _cr FROM 't2_recover_create.csv' WITH CSV HEADER
DO $$ DECLARE r RECORD; v INT; n INT:=0;
BEGIN FOR r IN SELECT * FROM _cr LOOP
  v:=ecod_rep.create_domain_change_request(r.ecod_domain_id,r.ecod_source_id,r.f_id,r.seqid_range,
     NULL,false,true,r.dtype,'v294 tranche-2b reseed','relaxed-recovered provisional rep for repless F-group','v294_t2b',r.ecod_uid);
  PERFORM ecod_rep.approve_hierarchy_change_request(v,'v294_t2b','tranche2b create');
  PERFORM ecod_rep.implement_domain_create(v); n:=n+1;
END LOOP; RAISE NOTICE 'created: %', n; END $$;
SELECT count(*) AS reassign_in_target FROM _w w JOIN ecod_rep.domain d ON d.uid=w.uid WHERE d.f_id::text=w.new_f_id;
SELECT count(*) AS created_prov_reps FROM _cr c JOIN ecod_rep.domain d ON d.ecod_uid=c.ecod_uid WHERE d.provisional_manual_rep AND d.f_id::text=c.f_id;
SELECT count(*) AS repless_active_now FROM ecod_rep.cluster c WHERE c.type='F' AND c.is_deprecated IS NOT TRUE
  AND NOT EXISTS (SELECT 1 FROM ecod_rep.domain d WHERE d.f_id=c.id AND (d.manual_rep OR d.provisional_manual_rep));
-- ROLLBACK;
COMMIT;
