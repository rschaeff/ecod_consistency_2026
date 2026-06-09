\set ON_ERROR_STOP on
BEGIN;
CREATE TEMP TABLE _cr(ecod_uid int, f_id text, ecod_domain_id text, ecod_source_id text, seqid_range text, dtype text);
\copy _cr FROM 'repsel_gold_create.csv' WITH CSV HEADER
DO $$ DECLARE r RECORD; v INT; n INT:=0;
BEGIN FOR r IN SELECT * FROM _cr LOOP
  v:=ecod_rep.create_domain_change_request(r.ecod_domain_id,r.ecod_source_id,r.f_id,r.seqid_range,
     NULL,false,true,r.dtype,'GOLD reparent rep-selection','best-ranked member promoted for reparented GOLD F-group under 10.1.3','gold_reparent',r.ecod_uid);
  PERFORM ecod_rep.approve_hierarchy_change_request(v,'gold_reparent','gold rep');
  PERFORM ecod_rep.implement_domain_create(v); n:=n+1;
END LOOP; RAISE NOTICE 'created: %', n; END $$;
SELECT 'gold reps created' q, count(*)::text v FROM _cr c JOIN ecod_rep.domain d ON d.ecod_uid=c.ecod_uid WHERE d.provisional_manual_rep AND d.f_id::text=c.f_id
UNION ALL SELECT 'live repless under 10.1.3', count(*)::text FROM ecod_rep.cluster c WHERE c.parent='10.1.3' AND c.type='F' AND c.is_deprecated IS NOT TRUE AND NOT EXISTS (SELECT 1 FROM ecod_rep.domain d WHERE d.f_id=c.id AND (d.manual_rep OR d.provisional_manual_rep))
UNION ALL SELECT 'repless active now', count(*)::text FROM ecod_rep.cluster c WHERE c.type='F' AND c.is_deprecated IS NOT TRUE AND NOT EXISTS (SELECT 1 FROM ecod_rep.domain d WHERE d.f_id=c.id AND (d.manual_rep OR d.provisional_manual_rep));
-- ROLLBACK;
COMMIT;
