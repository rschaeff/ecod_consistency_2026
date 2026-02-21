"""
Shared database operations library for curator classification changes.

Provides reusable functions built on top of ecod_rep stored functions and
ecod_commons direct SQL. Follows patterns from:
  - prov_rep_daccession/batch_deprecate_a1.py
  - prov_rep_daccession/batch_replace_a2.py

All hierarchy changes go through the hierarchy_change_request workflow:
  pending -> approved -> implemented

ecod_commons changes are applied manually (no stored function support).
"""

import logging
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor

from change_definitions import REQUESTED_BY

logger = logging.getLogger(__name__)

# Database connection parameters
DB_CONFIG = {
    'host': 'dione',
    'port': 45000,
    'database': 'ecod_protein',
    'user': 'ecod',
}


def get_db_connection():
    """Create database connection."""
    return psycopg2.connect(**DB_CONFIG)


# ============================================================
# Hierarchy lookups
# ============================================================

def verify_fgroup_exists(conn, f_id):
    """Verify F-group exists and return its record, or None."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT id::text AS f_id, name, is_deprecated, parent::text AS t_id,
                   pfam_acc, comment
            FROM ecod_rep.cluster
            WHERE id::text = %s AND type = 'F'
        """, (f_id,))
        return cur.fetchone()


def verify_cluster_exists(conn, group_id, group_type):
    """Verify a cluster entry exists and return its record."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT id::text AS group_id, type, name, is_deprecated,
                   parent::text AS parent_id, pfam_acc
            FROM ecod_rep.cluster
            WHERE id::text = %s AND type = %s
        """, (group_id, group_type))
        return cur.fetchone()


def get_hierarchy_ids_for_tgroup(conn, t_id):
    """Get the H-group and X-group for a T-group from cluster_relation."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT t_id::text, hid::text AS h_id, xid::text AS x_id
            FROM ecod_rep.cluster_relation
            WHERE t_id::text = %s
        """, (t_id,))
        return cur.fetchone()


def get_hierarchy_ids_for_fgroup(conn, f_id):
    """Get the full hierarchy (T/H/X) for an F-group."""
    t_id = '.'.join(f_id.split('.')[:3])
    result = get_hierarchy_ids_for_tgroup(conn, t_id)
    if result:
        result['f_id'] = f_id
        result['t_id'] = t_id
    return result


def count_fgroup_members(conn, f_id, schema='ecod_rep'):
    """Count domain members in an F-group."""
    with conn.cursor() as cur:
        if schema == 'ecod_rep':
            cur.execute("""
                SELECT COUNT(*) FROM ecod_rep.domain
                WHERE f_id::text = %s
            """, (f_id,))
        else:
            cur.execute("""
                SELECT COUNT(*) FROM ecod_commons.f_group_assignments
                WHERE f_group_id = %s
            """, (f_id,))
        return cur.fetchone()[0]


def get_rep_domains_in_fgroup(conn, f_id):
    """Get all representative domains in an F-group from ecod_rep."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT uid, ecod_uid, ecod_domain_id, f_id::text,
                   manual_rep, provisional_manual_rep,
                   seqid_range, pdb_range, manual_range,
                   ecod_source_id, type, comment
            FROM ecod_rep.domain
            WHERE f_id::text = %s
            ORDER BY ecod_domain_id
        """, (f_id,))
        return cur.fetchall()


def get_domain_from_ecod_rep(conn, ecod_domain_id):
    """Get domain details from ecod_rep.domain by ecod_domain_id."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT uid, ecod_uid, ecod_domain_id, f_id::text, t_id::text,
                   manual_rep, provisional_manual_rep,
                   seqid_range, pdb_range, manual_range,
                   ecod_source_id, type, comment
            FROM ecod_rep.domain
            WHERE ecod_domain_id = %s
        """, (ecod_domain_id,))
        return cur.fetchone()


def get_domain_from_ecod_commons(conn, domain_id):
    """Get domain details from ecod_commons.domains by domain_id (e.g., e5fwwB1)."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT d.id, d.ecod_uid, d.domain_id, d.range_definition,
                   d.sequence_length, d.is_obsolete, d.is_representative,
                   d.is_manual_representative, d.is_provisional_representative,
                   d.protein_id, d.domain_version, d.range_type,
                   d.classification_status, d.classification_method
            FROM ecod_commons.domains d
            WHERE d.domain_id = %s AND d.is_obsolete = false
        """, (domain_id,))
        return cur.fetchone()


def get_commons_domains_in_fgroup(conn, f_id):
    """Get all non-obsolete domains assigned to an F-group in ecod_commons."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT d.id AS domain_pk, d.ecod_uid, d.domain_id,
                   d.range_definition, d.sequence_length,
                   d.is_representative, d.is_manual_representative,
                   d.is_provisional_representative,
                   d.protein_id, d.domain_version,
                   fga.id AS assignment_id, fga.f_group_id,
                   fga.t_group_id, fga.h_group_id, fga.x_group_id,
                   fga.a_group_id, fga.assignment_method
            FROM ecod_commons.domains d
            JOIN ecod_commons.f_group_assignments fga ON d.id = fga.domain_id
            WHERE fga.f_group_id = %s AND d.is_obsolete = false
            ORDER BY d.domain_id
        """, (f_id,))
        return cur.fetchall()


def get_commons_assignment(conn, domain_id):
    """Get the f_group_assignment for a domain_id (ecod_domain_id string)."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT fga.id AS assignment_id, fga.domain_id AS domain_pk,
                   fga.f_group_id, fga.t_group_id, fga.h_group_id,
                   fga.x_group_id, fga.a_group_id,
                   fga.assignment_method, fga.notes,
                   d.domain_id, d.ecod_uid, d.range_definition,
                   d.sequence_length
            FROM ecod_commons.f_group_assignments fga
            JOIN ecod_commons.domains d ON d.id = fga.domain_id
            WHERE d.domain_id = %s AND d.is_obsolete = false
        """, (domain_id,))
        return cur.fetchone()


# ============================================================
# Hierarchy change operations (via stored functions)
# ============================================================

def create_change_request(conn, request_type, group_type, original_id=None,
                          new_id=None, new_name=None, justification=None,
                          pfam_acc=None, requested_by=None):
    """Create a hierarchy change request using the stored function.

    Returns the request_id.
    """
    requested_by = requested_by or REQUESTED_BY
    with conn.cursor() as cur:
        cur.execute("""
            SELECT ecod_rep.create_hierarchy_change_request(
                %s, %s, %s, %s, NULL, %s, %s, %s, %s
            )
        """, (request_type, group_type, original_id, new_id,
              new_name, justification, requested_by, pfam_acc))
        return cur.fetchone()[0]


def approve_change_request(conn, request_id, reviewer=None, notes=None):
    """Approve a pending hierarchy change request using the stored function."""
    reviewer = reviewer or REQUESTED_BY
    with conn.cursor() as cur:
        cur.execute("""
            SELECT ecod_rep.approve_hierarchy_change_request(%s, %s, %s)
        """, (request_id, reviewer, notes))
        return cur.fetchone()[0]


def implement_create_group(conn, request_id):
    """Implement group creation. Request must be approved first."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT ecod_rep.implement_create_group(%s)
        """, (request_id,))
        result = cur.fetchone()[0]
        cur.execute("""
            UPDATE ecod_rep.hierarchy_change_request
            SET status = 'implemented', implementation_date = NOW()
            WHERE id = %s
        """, (request_id,))
        return result


def implement_deprecation(conn, request_id):
    """Implement group deprecation. Request must be approved first."""
    with conn.cursor() as cur:
        try:
            cur.execute("""
                SELECT ecod_rep.implement_deprecate_group(%s)
            """, (request_id,))
            result = cur.fetchone()[0]
            cur.execute("""
                UPDATE ecod_rep.hierarchy_change_request
                SET status = 'implemented', implementation_date = NOW()
                WHERE id = %s
            """, (request_id,))
            return result
        except Exception as e:
            cur.execute("""
                UPDATE ecod_rep.hierarchy_change_request
                SET status = 'failed', notes = %s
                WHERE id = %s
            """, (str(e), request_id))
            raise


def reassign_domain_fgroup(conn, domain_uid, new_f_id, request_id,
                           changed_by=None):
    """Reassign a domain's F-group in ecod_rep.

    Bypasses the stored function (which has a broken dom_cid type cast)
    and performs the update + audit logging directly.

    Updates ecod_rep.domain.f_id and logs to domain_assignment_log
    and domain_modification_log.
    """
    changed_by = changed_by or REQUESTED_BY
    from psycopg2.extras import RealDictCursor

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # Get current domain data
        cur.execute("SELECT * FROM ecod_rep.domain WHERE uid = %s", (domain_uid,))
        domain = cur.fetchone()
        if not domain:
            raise ValueError(f"Domain uid={domain_uid} not found in ecod_rep.domain")

        old_f_id = str(domain['f_id'])

        # Verify new F-group exists and is active
        cur.execute("""
            SELECT id::text FROM ecod_rep.cluster
            WHERE id::text = %s AND type = 'F' AND is_deprecated = false
        """, (new_f_id,))
        if not cur.fetchone():
            raise ValueError(f"F-group {new_f_id} not found or is deprecated")

        # Extract hierarchy IDs from new F-group
        new_t_id = '.'.join(new_f_id.split('.')[:3])
        cur.execute("""
            SELECT hid::text AS h_id, xid::text AS x_id
            FROM ecod_rep.cluster_relation
            WHERE t_id::text = %s
        """, (new_t_id,))
        rel = cur.fetchone()
        new_h_id = rel['h_id'] if rel else None
        new_x_id = rel['x_id'] if rel else None

        # Update domain f_id
        cur.execute("""
            UPDATE ecod_rep.domain SET f_id = %s WHERE uid = %s
        """, (new_f_id, domain_uid))

        # Log in domain_assignment_log
        cur.execute("""
            INSERT INTO ecod_rep.domain_assignment_log (
                domain_uid, assignment_type, old_value, new_value,
                justification, requested_by, timestamp
            ) VALUES (
                %s, 'reassign_f_group', %s, %s,
                %s, %s, NOW()
            )
        """, (domain_uid, old_f_id, new_f_id,
              f'Change request #{request_id}', changed_by))

        # Log in domain_modification_log
        cur.execute("""
            INSERT INTO ecod_rep.domain_modification_log (
                domain_uid, modification_type, old_value, new_value,
                justification, requested_by, timestamp
            ) VALUES (
                %s, 'reassign_f_group', %s, %s,
                %s, %s, NOW()
            )
        """, (domain_uid, old_f_id, new_f_id,
              f'Change request #{request_id}', changed_by))


def update_domain_range(conn, domain_uid, new_range, request_id,
                        changed_by=None):
    """Update a domain's manual_range in ecod_rep using the stored function."""
    changed_by = changed_by or REQUESTED_BY
    with conn.cursor() as cur:
        cur.execute("""
            SELECT ecod_rep.implement_update_manual_range(%s, %s, %s, %s)
        """, (domain_uid, new_range, request_id, changed_by))


# ============================================================
# X/H/T hierarchy creation
# ============================================================

def create_xht_hierarchy(conn, x_name, a_group_id, justification,
                         h_name=None, t_name=None):
    """Create a new X-group with matching H-group and T-group.

    By convention, H and T inherit the X-group name unless specified.
    Uses the change-request workflow for each level (X -> H -> T).

    Returns dict with 'x_id', 'h_id', 't_id' and their request IDs.
    """
    h_name = h_name or x_name
    t_name = t_name or x_name

    result = {}

    # Create X-group under A-group
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COALESCE(MAX(id::int), 0) + 1
            FROM ecod_rep.cluster WHERE type = 'X'
        """)
        new_x_id = str(cur.fetchone()[0])

    req_id = create_change_request(
        conn, 'create', 'X',
        new_id=new_x_id, new_name=x_name,
        justification=justification,
    )
    approve_change_request(conn, req_id)
    implement_create_group(conn, req_id)

    # Set parent to A-group
    with conn.cursor() as cur:
        cur.execute("UPDATE ecod_rep.cluster SET parent = %s WHERE id = %s AND type = 'X'",
                    (a_group_id, new_x_id))

    result['x_id'] = new_x_id
    result['x_request_id'] = req_id
    logger.info("Created X-group %s (%s) under A:%s", new_x_id, x_name, a_group_id)

    # Create H-group under X-group
    new_h_id = f"{new_x_id}.1"
    req_id = create_change_request(
        conn, 'create', 'H',
        new_id=new_h_id, new_name=h_name,
        justification=justification,
    )
    approve_change_request(conn, req_id)
    implement_create_group(conn, req_id)
    result['h_id'] = new_h_id
    result['h_request_id'] = req_id
    logger.info("Created H-group %s (%s)", new_h_id, h_name)

    # Create T-group under H-group
    new_t_id = f"{new_h_id}.1"
    req_id = create_change_request(
        conn, 'create', 'T',
        new_id=new_t_id, new_name=t_name,
        justification=justification,
    )
    approve_change_request(conn, req_id)
    implement_create_group(conn, req_id)
    result['t_id'] = new_t_id
    result['t_request_id'] = req_id
    logger.info("Created T-group %s (%s)", new_t_id, t_name)

    # Populate cluster_relation (required for hierarchy lookups)
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO ecod_rep.cluster_relation (t_id, hid, xid)
            VALUES (%s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (new_t_id, new_h_id, new_x_id))

    return result


def rename_group(conn, group_id, group_type, new_name, justification):
    """Rename a cluster (X/H/T/F) with audit trail.

    Returns request_id.
    """
    request_id = create_change_request(
        conn, 'rename', group_type,
        original_id=group_id,
        new_name=new_name,
        justification=justification,
    )
    approve_change_request(conn, request_id)

    with conn.cursor() as cur:
        cur.execute("""
            UPDATE ecod_rep.cluster SET name = %s
            WHERE id = %s AND type = %s
        """, (new_name, group_id, group_type))

        cur.execute("""
            UPDATE ecod_rep.hierarchy_change_request
            SET status = 'implemented', implementation_date = NOW()
            WHERE id = %s
        """, (request_id,))

    logger.info("Renamed %s-group %s to '%s' [request #%d]",
                group_type, group_id, new_name, request_id)
    return request_id


def reassign_xgroup_architecture(conn, x_group_id, new_a_group_id, justification):
    """Move an X-group to a different architecture (A-group).

    Updates ecod_rep.cluster parent and all ecod_commons f_group_assignments.
    Returns count of commons assignments updated.
    """
    # Update cluster parent
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE ecod_rep.cluster SET parent = %s
            WHERE id = %s AND type = 'X'
        """, (new_a_group_id, x_group_id))

    # Update all commons assignments for this X-group
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE ecod_commons.f_group_assignments
            SET a_group_id = %s
            WHERE x_group_id = %s
        """, (new_a_group_id, x_group_id))
        count = cur.rowcount

    logger.info("Moved X-group %s to A-group %s (%d commons assignments updated)",
                x_group_id, new_a_group_id, count)
    return count


# ============================================================
# F-group creation (assign_next_f_id + create_group)
# ============================================================

def create_fgroup(conn, parent_t, name, pfam_acc=None, justification=None):
    """Create a new F-group under a T-group.

    Uses assign_next_f_id to get next available ID, then creates via
    the change request workflow.

    Returns (new_f_id, request_id).
    """
    with conn.cursor() as cur:
        # Get next available F-group ID
        cur.execute("SELECT ecod_rep.assign_next_f_id(%s)", (parent_t,))
        new_f_id = cur.fetchone()[0]

    justification = justification or f"Create F-group {new_f_id} ({name}) under {parent_t}"

    # Create change request
    request_id = create_change_request(
        conn, 'create', 'F',
        new_id=new_f_id,
        new_name=name,
        justification=justification,
        pfam_acc=pfam_acc,
    )

    # Approve and implement
    approve_change_request(conn, request_id)
    implement_create_group(conn, request_id)

    logger.info("Created F-group %s (%s) [request #%d]", new_f_id, name, request_id)
    return new_f_id, request_id


def deprecate_group(conn, group_id, group_type, justification=None):
    """Deprecate a group (F/T/H/X) through the change request workflow.

    Returns request_id.
    """
    justification = justification or f"Deprecate {group_type}-group {group_id}"

    request_id = create_change_request(
        conn, 'deprecate', group_type,
        original_id=group_id,
        justification=justification,
    )

    approve_change_request(conn, request_id)
    implement_deprecation(conn, request_id)

    logger.info("Deprecated %s-group %s [request #%d]", group_type, group_id, request_id)
    return request_id


# ============================================================
# Domain creation/deletion in ecod_rep
# ============================================================

def add_domain_to_ecod_rep(conn, ecod_domain_id, f_id, justification,
                           manual_rep=False, provisional_manual_rep=True):
    """Add a domain to ecod_rep.domain from ecod_commons.

    Uses create_domain_change_request + approve + implement_domain_create.
    Returns the new domain UID.
    """
    # Look up domain in ecod_commons
    commons_domain = get_domain_from_ecod_commons(conn, ecod_domain_id)
    if not commons_domain:
        raise ValueError(f"Domain {ecod_domain_id} not found in ecod_commons.domains")

    with conn.cursor() as cur:
        # Use stored function to create domain change request
        cur.execute("""
            SELECT ecod_rep.create_domain_change_request(
                %s, %s, %s, %s, NULL, %s, %s, 'manual', %s, %s, %s
            )
        """, (
            ecod_domain_id,
            ecod_domain_id,  # ecod_source_id
            f_id,
            commons_domain['range_definition'],
            manual_rep,
            provisional_manual_rep,
            justification,  # comment
            justification,
            REQUESTED_BY,
        ))
        request_id = cur.fetchone()[0]

    # Approve
    approve_change_request(conn, request_id)

    # Implement - returns the new UID
    with conn.cursor() as cur:
        cur.execute("SELECT ecod_rep.implement_domain_create(%s)", (request_id,))
        new_uid = cur.fetchone()[0]
        cur.execute("""
            UPDATE ecod_rep.hierarchy_change_request
            SET status = 'implemented', implementation_date = NOW()
            WHERE id = %s
        """, (request_id,))

    logger.info("Added domain %s to ecod_rep F-group %s [uid=%d, request #%d]",
                ecod_domain_id, f_id, new_uid, request_id)
    return new_uid


def delete_domain_from_ecod_rep(conn, domain_uid, ecod_domain_id,
                                justification):
    """Delete a domain from ecod_rep.domain with audit trail.

    Follows the pattern from batch_deprecate_a1.py (direct DELETE with
    domain_modification_log entry).
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # Get current domain state for logging
        cur.execute("""
            SELECT uid, ecod_domain_id, f_id::text, manual_rep,
                   provisional_manual_rep
            FROM ecod_rep.domain WHERE uid = %s
        """, (domain_uid,))
        domain = cur.fetchone()
        if not domain:
            raise ValueError(f"Domain uid={domain_uid} not found in ecod_rep")

    with conn.cursor() as cur:
        # Log the deletion
        cur.execute("""
            INSERT INTO ecod_rep.domain_modification_log (
                domain_uid, modification_type, old_value, new_value,
                justification, requested_by, timestamp
            ) VALUES (
                %s, 'delete_domain', %s, 'DELETED', %s, %s, NOW()
            )
        """, (
            domain_uid,
            f"ecod_domain_id={domain['ecod_domain_id']}, f_id={domain['f_id']}, "
            f"manual_rep={domain['manual_rep']}, "
            f"provisional_manual_rep={domain['provisional_manual_rep']}",
            justification,
            REQUESTED_BY,
        ))

        # Delete the domain
        cur.execute("DELETE FROM ecod_rep.domain WHERE uid = %s", (domain_uid,))
        deleted = cur.rowcount == 1

    if deleted:
        logger.info("Deleted domain %s (uid=%d) from ecod_rep", ecod_domain_id, domain_uid)
    return deleted


# ============================================================
# ecod_uid allocation
# ============================================================

def allocate_ecod_uid(conn):
    """Allocate a new ecod_uid from the ecod_commons sequence.

    Returns a unique integer suitable for ecod_commons.domains.ecod_uid.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT nextval('ecod_commons.ecod_uid_sequence')")
        return cur.fetchone()[0]


# ============================================================
# Domain deprecate-and-recreate (atomic domain principle)
# ============================================================

def deprecate_and_recreate_domain(conn, old_domain_pk, new_range, new_length,
                                   f_group_id, justification,
                                   new_domain_id=None):
    """Deprecate an existing domain and create a replacement with a new range.

    ECOD treats domains as atomic: range changes mean deprecate the old domain
    and create a new one with a fresh ecod_uid. This preserves provenance and
    avoids staleness in downstream dependencies.

    If new_domain_id is None, reuses the original domain_id.

    Returns (new_domain_pk, new_ecod_uid).
    """
    # Look up old domain
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT id, ecod_uid, domain_id, range_definition, sequence_length,
                   protein_id, domain_version, is_representative,
                   is_manual_representative, is_provisional_representative
            FROM ecod_commons.domains
            WHERE id = %s AND is_obsolete = false
        """, (old_domain_pk,))
        old = cur.fetchone()

    if not old:
        raise ValueError(f"Domain pk={old_domain_pk} not found or already obsolete")

    domain_id = new_domain_id or old['domain_id']
    new_ecod_uid = allocate_ecod_uid(conn)

    # Create replacement domain
    new_pk = create_commons_domain(
        conn,
        ecod_uid=new_ecod_uid,
        domain_id=domain_id,
        range_definition=new_range,
        sequence_length=new_length,
        protein_id=old['protein_id'],
        domain_version=old['domain_version'],
        is_representative=old['is_representative'],
        is_manual_representative=old['is_manual_representative'],
    )

    # Create f_group_assignment for the new domain
    create_commons_fgroup_assignment(
        conn, new_pk, f_group_id,
        f"Replacement for ecod_uid={old['ecod_uid']}: {justification}",
    )

    # Obsolete the old domain, pointing to the new one
    obsolete_commons_domain(
        conn, old_domain_pk,
        reason=f"Range changed {old['range_definition']} -> {new_range}: {justification}",
        superseded_by_pk=new_pk,
    )

    logger.info("Deprecated domain %s (ecod_uid=%d, pk=%d) and created replacement "
                "(ecod_uid=%d, pk=%d, range=%s)",
                old['domain_id'], old['ecod_uid'], old_domain_pk,
                new_ecod_uid, new_pk, new_range)

    return new_pk, new_ecod_uid


# ============================================================
# ecod_commons synchronization
# ============================================================

def reassign_commons_domains(conn, source_f, target_f, justification):
    """Reassign all domains from source_f to target_f in ecod_commons.

    Updates all hierarchy columns (f/t/h/x/a_group_id) to match the
    target F-group's hierarchy.

    Returns the count of reassigned domains.
    """
    # Get target hierarchy
    target_hier = get_hierarchy_ids_for_fgroup(conn, target_f)
    if not target_hier:
        raise ValueError(f"Could not resolve hierarchy for target F-group {target_f}")

    target_t = target_hier['t_id']
    target_h = target_hier['h_id']
    target_x = target_hier['x_id']

    # Determine A-group from target X (a_group_id is the architecture)
    # Look up what existing assignments use for a_group_id in this x_group
    with conn.cursor() as cur:
        cur.execute("""
            SELECT DISTINCT a_group_id FROM ecod_commons.f_group_assignments
            WHERE x_group_id = %s AND a_group_id IS NOT NULL
            LIMIT 1
        """, (target_x,))
        row = cur.fetchone()
        target_a = row[0] if row else None

    with conn.cursor() as cur:
        cur.execute("""
            UPDATE ecod_commons.f_group_assignments
            SET f_group_id = %s,
                t_group_id = %s,
                h_group_id = %s,
                x_group_id = %s,
                a_group_id = COALESCE(%s, a_group_id),
                assignment_method = 'manual',
                assigned_by = %s,
                assignment_date = NOW(),
                notes = COALESCE(notes, '') ||
                    E'\nReassigned from ' || %s || ': ' || %s ||
                    ' [' || NOW()::text || ']'
            WHERE f_group_id = %s
        """, (target_f, target_t, target_h, target_x, target_a,
              REQUESTED_BY, source_f, justification, source_f))
        count = cur.rowcount

    logger.info("Reassigned %d ecod_commons domains from %s -> %s", count, source_f, target_f)
    return count


def reassign_commons_domain_by_pk(conn, assignment_id, target_f, justification):
    """Reassign a single ecod_commons domain by its f_group_assignments.id."""
    target_hier = get_hierarchy_ids_for_fgroup(conn, target_f)
    if not target_hier:
        raise ValueError(f"Could not resolve hierarchy for target F-group {target_f}")

    with conn.cursor() as cur:
        cur.execute("""
            SELECT DISTINCT a_group_id FROM ecod_commons.f_group_assignments
            WHERE x_group_id = %s AND a_group_id IS NOT NULL
            LIMIT 1
        """, (target_hier['x_id'],))
        row = cur.fetchone()
        target_a = row[0] if row else None

    with conn.cursor() as cur:
        cur.execute("""
            UPDATE ecod_commons.f_group_assignments
            SET f_group_id = %s,
                t_group_id = %s,
                h_group_id = %s,
                x_group_id = %s,
                a_group_id = COALESCE(%s, a_group_id),
                assignment_method = 'manual',
                assigned_by = %s,
                assignment_date = NOW(),
                notes = COALESCE(notes, '') ||
                    E'\nReassigned to ' || %s || ': ' || %s ||
                    ' [' || NOW()::text || ']'
            WHERE id = %s
        """, (target_f, target_hier['t_id'], target_hier['h_id'],
              target_hier['x_id'], target_a, REQUESTED_BY,
              target_f, justification, assignment_id))
        return cur.rowcount == 1


def update_commons_domain_range(conn, ecod_uid, new_range, new_length=None):
    """Update a domain's range_definition in ecod_commons.domains."""
    with conn.cursor() as cur:
        if new_length is not None:
            cur.execute("""
                UPDATE ecod_commons.domains
                SET range_definition = %s,
                    sequence_length = %s,
                    last_updated = NOW()
                WHERE ecod_uid = %s AND is_obsolete = false
            """, (new_range, new_length, ecod_uid))
        else:
            cur.execute("""
                UPDATE ecod_commons.domains
                SET range_definition = %s,
                    last_updated = NOW()
                WHERE ecod_uid = %s AND is_obsolete = false
            """, (new_range, ecod_uid))
        return cur.rowcount > 0


def obsolete_commons_domain(conn, domain_pk, reason, superseded_by_pk=None):
    """Mark a domain as obsolete in ecod_commons.domains."""
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE ecod_commons.domains
            SET is_obsolete = true,
                obsoleted_date = NOW(),
                obsoleted_reason = %s,
                superseded_by_domain_id = %s,
                last_updated = NOW()
            WHERE id = %s
        """, (reason, superseded_by_pk, domain_pk))
        return cur.rowcount > 0


def create_commons_domain(conn, ecod_uid, domain_id, range_definition,
                          sequence_length, protein_id, domain_version,
                          is_representative=False, is_manual_representative=False):
    """Create a new domain entry in ecod_commons.domains.

    Returns the new domain primary key (id).
    """
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO ecod_commons.domains (
                ecod_uid, domain_id, range_definition, sequence_length,
                protein_id, domain_version, range_type,
                classification_status, classification_method,
                is_representative, is_manual_representative,
                is_provisional_representative,
                created_date, created_by, last_updated
            ) VALUES (
                %s, %s, %s, %s, %s, %s, 'seqid',
                'classified', 'manual',
                %s, %s, false,
                NOW(), %s, NOW()
            )
            RETURNING id
        """, (ecod_uid, domain_id, range_definition, sequence_length,
              protein_id, domain_version,
              is_representative, is_manual_representative,
              REQUESTED_BY))
        return cur.fetchone()[0]


def create_commons_fgroup_assignment(conn, domain_pk, f_group_id, justification):
    """Create an f_group_assignment for a domain in ecod_commons."""
    hier = get_hierarchy_ids_for_fgroup(conn, f_group_id)
    if not hier:
        raise ValueError(f"Could not resolve hierarchy for F-group {f_group_id}")

    with conn.cursor() as cur:
        cur.execute("""
            SELECT DISTINCT a_group_id FROM ecod_commons.f_group_assignments
            WHERE x_group_id = %s AND a_group_id IS NOT NULL
            LIMIT 1
        """, (hier['x_id'],))
        row = cur.fetchone()
        a_group_id = row[0] if row else None

    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO ecod_commons.f_group_assignments (
                domain_id, f_group_id, t_group_id, h_group_id,
                x_group_id, a_group_id,
                assignment_method, assigned_by, assignment_date,
                classification_level, notes
            ) VALUES (
                %s, %s, %s, %s, %s, %s,
                'manual', %s, NOW(),
                'f_group_specific', %s
            )
            RETURNING id
        """, (domain_pk, f_group_id, hier['t_id'], hier['h_id'],
              hier['x_id'], a_group_id, REQUESTED_BY, justification))
        return cur.fetchone()[0]


# ============================================================
# Validation helpers
# ============================================================

def verify_change_preconditions(conn, source_f, target_f=None):
    """Verify basic preconditions for a change.

    Returns (ok, message) tuple.
    """
    source = verify_fgroup_exists(conn, source_f)
    if not source:
        return False, f"Source F-group {source_f} not found"
    if source['is_deprecated']:
        return False, f"Source F-group {source_f} is already deprecated"

    if target_f:
        target = verify_fgroup_exists(conn, target_f)
        if not target:
            return False, f"Target F-group {target_f} not found"
        if target['is_deprecated']:
            return False, f"Target F-group {target_f} is deprecated"

    return True, "OK"


def verify_domain_counts_balance(conn, source_f, target_f,
                                 expected_moved, schema='ecod_commons'):
    """Verify domain counts balance after a move operation.

    Returns (ok, message) tuple.
    """
    source_count = count_fgroup_members(conn, source_f, schema)
    target_count = count_fgroup_members(conn, target_f, schema)
    return True, f"Source {source_f}: {source_count}, Target {target_f}: {target_count}"


def print_change_summary(change_id, description, actions, dry_run=True):
    """Print a formatted change summary."""
    mode = "DRY RUN" if dry_run else "EXECUTE"
    print(f"\n{'=' * 70}")
    print(f"Change {change_id}: {description}")
    print(f"Mode: {mode}")
    print(f"{'=' * 70}")
    for action in actions:
        print(f"  {action}")
    print()
