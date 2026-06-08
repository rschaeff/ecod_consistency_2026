\set ON_ERROR_STOP on
BEGIN;
CREATE TEMP TABLE _cr(ecod_uid int, f_id text, ecod_domain_id text, ecod_source_id text, seqid_range text, dtype text);
\copy _cr FROM 'repsel_t23full_create.csv' WITH CSV HEADER
DO $$ DECLARE r RECORD; v INT; n INT:=0;
BEGIN FOR r IN SELECT * FROM _cr LOOP
  v:=ecod_rep.create_domain_change_request(r.ecod_domain_id,r.ecod_source_id,r.f_id,r.seqid_range,
     NULL,false,true,r.dtype,'v294 rep-selection Tier-2/3','multi-member repless F-group: best-ranked candidate promoted as provisional rep (concordant, completeness-first)','v294_repsel_t23',r.ecod_uid);
  PERFORM ecod_rep.approve_hierarchy_change_request(v,'v294_repsel_t23','repsel t1');
  PERFORM ecod_rep.implement_domain_create(v); n:=n+1;
  IF n % 2000 = 0 THEN RAISE NOTICE '  created %', n; END IF;
END LOOP; RAISE NOTICE 'created total: %', n; END $$;
SELECT count(*) AS created_prov FROM _cr c JOIN ecod_rep.domain d ON d.ecod_uid=c.ecod_uid WHERE d.provisional_manual_rep AND d.f_id::text=c.f_id;
SELECT count(*) AS repless_active_now FROM ecod_rep.cluster c WHERE c.type='F' AND c.is_deprecated IS NOT TRUE
  AND NOT EXISTS (SELECT 1 FROM ecod_rep.domain d WHERE d.f_id=c.id AND (d.manual_rep OR d.provisional_manual_rep));
-- ROLLBACK;
COMMIT;
