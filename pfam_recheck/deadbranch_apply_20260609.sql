\set ON_ERROR_STOP on
BEGIN;
-- 1. deprecate the genuine v293 orphan (HA70_C, name already DEPRECATED) under dead T-group 10.1.2
DO $$ DECLARE v_req INT;
BEGIN
  v_req := ecod_rep.create_hierarchy_change_request('deprecate','F','10.1.2.61', NULL, NULL, NULL,
    'v294 dead-branch cleanup: v293 orphan F-group (HA70_C, already named DEPRECATED) under deprecated T-group 10.1.2',
    'v294_deadbranch', NULL);
  PERFORM ecod_rep.approve_hierarchy_change_request(v_req,'v294_deadbranch','dead-branch deprecate');
  PERFORM ecod_rep.implement_deprecate_group(v_req);
END $$;
-- 2. wire cluster_relation for the 2 LIVE Archaea T-groups v294 created without it
INSERT INTO ecod_rep.cluster_relation (t_id, hid, xid) VALUES
  ('1085.1.1'::public.dom_cid, '1085.1'::public.dom_cid, '1085'::public.dom_cid),
  ('7070.1.1'::public.dom_cid, '7070.1'::public.dom_cid, '7070'::public.dom_cid);
-- 3. create the 3 Archaea provisional reps (cluster_relation now resolvable)
CREATE TEMP TABLE _cr(ecod_uid int, f_id text, ecod_domain_id text, ecod_source_id text, seqid_range text, dtype text);
\copy _cr FROM 'repsel_archaea_create.csv' WITH CSV HEADER
DO $$ DECLARE r RECORD; v INT; n INT:=0;
BEGIN FOR r IN SELECT * FROM _cr LOOP
  v:=ecod_rep.create_domain_change_request(r.ecod_domain_id,r.ecod_source_id,r.f_id,r.seqid_range,
     NULL,false,true,r.dtype,'v294 dead-branch recovery','Archaea F-group (live T-group; v294 omitted cluster_relation): best-ranked member promoted','v294_deadbranch',r.ecod_uid);
  PERFORM ecod_rep.approve_hierarchy_change_request(v,'v294_deadbranch','archaea rep');
  PERFORM ecod_rep.implement_domain_create(v); n:=n+1;
END LOOP; RAISE NOTICE 'created: %', n; END $$;
SELECT 'HA70_C deprecated' q, is_deprecated::text v FROM ecod_rep.cluster WHERE id='10.1.2.61'
UNION ALL SELECT 'cluster_relation wired', count(*)::text FROM ecod_rep.cluster_relation WHERE t_id::text IN ('1085.1.1','7070.1.1')
UNION ALL SELECT 'archaea reps created', count(*)::text FROM _cr c JOIN ecod_rep.domain d ON d.ecod_uid=c.ecod_uid WHERE d.provisional_manual_rep AND d.f_id::text=c.f_id
UNION ALL SELECT 'repless active now', count(*)::text FROM ecod_rep.cluster c WHERE c.type='F' AND c.is_deprecated IS NOT TRUE AND NOT EXISTS (SELECT 1 FROM ecod_rep.domain d WHERE d.f_id=c.id AND (d.manual_rep OR d.provisional_manual_rep));
-- ROLLBACK;
COMMIT;
