-- Mechanism A: repair the (thoroughly broken) domain-create path so existing commons
-- reps can be seeded as provisional reps non-destructively, via the audited pipeline.
-- create_domain_change_request: fix ::ecod_rep.dom_cid cast; ADD p_ecod_uid -> request_data.
-- implement_domain_create: fix casts (public.dom_cid); INSERT seqid_range (not 'range');
--   add ecod_uid + t_id; rewrite domain_assignment_log to GENERIC columns.

-- ---- create_domain_change_request: drop old 11-arg, create 12-arg with ecod_uid ----
DROP FUNCTION IF EXISTS ecod_rep.create_domain_change_request(character varying,character varying,character varying,text,character varying,boolean,boolean,character varying,text,text,character varying);

CREATE OR REPLACE FUNCTION ecod_rep.create_domain_change_request(
    p_ecod_domain_id character varying, p_ecod_source_id character varying, p_f_id character varying,
    p_range text, p_scop_domain_id character varying DEFAULT NULL, p_manual_rep boolean DEFAULT false,
    p_provisional_manual_rep boolean DEFAULT false, p_type character varying DEFAULT 'manual',
    p_comment text DEFAULT NULL, p_justification text DEFAULT NULL, p_requested_by character varying DEFAULT CURRENT_USER,
    p_ecod_uid integer DEFAULT NULL)
 RETURNS integer LANGUAGE plpgsql AS $function$
DECLARE v_request_id INTEGER; v_domain_data JSONB;
BEGIN
    IF p_ecod_domain_id IS NULL OR p_ecod_source_id IS NULL OR p_f_id IS NULL OR p_range IS NULL THEN
        RAISE EXCEPTION 'Missing required fields: ecod_domain_id, ecod_source_id, f_id, range';
    END IF;
    IF NOT EXISTS(SELECT 1 FROM ecod_rep.cluster WHERE id = p_f_id::public.dom_cid AND type='F' AND is_deprecated=FALSE) THEN
        RAISE EXCEPTION 'F-group % not found or is deprecated', p_f_id;
    END IF;
    IF EXISTS(SELECT 1 FROM ecod_rep.domain WHERE ecod_domain_id = p_ecod_domain_id) THEN
        RAISE EXCEPTION 'Domain with ecod_domain_id % already exists', p_ecod_domain_id;
    END IF;
    v_domain_data := jsonb_build_object(
        'ecod_uid', p_ecod_uid, 'ecod_domain_id', p_ecod_domain_id, 'ecod_source_id', p_ecod_source_id,
        'scop_domain_id', p_scop_domain_id, 'f_id', p_f_id, 'range', p_range,
        'manual_rep', p_manual_rep, 'provisional_manual_rep', p_provisional_manual_rep,
        'type', p_type, 'comment', p_comment);
    INSERT INTO ecod_rep.hierarchy_change_request (request_type, group_type, new_id, new_name, justification, requested_by, request_data)
    VALUES ('create','F', p_f_id, p_ecod_domain_id, p_justification, p_requested_by,
            jsonb_build_object('operation','domain_create','domain_data', v_domain_data))
    RETURNING id INTO v_request_id;
    RAISE NOTICE 'Created domain creation request #% for domain %', v_request_id, p_ecod_domain_id;
    RETURN v_request_id;
END; $function$;

-- ---- implement_domain_create: full repair ----
CREATE OR REPLACE FUNCTION ecod_rep.implement_domain_create(p_request_id integer)
 RETURNS integer LANGUAGE plpgsql AS $function$
DECLARE
    v_request RECORD; v_dd JSONB; v_new_uid INTEGER; v_t_id VARCHAR; v_h_id VARCHAR; v_x_id VARCHAR;
BEGIN
    SELECT * INTO v_request FROM ecod_rep.hierarchy_change_request WHERE id = p_request_id;
    IF NOT FOUND THEN RAISE EXCEPTION 'Request % not found', p_request_id; END IF;
    IF v_request.status != 'approved' THEN RAISE EXCEPTION 'Request % is not approved (status: %)', p_request_id, v_request.status; END IF;
    v_dd := v_request.request_data->'domain_data';
    v_t_id := regexp_replace(v_dd->>'f_id', '(\d+\.\d+\.\d+)\.\d+', '\1');
    SELECT hid, xid INTO v_h_id, v_x_id FROM ecod_rep.cluster_relation WHERE t_id = v_t_id::public.dom_cid;
    IF v_h_id IS NULL OR v_x_id IS NULL THEN RAISE EXCEPTION 'Could not determine H/X for T-group %', v_t_id; END IF;

    INSERT INTO ecod_rep.domain (
        ecod_uid, ecod_domain_id, ecod_source_id, scop_domain_id, f_id, t_id,
        seqid_range, manual_rep, provisional_manual_rep, type, comment)
    VALUES (
        (v_dd->>'ecod_uid')::integer, v_dd->>'ecod_domain_id', v_dd->>'ecod_source_id', v_dd->>'scop_domain_id',
        (v_dd->>'f_id')::public.dom_cid, v_t_id::public.dom_cid,
        v_dd->>'range', (v_dd->>'manual_rep')::boolean, (v_dd->>'provisional_manual_rep')::boolean,
        (v_dd->>'type')::public.domain_type, v_dd->>'comment')
    RETURNING uid INTO v_new_uid;

    INSERT INTO ecod_rep.domain_assignment_log (domain_uid, assignment_type, old_value, new_value, justification, requested_by, timestamp)
    VALUES (v_new_uid, 'domain_create', NULL, v_dd->>'f_id', 'Domain created via change request #'||p_request_id, v_request.requested_by, NOW());

    INSERT INTO ecod_rep.hierarchy_change_history (change_request_id, operation, group_type, group_id, old_data, new_data, changed_at, changed_by)
    VALUES (p_request_id, 'domain_create', 'F', v_dd->>'f_id', NULL,
            jsonb_build_object('uid', v_new_uid, 'ecod_uid', v_dd->>'ecod_uid', 'ecod_domain_id', v_dd->>'ecod_domain_id', 'f_id', v_dd->>'f_id'),
            NOW(), v_request.requested_by);
    RAISE NOTICE 'Created domain % (UID: %, ecod_uid: %)', v_dd->>'ecod_domain_id', v_new_uid, v_dd->>'ecod_uid';
    RETURN v_new_uid;
END; $function$;
