# Perceptive Closure External Operational Validation v0.1

> ICLR reviewers: start with FOR_REVIEWERS.md.

This repository implements a source-frozen external operational validation of Perceptive Closure against Apache Polaris's OPA authorization path around merged pull request `apache/polaris#4992`.

The authoritative scientific protocol is defined in `WorkPlan.md`; implementation evidence and deviations are recorded in `Path.md`.

## Phase status (final)

- Phase 1: ELIGIBLE — 8/8 gates, 26 source artifacts, 8 native cases.
- Phase 2: IDENTIFIED under the fixed experimental contract — one exact contract completion.
- Phase 3: MEASURED — 64/64 freeze cells, 10/10 controls, 8/8 cases kept.
- Phase 4: PASS — POSITIVE EXTERNAL — 218 sealed artifacts, 12/12 corruptions detected, 20/20 clauses pass.
- Authoritative sealed run exists: `results/external_validation_v01/external_v01_polaris_pr4992/` with its `SEALED` marker.

> Interpretation: the positive IDENTIFIED/MEASURED result is contract-relative. The submitted manuscript separately treats the pre-existing Polaris source/public evidence as E/R boundary-underidentified. The fixed-contract result does not override that source-relative conclusion.

## Reproduction history vs reviewer snapshot

The canonical execution history demonstrated clean end-to-end regeneration with a byte-identical final seal (see the `Path.md` ledger). The anonymized reviewer snapshot preserves known distribution/canonical-baseline mismatch behavior documented in `ANONYMIZATION_REPORT.json`; this does not alter the scientific result. Reviewer-byte hashes (`REVIEW_SHA256SUMS.txt`) and canonical experiment seals must remain distinct — the former authenticate the redacted reviewer bytes, never the original seals.

## Phase-1 execution

```powershell
$env:PC_PYTHON = ".venv\Scripts\python.exe"
node scripts/run_external_validation.mjs --run-id external_v01_polaris_pr4992
```

Use `--through-phase 2` to regenerate Phase 1 and then compile and seal the Phase-2 contract. The orchestrator stops at the first failed gate. It never runs a closure planner in Phase 1 or Phase 2.

## Tests

```powershell
.venv\Scripts\python.exe -m pytest
```

Scientific outputs are written under `results/external_validation_v01/<run_id>/`. A named-run cleaner may remove only an unsealed run located strictly beneath that results root.
