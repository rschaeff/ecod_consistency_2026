# F-group Reconciliation Findings — v294 Authority Inversion & Pfam-Evidence Review

**Date:** 2026-06-05
**Scope:** the "repless" active F-groups in `ecod_rep` and the 456 manual-representative
"movers" implied by the v294 Pfam-reconciliation migration.
**Status:** analysis + prototype only. **No database changes were made.**
(`backups/ecod_rep_backup_20260605.dump` taken; all implementation dry-runs rolled back.)

---

## 1. The problem: an incomplete, authority-inverted migration

`ecod_rep` has **14,255 active F-groups with no representative** (no `manual_rep` /
`provisional_manual_rep` domain in `ecod_rep.domain`); **~117k `ecod_commons` domains**
are attached to them. Normal ECOD authority flows **ecod_rep → commons** (ecod_rep is the
curated reference; commons is downstream).

The v294 "Pfam v38.2 reconciliation" migration (run **2026-02-22**, in the unreleased
**v293.1** development line) **inverted** this. On 2026-02-22 it:

1. **created** ~340 new F-group *nodes* in `ecod_rep.cluster` (mostly introduced in the
   never-released v293.1),
2. **wrote** new F-group *assignments* into `ecod_commons.f_group_assignments` via
   `assignment_method='promotion'`, `assigned_by='migration_from_public_schema'`
   (i.e. automated, **not** curatorial), and
3. **did NOT** update `ecod_rep.domain` — the authoritative rep→F-group membership.

So `is_manual_representative=true` on these commons domains is a **legacy flag carried by
the migration**, not evidence that the new F-group home was manually decided. Lifting
commons → ecod_rep blindly would import automated, unreleased reclassifications into the
released authoritative reference.

### The 456 "movers"
Of the 14,255 repless F-groups, **963** have a commons domain flagged as some kind of rep
(propagation-gap candidates); **344** have a commons **manual** rep → **456 mover domains**.
Critically, **all 456 already exist in `ecod_rep.domain`** as `manual_rep=true`:
- 72 have **no** F-group (`f_id` NULL — classified only to T-group),
- 384 sit in a **different** F-group than commons (≈380/384: old = v293 **released** →
  new = v293.1 **dev**), almost always a sibling within the **same T-group**.

So "propagation" is an **`f_id` reassignment** on existing rows (same `ecod_uid`), not a
flag flip and not a domain insert.

---

## 2. Method: re-decide placement ecod_rep-first, from Pfam evidence

Rather than trust the migration's commons assignments, we re-derived each domain's correct
F-group from **Pfam-A v38.2** evidence, ecod_rep-first.

**Caveat discovered:** `ecod_commons.protein_pfam_hits` (the stored scan) keeps **all**
overlapping family hits per region and does **not** reflect a `--cut_ga` top-hit-per-region
policy — it over-reports and produces spurious verdicts. So we ran a **fresh** scan under
current policy:

- `hmmscan --cpu 8 --cut_ga --domtblout` (HMMER 3.1b2) vs `~/data/pfam/v38.2/Pfam-A.hmm`,
  **full protein sequences** (436 PDB proteins), on leda via SLURM.
- resolve overlaps to **top-hit-per-region** (greedy by domain bitscore; drop a lower hit
  overlapping a kept one by ≥50% of its envelope).
- **≥60%-of-domain** overlap → dominant Pfam → F-group via `ecod_rep.cluster.pfam_acc` → verdict.

**Stored vs fresh:** 420/456 verdicts unchanged; **all 29 stored `points_to_other_fgroup`
were artifacts** (vanished under top-hit-per-region); 4 of 6 "contradicted" cases were also
artifacts. Validated set grew 163 → **174**; genuinely-questionable set shrank 38 → **6**.
The stored hits were the noisier source — the fresh scan confirmed and cleaned the analysis.

---

## 3. Results (fresh, policy-correct — `pfam_recheck/fresh_verdicts_20260605.csv`)

| Verdict | n | Action |
|---|---|---|
| supports_commons | 174 | **APPLY** (158 non-stranding; 16 strand an old group) |
| ambiguous_both | 151 | REVIEW |
| no_dominant_pfam | 125 | REVIEW |
| supports_old_ecod_rep | 3 | HOLD (Pfam contradicts the move) |
| pfam_has_no_fgroup_here | 3 | HOLD |

Consolidated curator sheet with tier + recommended action:
`pfam_recheck/movers_curator_review_20260605.csv`.

### Stranding (the 16 within supports_commons)
Each is the lone seeded rep of an old F-group; moving it leaves that group repless.
All 16 are **legacy experimental (PDB)** domains with strong Pfam identity — **not** oddballs,
fragments, or predicted models. Disposition:
- **10 live old groups** (4–200 members) → apply move **+ seed a new provisional rep**.
- **3 vacated tiny groups** (≤2 members; e.g. eRF1_1 `4.23.1.1` wholesale → Pelota_N) →
  apply move **+ deprecate/merge** the old group.
- **1 oddball** (Lsr2 `e2kngA1`; target `130.1.1.33` is name-flagged "(DEPRECATED)") → curator hold.

### Suggested provisional reps (`pfam_recheck/reseed_suggestions_20260605.csv`)
Re-scanned the remaining members the same way. **None of the candidates exist in
`ecod_rep.domain`** — re-seeding is the **domain-create** path, not a flag flip.
- 4 groups: clean experimental + Pfam-confirmed rep (Cullin `e8vvyA02` 100%/bit517, …).
- 3 groups: predicted-only (AF2) confirmed rep — usable provisionally, flag for curator.
- 2 groups (EF-hand `108.1.1.3`, RCC1 `5.1.4.7`): **no** Pfam-confirmable rep
  (EF-hands too short for Pfam to dominate; RCC1 is a repeat superseded by the WD40_RLD
  propeller — `5.1.4.7` looks **vestigial / merge candidate**).
- 1 group (T4_gp9_10 `3386.1.1.1`): no usable candidate (all members obsolete).

---

## 4. Composite Pfams: the heart of the REVIEW pile

**266 of 276 REVIEW cases (96%) involve a composite (multi-Pfam) F-group**, almost entirely
by moving **TO** a composite target (262). This is *why* the single-dominant-Pfam rule can't
adjudicate them.

A **composite-aware (architecture) rule** was prototyped (`pfam_recheck/composite_rule.py`,
output `composite_rule_20260605.csv`): collect the domain's **set** of top-hit-per-region
Pfams (≥50% of each hit inside the domain), match that set against each F-group's Pfam
*combination* (Jaccard; exact-set match preferred). Honest outcome:

| Outcome | n | from ambiguous | from no_dominant |
|---|---|---|---|
| **apply → commons** (arch == target) | 74 | 13 | 61 |
| **reroute → other F-group** (arch fits a different/simpler group) | 44 | 3 | 41 |
| subset-ambiguous (domain = old Pfam, lacks the composite's extra) | 149 | 130 | 19 |
| no architecture | 8 | 4 | 4 |
| genuine supports-old | 1 | 1 | 0 |

- **Cracks `no_dominant_pfam`: 102/125 (82%)** — multi-Pfam domains whose full architecture
  matches a specific F-group exactly.
- **Barely helps `ambiguous_both`: 16/151** — 130 are the **subset-ambiguous** case
  (`{P}` → `{P,Q}`): the domain has the old Pfam but not the composite's extra Pfam.
  Irreducibly structural: is the extra Pfam **truly absent** or **below `--cut_ga`**?
- Surfaces a new error class: **44 "reroute"** — the migration over-aggregated these into a
  composite group when a simpler/different sibling F-group fits the domain's actual architecture.

---

## 5. Resolving the subset-ambiguous pile: the self-hit pitfall + a non-circular rescan

The 149 subset-ambiguous cases collapse to one question — "does the domain actually contain
the composite's extra Pfam Q?" The first instinct was to reclassify them structurally
(pyecod-mini / DPAM). **That is circular:** all 456 movers are ECOD reps living in the
reference library, so a sequence/structure search recovers the domain's *own* current label
(self-hit). Confirmed in a pilot — `1gcy_A` classified by matching `e1gcyA2` (itself) at 100%
coverage, E=0. pyecod-mini and DPAM have no built-in self / F-group exclusion, so they cannot
answer this without a leave-F-group-out reference.

A **non-circular** test answers it directly: rescan each domain against its *specific* missing
Pfam Q **without `--cut_ga`** (Pfam HMMs are independent of the ECOD query), and compare Q's
best in-domain bitscore to Q's gathering threshold (GA). Result
(`pfam_recheck/relaxed_pfam_check_20260605.csv`):

| Outcome | n | Meaning |
|---|---|---|
| **Q above GA** | 130 | extra Pfam **is** present above threshold → composite **Pfam-justified** |
| Q sub-GA | 13 | extra Pfam just below GA (Δ −0.2 to −4.4) → genuinely borderline |
| **Q absent** | 6 | extra Pfam not present at all → composite **over-reach**; keep the simpler old group |

**Method correction:** the 130 "above GA" were never truly ambiguous — they were an artifact of
the architecture rule's top-hit-per-region step (`OVERLAP_KILL=0.5`), which discarded the extra
Pfam Q whenever it overlapped a higher-scoring Pfam in the same region. Examples: `e1ea5A1`
PF20434 score 39.7 vs GA 26.8 (Δ+12.9); `e1cjwA1` PF13673 37.7 vs 23.6 (Δ+14.1); `e1auiB2`
EF-hand PF00036 27.7 vs 25.4. For these, overlapping Pfam models genuinely co-describe one ECOD
domain — a legitimate composite. **Lesson: do not apply aggressive overlap resolution when
detecting composite architecture; keep all above-GA Pfams.**

The 6 `Q_absent` are the real over-created composites (e.g. `e1ihmA2` missing PF00915;
`e3vkhA3`/`e4rh7A4` missing PF12774 in the P-loop NTPase `2004.1.1` corner). The 13 `Q_sub_GA`
are the true "necessary-evil" boundary cases.

### 5b. Provenance: `pfam_acc` was never hmmscan-validated; the 19 are not version artifacts

The `cluster.pfam_acc` values I validate against are **not a hmmscan-confirmed ground truth**:
`ecod_commons.f_group_pfam_validation` (hmmscan_status / hmmscan_passed / pfam_version_id) is
**empty** — built but never run; all 344 composite targets are `pending`. And `pfam_versions`
registers **only Pfam 37.4** (not the v38.2 the migration claimed). So the composite combinations
could be illusions from (a) an older Pfam version or (b) InterPro annotation transfer (the schema
has `interpro_uniprot*`, `pfam_interpro`, and `tmp_uid_pfam_id_hmm` vs `tmp_uid_pfam_id`).

A **37.4 disambiguation rescan** of the 19 unconfirmed missing Pfams settles it: **0/19 pass GA
under 37.4 either**, with scores essentially identical across versions (e.g. PF00108 25.0/25.0,
PF00350 26.5/26.6). So hypothesis (a) is **rejected** — these are not version drift. Hypothesis
(b) is **supported**: the 6 `Q_absent` are absent in both versions and the 13 `Q_sub_GA` are
sub-GA in both, so neither could have come from a gathering-threshold hmmscan — consistent with
non-hmmscan (InterPro/annotation-transfer) provenance, matching the empty validation table.

**Consequence:** demote `cluster.pfam_acc` from "ground truth" to "candidate label"; the current
hmmscan IS the validation that was never run. The 6 `Q_absent` firm to **HOLD** (composite wrong),
the 13 `Q_sub_GA` to **don't-trust-composite** curator review.

---

## 6. Principle: composite Pfams are a necessary evil

A composite-Pfam F-group marks a place where **ECOD and Pfam disagree on domain boundaries**.
That disagreement has multiple causes, which must be distinguished before creating a composite:

- **Pfam over-fragments one ECOD domain** into several adjacent models (e.g. TPR/HEAT/RCC1
  repeats, propellers) — the ECOD domain is one unit; the composite is just Pfam granularity.
- **One ECOD domain genuinely spans multiple Pfam families** (a real multi-Pfam architecture).
- **Pfam boundary/threshold artifacts** — a defining Pfam falls below `--cut_ga` in some
  members (the subset-ambiguous case), so the "composite" is partly an evidence artifact.
- **Mixed membership** — the F-group lumps domains of differing architectures.

**Composites should be created sparingly.** Each one should be justified by a real boundary
disagreement, not minted automatically by a dominant-Pfam / migration rule. The §5 rescan bears
this out: of the 149 automated subset composites, **130 were Pfam-justified** (the extra Pfam is
really there, above GA), **6 were over-reach** (extra Pfam absent), and **13 were true borderline**
boundaries. The right gate before trusting/creating a composite is the **non-circular relaxed-Pfam
test** ("is the extra Pfam present above/near GA in this domain?") — *not* an ECOD self-classifier.

### 6b. Worked example — composite Pkinase F-groups (partner-independence test)

A practical diagnostic for "is a composite real, or is it over-merging two domains?": does each
non-defining partner Pfam appear **independently** elsewhere in ECOD? Applied to the 14 active
composite kinase F-groups (all in the kinase T-group `206.1.1`/`206.1.2`):

- **Partners that appear independently are all themselves kinase Pfams** — ABC1 (PF03109, 3
  F-groups), RIO1 (PF01163), APH (PF01636), Pkinase_fungal (PF17667), IPK, Kdo, Kinase-like —
  and they appear independently *within the kinase T-group*. So composites like `Pkinase, ABC1`
  are one kinase domain described by multiple Pfam models (Pfam over-fragmentation), not a merge.
- **Partners with zero independent occurrences are kinase appendages, not domains:** `Pkinase_C`
  (PF00433, AGC C-terminal tail), `TGF_beta_GS` (PF08515, GS regulatory motif), `EphA2_TM`
  (PF14575, a transmembrane region) — only ever seen fused to the kinase.

Conclusion: **no non-kinase partner is a free-standing ECOD domain**, so these composites do not
merge independent domains — they are the kinase fold under multiple Pfam models plus small
appendages, and are defensible. Two warrant a curator flag because the partner is non-globular:
`EphA2_TM` (a transmembrane Pfam should not co-define a globular F-group) in `206.1.1.22`, and
`TGF_beta_GS` in `206.1.1.4`/`.21`. The mover targets `206.1.1.71` (Pkinase+Kdo) and `206.1.1.72`
(Pkinase+Pkinase_fungal) are kinase+kinase-variant — keep.

The same test on **Fer4 / iron-sulfur ferredoxin** composites (PF00037 = Fer4, the 4Fe-4S
cluster-binding domain; 27 composites, all in the ferredoxin T-groups `205.1.1`/`187.1.1`) gives
the same verdict. Nearly every partner is **another Fer4-family model** (`Fer4_2/3/5/6/7/9/10/11/17/21`,
`Fer4_RLI`) — Pfam's many overlapping models for one small Fe-S fold, compounded by ferredoxins
tiling **tandem 4Fe-4S clusters** (genuinely repeat-like). The few non-`Fer4_*` partners
(`DUF3470`, `APS-reductase_C`, `Fer4_RLI`, `LdpA_Fe-S-bd`), when they occur independently, do so
**only inside the same `205.1.1` ferredoxin T-group** — none is a free-standing domain in another
fold, so there is no over-merge of the Fe-S cluster with an unrelated catalytic domain. Watch case:
`e3mmcB1` (mover, old `205.1.1.1`) is dominated by **NIR_SIR (PF01077)**, not Fer4 — a siroheme/Fe-S
reductase parked in the ferredoxin T-group (already in the HOLD / `pfam_has_no_fgroup` bucket).

More broadly, **repeat folds** (β-propellers `5.1.*`, TPR/HEAT `109.*`), **EF-hands** (`108.1.1`),
and **iron-sulfur ferredoxins** (`205.1.1`) are the zones where Pfam and ECOD boundaries genuinely
don't converge (repeats/tandem modules stymie both); an accurate composite F-group *description* is
the right interim state pending an eventual split into single domains.

---

## 7. Recommendation

> **APPLIED 2026-06-08 (committed to live `ecod_rep`):**
> - **F-group name fixes:** 3,477 (3,069 single + 408 composite) accession→family-name renames (audited, logged).
> - **`implement_reassign_f_group` repaired** (the 2-bug fix; committed).
> - **362 clean APPLY reassignments** (the 245 doubly-confirmed + 117 curator-cleared from the 133)
>   via the audited `create_domain_update_request → approve → implement_domain_update` path —
>   all 362 now in their `commons_f` target, 362+362 audit-log rows. Backup
>   `ecod_rep_backup_20260608_pre_reassign.dump` predates it.
> - **Stranding (16) resolved:** 15 reassigned + **6 F-groups deprecated** (58 commons members
>   rehomed to the T-group `.0`) + **7 provisional reps re-seeded** (via the now-repaired
>   `create_domain_change_request`/`implement_domain_create`, mechanism A — they had ~6 bugs and
>   had never run). Lsr2 (`e2kngA1`) **held** (target `130.1.1.33` is curator-flagged deprecated).
> - **Tranche 2 (the 674 non-manual propagation candidates — 621 provisional + 52 manual reps):**
>   fresh `--cut_ga` validation → **252 propagated** (213 reassign + 39 create, `requested_by='v294_t2'`).
>   Relaxed-Pfam rescan (no `cut_ga`) on the 236 no-arch/ambiguous recovered **190** (commons Pfam
>   present ≥GA but missed by the architecture pass) → **153 more propagated** (122 reassign + 31
>   create, `requested_by='v294_t2b'`); 34 sub-GA borderline + 12 Pfam-absent held.
>   Then the **107 ecod_rep-stranding movers** (mover was old_f's only ecod_rep rep) were **all
>   reassigned** (`requested_by='v294_t2c'`) — pure rep placement, **0 deprecations**, no commons
>   writes; old_f kept as repless real F-groups (temporal stability). **512/674 placed.**
>   Held: 34 borderline, 12 structural, 116 points-other/supports-old.
>   Backups `ecod_rep_backup_20260608_pre_tranche2{,b,c}.dump`.
> - **Authority model:** ecod_rep is authoritative and **separate**; commons is a **separate
>   reconciliation pass**. ecod_rep stores only reps, so "stranding" = old_f losing its last *ecod_rep*
>   rep (commons membership irrelevant here). Commons carries its own large inversion debt — **93,265**
>   non-reps in a different F-group than their named rep, **174,186** with no rep pointer — for that pass.
> - **Net:** repless active F-groups **14,255 → 13,586** (−669 across all tranches).
> - **Held for curator:** Lsr2; 44 REROUTE; 21 REVIEW; 13 HOLD; tranche-2 held (above); 27 ECOD-wide
>   "(DEPRECATED)"-in-name-but-active F-groups; the lone `is_representative`/designation inconsistency.
> - **Data note:** commons `is_representative` = `is_manual ∨ is_provisional` (verified: 0 reps without
>   a designation, 1 designation-without-rep). Use `is_manual ∨ is_provisional` as the rep test.
> - **Bigger remainder:** ~13,316 repless F-groups have members but **no representative at all** —
>   a rep-*selection* project (not propagation), out of scope for this effort.

After all evidence layers (fresh `--cut_ga` verdict → composite-architecture rule →
non-circular relaxed-Pfam rescan), the 456 movers consolidate as
(`pfam_recheck/movers_curator_review_20260605.csv`, `final_class` / `final_action`):

| Class | n | Composition |
|---|---|---|
| **APPLY** | **378** | 158 non-stranding `supports_commons` + 16 stranding (paired actions) + 74 composite-architecture-confirmed + 130 composite Pfam-justified (extra Pfam ≥ GA) |
| **REROUTE** | 44 | architecture fits a *different* F-group than the migration target — re-place, don't use commons target |
| **REVIEW** | 21 | 13 borderline composite (extra Pfam sub-GA) + 8 no-Pfam-architecture (structural) |
| **HOLD** | 13 | 6 composite over-reach (extra Pfam absent, keep old) + 4 supports-old/arch-old + 3 no-F-group-here |

Sequencing:
1. **Batch 1 (clean):** the **158 non-stranding `supports_commons`** via the audited
   request→approve→implement path (after repairing `implement_reassign_f_group`).
2. **Composite APPLY (204 = 74 + 130):** Pfam-justified placements into composite F-groups. Apply
   after curator sign-off on the composites themselves (per §6 — Pfam-justified ≠ ideal boundary).
3. **Stranding (16):** paired re-seed (10, via domain-create) / deprecate-merge (3) / hold (1: Lsr2).
4. **REROUTE (44):** identify the better-fit sibling F-group first, then place there.
5. **REVIEW (21):** 13 sub-GA borderline + 8 no-arch → curator / leave-F-group-out structural pass.
6. **HOLD (13):** keep current; do not apply.
7. **Do not** mint composite F-groups automatically; gate on the relaxed-Pfam test, not a self-classifier.
8. **Independent structural confirmation (DONE — see §8):** re-derived non-circularly with the
   current algorithm (pyecod-mini self-exclusion). 245 APPLY moves are doubly-confirmed; 133
   APPLY are structurally unconfirmed and pulled out for curator review.

---

## 8. Independent structural validation (non-circular, pyecod-mini self-exclusion)

The self-exclusion feature shipped in `pyecod_mini` (v2.1.0, `--exclude-self`/`--exclude-fgroups`)
and `pyecod_prod` (summary `f_group` + classification lookup) per the FR. We generated develop291
BLAST+HHsearch evidence for all 436 mover chains (injected into a pyecod_prod batch — no repo
modification), partitioned each mover with **self + old-F-group excluded**, and mapped each
re-derived `reference_ecod_domain_id` to its **v294** F-group (lookup built from
`ecod_commons`, 2.97M domains) to verdict against `commons_f`.

**Structural verdicts (456):** supports_commons 294 (65%) · other 84 · supports_old 46 · unclassified 32.

**Structural × Pfam `final_class` (the actionable cut):**

| | supports_commons | other | supports_old | unclassified |
|---|---|---|---|---|
| **APPLY (378)** | **245** | 64 | 38 | 31 |
| REROUTE (44) | 27 | 16 | 1 | 0 |
| REVIEW (21) | 14 | 2 | 5 | 0 |
| HOLD (13) | 8 | 2 | 2 | 1 |

- **245 APPLY moves are doubly-confirmed** (Pfam-justified *and* independently structurally
  re-derived) → the highest-confidence batch.
- **133 APPLY moves are structurally unconfirmed** (64 other, 38 supports_old, 31 unclassified) →
  pulled to `pfam_recheck/apply_struct_unconfirmed_133_20260608.csv` for curator review. Only 42
  of these are composite-Pfam-justified (`Q_above_GA`); many (e.g. EF-hand `108.1.1`) re-derive a
  *sibling* F-group in the same family — i.e. the composite sub-split is structurally fine-grained.
- **27 REROUTE + 8 HOLD now re-derive commons structurally** — a second opinion that the migration
  target may have been right for those.

**Caveats:** `supports_old` is often a Pfam-granularity sub-split of the same structural family
(structure sees the parent, Pfam adds the composite); `unclassified` (32) means the old F-group was
structurally isolated so no independent confirmation is *possible*; exclusion is by develop291
`f_group` while the verdict maps to v294 (aligned for most, matters at the borderline).
`struct_verdict` / `concordance` are folded into the master curator-review CSV.

---

## 9. Defect found & fixed: F-group names were Pfam accessions, not family names

The v294 migration's Pfam-evidence naming wrote the Pfam **accession** into
`ecod_rep.cluster.name` instead of the HMM family **NAME** — the classic hmmscan `--acc`
mistake. It hit two ways, both migration-created (all v293.1/v294, zero from released versions):

- **Single-Pfam F-groups (3,069 active):** `name = pfam_acc` outright (e.g. `name = "PF31211"`).
- **Composite F-groups (408 active):** component(s) whose name couldn't be resolved were left as
  accessions inside the name-list (e.g. `"LRR_6, PF29265"`, `"PF29148, PF29151, PF29158"`). These
  were missed on the first pass (the `", "` separator dodged the single-accession regex).

The unresolved tokens are all **recent ECOD-seeded Pfams** (PF26xxx–PF31xxx) absent from the
migration's name lookup; **all 3,477 resolve** to a real v38.2 `NAME` (0 unresolved) —
PF31211→`Taz1_DD`, PF26557→`Cullin_AB`, PF29265→`LRR_CARMIL`, PF29148/151/158→`YPP1_N/_middle/_C`.
108 single + several composite cases are mover `commons_f` targets — which is how it surfaced.

**Fixed — committed 2026-06-08 in two passes (3,069 single + 408 composite = 3,477; the only
persisted DB changes in this effort)** via the audited rename pipeline
(`create_hierarchy_change_request` → `approve` → `implement_rename_group`): each rename logged to
`hierarchy_change_history` and noted in the cluster `comment`, fully reversible (backup
`ecod_rep_backup_20260608.dump` predates both). The composite pass replaces **only** the bare-accession
tokens, preserving already-correct component names. Verified: **0** active F-group names contain a
bare accession. **`pfam_acc` is untouched**
— the accession remains authoritative there; only the human-readable `name` changed. Curator CSV
display names were regenerated to match.

**Root cause (for the migration codebase):** F-group naming — both the single-Pfam path **and**
per-component in the composite path — must read the HMM `NAME` field, not the `--acc` accession,
or re-runs reintroduce the defect (esp. for newer Pfams missing from any name lookup). Rename maps:
`pfam_recheck/fgroup_accession_rename_20260608.csv` (3,069 single) +
`fgroup_composite_rename_20260608.csv` (408 composite); batches:
`rename_accession_fgroups_20260608.sql`, `rename_composite_fgroups_20260608.sql`.

---

## 10. Artifacts

| File | Contents |
|---|---|
| `pfam_recheck/movers_curator_review_20260605.csv` | **Primary** — 456 movers; verdict + tier + composite_outcome + relaxed_Q_verdict + **final_class / final_action** |
| `pfam_recheck/fresh_verdicts_20260605.csv` | authoritative per-domain verdicts (fresh `--cut_ga` scan) |
| `pfam_recheck/verdict_changes_20260605.csv` | 36 stored-vs-fresh differences (why we re-scanned) |
| `pfam_recheck/composite_rule_20260605.csv` | composite-aware architecture rule output (74 apply / 44 reroute / 149 subset / 8 no-arch) |
| `pfam_recheck/relaxed_pfam_check_20260605.csv` | **non-circular relaxed-Pfam rescan** of the 149 subset (130 Q≥GA / 13 sub-GA / 6 absent) |
| `pfam_recheck/structural_queue_20260605.tsv` | the 157 (149 subset + 8 no-arch) flagged for non-Pfam checks |
| `pfam_recheck/reseed_suggestions_20260605.csv` | suggested provisional rep per stranded live group |
| `pfam_recheck/reseed_candidates.csv` | 165 candidate members behind the suggestions |
| `pfam_recheck/pfam_ga.tsv` | Pfam-A v38.2 domain GA thresholds (acc→GA) used by the rescan |
| `pfam_recheck/disambig19*.{tsv,domtbl}` | 37.4-vs-38.2 disambiguation of the 19 unconfirmed (0 version drift) |
| `pfam_recheck/*.py`, `*.sbatch` | reproducible pipeline (scan + parse + rules) |
| `docs/FEATURE_REQUEST_pyecod_self_exclusion.md` | spec for non-circular rep validation (pyecod_mini/prod + dpam) |
| `pfam_recheck/mover_validation_manifest_20260605.tsv` | 456-mover regression batch (domain_id, pdb_chain, old_f, commons_f, t_id, final_class) |
| `pfam_recheck/mover_exclusion_fgroup_members_20260605.tsv` | per-F-group reference domain ids to mask (explicit exclude-list) |
| `pfam_recheck/full_validation_20260608.tsv` | **structural validation of all 456** (struct_verdict, rederived_f, concordance vs Pfam) |
| `pfam_recheck/apply_struct_unconfirmed_133_20260608.csv` | the 133 APPLY moves structurally unconfirmed — focused curator list |
| `pfam_recheck/fgroup_accession_rename_20260608.csv` | rename map for the 3,069 single-Pfam accession-named F-groups |
| `pfam_recheck/fgroup_composite_rename_20260608.csv` | rename map for the 408 composite F-groups with accession component(s) |
| `pfam_recheck/rename_accession_fgroups_20260608.sql` | single-Pfam rename batch (**COMMITTED** 2026-06-08, 3,069) |
| `pfam_recheck/rename_composite_fgroups_20260608.sql` | composite rename batch (**COMMITTED** 2026-06-08, 408) |
| `pfam_recheck/v294_classification_lookup.tsv` | domain_id→v294 X/H/T/F (2.97M) for verdict mapping |
| `pfam_recheck/{pilot_evidence,full_evidence,full_run_validation,pilot_run_validation}.py` | evidence-gen + non-circular validation drivers (use pyecod_prod/mini; no repo edits) |
| `pfam_reconcile_movers_20260605.csv` | earlier stored-hits pass (**superseded**) |
| `propagate_manual_reps_20260605.sql` | original commons→ecod_rep script (**DO NOT RUN** — backwards authority) |
| `backups/ecod_rep_backup_20260605.dump` | pre-change schema+function backup |

See project memory: `v294-authority-inversion`, `pfam-reconciliation-method`,
`implement-reassign-f-group-repair`, `composite-pfam-principle`, `pfam-acc-unvalidated`.
