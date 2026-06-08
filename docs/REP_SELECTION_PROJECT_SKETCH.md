# Rep-Selection Project — Design Sketch (2026-06-08)

Successor to the v294 propagation effort. Where propagation placed reps that **already existed**
in commons, rep-selection **picks and creates** a provisional representative for each repless
ecod_rep F-group that has members but no designated rep.

## Goal
For each repless active ecod_rep F-group: rank its commons member domains, pick the best, and
create it as a `provisional_manual_rep` via the repaired `create_domain_change_request →
implement_domain_create` path. **Never deprecate** a pfam'd repless F-group (temporal stability).
ecod_rep-scoped only; commons cluster-coherence is a separate pass.

## Scope (current, after propagation)
- **13,586** repless active F-groups; **13,579** have ≥1 commons member; 7 empty → leave.
- **72,649** candidate domains: 10,507 PDB / 59,910 AF2.
- **7,195 (53%) single-member** F-groups — the lone member *is* the pick (trivial).
- Only **815** F-groups have any PDB candidate → ~12,764 will get an **AF2 provisional rep** (accepted).
- avg 5.4 members, max 706.

## Available ranking signals
| signal | source | populated | role |
|---|---|---|---|
| `source_type` pdb/afdb | proteins | 100% | primary quality prior (PDB ≫ AF2) |
| `sequence_length` | domains | 86% | completeness vs Pfam HMM length |
| `classification_confidence` | domains | **6%** | unusable |
| `representative_confidence` | domains | **0%** | unusable |
| pLDDT | `af2_human.*`, `bfvd.*`, … per-source | scattered | AF2 tiebreaker (v2 refinement) |
| **Pfam concordance** | fresh `--cut_ga` scan vs F-group `pfam_acc` | to build | **primary selector + validation gate** |

Because commons' own confidence fields are empty, Pfam concordance is what turns "pick any member"
into "pick the member that best exemplifies the F-group's defining Pfam" — and it doubles as a gate
against entrenching migration mis-assignments.

## Ranking (lexicographic, v1)
For each F-group, score each candidate and take the top:
1. **Pfam-concordant** with the F-group's `pfam_acc` above GA (preferred; see gate).
2. `source_type`: **PDB > AF2**.
3. Concordant: Pfam match quality (score − GA margin, HMM coverage). Else: `sequence_length`
   proximity to the Pfam HMM length (penalize fragments and fusions).
4. `sequence_length` (full-fold preference).
5. `ecod_uid` (stable tiebreak).

## Validation gate (provisional, but not blind)
Provisional reps are low-bar, but **gate on Pfam concordance**: if *no* member matches the
F-group's `pfam_acc` above GA, do **not** promote a misfit — flag the F-group for curator
(`pfam_acc` and/or membership suspect). Reuses the tranche-2 verdict machinery.

## Phasing
- **Tier 1 — single-member (7,195, 53%)**: member is the pick; promote, Pfam-gated. Biggest easy win.
- **Tier 2 — has a PDB candidate (815)**: prefer experimental; rank PDBs.
- **Tier 3 — multi-member AF2-only (~5,569)**: rank AF2 (+pLDDT in v2).

## Compute
Fresh `--cut_ga` scan of the distinct candidate proteins (< 72,649; many AF2 share proteins),
full-protein, top-hit-per-region — same SLURM pipeline as the tranches. Hours, not days.

## Pilot (proposed first step)
Tier 1 single-member, ~200-group sample: fresh-scan → measure Pfam-concordance rate → promote the
concordant, inspect the misfits. Calibrates the gate strictness and AF2-rep acceptance before
scaling to all 7,195, then the multi-member tiers.

## Pilot results (Tier-1, 200 single-member groups, 2026-06-08)
**The scanning substrate is `domain_sequences`, not `protein_sequences`.** A first pass on full
protein sequences gave a misleading 68% (18% of members weren't even in `protein_sequences`, and
cut_ga-on-protein-then-map-to-range manufactured spurious no-Pfam/discordant calls). Re-scanning the
**exact domain sequences** (header = ecod_uid):

| verdict | n |
|---|---|
| concordant (exact 188 / contains 3 / dominant 4) | **195** |
| partial_overlap (shares core Pfam; tandem-repeat redundancy) | 5 |
| discordant / no_pfam | **0** |

**195/200 = 98% strict; 200/200 acceptable** (the 5 partials are TPR/Ankyrin/WD40 groups whose
`pfam_acc` lists several redundant repeat models — the member hits a subset incl. the core repeat).

Conclusions:
- Use `ecod_commons.domain_sequences` (keyed `domains.id`; 96.5% candidate coverage). Fallback to
  protein+range only for the ~3.5% without a domain sequence.
- Single-member promotion is **very high confidence** — the gate rarely fires.
- **Refined gate:** PASS if member Pfams ∩ F-group `pfam_acc` ≠ ∅. FLAG only if the member has Pfams
  that wholly disagree (discordant) or none at all (→ try relaxed rescan before flagging).

## Tier-1 EXECUTED (2026-06-08) — 7,146 provisional reps
Scanned all 7,195 single-member domain sequences (20-way SLURM array; a single-node run was killed
at the 1 hr limit and gave a misleading 73% no_pfam — **always array-scan at this scale**). Verdict:
**7,193/7,195 PASS (99.97%)**, 2 discordant (near-miss superfamily variants). Created **7,146**
provisional reps via `implement_domain_create` (`requested_by='v294_repsel_t1'`); **repless 13,586 →
6,440**. Whole effort to date: **14,255 → 6,440** (more than halved).

Excluded / quarantined (pre-flight catches, not in the batch):
- **10 dead-branch orphans** — F-groups whose **T-group is deprecated** (e.g. 8 under `10.1.2`
  "GOLD domain-like", deprecated 2025-07-23; the 2025-04-25 F-group reorg "left orphaned F-group
  references"). See the methodology fix below.
- **3 `ecod_domain_id` collisions** — domain already a prov rep of another F-group (commons
  double-assignment): `P09820_nD1`, `Q9DE14_nD3`, `Q50288_nD1` → curator.
- **2 discordant** (`2004.1.1.1092`, `4333.1.1.8`) → curator.
- **34 already-in-ecod_rep** under a *different* `f_id` → defer (tranche-2-style reassign).

### Methodology fix: repless must exclude deprecated *ancestors*, not just the F-group's own flag
The repless query filtered `F.is_deprecated` only, so it included **29** F-groups hanging under a
deprecated **T/H/X** ancestor (dead-branch orphans the cleanup script missed). True **live**-repless
was 13,557, not 13,586. `implement_domain_create` correctly refuses these (its
`cluster_relation` H/X lookup excludes deprecated T-groups → "Could not determine H/X"). **Use
`cluster_relation` membership (or an ancestor `is_deprecated` traversal) as the live-branch gate**
in all rep-selection tiers; quarantine the orphans for curator dead-branch cleanup.

## Open questions for the curator
1. **Pfam gate strictness** — require above-GA concordance, or allow sub-GA (relaxed) for provisional?
2. **Single-member misfits** (member's Pfam ≠ F-group pfam_acc) — promote anyway (provisional) or hold?
3. **pLDDT for AF2 ranking** — source it for v1, or defer to v2 (source_type+length+Pfam only)?
4. **Batch cadence / audit tag** — one `requested_by` per tier (e.g. `v294_repsel_t1`)?
