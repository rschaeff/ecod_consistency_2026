# Feature Request — Self-exclusion for non-circular validation of existing ECOD reps

**For:** `pyecod_mini` (primary) and `pyecod_prod` (evidence stage); a parallel FR is noted for `dpam_c2`.
**Requested by:** ECOD consistency project (v294 F-group reconciliation), 2026-06-05.
**Status:** spec only — to be implemented in the pyecod repos by a dedicated CC instance.

---

## 1. Motivation

We need to validate **existing** ECOD representative domains (`ecod_rep.domain`) with the
current classification algorithm — i.e. ask "does ECOD's own BLAST/HHsearch evidence place this
domain where it currently sits?" The immediate use case is the **456 v294 "movers"** (manual
reps whose F-group assignment is in question); the eventual use case is a full self-consistency
audit of all reps.

**The blocker:** every rep is itself in the ECOD reference library, so a naive run is
**circular** — the query self-matches its own reference entry and the algorithm trivially
recovers the existing label.

**Demonstrated (pilot):** `pyecod-mini 1gcy_A` classified domain `d2` (1–357) by matching
`reference_ecod_domain_id="e1gcyA2"` — *the query itself* — at 100% coverage, E-value 0.0. No
independent signal was tested.

There is currently no self/F-group exclusion in either pipeline (the existing `exclude`
machinery is for *designed/synthetic* proteins, not self-hits).

---

## 2. Requested capability

An option to **exclude specified reference evidence** from partitioning, so a query is
classified from *independent* evidence only. Configurable granularity:

- exclude **self** (the query's own reference domain id),
- exclude the query's **F-group** (all reference domains in the same F-group),
- exclude the query's **T-group** (optional, stricter),
- exclude by an **explicit list** of reference domain ids and/or F-group ids (most flexible;
  lets the caller decide policy without the tool needing DB knowledge).

The default behavior is unchanged (no exclusion) — this is opt-in.

---

## 3. Where it fits (suggested)

`pyecod_mini` owns evidence parsing, so it can filter on read with **no DB/batch dependency**
(consistent with `PYECOD_MINI_API_SPEC.md`): the `domain_summary.xml` evidence items already
carry `reference_ecod_domain_id`, `t_group`, `h_group`, `x_group`. So pyecod_mini can drop a hit
whose `reference_ecod_domain_id` is in the self/exclude set, or whose `t_group` is in an exclude
set. **F-group (4th level)** is not currently emitted on the evidence item — either:
- add `f_group` to the evidence item in the summary, **or**
- accept an explicit exclude-list of reference domain ids (the consistency project can supply the
  per-query F-group membership lists), **or**
- support `--exclude-fgroup` by matching against a provided id→f_group map file.

Optionally, `pyecod_prod` can apply the same mask at **summary generation** so masked summaries
are produced once and reused across runs.

---

## 4. Proposed API

**Library** (`pyecod_mini.partition_protein`):
```python
partition_protein(
    summary_xml, output_xml=None, *,
    exclude_self: bool = False,            # drop hits to the query's own domain id(s)
    exclude_domain_ids: list[str] | None = None,
    exclude_fgroups: list[str] | None = None,
    exclude_tgroups: list[str] | None = None,
    ...
) -> PartitionResult
```

**CLI** (`pyecod-mini`):
```
--exclude-self
--exclude-domains FILE      # newline list of reference ecod domain ids to mask
--exclude-fgroups FILE      # newline list of F-group ids to mask
--exclude-tgroups FILE
```

**Output additions** (so callers can confirm a run was non-circular):
- per-partition metadata: number of evidence items masked, and the exclusion policy used;
- ideally a per-domain note when the *top* evidence item was masked (i.e. self-hit removed).

---

## 5. Acceptance test

1. Running pyecod-mini on a rep with `--exclude-self` **and** its own F-group excluded must
   **not** recover the rep via self-hit; classification must come from other evidence (or be
   unclassified if none exists).
2. **Regression batch:** the consistency project will supply the **456 movers** (domain id +
   current F-group + commons target). For each, the masked run should report whether the
   algorithm **re-derives the current F-group** (supported), lands on a **different F-group**
   (which one), or **fails to classify** (placement unsupported by independent evidence).

---

## 6. Notes

- **Reference version:** validation should run against a current reference (v294.x). Masking uses
  the evidence hits' own classification fields, so it is version-agnostic.
- **Inputs we will provide:** the 456 mover domain ids with `old_f`/`commons_f`, and, if F-group
  derivation from the summary is non-trivial, an explicit per-query exclude-list of reference
  domain ids.
- **DPAM (`dpam_c2`) parallel FR:** the same circularity applies to DPAM's structural search
  (Foldseek/DALI vs `ECOD70` templates). A sibling feature — exclude self / same-F-group
  templates from the DALI/Foldseek candidate set (steps FILTER_FOLDSEEK / DALI_CANDIDATES) — is
  needed before DPAM can validate existing reps non-circularly.

---

## 7. Why this matters (project context)

The v294 migration assigned F-groups in `ecod_commons` (and created cluster nodes) without
updating `ecod_rep.domain` and without hmmscan-validating `cluster.pfam_acc`
(`f_group_pfam_validation` is empty; only Pfam 37.4 was ever registered). Pfam-evidence checks
resolved most of the 456 movers, but a structural/algorithmic re-derivation — done
**non-circularly** — is the independent confirmation. This feature is the prerequisite.
See `docs/FGROUP_RECONCILIATION_FINDINGS_20260605.md`.
