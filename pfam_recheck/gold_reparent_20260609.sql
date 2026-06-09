\set ON_ERROR_STOP on
BEGIN;
CREATE TEMP TABLE _g AS
SELECT c.id AS old_fid, '10.1.3.'||split_part(c.id,'.',4) AS new_fid, c.name, c.pfam_acc
FROM ecod_rep.cluster c WHERE c.type='F' AND c.is_deprecated IS NOT TRUE AND c.parent='10.1.2';
-- 1. create T-group 10.1.3 "GOLD domain-like" under live H-group 10.1
DO $$ DECLARE v INT;
BEGIN
  v := ecod_rep.create_hierarchy_change_request('create','T',NULL,'10.1.3',NULL,'GOLD domain-like',
    'Reparent: GOLD-domain F-groups orphaned under deprecated T-group 10.1.2 (group-number reuse); rehome under live H-group 10.1 (Concanavalin A-like) as new T-group 10.1.3','gold_reparent',NULL);
  PERFORM ecod_rep.approve_hierarchy_change_request(v,'gold_reparent','create GOLD T-group 10.1.3');
  PERFORM ecod_rep.implement_create_group(v);
END $$;
-- 2. wire cluster_relation for the new T-group
INSERT INTO ecod_rep.cluster_relation (t_id,hid,xid) VALUES ('10.1.3'::public.dom_cid,'10.1'::public.dom_cid,'10'::public.dom_cid);
-- 3. per F-group: create new node (keep suffix + name + pfam_acc), move commons members, deprecate old node
DO $$ DECLARE r RECORD; v INT; n INT:=0;
BEGIN FOR r IN SELECT * FROM _g LOOP
  v := ecod_rep.create_hierarchy_change_request('create','F',NULL,r.new_fid,NULL,r.name,
    'Reparented from '||r.old_fid||' (GOLD T-group 10.1.2 deprecated)','gold_reparent',r.pfam_acc);
  PERFORM ecod_rep.approve_hierarchy_change_request(v,'gold_reparent','create reparented F');
  PERFORM ecod_rep.implement_create_group(v);
  UPDATE ecod_commons.f_group_assignments SET f_group_id=r.new_fid, t_group_id='10.1.3'
    WHERE f_group_id=r.old_fid;
  v := ecod_rep.create_hierarchy_change_request('deprecate','F',r.old_fid,NULL,NULL,NULL,
    'Vacated: content reparented to '||r.new_fid||' under live T-group 10.1.3','gold_reparent',NULL);
  PERFORM ecod_rep.approve_hierarchy_change_request(v,'gold_reparent','deprecate vacated GOLD F');
  PERFORM ecod_rep.implement_deprecate_group(v);
  n:=n+1;
END LOOP; RAISE NOTICE 'reparented: %', n; END $$;
-- verification
SELECT '10.1.3 created as' q, name v FROM ecod_rep.cluster WHERE id='10.1.3'
UNION ALL SELECT 'live F-groups under 10.1.3', count(*)::text FROM ecod_rep.cluster WHERE parent='10.1.3' AND type='F' AND is_deprecated IS NOT TRUE
UNION ALL SELECT 'old 10.1.2.X deprecated', count(*)::text FROM _g g JOIN ecod_rep.cluster c ON c.id=g.old_fid WHERE c.is_deprecated
UNION ALL SELECT 'commons members on new 10.1.3.X', count(*)::text FROM ecod_commons.f_group_assignments fga JOIN _g g ON g.new_fid=fga.f_group_id
UNION ALL SELECT 'commons still on old 10.1.2.X', count(*)::text FROM ecod_commons.f_group_assignments fga JOIN _g g ON g.old_fid=fga.f_group_id
UNION ALL SELECT 'cluster_relation 10.1.3 wired', count(*)::text FROM ecod_rep.cluster_relation WHERE t_id::text='10.1.3';
-- ROLLBACK;
COMMIT;
