# Perceptive Closure External Operational Validation v0.1

This repository implements a source-frozen external operational validation of Perceptive Closure against Apache Polaris's OPA authorization path around merged pull request `apache/polaris#4992`.

The authoritative scientific protocol is defined in `WorkPlan.md`; implementation evidence and deviations are recorded in `Path.md`.

## Phase status

- Phase 1: external source lock and preregistration.
- Phases 2–4: unavailable until their upstream gates pass.

## Phase-1 execution

```powershell
$env:PC_PYTHON = ".venv\Scripts\python.exe"
node scripts/run_external_validation.mjs --run-id external_v01_polaris_pr4992
```

The orchestrator stops at the first failed gate. It does not derive E/R/A touch or run a closure planner during Phase 1.

## Tests

```powershell
.venv\Scripts\python.exe -m pytest
```

Scientific outputs are written under `results/external_validation_v01/<run_id>/`. A named-run cleaner may remove only an unsealed run located strictly beneath that results root.
