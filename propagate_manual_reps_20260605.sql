-- =============================================================================
-- propagate_manual_reps_20260605.sql
-- Generated 2026-06-05 against dione:45000 / ecod_protein
--
-- PURPOSE
--   Bring ecod_rep.domain into line with ecod_commons for the 344 "repless"
--   active F-groups whose attached commons domain carries is_manual_representative.
--
-- KEY FINDING (read before running)
--   These are NOT missing flags. All 456 candidate domains ALREADY exist in
--   ecod_rep.domain as manual_rep=true -- but attached to a DIFFERENT F-group
--   than commons assigns (almost always a sibling within the SAME T-group).
--   So each statement is an f_id REASSIGNMENT on the existing row (same ecod_uid),
--   matching the commons F-group. manual_rep stays true.
--
-- TIERS (456 domains across 344 commons F-groups)
--   T1 FILL-IN              72 dom / 71 fg  ecod_rep f_id was NULL (T-only)     SAFE
--   T2 OLD DEPRECATED       42 dom / 38 fg  old ecod_rep F-group is deprecated  SAFE
--   T3 RECLASSIFY          272 dom /179 fg  old active F-group keeps other reps  REVIEW
--   T4 STRANDS OLD GROUP    70 dom / 61 fg  move EMPTIES an active F-group       HOLD
--                                           -> would create 61 NEW repless F-groups
--
-- Each UPDATE is guarded: WHERE ecod_uid=N AND manual_rep IS TRUE
--   AND f_id IS NOT DISTINCT FROM <expected old f_id>.
--   If the row has drifted, that statement updates 0 rows (safe no-op).
--
-- NO LOGGING is emitted here (ecod_rep.domain has no change trigger). If you want
--   an audit trail, populate ecod_rep.domain_assignment_log
--   (assignment_type/old_value/new_value) -- see commented block at the foot.
--
-- DEFAULT IS ROLLBACK. Review row counts, then change the final ROLLBACK to COMMIT.
--   Recommended: run T1+T2 first (SAFE), verify, then decide on T3; HOLD T4.
-- =============================================================================

\set ON_ERROR_STOP on
\timing on

BEGIN;

-- Snapshot the affected ecod_uids' current f_id BEFORE (for diffing if desired)
CREATE TEMP TABLE _before AS
SELECT ecod_uid, f_id AS old_f_id, t_id, manual_rep
FROM ecod_rep.domain
WHERE ecod_uid IN (
  WITH repless AS (
    SELECT c.id FROM ecod_rep.cluster c
    WHERE c.type='F' AND c.is_deprecated IS NOT TRUE
      AND NOT EXISTS (SELECT 1 FROM ecod_rep.domain d
         WHERE d.f_id=c.id AND (d.manual_rep IS TRUE OR d.provisional_manual_rep IS TRUE))
  )
  SELECT dom.ecod_uid
  FROM repless r
  JOIN ecod_commons.f_group_assignments fga ON fga.f_group_id=r.id
  JOIN ecod_commons.domains dom ON dom.id=fga.domain_id AND dom.is_obsolete IS NOT TRUE
  WHERE dom.is_manual_representative
);

-- Snapshot the 344 TARGET commons F-groups BEFORE the updates (while still repless)
CREATE TEMP TABLE _targets AS
WITH repless AS (
  SELECT c.id FROM ecod_rep.cluster c
  WHERE c.type='F' AND c.is_deprecated IS NOT TRUE
    AND NOT EXISTS (SELECT 1 FROM ecod_rep.domain d
       WHERE d.f_id=c.id AND (d.manual_rep IS TRUE OR d.provisional_manual_rep IS TRUE))
)
SELECT DISTINCT fga.f_group_id AS f_id
FROM ecod_commons.f_group_assignments fga
JOIN ecod_commons.domains dom ON dom.id=fga.domain_id AND dom.is_obsolete IS NOT TRUE
WHERE dom.is_manual_representative AND fga.f_group_id IN (SELECT id FROM repless);

-- ----- TIER 1: FILL-IN (ecod_rep f_id was NULL / T-group only) -- SAFE -----
UPDATE ecod_rep.domain SET f_id='7579.1.1.98', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=10833 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e1jfrA1  (null) -> 7579.1.1.98
UPDATE ecod_rep.domain SET f_id='207.1.1.157', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1088877 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e4kxfK5  (null) -> 207.1.1.157
UPDATE ecod_rep.domain SET f_id='3435.1.1.7', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1108116 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e4je3A1  (null) -> 3435.1.1.7
UPDATE ecod_rep.domain SET f_id='109.4.1.1575', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1141025 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e4n5cD1  (null) -> 109.4.1.1575
UPDATE ecod_rep.domain SET f_id='109.4.1.1438', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1145793 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e2gw1A1  (null) -> 109.4.1.1438
UPDATE ecod_rep.domain SET f_id='3090.1.1.2', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=119222 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e2knjA1  (null) -> 3090.1.1.2
UPDATE ecod_rep.domain SET f_id='101.1.1.364', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1288513 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e4jp0A3  (null) -> 101.1.1.364
UPDATE ecod_rep.domain SET f_id='389.1.1.110', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=146868 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e3nsjA2  (null) -> 389.1.1.110
UPDATE ecod_rep.domain SET f_id='304.166.1.9', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1681454 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e5c2uA1  (null) -> 304.166.1.9
UPDATE ecod_rep.domain SET f_id='5.1.4.331', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1687171 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e5cwwB1  (null) -> 5.1.4.331
UPDATE ecod_rep.domain SET f_id='1010.1.1.1', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1688243 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e4z8qB1  (null) -> 1010.1.1.1
UPDATE ecod_rep.domain SET f_id='1009.1.1.1', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1688245 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e4zmkA1  (null) -> 1009.1.1.1
UPDATE ecod_rep.domain SET f_id='1041.1.1.1', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1736241 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e5cowA1  (null) -> 1041.1.1.1
UPDATE ecod_rep.domain SET f_id='109.4.1.1573', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1736252 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e5ganJ1  (null) -> 109.4.1.1573
UPDATE ecod_rep.domain SET f_id='1047.1.1.1', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1779594 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e5hx2A2  (null) -> 1047.1.1.1
UPDATE ecod_rep.domain SET f_id='11.41.1.1', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1779600 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e5hx2D2  (null) -> 11.41.1.1
UPDATE ecod_rep.domain SET f_id='1058.1.1.1', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1821879 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e2gv9B7  (null) -> 1058.1.1.1
UPDATE ecod_rep.domain SET f_id='304.9.1.92', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1824183 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e5hb7A1  (null) -> 304.9.1.92
UPDATE ecod_rep.domain SET f_id='1088.1.1.1', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1841022 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e4uxeB3  (null) -> 1088.1.1.1
UPDATE ecod_rep.domain SET f_id='872.12.1.1', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1916704 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e5evfA1  (null) -> 872.12.1.1
UPDATE ecod_rep.domain SET f_id='4178.1.1.4', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2038 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e2f2hA3  (null) -> 4178.1.1.4
UPDATE ecod_rep.domain SET f_id='109.3.1.170', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2075105 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e5h28A1  (null) -> 109.3.1.170
UPDATE ecod_rep.domain SET f_id='148.1.3.203', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2076897 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e5kzfJ4  (null) -> 148.1.3.203
UPDATE ecod_rep.domain SET f_id='1164.1.1.2', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2084857 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e5x90D1  (null) -> 1164.1.1.2
UPDATE ecod_rep.domain SET f_id='109.4.1.1284', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2322965 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e6f5dL1  (null) -> 109.4.1.1284
UPDATE ecod_rep.domain SET f_id='1194.1.1.1', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2323779 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e4fweA5  (null) -> 1194.1.1.1
UPDATE ecod_rep.domain SET f_id='1201.1.1.1', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2323862 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e5n0sA3  (null) -> 1201.1.1.1
UPDATE ecod_rep.domain SET f_id='376.1.3.56', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2323923 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e5oqdC1  (null) -> 376.1.3.56
UPDATE ecod_rep.domain SET f_id='101.1.2.500', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2323924 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e5oqdC2  (null) -> 101.1.2.500
UPDATE ecod_rep.domain SET f_id='4.29.1.1', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2323952 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e5ud5A1  (null) -> 4.29.1.1
UPDATE ecod_rep.domain SET f_id='2.1.1.224', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2323967 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e5vbnA1  (null) -> 2.1.1.224
UPDATE ecod_rep.domain SET f_id='109.4.1.1697', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2323971 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e5ve8B1  (null) -> 109.4.1.1697
UPDATE ecod_rep.domain SET f_id='11.1.1.987', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2323974 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e5vhvA2  (null) -> 11.1.1.987
UPDATE ecod_rep.domain SET f_id='101.1.2.500', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2324026 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e5xfoA4  (null) -> 101.1.2.500
UPDATE ecod_rep.domain SET f_id='1195.1.1.2', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2324037 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e5xynD1  (null) -> 1195.1.1.2
UPDATE ecod_rep.domain SET f_id='2008.1.1.149', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2324072 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e6bzfB1  (null) -> 2008.1.1.149
UPDATE ecod_rep.domain SET f_id='102.1.1.111', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2324073 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e6bzfB2  (null) -> 102.1.1.111
UPDATE ecod_rep.domain SET f_id='2008.8.1.1', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2324093 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e6f1sA1  (null) -> 2008.8.1.1
UPDATE ecod_rep.domain SET f_id='9.30.1.1', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2387804 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e5xllA1  (null) -> 9.30.1.1
UPDATE ecod_rep.domain SET f_id='304.9.1.78', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2387865 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e6f7jB1  (null) -> 304.9.1.78
UPDATE ecod_rep.domain SET f_id='7030.1.1.1', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2485644 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e5w4aB1  (null) -> 7030.1.1.1
UPDATE ecod_rep.domain SET f_id='633.16.2.2', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2485650 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e5yclA2  (null) -> 633.16.2.2
UPDATE ecod_rep.domain SET f_id='7052.1.1.1', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2485656 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e6a29E1  (null) -> 7052.1.1.1
UPDATE ecod_rep.domain SET f_id='7053.1.1.1', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2485657 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e6a29E2  (null) -> 7053.1.1.1
UPDATE ecod_rep.domain SET f_id='7035.1.1.1', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2485680 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e6ebnA3  (null) -> 7035.1.1.1
UPDATE ecod_rep.domain SET f_id='7040.1.1.1', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2485693 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e6ghcB1  (null) -> 7040.1.1.1
UPDATE ecod_rep.domain SET f_id='7059.1.1.1', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2502890 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e6dnmA1  (null) -> 7059.1.1.1
UPDATE ecod_rep.domain SET f_id='207.16.1.1', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2502901 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e6gjeC1  (null) -> 207.16.1.1
UPDATE ecod_rep.domain SET f_id='7083.1.1.1', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2526309 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e6a9sA2  (null) -> 7083.1.1.1
UPDATE ecod_rep.domain SET f_id='1205.2.1.1', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2526314 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e6d7yA1  (null) -> 1205.2.1.1
UPDATE ecod_rep.domain SET f_id='7075.1.1.1', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2526315 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e6d7yB1  (null) -> 7075.1.1.1
UPDATE ecod_rep.domain SET f_id='7093.1.1.1', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2526318 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e6hq6A4  (null) -> 7093.1.1.1
UPDATE ecod_rep.domain SET f_id='375.15.1.1', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2526330 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e6jdeB3  (null) -> 375.15.1.1
UPDATE ecod_rep.domain SET f_id='7091.1.1.1', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2526331 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e6jdeB4  (null) -> 7091.1.1.1
UPDATE ecod_rep.domain SET f_id='7092.1.1.1', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2526332 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e6jl2A2  (null) -> 7092.1.1.1
UPDATE ecod_rep.domain SET f_id='922.1.1.21', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2526352 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e6qixA1  (null) -> 922.1.1.21
UPDATE ecod_rep.domain SET f_id='7084.1.1.2', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2526353 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e6qixA2  (null) -> 7084.1.1.2
UPDATE ecod_rep.domain SET f_id='7103.1.1.1', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2576194 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e6h1wA2  (null) -> 7103.1.1.1
UPDATE ecod_rep.domain SET f_id='558.1.1.19', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2576204 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e6iwvA1  (null) -> 558.1.1.19
UPDATE ecod_rep.domain SET f_id='906.2.1.1', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2576208 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e6j2pA2  (null) -> 906.2.1.1
UPDATE ecod_rep.domain SET f_id='7112.1.1.1', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2576209 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e6jq1B2  (null) -> 7112.1.1.1
UPDATE ecod_rep.domain SET f_id='7529.1.1.14', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2623804 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e6bxrA1  (null) -> 7529.1.1.14
UPDATE ecod_rep.domain SET f_id='109.4.1.1413', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=4613 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e1xqrA1  (null) -> 109.4.1.1413
UPDATE ecod_rep.domain SET f_id='211.1.1.41', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=5723 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e1ecsA1  (null) -> 211.1.1.41
UPDATE ecod_rep.domain SET f_id='4099.1.1.25', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=6542 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e2ftxA1  (null) -> 4099.1.1.25
UPDATE ecod_rep.domain SET f_id='207.1.1.162', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=7186 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e2astB2  (null) -> 207.1.1.162
UPDATE ecod_rep.domain SET f_id='207.1.1.199', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=7190 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e1jl5A1  (null) -> 207.1.1.199
UPDATE ecod_rep.domain SET f_id='235.1.1.33', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=7423 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e1am7A1  (null) -> 235.1.1.33
UPDATE ecod_rep.domain SET f_id='4075.1.1.2', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=7608 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e1x0hA1  (null) -> 4075.1.1.2
UPDATE ecod_rep.domain SET f_id='4986.1.1.4', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=7939 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e1xu6A1  (null) -> 4986.1.1.4
UPDATE ecod_rep.domain SET f_id='387.1.5.28', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=8441 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e1ozzA1  (null) -> 387.1.5.28
UPDATE ecod_rep.domain SET f_id='389.1.1.99', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=8461 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM NULL;  -- e1moxC1  (null) -> 389.1.1.99
-- ----- TIER 2: OLD F-GROUP DEPRECATED -- SAFE -----
UPDATE ecod_rep.domain SET f_id='1.1.7.87', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1002475 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '1.1.7.38';  -- e3ne5B2  1.1.7.38 -> 1.1.7.87
UPDATE ecod_rep.domain SET f_id='6119.1.1.2', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1002477 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '6119.1.1.1';  -- e3ne5B4  6119.1.1.1 -> 6119.1.1.2
UPDATE ecod_rep.domain SET f_id='6082.1.1.3', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1005491 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '6082.1.1.2';  -- e3hbzA1  6082.1.1.2 -> 6082.1.1.3
UPDATE ecod_rep.domain SET f_id='1.1.7.87', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1096987 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '1.1.7.38';  -- e4kksA2  1.1.7.38 -> 1.1.7.87
UPDATE ecod_rep.domain SET f_id='4176.1.1.2', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=10975 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '4176.1.1.1';  -- e2o3iA2  4176.1.1.1 -> 4176.1.1.2
UPDATE ecod_rep.domain SET f_id='1.13.1.2', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1141837 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '1.13.1.1';  -- e1yleA2  1.13.1.1 -> 1.13.1.2
UPDATE ecod_rep.domain SET f_id='11.1.1.1155', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1144732 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '11.1.1.149';  -- e2nykA2  11.1.1.149 -> 11.1.1.1155
UPDATE ecod_rep.domain SET f_id='1.1.7.87', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1145751 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '1.1.7.38';  -- e3lnnA2  1.1.7.38 -> 1.1.7.87
UPDATE ecod_rep.domain SET f_id='1.1.7.87', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1145817 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '1.1.7.38';  -- e3h94A2  1.1.7.38 -> 1.1.7.87
UPDATE ecod_rep.domain SET f_id='6119.1.1.2', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1145819 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '6119.1.1.1';  -- e3h94A4  6119.1.1.1 -> 6119.1.1.2
UPDATE ecod_rep.domain SET f_id='101.1.1.301', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=119500 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '101.1.1.73';  -- e3nnqA1  101.1.1.73 -> 101.1.1.301
UPDATE ecod_rep.domain SET f_id='5.1.4.269', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1291898 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '5.1.4.2';  -- e4ci8A1  5.1.4.2 -> 5.1.4.269
UPDATE ecod_rep.domain SET f_id='5.1.4.293', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1291899 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '5.1.4.2';  -- e4ci8A2  5.1.4.2 -> 5.1.4.293
UPDATE ecod_rep.domain SET f_id='1.1.7.88', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1313622 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '1.1.7.3';  -- e4tkoB1  1.1.7.3 -> 1.1.7.88
UPDATE ecod_rep.domain SET f_id='3234.1.1.2', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=147021 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '3234.1.1.1';  -- e3n54B1  3234.1.1.1 -> 3234.1.1.2
UPDATE ecod_rep.domain SET f_id='12.1.1.117', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1498230 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '12.1.1.20';  -- e3lm3A2  12.1.1.20 -> 12.1.1.117
UPDATE ecod_rep.domain SET f_id='2484.1.1.195', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1503129 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2484.1.1.64';  -- e4wwxB2  2484.1.1.64 -> 2484.1.1.195
UPDATE ecod_rep.domain SET f_id='3948.1.1.3', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1503130 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '3948.1.1.1';  -- e4wwxB3  3948.1.1.1 -> 3948.1.1.3
UPDATE ecod_rep.domain SET f_id='3386.2.1.4', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1839971 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '3386.2.1.1';  -- e5iv5I2  3386.2.1.1 -> 3386.2.1.4
UPDATE ecod_rep.domain SET f_id='3070.1.1.18', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=185292 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '3070.1.1.3';  -- e3gs9A2  3070.1.1.3 -> 3070.1.1.18
UPDATE ecod_rep.domain SET f_id='207.2.1.75', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=185295 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '207.2.1.7';  -- e3h09A3  207.2.1.7 -> 207.2.1.75
UPDATE ecod_rep.domain SET f_id='3305.1.1.7', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=185457 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '3305.1.1.1';  -- e3p8cF1  3305.1.1.1 -> 3305.1.1.7
UPDATE ecod_rep.domain SET f_id='2004.1.1.453', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=185910 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2004.1.1.147';  -- e2e87A1  2004.1.1.147 -> 2004.1.1.453
UPDATE ecod_rep.domain SET f_id='3425.2.1.3', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=185951 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '3425.2.1.1';  -- e2fgtA2  3425.2.1.1 -> 3425.2.1.3
UPDATE ecod_rep.domain SET f_id='375.1.1.204', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1885533 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '375.1.1.24';  -- e5ijlA2  375.1.1.24 -> 375.1.1.204
UPDATE ecod_rep.domain SET f_id='1.3.1.2', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1885536 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '1.3.1.1';  -- e5ijlA5  1.3.1.1 -> 1.3.1.2
UPDATE ecod_rep.domain SET f_id='513.2.1.2', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1891399 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '513.2.1.1';  -- e3k6rA1  513.2.1.1 -> 513.2.1.2
UPDATE ecod_rep.domain SET f_id='2007.15.1.11', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2041636 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.4.1.193';  -- e5ulmA1  109.4.1.193 -> 2007.15.1.11
UPDATE ecod_rep.domain SET f_id='327.21.1.2', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2080138 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '327.21.1.1';  -- e5ucgA2  327.21.1.1 -> 327.21.1.2
UPDATE ecod_rep.domain SET f_id='3077.1.1.3', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=224012 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '3077.1.1.2';  -- e4ei0A2  3077.1.1.2 -> 3077.1.1.3
UPDATE ecod_rep.domain SET f_id='3597.1.1.5', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=224022 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '3597.1.1.2';  -- e4fe9A2  3597.1.1.2 -> 3597.1.1.5
UPDATE ecod_rep.domain SET f_id='101.1.2.543', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2324055 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '101.1.2.155';  -- e6b39A1  101.1.2.155 -> 101.1.2.543
UPDATE ecod_rep.domain SET f_id='5087.2.1.2', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2373 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '5087.2.1.1';  -- e1lshA1  5087.2.1.1 -> 5087.2.1.2
UPDATE ecod_rep.domain SET f_id='3735.1.1.14', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2387867 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '3735.1.1.3';  -- e6fb3A2  3735.1.1.3 -> 3735.1.1.14
UPDATE ecod_rep.domain SET f_id='139.2.1.18', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2576201 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '139.2.1.2';  -- e6i5bA2  139.2.1.2 -> 139.2.1.18
UPDATE ecod_rep.domain SET f_id='109.4.1.1802', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=4549 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.4.1.6';  -- e1a17A1  109.4.1.6 -> 109.4.1.1802
UPDATE ecod_rep.domain SET f_id='109.4.1.1707', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=4563 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.4.1.9';  -- e2c2lA1  109.4.1.9 -> 109.4.1.1707
UPDATE ecod_rep.domain SET f_id='205.1.1.47', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=5482 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '205.1.1.13';  -- e1jnrB1  205.1.1.13 -> 205.1.1.47
UPDATE ecod_rep.domain SET f_id='4.15.1.2', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=607 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '4.15.1.1';  -- e2f5tX1  4.15.1.1 -> 4.15.1.2
UPDATE ecod_rep.domain SET f_id='2002.1.1.301', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=8818 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2002.1.1.5';  -- e1gcyA2  2002.1.1.5 -> 2002.1.1.301
UPDATE ecod_rep.domain SET f_id='2003.1.2.63', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9224 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2003.1.2.3';  -- e1kdgA2  2003.1.2.3 -> 2003.1.2.63
UPDATE ecod_rep.domain SET f_id='2004.1.1.1172', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9690 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2004.1.1.113';  -- e1qhlA1  2004.1.1.113 -> 2004.1.1.1172
-- ----- TIER 3: RECLASSIFY (old active F-group survives, keeps other reps) -- REVIEW -----
UPDATE ecod_rep.domain SET f_id='2004.1.1.654', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1005523 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2004.1.1.195';  -- e3u44B2  2004.1.1.195 -> 2004.1.1.654
UPDATE ecod_rep.domain SET f_id='2007.2.3.21', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=10114 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2007.2.3.1';  -- e2shpA3  2007.2.3.1 -> 2007.2.3.21
UPDATE ecod_rep.domain SET f_id='2011.1.1.20', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=10163 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2011.1.1.6';  -- e1r3nA2  2011.1.1.6 -> 2011.1.1.20
UPDATE ecod_rep.domain SET f_id='247.1.1.29', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1019409 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '247.1.1.11';  -- e4gcwA1  247.1.1.11 -> 247.1.1.29
UPDATE ecod_rep.domain SET f_id='207.1.1.142', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1030869 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '207.1.1.20';  -- e1h6tA3  207.1.1.20 -> 207.1.1.142
UPDATE ecod_rep.domain SET f_id='5.1.4.274', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1031088 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '5.1.4.1';  -- e3sfzA5  5.1.4.1 -> 5.1.4.274
UPDATE ecod_rep.domain SET f_id='5.1.5.75', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1031089 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '5.1.5.1';  -- e3sfzA6  5.1.5.1 -> 5.1.5.75
UPDATE ecod_rep.domain SET f_id='2004.1.1.414', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1031105 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2004.1.1.14';  -- e3zztA4  2004.1.1.14 -> 2004.1.1.414
UPDATE ecod_rep.domain SET f_id='206.1.1.72', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1031124 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '206.1.1.1';  -- e4e3cB1  206.1.1.1 -> 206.1.1.72
UPDATE ecod_rep.domain SET f_id='221.1.1.164', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1031125 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '221.1.1.2';  -- e4e3cB2  221.1.1.2 -> 221.1.1.164
UPDATE ecod_rep.domain SET f_id='10.1.1.74', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1070 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '10.1.1.11';  -- e1dypA1  10.1.1.11 -> 10.1.1.74
UPDATE ecod_rep.domain SET f_id='10.2.1.89', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1070876 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '10.2.1.48';  -- e4kq7A1  10.2.1.48 -> 10.2.1.89
UPDATE ecod_rep.domain SET f_id='10.1.1.74', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1072 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '10.1.1.11';  -- e1o4yA1  10.1.1.11 -> 10.1.1.74
UPDATE ecod_rep.domain SET f_id='7579.1.1.89', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=10780 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '7579.1.1.1';  -- e1ea5A1  7579.1.1.1 -> 7579.1.1.89
UPDATE ecod_rep.domain SET f_id='7579.1.1.89', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=10781 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '7579.1.1.1';  -- e1dx4A1  7579.1.1.1 -> 7579.1.1.89
UPDATE ecod_rep.domain SET f_id='7579.1.1.89', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=10782 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '7579.1.1.1';  -- e2bceA1  7579.1.1.1 -> 7579.1.1.89
UPDATE ecod_rep.domain SET f_id='7579.1.1.93', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=10804 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '7579.1.1.6';  -- e1k8qA1  7579.1.1.6 -> 7579.1.1.93
UPDATE ecod_rep.domain SET f_id='7579.1.1.92', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=10811 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '7579.1.1.6';  -- e1c4xA1  7579.1.1.6 -> 7579.1.1.92
UPDATE ecod_rep.domain SET f_id='7579.1.1.89', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=10839 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '7579.1.1.1';  -- e1ukcA1  7579.1.1.1 -> 7579.1.1.89
UPDATE ecod_rep.domain SET f_id='7579.1.1.94', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=10852 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '7579.1.1.3';  -- e2hu7A2  7579.1.1.3 -> 7579.1.1.94
UPDATE ecod_rep.domain SET f_id='7581.1.1.22', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=10875 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '7581.1.1.1';  -- e1wdkC2  7581.1.1.1 -> 7581.1.1.22
UPDATE ecod_rep.domain SET f_id='7581.1.1.23', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=10878 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '7581.1.1.13';  -- e1hnjA1  7581.1.1.13 -> 7581.1.1.23
UPDATE ecod_rep.domain SET f_id='1.1.1.27', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1088763 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '1.1.1.1';  -- e1mppA1  1.1.1.1 -> 1.1.1.27
UPDATE ecod_rep.domain SET f_id='1.1.1.27', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1088767 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '1.1.1.1';  -- e1oewA2  1.1.1.1 -> 1.1.1.27
UPDATE ecod_rep.domain SET f_id='1.1.1.27', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1088769 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '1.1.1.1';  -- e1smrA2  1.1.1.1 -> 1.1.1.27
UPDATE ecod_rep.domain SET f_id='206.1.1.70', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1088849 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '206.1.1.1';  -- e4bkyA1  206.1.1.1 -> 206.1.1.70
UPDATE ecod_rep.domain SET f_id='213.1.1.72', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=11057 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '213.1.1.1';  -- e1cjwA1  213.1.1.1 -> 213.1.1.72
UPDATE ecod_rep.domain SET f_id='213.1.1.72', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=11071 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '213.1.1.1';  -- e1u6mA1  213.1.1.1 -> 213.1.1.72
UPDATE ecod_rep.domain SET f_id='205.1.1.71', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1107951 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '205.1.1.17';  -- e1h0hB2  205.1.1.17 -> 205.1.1.71
UPDATE ecod_rep.domain SET f_id='205.1.1.48', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1107957 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '205.1.1.17';  -- e1kqfB3  205.1.1.17 -> 205.1.1.48
UPDATE ecod_rep.domain SET f_id='207.1.1.161', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1108122 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '207.1.1.22';  -- e4k17A2  207.1.1.22 -> 207.1.1.161
UPDATE ecod_rep.domain SET f_id='7581.1.1.22', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1108126 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '7581.1.1.2';  -- e4kc5A1  7581.1.1.2 -> 7581.1.1.22
UPDATE ecod_rep.domain SET f_id='213.1.1.75', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=11106 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '213.1.1.7';  -- e1lrzA3  213.1.1.7 -> 213.1.1.75
UPDATE ecod_rep.domain SET f_id='2004.1.1.500', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1117696 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2004.1.1.156';  -- e3vkhA3  2004.1.1.156 -> 2004.1.1.500
UPDATE ecod_rep.domain SET f_id='2484.1.1.197', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1121969 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2484.1.1.34';  -- e4m8oA3  2484.1.1.34 -> 2484.1.1.197
UPDATE ecod_rep.domain SET f_id='54.1.1.7', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1124210 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '54.1.1.2';  -- e4lp7B2  54.1.1.2 -> 54.1.1.7
UPDATE ecod_rep.domain SET f_id='11.1.1.861', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1125473 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '11.1.1.72';  -- e4ij2F1  11.1.1.72 -> 11.1.1.861
UPDATE ecod_rep.domain SET f_id='7581.1.1.24', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1141779 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '7581.1.1.4';  -- e1tedA2  7581.1.1.4 -> 7581.1.1.24
UPDATE ecod_rep.domain SET f_id='206.1.1.71', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1144179 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '206.1.1.1';  -- e4o1pC2  206.1.1.1 -> 206.1.1.71
UPDATE ecod_rep.domain SET f_id='11.1.5.96', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1144822 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '11.1.5.26';  -- e3f83A1  11.1.5.26 -> 11.1.5.96
UPDATE ecod_rep.domain SET f_id='108.1.1.97', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1145809 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '108.1.1.29';  -- e2lhiA1  108.1.1.29 -> 108.1.1.97
UPDATE ecod_rep.domain SET f_id='206.1.1.70', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1145884 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '206.1.1.1';  -- e4cfeA1  206.1.1.1 -> 206.1.1.70
UPDATE ecod_rep.domain SET f_id='206.1.1.70', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1145908 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '206.1.1.1';  -- e4cfhA1  206.1.1.1 -> 206.1.1.70
UPDATE ecod_rep.domain SET f_id='2004.1.1.433', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1148095 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2004.1.1.87';  -- e2o5vA1  2004.1.1.87 -> 2004.1.1.433
UPDATE ecod_rep.domain SET f_id='5.1.5.78', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1148107 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '5.1.5.1';  -- e3j65q2  5.1.5.1 -> 5.1.5.78
UPDATE ecod_rep.domain SET f_id='2498.1.1.90', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=11490 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2498.1.1.45';  -- e2i47A1  2498.1.1.45 -> 2498.1.1.90
UPDATE ecod_rep.domain SET f_id='2490.3.1.3', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=11511 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2490.3.1.1';  -- e2j01P1  2490.3.1.1 -> 2490.3.1.3
UPDATE ecod_rep.domain SET f_id='207.1.1.158', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1180304 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '207.1.1.24';  -- e4lxrA1  207.1.1.24 -> 207.1.1.158
UPDATE ecod_rep.domain SET f_id='10.2.1.87', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1184 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '10.2.1.45';  -- e1hx6A2  10.2.1.45 -> 10.2.1.87
UPDATE ecod_rep.domain SET f_id='108.1.1.98', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=118926 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '108.1.1.1';  -- e1auiB1  108.1.1.1 -> 108.1.1.98
UPDATE ecod_rep.domain SET f_id='108.1.1.97', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=118927 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '108.1.1.29';  -- e1auiB2  108.1.1.29 -> 108.1.1.97
UPDATE ecod_rep.domain SET f_id='108.1.1.97', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=118942 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '108.1.1.1';  -- e1exrA1  108.1.1.1 -> 108.1.1.97
UPDATE ecod_rep.domain SET f_id='108.1.1.96', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=118943 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '108.1.1.29';  -- e1exrA2  108.1.1.29 -> 108.1.1.96
UPDATE ecod_rep.domain SET f_id='108.1.1.99', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=118952 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '108.1.1.29';  -- e1hqvA2  108.1.1.29 -> 108.1.1.99
UPDATE ecod_rep.domain SET f_id='108.1.1.97', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=118964 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '108.1.1.29';  -- e1jbaA2  108.1.1.29 -> 108.1.1.97
UPDATE ecod_rep.domain SET f_id='108.1.1.99', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=118965 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '108.1.1.29';  -- e1jfjA1  108.1.1.29 -> 108.1.1.99
UPDATE ecod_rep.domain SET f_id='108.1.1.98', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=118966 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '108.1.1.1';  -- e1jfjA2  108.1.1.1 -> 108.1.1.98
UPDATE ecod_rep.domain SET f_id='108.1.1.98', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=118995 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '108.1.1.1';  -- e1nyaA2  108.1.1.1 -> 108.1.1.98
UPDATE ecod_rep.domain SET f_id='108.1.1.97', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=119003 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '108.1.1.29';  -- e1omrA2  108.1.1.29 -> 108.1.1.97
UPDATE ecod_rep.domain SET f_id='108.1.1.97', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=119019 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '108.1.1.1';  -- e1qv0A1  108.1.1.1 -> 108.1.1.97
UPDATE ecod_rep.domain SET f_id='2004.1.1.415', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=119021 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2004.1.1.1';  -- e1r7rA6  2004.1.1.1 -> 2004.1.1.415
UPDATE ecod_rep.domain SET f_id='108.1.1.98', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=119032 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '108.1.1.29';  -- e1s6cA1  108.1.1.29 -> 108.1.1.98
UPDATE ecod_rep.domain SET f_id='108.1.1.97', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=119034 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '108.1.1.1';  -- e1s6iA1  108.1.1.1 -> 108.1.1.97
UPDATE ecod_rep.domain SET f_id='108.1.1.96', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=119035 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '108.1.1.1';  -- e1s6iA2  108.1.1.1 -> 108.1.1.96
UPDATE ecod_rep.domain SET f_id='108.1.1.103', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=119099 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '108.1.1.29';  -- e1xo5A1  108.1.1.29 -> 108.1.1.103
UPDATE ecod_rep.domain SET f_id='109.4.1.1389', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1291870 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.4.1.173';  -- e4hnwA1  109.4.1.173 -> 109.4.1.1389
UPDATE ecod_rep.domain SET f_id='109.4.1.1389', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1291871 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.4.1.173';  -- e4hnxA1  109.4.1.173 -> 109.4.1.1389
UPDATE ecod_rep.domain SET f_id='2490.3.1.3', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1291890 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2490.3.1.1';  -- e1vw4J1  2490.3.1.1 -> 2490.3.1.3
UPDATE ecod_rep.domain SET f_id='70.3.1.12', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1295900 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '70.3.1.3';  -- e3lazA1  70.3.1.3 -> 70.3.1.12
UPDATE ecod_rep.domain SET f_id='5.1.4.270', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1310587 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '5.1.4.1';  -- e4nsxA2  5.1.4.1 -> 5.1.4.270
UPDATE ecod_rep.domain SET f_id='2011.1.1.35', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1310610 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2011.1.1.12';  -- e4upcA1  2011.1.1.12 -> 2011.1.1.35
UPDATE ecod_rep.domain SET f_id='109.4.1.1332', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1316581 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.4.1.2';  -- e2ru4B1  109.4.1.2 -> 109.4.1.1332
UPDATE ecod_rep.domain SET f_id='206.1.1.70', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1322288 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '206.1.1.1';  -- e4qfgA1  206.1.1.1 -> 206.1.1.70
UPDATE ecod_rep.domain SET f_id='2004.1.1.414', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1389177 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2004.1.1.14';  -- e3izq11  2004.1.1.14 -> 2004.1.1.414
UPDATE ecod_rep.domain SET f_id='2486.1.1.15', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1407180 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2486.1.1.3';  -- e4rcnA6  2486.1.1.3 -> 2486.1.1.15
UPDATE ecod_rep.domain SET f_id='10.12.1.101', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1411386 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '10.12.1.9';  -- e3kv4A2  10.12.1.9 -> 10.12.1.101
UPDATE ecod_rep.domain SET f_id='206.1.1.73', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1411819 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '206.1.1.11';  -- e4uw0A1  206.1.1.11 -> 206.1.1.73
UPDATE ecod_rep.domain SET f_id='2004.1.1.500', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1447873 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2004.1.1.156';  -- e4rh7A4  2004.1.1.156 -> 2004.1.1.500
UPDATE ecod_rep.domain SET f_id='2004.1.1.429', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1447958 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2004.1.1.87';  -- e4ux3A1  2004.1.1.87 -> 2004.1.1.429
UPDATE ecod_rep.domain SET f_id='207.2.1.74', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=146239 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '207.2.1.10';  -- e3ml3A1  207.2.1.10 -> 207.2.1.74
UPDATE ecod_rep.domain SET f_id='2004.1.1.422', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=146895 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2004.1.1.73';  -- e3h2yA1  2004.1.1.73 -> 2004.1.1.422
UPDATE ecod_rep.domain SET f_id='109.3.1.164', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1482703 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.3.1.1';  -- e4rlvA1  109.3.1.1 -> 109.3.1.164
UPDATE ecod_rep.domain SET f_id='2004.1.1.417', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1487349 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2004.1.1.5';  -- e4rfsA1  2004.1.1.5 -> 2004.1.1.417
UPDATE ecod_rep.domain SET f_id='2004.1.1.445', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1487350 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2004.1.1.5';  -- e4rfsB1  2004.1.1.5 -> 2004.1.1.445
UPDATE ecod_rep.domain SET f_id='2004.1.1.473', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1495179 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2004.1.1.184';  -- e4pj3A3  2004.1.1.184 -> 2004.1.1.473
UPDATE ecod_rep.domain SET f_id='2003.1.5.182', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1514546 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2003.1.5.2';  -- e1qamA3  2003.1.5.2 -> 2003.1.5.182
UPDATE ecod_rep.domain SET f_id='2003.1.5.155', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1514550 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2003.1.5.2';  -- e1zq9A3  2003.1.5.2 -> 2003.1.5.155
UPDATE ecod_rep.domain SET f_id='11.1.1.862', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1539 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '11.1.1.2';  -- e2cspA1  11.1.1.2 -> 11.1.1.862
UPDATE ecod_rep.domain SET f_id='10.12.1.101', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1546393 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '10.12.1.9';  -- e3k2oB1  10.12.1.9 -> 10.12.1.101
UPDATE ecod_rep.domain SET f_id='206.1.1.70', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1549037 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '206.1.1.1';  -- e4lgdB1  206.1.1.1 -> 206.1.1.70
UPDATE ecod_rep.domain SET f_id='109.4.1.1299', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1555748 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.4.1.89';  -- e4yc7B1  109.4.1.89 -> 109.4.1.1299
UPDATE ecod_rep.domain SET f_id='109.4.1.1299', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1555749 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.4.1.89';  -- e4ydhA1  109.4.1.89 -> 109.4.1.1299
UPDATE ecod_rep.domain SET f_id='2004.1.1.433', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1556802 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2004.1.1.87';  -- e4ad8A1  2004.1.1.87 -> 2004.1.1.433
UPDATE ecod_rep.domain SET f_id='109.4.1.1264', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1563569 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.4.1.118';  -- e5aioA1  109.4.1.118 -> 109.4.1.1264
UPDATE ecod_rep.domain SET f_id='2004.1.1.417', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1565411 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2004.1.1.5';  -- e2vf7B2  2004.1.1.5 -> 2004.1.1.417
UPDATE ecod_rep.domain SET f_id='1.1.1.27', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1568669 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '1.1.1.1';  -- e2aprA2  1.1.1.1 -> 1.1.1.27
UPDATE ecod_rep.domain SET f_id='11.1.1.870', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1594 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '11.1.1.38';  -- e1f00I2  11.1.1.38 -> 11.1.1.870
UPDATE ecod_rep.domain SET f_id='5.1.4.259', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1676525 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '5.1.4.1';  -- e4ui9R1  5.1.4.1 -> 5.1.4.259
UPDATE ecod_rep.domain SET f_id='109.4.1.1264', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1676526 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.4.1.118';  -- e4ui9Y1  109.4.1.118 -> 109.4.1.1264
UPDATE ecod_rep.domain SET f_id='4.1.1.299', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1680001 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '4.1.1.3';  -- e4ytkA1  4.1.1.3 -> 4.1.1.299
UPDATE ecod_rep.domain SET f_id='2003.2.1.8', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1684052 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2003.2.1.1';  -- e1y5iA4  2003.2.1.1 -> 2003.2.1.8
UPDATE ecod_rep.domain SET f_id='1.2.1.4', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1693513 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '1.2.1.2';  -- e1ihmA2  1.2.1.2 -> 1.2.1.4
UPDATE ecod_rep.domain SET f_id='109.4.1.1555', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1713369 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.4.1.210';  -- e4zlhB1  109.4.1.210 -> 109.4.1.1555
UPDATE ecod_rep.domain SET f_id='2002.1.1.263', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1716688 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2002.1.1.23';  -- e4z87A1  2002.1.1.23 -> 2002.1.1.263
UPDATE ecod_rep.domain SET f_id='139.2.1.17', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1721533 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '139.2.1.7';  -- e4qo5A1  139.2.1.7 -> 139.2.1.17
UPDATE ecod_rep.domain SET f_id='206.1.1.72', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1723258 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '206.1.1.1';  -- e4xhhA1  206.1.1.1 -> 206.1.1.72
UPDATE ecod_rep.domain SET f_id='7516.1.1.106', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1723271 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '7516.1.1.2';  -- e5ekeC1  7516.1.1.2 -> 7516.1.1.106
UPDATE ecod_rep.domain SET f_id='2004.1.1.436', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1731077 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2004.1.1.137';  -- e4ww4B1  2004.1.1.137 -> 2004.1.1.436
UPDATE ecod_rep.domain SET f_id='1.1.9.35', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=177 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '1.1.9.9';  -- e1t62A1  1.1.9.9 -> 1.1.9.35
UPDATE ecod_rep.domain SET f_id='2004.1.1.514', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1779584 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2004.1.1.198';  -- e5dnyB1  2004.1.1.198 -> 2004.1.1.514
UPDATE ecod_rep.domain SET f_id='109.4.1.1620', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1779592 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.4.1.257';  -- e5frpA1  109.4.1.257 -> 109.4.1.1620
UPDATE ecod_rep.domain SET f_id='331.22.1.2', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1790181 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '331.22.1.1';  -- e5d0qC1  331.22.1.1 -> 331.22.1.2
UPDATE ecod_rep.domain SET f_id='207.1.1.323', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1820968 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '207.1.1.1';  -- e4j0mA1  207.1.1.1 -> 207.1.1.323
UPDATE ecod_rep.domain SET f_id='5.1.4.254', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1824186 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '5.1.4.1';  -- e5igoC1  5.1.4.1 -> 5.1.4.254
UPDATE ecod_rep.domain SET f_id='101.1.1.288', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1826881 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '101.1.1.3';  -- e2xb0X2  101.1.1.3 -> 101.1.1.288
UPDATE ecod_rep.domain SET f_id='109.4.1.1303', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1828347 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.4.1.83';  -- e5ctqA1  109.4.1.83 -> 109.4.1.1303
UPDATE ecod_rep.domain SET f_id='109.4.1.1303', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1830979 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.4.1.83';  -- e5jpzB1  109.4.1.83 -> 109.4.1.1303
UPDATE ecod_rep.domain SET f_id='109.3.1.176', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1841007 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.3.1.8';  -- e4bepB3  109.3.1.8 -> 109.3.1.176
UPDATE ecod_rep.domain SET f_id='109.4.1.1442', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1842535 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.4.1.955';  -- e2iw3A2  109.4.1.955 -> 109.4.1.1442
UPDATE ecod_rep.domain SET f_id='109.3.1.162', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1842586 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.3.1.1';  -- e5ja4D1  109.3.1.1 -> 109.3.1.162
UPDATE ecod_rep.domain SET f_id='7515.1.1.15', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1843702 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '7515.1.1.6';  -- e3q3qA1  7515.1.1.6 -> 7515.1.1.15
UPDATE ecod_rep.domain SET f_id='109.4.1.1463', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1843715 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.4.1.125';  -- e5dlqB1  109.4.1.125 -> 109.4.1.1463
UPDATE ecod_rep.domain SET f_id='2003.1.1.155', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=184980 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2003.1.1.36';  -- e2x58A2  2003.1.1.36 -> 2003.1.1.155
UPDATE ecod_rep.domain SET f_id='108.1.1.103', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1851163 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '108.1.1.1';  -- e2n8yA1  108.1.1.1 -> 108.1.1.103
UPDATE ecod_rep.domain SET f_id='207.1.1.130', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=185442 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '207.1.1.24';  -- e3ojaB1  207.1.1.24 -> 207.1.1.130
UPDATE ecod_rep.domain SET f_id='2488.1.1.19', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=185748 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2488.1.1.3';  -- e4fmwA1  2488.1.1.3 -> 2488.1.1.19
UPDATE ecod_rep.domain SET f_id='54.1.1.6', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=185755 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '54.1.1.1';  -- e4g1gA2  54.1.1.1 -> 54.1.1.6
UPDATE ecod_rep.domain SET f_id='2486.1.1.15', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1866768 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2486.1.1.3';  -- e5fifD2  2486.1.1.3 -> 2486.1.1.15
UPDATE ecod_rep.domain SET f_id='109.4.1.1255', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1870438 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.4.1.22';  -- e2vglA1  109.4.1.22 -> 109.4.1.1255
UPDATE ecod_rep.domain SET f_id='2003.1.9.8', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1870442 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2003.1.9.1';  -- e3cmmA1  2003.1.9.1 -> 2003.1.9.8
UPDATE ecod_rep.domain SET f_id='2004.1.1.431', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1870486 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2004.1.1.47';  -- e5g53C1  2004.1.1.47 -> 2004.1.1.431
UPDATE ecod_rep.domain SET f_id='205.1.1.41', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1916683 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '205.1.1.1';  -- e3mmcB1  205.1.1.1 -> 205.1.1.41
UPDATE ecod_rep.domain SET f_id='109.4.1.1333', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1933284 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.4.1.44';  -- e5f0pA1  109.4.1.44 -> 109.4.1.1333
UPDATE ecod_rep.domain SET f_id='5054.1.1.59', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1933321 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '5054.1.1.2';  -- e5tj6A1  5054.1.1.2 -> 5054.1.1.59
UPDATE ecod_rep.domain SET f_id='2490.3.1.3', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1951795 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2490.3.1.1';  -- e3j9zLH1  2490.3.1.1 -> 2490.3.1.3
UPDATE ecod_rep.domain SET f_id='207.1.1.144', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1954217 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '207.1.1.20';  -- e5hl3A2  207.1.1.20 -> 207.1.1.144
UPDATE ecod_rep.domain SET f_id='205.1.1.44', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2033698 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '205.1.1.17';  -- e2vpzB2  205.1.1.17 -> 205.1.1.44
UPDATE ecod_rep.domain SET f_id='109.4.1.1264', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2036593 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.4.1.118';  -- e5tqbB1  109.4.1.118 -> 109.4.1.1264
UPDATE ecod_rep.domain SET f_id='2004.1.1.480', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2044878 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2004.1.1.87';  -- e5h68A1  2004.1.1.87 -> 2004.1.1.480
UPDATE ecod_rep.domain SET f_id='2004.1.1.417', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2057238 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2004.1.1.5';  -- e5x3xA1  2004.1.1.5 -> 2004.1.1.417
UPDATE ecod_rep.domain SET f_id='207.1.1.210', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2066777 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '207.1.1.24';  -- e3wpcA1  207.1.1.24 -> 207.1.1.210
UPDATE ecod_rep.domain SET f_id='5.1.5.80', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2066817 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '5.1.5.1';  -- e5mzhB2  5.1.5.1 -> 5.1.5.80
UPDATE ecod_rep.domain SET f_id='1075.5.1.12', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2072472 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '1075.5.1.2';  -- e5t77A1  1075.5.1.2 -> 1075.5.1.12
UPDATE ecod_rep.domain SET f_id='2006.1.1.44', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2075048 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2006.1.1.1';  -- e1x42A3  2006.1.1.1 -> 2006.1.1.44
UPDATE ecod_rep.domain SET f_id='109.4.1.1287', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2080125 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.4.1.118';  -- e5jqyA1  109.4.1.118 -> 109.4.1.1287
UPDATE ecod_rep.domain SET f_id='109.4.1.1287', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2082640 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.4.1.118';  -- e5jzuA1  109.4.1.118 -> 109.4.1.1287
UPDATE ecod_rep.domain SET f_id='108.1.1.97', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2084847 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '108.1.1.29';  -- e5ve9B1  108.1.1.29 -> 108.1.1.97
UPDATE ecod_rep.domain SET f_id='108.1.1.102', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2084854 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '108.1.1.8';  -- e5w1fD1  108.1.1.8 -> 108.1.1.102
UPDATE ecod_rep.domain SET f_id='1.1.17.9', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=215 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '1.1.17.1';  -- e1arbA1  1.1.17.1 -> 1.1.17.9
UPDATE ecod_rep.domain SET f_id='5.1.3.136', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2192 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '5.1.3.20';  -- e2hqsA1  5.1.3.20 -> 5.1.3.136
UPDATE ecod_rep.domain SET f_id='5.1.3.134', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2198 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '5.1.3.26';  -- e1w8oA3  5.1.3.26 -> 5.1.3.134
UPDATE ecod_rep.domain SET f_id='5.1.3.134', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2200 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '5.1.3.26';  -- e1w0pA3  5.1.3.26 -> 5.1.3.134
UPDATE ecod_rep.domain SET f_id='5.1.4.253', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2206 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '5.1.4.1';  -- e1tbgA1  5.1.4.1 -> 5.1.4.253
UPDATE ecod_rep.domain SET f_id='5.1.4.310', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2218 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '5.1.4.1';  -- e2ovrB1  5.1.4.1 -> 5.1.4.310
UPDATE ecod_rep.domain SET f_id='7515.1.1.14', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=223848 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '7515.1.1.8';  -- e3iddA1  7515.1.1.8 -> 7515.1.1.14
UPDATE ecod_rep.domain SET f_id='70.3.1.11', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=223873 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '70.3.1.1';  -- e3n71A1  70.3.1.1 -> 70.3.1.11
UPDATE ecod_rep.domain SET f_id='11.1.1.1383', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=223972 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '11.1.1.200';  -- e4ak1A2  11.1.1.200 -> 11.1.1.1383
UPDATE ecod_rep.domain SET f_id='11.1.1.1157', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=223973 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '11.1.1.200';  -- e4ak1A3  11.1.1.200 -> 11.1.1.1157
UPDATE ecod_rep.domain SET f_id='11.1.1.1158', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=223974 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '11.1.1.200';  -- e4ak1A4  11.1.1.200 -> 11.1.1.1158
UPDATE ecod_rep.domain SET f_id='10.32.1.215', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=224055 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '10.32.1.10';  -- e4hg6B3  10.32.1.10 -> 10.32.1.215
UPDATE ecod_rep.domain SET f_id='702.1.1.9', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2266 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '702.1.1.1';  -- e2bibA1  702.1.1.1 -> 702.1.1.9
UPDATE ecod_rep.domain SET f_id='69.1.1.11', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2298 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '69.1.1.4';  -- e1dq3A1  69.1.1.4 -> 69.1.1.11
UPDATE ecod_rep.domain SET f_id='2007.1.20.2', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2617272 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2007.1.20.1';  -- e5ym0A1  2007.1.20.1 -> 2007.1.20.2
UPDATE ecod_rep.domain SET f_id='101.1.9.82', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2825 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '101.1.9.17';  -- e1r8dA1  101.1.9.17 -> 101.1.9.82
UPDATE ecod_rep.domain SET f_id='101.1.9.82', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2826 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '101.1.9.17';  -- e1q06A1  101.1.9.17 -> 101.1.9.82
UPDATE ecod_rep.domain SET f_id='103.1.1.84', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=3085 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '103.1.1.14';  -- e1wj7A1  103.1.1.14 -> 103.1.1.84
UPDATE ecod_rep.domain SET f_id='108.1.1.97', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=3138 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '108.1.1.1';  -- e1qx2A1  108.1.1.1 -> 108.1.1.97
UPDATE ecod_rep.domain SET f_id='108.1.1.102', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=3139 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '108.1.1.8';  -- e1k8uA1  108.1.1.8 -> 108.1.1.102
UPDATE ecod_rep.domain SET f_id='108.1.1.99', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=3146 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '108.1.1.1';  -- e2opoA1  108.1.1.1 -> 108.1.1.99
UPDATE ecod_rep.domain SET f_id='108.1.1.99', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=3148 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '108.1.1.29';  -- e2pvbA1  108.1.1.29 -> 108.1.1.99
UPDATE ecod_rep.domain SET f_id='108.1.1.96', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=3152 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '108.1.1.29';  -- e1ozsA1  108.1.1.29 -> 108.1.1.96
UPDATE ecod_rep.domain SET f_id='108.1.1.97', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=3155 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '108.1.1.1';  -- e1c7vA1  108.1.1.1 -> 108.1.1.97
UPDATE ecod_rep.domain SET f_id='108.1.1.96', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=3161 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '108.1.1.29';  -- e1oqpA1  108.1.1.29 -> 108.1.1.96
UPDATE ecod_rep.domain SET f_id='108.1.1.96', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=3163 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '108.1.1.29';  -- e2obhA2  108.1.1.29 -> 108.1.1.96
UPDATE ecod_rep.domain SET f_id='108.1.1.97', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=3174 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '108.1.1.1';  -- e1tizA1  108.1.1.1 -> 108.1.1.97
UPDATE ecod_rep.domain SET f_id='108.1.1.121', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=3190 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '108.1.1.29';  -- e1snlA1  108.1.1.29 -> 108.1.1.121
UPDATE ecod_rep.domain SET f_id='198.1.1.13', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=3263 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '198.1.1.1';  -- e1l9lA1  198.1.1.1 -> 198.1.1.13
UPDATE ecod_rep.domain SET f_id='198.1.1.10', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=3264 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '198.1.1.2';  -- e2gtgA1  198.1.1.2 -> 198.1.1.10
UPDATE ecod_rep.domain SET f_id='5069.1.1.54', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=4234 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '5069.1.1.1';  -- e1ppjC2  5069.1.1.1 -> 5069.1.1.54
UPDATE ecod_rep.domain SET f_id='109.3.1.165', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=4516 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.3.1.1';  -- e1n11A1  109.3.1.1 -> 109.3.1.165
UPDATE ecod_rep.domain SET f_id='109.3.1.162', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=4520 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.3.1.8';  -- e1iknD1  109.3.1.8 -> 109.3.1.162
UPDATE ecod_rep.domain SET f_id='109.4.1.1793', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=4537 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.4.1.109';  -- e1ouvA1  109.4.1.109 -> 109.4.1.1793
UPDATE ecod_rep.domain SET f_id='109.4.1.1288', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=4550 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.4.1.5';  -- e1elwA1  109.4.1.5 -> 109.4.1.1288
UPDATE ecod_rep.domain SET f_id='109.4.1.1394', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=4551 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.4.1.5';  -- e1elrA1  109.4.1.5 -> 109.4.1.1394
UPDATE ecod_rep.domain SET f_id='109.4.1.1263', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=4554 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.4.1.5';  -- e1fchA1  109.4.1.5 -> 109.4.1.1263
UPDATE ecod_rep.domain SET f_id='109.4.1.3572', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=4560 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.4.1.5';  -- e1w3bA1  109.4.1.5 -> 109.4.1.3572
UPDATE ecod_rep.domain SET f_id='109.4.1.1264', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=4562 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.4.1.95';  -- e1xnfA1  109.4.1.95 -> 109.4.1.1264
UPDATE ecod_rep.domain SET f_id='109.4.1.1316', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=4575 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.4.1.83';  -- e2ooeA1  109.4.1.83 -> 109.4.1.1316
UPDATE ecod_rep.domain SET f_id='109.4.1.1265', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=4604 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.4.1.16';  -- e1m8zA1  109.4.1.16 -> 109.4.1.1265
UPDATE ecod_rep.domain SET f_id='109.4.1.1299', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=4616 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.4.1.89';  -- e2bnxA1  109.4.1.89 -> 109.4.1.1299
UPDATE ecod_rep.domain SET f_id='108.1.1.99', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=48960 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '108.1.1.1';  -- e2opoB1  108.1.1.1 -> 108.1.1.99
UPDATE ecod_rep.domain SET f_id='5054.1.1.59', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=4922 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '5054.1.1.2';  -- e1orqC1  5054.1.1.2 -> 5054.1.1.59
UPDATE ecod_rep.domain SET f_id='315.1.1.9', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=4936 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '315.1.1.5';  -- e2aalA1  315.1.1.5 -> 315.1.1.9
UPDATE ecod_rep.domain SET f_id='304.9.1.77', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=5049 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '304.9.1.1';  -- e1wg5A1  304.9.1.1 -> 304.9.1.77
UPDATE ecod_rep.domain SET f_id='304.9.1.77', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=5091 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '304.9.1.1';  -- e1welA1  304.9.1.1 -> 304.9.1.77
UPDATE ecod_rep.domain SET f_id='304.9.1.77', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=5092 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '304.9.1.1';  -- e2cpyA1  304.9.1.1 -> 304.9.1.77
UPDATE ecod_rep.domain SET f_id='304.60.1.8', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=5389 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '304.60.1.2';  -- e1zavA1  304.60.1.2 -> 304.60.1.8
UPDATE ecod_rep.domain SET f_id='205.1.1.80', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=5472 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '205.1.1.1';  -- e1h98A1  205.1.1.1 -> 205.1.1.80
UPDATE ecod_rep.domain SET f_id='205.1.1.41', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=5474 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '205.1.1.1';  -- e1xerA1  205.1.1.1 -> 205.1.1.41
UPDATE ecod_rep.domain SET f_id='205.1.1.42', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=5478 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '205.1.1.16';  -- e3c8yA3  205.1.1.16 -> 205.1.1.42
UPDATE ecod_rep.domain SET f_id='205.1.1.41', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=5479 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '205.1.1.1';  -- e1hfeL2  205.1.1.1 -> 205.1.1.41
UPDATE ecod_rep.domain SET f_id='221.4.1.23', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=6236 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '221.4.1.1';  -- e1q33A1  221.4.1.1 -> 221.4.1.23
UPDATE ecod_rep.domain SET f_id='244.4.1.3', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=6738 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '244.4.1.2';  -- e1ublL5  244.4.1.2 -> 244.4.1.3
UPDATE ecod_rep.domain SET f_id='244.4.1.3', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=6740 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '244.4.1.2';  -- e1wuiL3  244.4.1.2 -> 244.4.1.3
UPDATE ecod_rep.domain SET f_id='244.4.1.3', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=6742 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '244.4.1.2';  -- e1cc1L3  244.4.1.2 -> 244.4.1.3
UPDATE ecod_rep.domain SET f_id='206.1.1.70', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=7063 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '206.1.1.1';  -- e2gfsA1  206.1.1.1 -> 206.1.1.70
UPDATE ecod_rep.domain SET f_id='206.1.1.73', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=7065 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '206.1.1.1';  -- e3bqcA1  206.1.1.1 -> 206.1.1.73
UPDATE ecod_rep.domain SET f_id='206.1.1.70', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=7073 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '206.1.1.1';  -- e1kobA1  206.1.1.1 -> 206.1.1.70
UPDATE ecod_rep.domain SET f_id='206.1.1.72', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=7078 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '206.1.1.1';  -- e1yhwA1  206.1.1.1 -> 206.1.1.72
UPDATE ecod_rep.domain SET f_id='206.1.1.70', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=7079 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '206.1.1.1';  -- e1o6yA1  206.1.1.1 -> 206.1.1.70
UPDATE ecod_rep.domain SET f_id='206.1.1.71', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=7095 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '206.1.1.1';  -- e1xwsA1  206.1.1.1 -> 206.1.1.71
UPDATE ecod_rep.domain SET f_id='206.1.1.70', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=7096 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '206.1.1.1';  -- e1s9jA1  206.1.1.1 -> 206.1.1.70
UPDATE ecod_rep.domain SET f_id='206.1.1.70', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=7099 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '206.1.1.1';  -- e2jflA1  206.1.1.1 -> 206.1.1.70
UPDATE ecod_rep.domain SET f_id='207.1.1.130', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=7192 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '207.1.1.24';  -- e1oznA1  207.1.1.24 -> 207.1.1.130
UPDATE ecod_rep.domain SET f_id='207.1.1.140', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=7194 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '207.1.1.24';  -- e1xkuA1  207.1.1.24 -> 207.1.1.140
UPDATE ecod_rep.domain SET f_id='207.1.1.197', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=7198 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '207.1.1.29';  -- e1dceA3  207.1.1.29 -> 207.1.1.197
UPDATE ecod_rep.domain SET f_id='208.1.1.20', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=7243 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '208.1.1.1';  -- e2oi5A1  208.1.1.1 -> 208.1.1.20
UPDATE ecod_rep.domain SET f_id='880.1.1.4', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=7316 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '880.1.1.1';  -- e3bznA1  880.1.1.1 -> 880.1.1.4
UPDATE ecod_rep.domain SET f_id='219.1.1.111', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=7388 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '219.1.1.13';  -- e1x3zA1  219.1.1.13 -> 219.1.1.111
UPDATE ecod_rep.domain SET f_id='219.1.1.111', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=7389 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '219.1.1.13';  -- e2f4mA1  219.1.1.13 -> 219.1.1.111
UPDATE ecod_rep.domain SET f_id='235.1.1.31', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=7424 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '235.1.1.9';  -- e1gbsA1  235.1.1.9 -> 235.1.1.31
UPDATE ecod_rep.domain SET f_id='235.1.1.32', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=7425 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '235.1.1.9';  -- e1qsaA2  235.1.1.9 -> 235.1.1.32
UPDATE ecod_rep.domain SET f_id='237.1.1.33', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=7437 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '237.1.1.7';  -- e1prtA1  237.1.1.7 -> 237.1.1.33
UPDATE ecod_rep.domain SET f_id='376.1.3.56', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=8128 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '376.1.3.1';  -- e1wepA1  376.1.3.1 -> 376.1.3.56
UPDATE ecod_rep.domain SET f_id='389.1.1.97', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=8457 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '389.1.1.17';  -- e2p3uA1  389.1.1.17 -> 389.1.1.97
UPDATE ecod_rep.domain SET f_id='389.1.1.101', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=8462 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '389.1.1.1';  -- e1k36A1  389.1.1.1 -> 389.1.1.101
UPDATE ecod_rep.domain SET f_id='389.1.1.99', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=8463 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '389.1.1.1';  -- e1xdtR1  389.1.1.1 -> 389.1.1.99
UPDATE ecod_rep.domain SET f_id='2002.1.1.263', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=8696 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2002.1.1.23';  -- e1zfjA2  2002.1.1.23 -> 2002.1.1.263
UPDATE ecod_rep.domain SET f_id='2002.1.1.266', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=8800 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2002.1.1.60';  -- e1a0cA1  2002.1.1.60 -> 2002.1.1.266
UPDATE ecod_rep.domain SET f_id='2003.1.1.152', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9036 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2003.1.1.72';  -- e1ek6A1  2003.1.1.72 -> 2003.1.1.152
UPDATE ecod_rep.domain SET f_id='2003.1.1.141', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9044 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2003.1.1.72';  -- e1orrA1  2003.1.1.72 -> 2003.1.1.141
UPDATE ecod_rep.domain SET f_id='2003.1.1.141', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9093 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2003.1.1.72';  -- e2b69A1  2003.1.1.72 -> 2003.1.1.141
UPDATE ecod_rep.domain SET f_id='2003.1.1.148', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9109 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2003.1.1.3';  -- e1yo6A1  2003.1.1.3 -> 2003.1.1.148
UPDATE ecod_rep.domain SET f_id='2003.1.1.147', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9183 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2003.1.1.27';  -- e2g5cA2  2003.1.1.27 -> 2003.1.1.147
UPDATE ecod_rep.domain SET f_id='2003.1.1.147', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9184 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2003.1.1.27';  -- e2f1kA2  2003.1.1.27 -> 2003.1.1.147
UPDATE ecod_rep.domain SET f_id='2003.1.2.60', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9227 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2003.1.2.12';  -- e1ryiA2  2003.1.2.12 -> 2003.1.2.60
UPDATE ecod_rep.domain SET f_id='2003.1.2.73', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9230 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2003.1.2.17';  -- e2iidA2  2003.1.2.17 -> 2003.1.2.73
UPDATE ecod_rep.domain SET f_id='2003.1.2.99', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9237 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2003.1.2.15';  -- e2vouA2  2003.1.2.15 -> 2003.1.2.99
UPDATE ecod_rep.domain SET f_id='2003.1.2.69', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9280 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2003.1.2.29';  -- e1w4xA1  2003.1.2.29 -> 2003.1.2.69
UPDATE ecod_rep.domain SET f_id='2003.1.3.15', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9291 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2003.1.3.5';  -- e1ps9A3  2003.1.3.5 -> 2003.1.3.15
UPDATE ecod_rep.domain SET f_id='2003.1.5.179', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9346 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2003.1.5.82';  -- e1l3iA1  2003.1.5.82 -> 2003.1.5.179
UPDATE ecod_rep.domain SET f_id='2003.1.5.153', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9355 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2003.1.5.4';  -- e1jg1A1  2003.1.5.4 -> 2003.1.5.153
UPDATE ecod_rep.domain SET f_id='2003.1.5.153', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9356 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2003.1.5.4';  -- e1i1nA1  2003.1.5.4 -> 2003.1.5.153
UPDATE ecod_rep.domain SET f_id='2003.1.5.154', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9388 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2003.1.5.66';  -- e1xxlA1  2003.1.5.66 -> 2003.1.5.154
UPDATE ecod_rep.domain SET f_id='2003.1.5.151', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9393 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2003.1.5.81';  -- e1y8cA1  2003.1.5.81 -> 2003.1.5.151
UPDATE ecod_rep.domain SET f_id='2003.1.5.151', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9395 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2003.1.5.81';  -- e1wznA1  2003.1.5.81 -> 2003.1.5.151
UPDATE ecod_rep.domain SET f_id='2003.1.5.201', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9406 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2003.1.5.82';  -- e2gh1A1  2003.1.5.82 -> 2003.1.5.201
UPDATE ecod_rep.domain SET f_id='2007.6.1.17', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9485 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2007.6.1.12';  -- e1nriA1  2007.6.1.12 -> 2007.6.1.17
UPDATE ecod_rep.domain SET f_id='2004.1.1.414', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9600 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2004.1.1.14';  -- e2bv3A5  2004.1.1.14 -> 2004.1.1.414
UPDATE ecod_rep.domain SET f_id='2004.1.1.414', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9601 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2004.1.1.14';  -- e2dy1A5  2004.1.1.14 -> 2004.1.1.414
UPDATE ecod_rep.domain SET f_id='2004.1.1.414', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9602 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2004.1.1.14';  -- e1n0uA5  2004.1.1.14 -> 2004.1.1.414
UPDATE ecod_rep.domain SET f_id='2004.1.1.474', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9605 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2004.1.1.73';  -- e1wf3A2  2004.1.1.73 -> 2004.1.1.474
UPDATE ecod_rep.domain SET f_id='2004.1.1.414', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9608 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2004.1.1.73';  -- e1mkyA3  2004.1.1.73 -> 2004.1.1.414
UPDATE ecod_rep.domain SET f_id='2004.1.1.597', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9623 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2004.1.1.74';  -- e1wxqA2  2004.1.1.74 -> 2004.1.1.597
UPDATE ecod_rep.domain SET f_id='2004.1.1.414', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9624 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2004.1.1.73';  -- e2cxxA1  2004.1.1.73 -> 2004.1.1.414
UPDATE ecod_rep.domain SET f_id='2004.1.1.414', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9626 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2004.1.1.14';  -- e1zunB3  2004.1.1.14 -> 2004.1.1.414
UPDATE ecod_rep.domain SET f_id='2004.1.1.417', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9677 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2004.1.1.5';  -- e1b0uA1  2004.1.1.5 -> 2004.1.1.417
UPDATE ecod_rep.domain SET f_id='2004.1.1.481', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9688 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2004.1.1.87';  -- e1w1wA1  2004.1.1.87 -> 2004.1.1.481
UPDATE ecod_rep.domain SET f_id='2004.1.1.417', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9693 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2004.1.1.5';  -- e1vplA1  2004.1.1.5 -> 2004.1.1.417
UPDATE ecod_rep.domain SET f_id='2004.1.1.417', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9695 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2004.1.1.5';  -- e3dhwC2  2004.1.1.5 -> 2004.1.1.417
UPDATE ecod_rep.domain SET f_id='2004.1.1.508', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9698 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2004.1.1.195';  -- e1uaaA2  2004.1.1.195 -> 2004.1.1.508
UPDATE ecod_rep.domain SET f_id='2004.1.1.489', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9709 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2004.1.1.120';  -- e1c4oA1  2004.1.1.120 -> 2004.1.1.489
UPDATE ecod_rep.domain SET f_id='2004.1.1.462', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9749 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2004.1.1.1';  -- e1qvrC4  2004.1.1.1 -> 2004.1.1.462
UPDATE ecod_rep.domain SET f_id='2004.1.1.415', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9774 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2004.1.1.1';  -- e1iqpA3  2004.1.1.1 -> 2004.1.1.415
UPDATE ecod_rep.domain SET f_id='2004.1.1.420', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9777 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2004.1.1.1';  -- e1lv7A2  2004.1.1.1 -> 2004.1.1.420
UPDATE ecod_rep.domain SET f_id='2005.1.1.47', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9835 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2005.1.1.18';  -- e1gpmA2  2005.1.1.18 -> 2005.1.1.47
UPDATE ecod_rep.domain SET f_id='2006.1.1.44', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9871 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2006.1.1.1';  -- e2gfhA1  2006.1.1.1 -> 2006.1.1.44
UPDATE ecod_rep.domain SET f_id='2006.1.1.46', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9877 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2006.1.1.1';  -- e1zd3A1  2006.1.1.1 -> 2006.1.1.46
UPDATE ecod_rep.domain SET f_id='2006.1.1.44', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9878 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2006.1.1.1';  -- e2b0cA1  2006.1.1.1 -> 2006.1.1.44
UPDATE ecod_rep.domain SET f_id='2006.1.1.44', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9910 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2006.1.1.15';  -- e2o2xA1  2006.1.1.15 -> 2006.1.1.44
UPDATE ecod_rep.domain SET f_id='2006.1.1.44', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9911 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2006.1.1.15';  -- e2gmwA1  2006.1.1.15 -> 2006.1.1.44
UPDATE ecod_rep.domain SET f_id='2007.2.1.9', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9996 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2007.2.1.1';  -- e1f4pA1  2007.2.1.1 -> 2007.2.1.9
-- ----- TIER 4: STRANDS OLD F-GROUP (empties an active F-group of reps) -- HOLD/REVIEW -----
UPDATE ecod_rep.domain SET f_id='11.1.4.97', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1005465 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '11.1.4.39';  -- e2xidB4  11.1.4.39 -> 11.1.4.97
UPDATE ecod_rep.domain SET f_id='7579.1.1.97', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=10820 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '7579.1.1.31';  -- e1qo7A1  7579.1.1.31 -> 7579.1.1.97
UPDATE ecod_rep.domain SET f_id='7579.1.1.118', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=10862 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '7579.1.1.32';  -- e2jbwA1  7579.1.1.32 -> 7579.1.1.118
UPDATE ecod_rep.domain SET f_id='109.35.1.10', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1124192 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.35.1.1';  -- e4adyA2  109.35.1.1 -> 109.35.1.10
UPDATE ecod_rep.domain SET f_id='109.4.1.2094', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1126564 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.4.1.255';  -- e4bujF1  109.4.1.255 -> 109.4.1.2094
UPDATE ecod_rep.domain SET f_id='109.4.1.1384', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1147811 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.4.1.240';  -- e4g23A1  109.4.1.240 -> 109.4.1.1384
UPDATE ecod_rep.domain SET f_id='108.1.1.98', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=119101 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '108.1.1.3';  -- e1y1xA1  108.1.1.3 -> 108.1.1.98
UPDATE ecod_rep.domain SET f_id='5.1.4.280', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1310586 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '5.1.4.39';  -- e4nsxA1  5.1.4.39 -> 5.1.4.280
UPDATE ecod_rep.domain SET f_id='109.4.1.1350', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1348265 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.4.1.117';  -- e4pjuA1  109.4.1.117 -> 109.4.1.1350
UPDATE ecod_rep.domain SET f_id='3235.1.1.26', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=147022 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '3235.1.1.1';  -- e3p8cD1  3235.1.1.1 -> 3235.1.1.26
UPDATE ecod_rep.domain SET f_id='109.4.1.1294', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1487475 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.4.1.7';  -- e4rg6A1  109.4.1.7 -> 109.4.1.1294
UPDATE ecod_rep.domain SET f_id='4.1.1.314', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1551400 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '4.1.1.146';  -- e3j6bQ1  4.1.1.146 -> 4.1.1.314
UPDATE ecod_rep.domain SET f_id='109.4.1.1398', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1673889 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.4.1.185';  -- e4ui9O2  109.4.1.185 -> 109.4.1.1398
UPDATE ecod_rep.domain SET f_id='109.35.1.11', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1676515 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.35.1.1';  -- e4ui9A2  109.35.1.1 -> 109.35.1.11
UPDATE ecod_rep.domain SET f_id='5.1.4.283', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1676519 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '5.1.4.39';  -- e4ui9I1  5.1.4.39 -> 5.1.4.283
UPDATE ecod_rep.domain SET f_id='2003.1.1.260', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1716676 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2003.1.1.71';  -- e3nklB1  2003.1.1.71 -> 2003.1.1.260
UPDATE ecod_rep.domain SET f_id='109.4.1.1798', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1718749 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.4.1.99';  -- e5dseC1  109.4.1.99 -> 109.4.1.1798
UPDATE ecod_rep.domain SET f_id='109.4.1.1315', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1722652 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.4.1.198';  -- e5a6cB1  109.4.1.198 -> 109.4.1.1315
UPDATE ecod_rep.domain SET f_id='1033.1.1.3', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1723255 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '1033.1.1.1';  -- e4r04A5  1033.1.1.1 -> 1033.1.1.3
UPDATE ecod_rep.domain SET f_id='101.1.2.530', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1734343 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '101.1.2.93';  -- e2wteA2  101.1.2.93 -> 101.1.2.530
UPDATE ecod_rep.domain SET f_id='331.3.1.50', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1806521 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '331.3.1.8';  -- e3tgoC1  331.3.1.8 -> 331.3.1.50
UPDATE ecod_rep.domain SET f_id='109.4.1.1594', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1820986 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.4.1.298';  -- e5dfzB2  109.4.1.298 -> 109.4.1.1594
UPDATE ecod_rep.domain SET f_id='2004.1.1.428', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1840991 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2004.1.1.24';  -- e3mwyW4  2004.1.1.24 -> 2004.1.1.428
UPDATE ecod_rep.domain SET f_id='130.1.1.33', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=184739 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '130.1.1.9';  -- e2kngA1  130.1.1.9 -> 130.1.1.33
UPDATE ecod_rep.domain SET f_id='5.1.7.4', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=185234 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '5.1.7.2';  -- e3f6kA1  5.1.7.2 -> 5.1.7.4
UPDATE ecod_rep.domain SET f_id='4.1.1.391', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=185635 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '4.1.1.67';  -- e4a53A1  4.1.1.67 -> 4.1.1.391
UPDATE ecod_rep.domain SET f_id='3386.1.1.4', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=185943 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '3386.1.1.1';  -- e1qexA3  3386.1.1.1 -> 3386.1.1.4
UPDATE ecod_rep.domain SET f_id='2004.1.1.428', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1866774 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2004.1.1.24';  -- e5hzrA2  2004.1.1.24 -> 2004.1.1.428
UPDATE ecod_rep.domain SET f_id='2003.1.5.152', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1885547 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2003.1.5.21';  -- e5kokA1  2003.1.5.21 -> 2003.1.5.152
UPDATE ecod_rep.domain SET f_id='109.4.1.1259', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1889998 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.4.1.207';  -- e5d08A3  109.4.1.207 -> 109.4.1.1259
UPDATE ecod_rep.domain SET f_id='109.4.1.1739', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1891442 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.4.1.183';  -- e5t8vA1  109.4.1.183 -> 109.4.1.1739
UPDATE ecod_rep.domain SET f_id='141.1.1.33', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=1933300 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '141.1.1.6';  -- e5h9dC1  141.1.1.6 -> 141.1.1.33
UPDATE ecod_rep.domain SET f_id='109.4.1.1304', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2095496 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.4.1.198';  -- e5o01A1  109.4.1.198 -> 109.4.1.1304
UPDATE ecod_rep.domain SET f_id='5.1.3.117', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2187 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '5.1.3.6';  -- e1zgkA1  5.1.3.6 -> 5.1.3.117
UPDATE ecod_rep.domain SET f_id='5.1.4.291', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2205 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '5.1.4.10';  -- e1k3iA3  5.1.4.10 -> 5.1.4.291
UPDATE ecod_rep.domain SET f_id='5.1.4.257', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2224 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '5.1.4.13';  -- e1tyeA1  5.1.4.13 -> 5.1.4.257
UPDATE ecod_rep.domain SET f_id='5.1.4.405', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2225 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '5.1.4.64';  -- e1l0qA2  5.1.4.64 -> 5.1.4.405
UPDATE ecod_rep.domain SET f_id='5.1.4.406', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2233 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '5.1.4.52';  -- e2ebsA1  5.1.4.52 -> 5.1.4.406
UPDATE ecod_rep.domain SET f_id='5.1.4.279', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2235 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '5.1.4.29';  -- e1k32A3  5.1.4.29 -> 5.1.4.279
UPDATE ecod_rep.domain SET f_id='5.1.4.255', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2240 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '5.1.4.7';  -- e1a12A1  5.1.4.7 -> 5.1.4.255
UPDATE ecod_rep.domain SET f_id='5.1.4.620', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2323934 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '5.1.4.6';  -- e5teeA1  5.1.4.6 -> 5.1.4.620
UPDATE ecod_rep.domain SET f_id='5.1.4.285', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2323935 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '5.1.4.6';  -- e5teeA2  5.1.4.6 -> 5.1.4.285
UPDATE ecod_rep.domain SET f_id='2.1.1.243', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2323987 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2.1.1.66';  -- e5w2lB1  2.1.1.66 -> 2.1.1.243
UPDATE ecod_rep.domain SET f_id='396.3.1.7', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2526320 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '396.3.1.2';  -- e6iczZ1  396.3.1.2 -> 396.3.1.7
UPDATE ecod_rep.domain SET f_id='101.1.2.493', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2750 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '101.1.2.13';  -- e1ldjA2  101.1.2.13 -> 101.1.2.493
UPDATE ecod_rep.domain SET f_id='101.1.2.493', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2751 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '101.1.2.13';  -- e2hyeC2  101.1.2.13 -> 101.1.2.493
UPDATE ecod_rep.domain SET f_id='101.1.9.82', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=2827 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '101.1.9.14';  -- e1q08A1  101.1.9.14 -> 101.1.9.82
UPDATE ecod_rep.domain SET f_id='198.1.1.26', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=3262 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '198.1.1.3';  -- e1nklA1  198.1.1.3 -> 198.1.1.26
UPDATE ecod_rep.domain SET f_id='601.23.1.4', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=3761 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '601.23.1.1';  -- e1ewqA1  601.23.1.1 -> 601.23.1.4
UPDATE ecod_rep.domain SET f_id='601.23.1.4', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=3762 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '601.23.1.1';  -- e1wb9A1  601.23.1.1 -> 601.23.1.4
UPDATE ecod_rep.domain SET f_id='109.4.1.1345', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=4578 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.4.1.55';  -- e1qgrA1  109.4.1.55 -> 109.4.1.1345
UPDATE ecod_rep.domain SET f_id='109.4.1.1345', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=4579 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.4.1.55';  -- e2bptA1  109.4.1.55 -> 109.4.1.1345
UPDATE ecod_rep.domain SET f_id='109.4.1.1313', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=4580 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.4.1.204';  -- e1qbkB1  109.4.1.204 -> 109.4.1.1313
UPDATE ecod_rep.domain SET f_id='109.4.1.1321', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=4585 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.4.1.35';  -- e1b3uA1  109.4.1.35 -> 109.4.1.1321
UPDATE ecod_rep.domain SET f_id='109.4.1.1501', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=4586 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.4.1.34';  -- e1u6gC1  109.4.1.34 -> 109.4.1.1501
UPDATE ecod_rep.domain SET f_id='109.4.1.1283', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=4606 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.4.1.207';  -- e1oyzA1  109.4.1.207 -> 109.4.1.1283
UPDATE ecod_rep.domain SET f_id='109.4.1.1283', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=4607 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '109.4.1.207';  -- e1te4A1  109.4.1.207 -> 109.4.1.1283
UPDATE ecod_rep.domain SET f_id='4.1.1.295', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=586 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '4.1.1.95';  -- e1vqoT1  4.1.1.95 -> 4.1.1.295
UPDATE ecod_rep.domain SET f_id='4.23.1.2', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=608 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '4.23.1.1';  -- e2qi2A1  4.23.1.1 -> 4.23.1.2
UPDATE ecod_rep.domain SET f_id='4.23.1.2', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=609 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '4.23.1.1';  -- e2vgnA1  4.23.1.1 -> 4.23.1.2
UPDATE ecod_rep.domain SET f_id='207.1.1.165', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=7191 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '207.1.1.11';  -- e1p9aG1  207.1.1.11 -> 207.1.1.165
UPDATE ecod_rep.domain SET f_id='207.1.1.164', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=7193 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '207.1.1.11';  -- e1w8aA1  207.1.1.11 -> 207.1.1.164
UPDATE ecod_rep.domain SET f_id='207.9.1.7', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=7227 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '207.9.1.2';  -- e2bm5A1  207.9.1.2 -> 207.9.1.7
UPDATE ecod_rep.domain SET f_id='2500.1.1.7', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9015 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2500.1.1.5';  -- e1hk8A1  2500.1.1.5 -> 2500.1.1.7
UPDATE ecod_rep.domain SET f_id='2003.1.3.15', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9290 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2003.1.3.3';  -- e1djqA3  2003.1.3.3 -> 2003.1.3.15
UPDATE ecod_rep.domain SET f_id='2003.1.3.15', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9294 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2003.1.3.3';  -- e1gteA5  2003.1.3.3 -> 2003.1.3.15
UPDATE ecod_rep.domain SET f_id='2003.1.5.152', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9382 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2003.1.5.21';  -- e2fk8A1  2003.1.5.21 -> 2003.1.5.152
UPDATE ecod_rep.domain SET f_id='2004.1.1.419', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9644 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2004.1.1.20';  -- e2afhE1  2004.1.1.20 -> 2004.1.1.419
UPDATE ecod_rep.domain SET f_id='2004.1.1.428', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9727 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2004.1.1.24';  -- e1z3iX1  2004.1.1.24 -> 2004.1.1.428
UPDATE ecod_rep.domain SET f_id='2005.1.1.54', manual_rep=true, last_modified_release_id=4 WHERE ecod_uid=9843 AND manual_rep IS TRUE AND f_id IS NOT DISTINCT FROM '2005.1.1.16';  -- e2d13A1  2005.1.1.16 -> 2005.1.1.54

-- =============================================================================
-- VERIFICATION (runs inside the transaction)
-- =============================================================================

-- How many of the 456 rows actually changed f_id (guards may no-op some):
SELECT count(*) AS rows_reassigned
FROM _before b JOIN ecod_rep.domain d USING (ecod_uid)
WHERE d.f_id IS DISTINCT FROM b.old_f_id;

-- Of the 344 target commons F-groups, how many now have a manual rep in ecod_rep:
SELECT
  count(*) AS target_fgroups,
  count(*) FILTER (WHERE EXISTS (
    SELECT 1 FROM ecod_rep.domain d
    WHERE d.f_id=t.f_id AND d.manual_rep IS TRUE)) AS now_have_manual_rep
FROM _targets t;

-- NEW repless F-groups created as a side effect (should equal the T4 count, 61,
-- if T4 statements are included; 0 if you stripped T4 before running):
WITH moved_from AS (SELECT DISTINCT old_f_id FROM _before WHERE old_f_id IS NOT NULL)
SELECT count(*) AS old_fgroups_now_repless
FROM moved_from m
JOIN ecod_rep.cluster c ON c.id=m.old_f_id AND c.type='F' AND c.is_deprecated IS NOT TRUE
WHERE NOT EXISTS (
  SELECT 1 FROM ecod_rep.domain d
  WHERE d.f_id=m.old_f_id AND (d.manual_rep IS TRUE OR d.provisional_manual_rep IS TRUE));

-- -----------------------------------------------------------------------------
-- OPTIONAL audit log (uncomment to record the reassignments):
-- INSERT INTO ecod_rep.domain_assignment_log (domain_uid, assignment_type, old_value, new_value)
-- SELECT d.uid, 'f_group_reassign_manual_rep', b.old_f_id, d.f_id
-- FROM _before b JOIN ecod_rep.domain d USING (ecod_uid)
-- WHERE d.f_id IS DISTINCT FROM b.old_f_id;
-- -----------------------------------------------------------------------------

-- SAFETY: default is ROLLBACK. Change to COMMIT once the counts look right.
ROLLBACK;
-- COMMIT;
