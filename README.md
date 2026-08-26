# Perceptive Closure External Operational Validation v0.1

This repository implements a source-frozen external operational validation of Perceptive Closure against Apache Polaris's OPA authorization path around merged pull request `apache/polaris#4992`.

The authoritative scientific protocol is defined in `WorkPlan.md`; implementation evidence and deviations are recorded in `Path.md`.

## Phase status

- Phase 1: complete; external source lock and preregistration are eligible.
- Phase 2: extensional contract recovery and mechanical touch extraction.
- Phases 3–4: unavailable until their upstream gates pass.

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
