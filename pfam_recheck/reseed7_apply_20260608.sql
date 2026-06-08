\set ON_ERROR_STOP on
BEGIN;
CREATE TEMP TABLE _rs(ecod_uid int, f_id text, ecod_domain_id text, ecod_source_id text, seqid_range text, dtype text);
\copy _rs FROM 'reseed7_input.csv' WITH CSV HEADER
DO $$
DECLARE r RECORD; v_req INT; v_uid INT; n INT:=0;
BEGIN
  FOR r IN SELECT * FROM _rs LOOP
    v_req := ecod_rep.create_domain_change_request(r.ecod_domain_id, r.ecod_source_id, r.f_id, r.seqid_range,
      NULL, false, true, r.dtype, 'v294 reconciliation reseed',
      'provisional rep re-seeded for stranded F-group (Pfam-confirmed / curator-accepted)', 'v294_strand', r.ecod_uid);
    PERFORM ecod_rep.approve_hierarchy_change_request(v_req,'v294_strand','reseed');
    v_uid := ecod_rep.implement_domain_create(v_req);
    n:=n+1;
  END LOOP;
  RAISE NOTICE 'reseeded: %', n;
END $$;
SELECT r.f_id, d.ecod_domain_id, d.ecod_uid, d.t_id, d.seqid_range, d.type, d.provisional_manual_rep AS prov
FROM _rs r JOIN ecod_rep.domain d ON d.ecod_uid=r.ecod_uid ORDER BY r.f_id;
SELECT count(*) AS reseeded_ok FROM _rs r JOIN ecod_rep.domain d ON d.ecod_uid=r.ecod_uid AND d.f_id::text=r.f_id WHERE d.provisional_manual_rep;
COMMIT;
