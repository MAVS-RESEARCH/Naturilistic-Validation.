# For Reviewers

> **Start here.** This is a short map of the artifact: what it supports,
> where the final result is, and where to look if you want more detail.

## What this artifact is

This is an anonymized snapshot of a source-frozen, contract-relative
external validation of Perceptive Closure against the Apache Polaris OPA
authorization path around PR #4992. It supports the paper's Polaris
analysis with a deterministic, exactly recomputed measurement, not a
statistical or prevalence claim.

## `WorkPlan.md` and `Path.md`

**`WorkPlan.md` = what was supposed to happen.** It specifies the planned
phases, gates, acceptance criteria, and evidence the experiment was
designed to produce.

**`Path.md` = what actually happened.** It ledgers the implementation
steps, tests, failures, deviations, and gate outcomes on the way to the
final state.

Both are available for reviewers who want the original protocol or
execution history; neither needs to be read front-to-back.

## Main result

- Phase 1: `ELIGIBLE` — 8/8 gates, 26 source artifacts, 8 native cases.
- Phase 2: `IDENTIFIED` — one exact contract completion with full touch
  coverage and fidelity.
- Phase 3: `MEASURED` — 64/64 freeze cells, 10/10 controls, 8/8 cases kept.
- Phase 4: `PASS — POSITIVE EXTERNAL` — 218 sealed artifacts, 12/12
  corruptions detected, 20/20 clauses pass.
- Authoritative seal: `results/external_validation_v01/external_v01_polaris_pr4992/SEALED`.
- One pre-existing `freeze_lattice.csv` byte mismatch is intentionally
  preserved; it predates redaction and is not hidden.

## Where to look

1. `results/external_validation_v01/external_v01_polaris_pr4992/SEALED` — authoritative final seal.
2. `results/external_validation_v01/external_v01_polaris_pr4992/reports/CLAIMS.md` — what is claimed.
3. `results/external_validation_v01/external_v01_polaris_pr4992/reports/REPRODUCE.md` — how it was run.
4. `results/external_validation_v01/external_v01_polaris_pr4992/contract/` — contract and touch evidence.
5. `WorkPlan.md` — original protocol for deeper inspection.
6. `Path.md` — execution ledger for deeper inspection.

## Quick verification

Verification inside the distributed copy is read-only. Do not run
`npm run phase4` against the extracted artifact: the run is already
sealed and the cleaner intentionally refuses to overwrite it. See
`README_REVIEW.md` for the safe in-place checks and the pytest suite,
including the authoritative checks and their known pre-existing mismatch.

## Scope / important interpretation

The `IDENTIFIED` / `MEASURED` / `POSITIVE EXTERNAL` labels are conditional
on the fixed experimental contract. They do not show that the
pre-existing Polaris source alone determines the E-versus-R diagnosis:
source/public evidence alone leaves the E/R governing interpretation
underidentified. Do not mistake this fixed-contract result for the paper's
separate source-relative analysis.

## Reviewer snapshot

This is an anonymous reviewer snapshot. Details are in
`README_REVIEW.md` and `ANONYMIZATION_REPORT.json`.
