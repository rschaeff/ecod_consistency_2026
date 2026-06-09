# Session 2026-06-08 — v294 repless-F-group remediation (ecod_rep)

Closure record for the day's work. Detailed write-ups: propagation in
`FGROUP_RECONCILIATION_FINDINGS_20260605.md`; rep-selection in `REP_SELECTION_PROJECT_SKETCH.md`.

## Headline
**Repless active ecod_rep F-groups: 14,255 → 107** (99.2% reduction) — every F-group with no
manual/provisional representative now has one, except a 107-group special-case residue.

## What was done (all on **dione** `ecod_protein`, schemas `ecod_rep`/`ecod_commons`)
All changes via the audited request→approve→implement pipeline, dry-run-then-commit, per-batch
`pg_dump` backup. Provenance is the `requested_by` tag in `ecod_rep.domain_assignment_log`:

| batch | tag | rows | what |
|---|---|---|---|
| Clean reassignments | `v294_reconcile` | 362 | tranche-1 Pfam-validated movers |
| Stranding (16) | `v294_strand` | 22 | 15 reassign + 7 re-seed (+6 F-groups deprecated, in hierarchy_change_history) |
| Tranche-2 cut_ga | `v294_t2` | 252 | non-manual rep propagation |
| Tranche-2 relaxed | `v294_t2b` | 153 | relaxed-Pfam recovery |
| Tranche-2 stranding | `v294_t2c` | 107 | ecod_rep-stranding movers reassigned |
| Rep-selection Tier-1 | `v294_repsel_t1` | 7,146 | single-member: sole member promoted |
| Rep-selection Tier-2/3 | `v294_repsel_t23` | 6,333 | multi-member: best-ranked candidate promoted |
| **total** | | **14,375** | |

Plus (not domain_assignment_log): 3,477 F-group accession→name renames; repaired
`implement_reassign_f_group` and the `create_domain_change_request`/`implement_domain_create` path
(both had never run); 6 F-group deprecations + 58 commons rehomes (the 16-stranding batch only).

## The residue (curator/follow-up, not rep placement) — 107 → 103 (2026-06-09)
Originally 24 dead-branch orphans · 7 empty · 76 deferrals. The "24 dead-branch" turned out to be
mostly **v294 wiring bugs, not old orphans** (release id 4 = v294): 23 of 24 are v294-created
F-groups with valid Pfams — 20 jelly-roll families (`EMP24_GP25L`, `CBM_4_9`…) **mis-parented under
the deprecated T-group `10.1.2`**, and 3 under 2 live Archaea T-groups (`1085.1.1`/`7070.1.1`) that
v294 created **without `cluster_relation` rows**. Only `10.1.2.61` (`HA70_C`, v293) was genuine.
**2026-06-09:** deprecated the 1, wired `cluster_relation` + repped the 3 (then forward-synced),
**held the 20** for curator reparenting (only `10.1.1` is live under H-group `10.1`; may need a new
live T-group or fold into v294.2). **Repless now 103** = 20 held + 7 empty + 76 deferrals.
Lesson: F-group under a deprecated ancestor ≠ junk — check `introduced_release` first.

## Deployment status
**STAGED ON DIONE ONLY — NOT deployed to sangala prod (`ecod_af2_pdb`).** This is source-db work;
a prod push is a separate future step. Backups: `backups/ecod_rep_backup_20260608_pre_*.dump`
(pre_reassign, pre_tranche2, pre_tranche2b, pre_tranche2c, pre_repsel_t1, pre_repsel_t23).

## Methodology lessons banked (see memory)
- Scan `ecod_commons.domain_sequences` (exact domain, 96.5% cov), NOT `protein_sequences`.
- Array-scan at scale; a single-node hmmscan hit the 1 hr limit and faked 73% no-Pfam (truncation).
- FASTA export via `psql -tA`/`\o`, never `\copy ... TO` (escapes newline → literal `\n`).
- Repless enumeration must exclude **deprecated ancestors** (`cluster_relation` is the live gate).
- Never deprecate a pfam'd repless F-group (temporal stability) — leave it for rep-selection.
- Ranker: concordant → complete (HMM cov ≥0.8) → experimental(PDB) → coverage → score → length;
  completeness outranks source (a full AF2 beats a crystal fragment).
- `ecod_rep` authoritative + separate; commons is its own pass. Stranding = losing the last *ecod_rep* rep.

## Remaining (separate efforts, scoped/documented)
1. **Curator queue** — the 107 residue + earlier holds (44 REROUTE / 21 REVIEW / 13 HOLD / Lsr2 /
   27 "(DEPRECATED)"-in-name F-groups / the lone `is_representative` inconsistency).
2. **Commons rep sync (forward, ecod_rep → commons) — DONE 2026-06-09.**
   `commons_forward_sync_20260609.sql`: flagged 13,515 commons domains to match ecod_rep (46,410 reps
   reflected; all 25,285 provisional reps confirmed), and pointed 122,246 NULL-pointer non-reps at
   their F-group's rep. No-rep-pointer debt 174,186 → 50,157 (48,990 F-group-no-rep + 1,167
   rep-not-in-commons); 0 CHECK violations. Direction matters — the v294 mess came from doing it
   *backwards*. Backups: `commons_sync_step1_preimage` + `commons_sync_step2_pointed_ids`. Left
   alone: 1,384 commons-only reps (reverse direction) and the **93,265 "follower in a different
   F-group than its named rep"** debt — the messy part, and the natural input to the non-rep
   checking pass.
3. **Prod deployment** — push the dione ecod_rep changes to sangala.
4. **Migration codebase root-cause** — the `--acc` naming bug + the broken `implement_*` functions.
