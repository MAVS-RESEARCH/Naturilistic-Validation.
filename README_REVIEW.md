# Reviewer Snapshot — Anonymized

This is an anonymized reviewer snapshot prepared for double-blind review.

- Author-specific Git history (commit hashes, author names/emails, chronology, messages)
  and identity-bearing provenance were intentionally omitted. The review branch is an
  orphan snapshot with no parent relationship to any canonical history.
- Scientific results, negative evidence, failed attempts, and external upstream
  provenance were preserved. No experiment outcome, metric, sample count, model output,
  freeze geometry, cost, policy semantic, theorem claim, target definition,
  preregistered criterion, external source version, or falsification outcome was edited
  for anonymization. Identity-only transformations do not alter conclusions.
- Author-controlled repository URLs and local filesystem paths were replaced with
  stable semantic placeholders (for example `<AUTHOR_REPOSITORY>`, `<TEMP_DIR>`,
  `https://anonymous.example/...`). Author-controlled Git object identifiers were
  replaced with stable anonymous aliases (for example `<AUTHOR_REPO_COMMIT_001>`)
  preserving chronology and co-occurrence. External provenance (upstream repository
  URLs, upstream commits, content hashes, specifications) was preserved byte-identical.
- `REVIEW_SHA256SUMS.txt` authenticates the sanitized reviewer bytes only. It does not
  authenticate any canonical experiment seal and must not be mistaken for an original
  seal. Canonical identity and provenance will be restored after double-blind review.
- License terms are unchanged; copyright holder is shown as Anonymous Authors in this
  reviewer copy only. The canonical branch remains authoritative for legal ownership.

## Quick read-only verification

These checks are safe inside the extracted reviewer copy. They never
delete or overwrite the sealed run.

```powershell
python -m pytest tests/ -q --ignore=tests/metamorphic/test_phase2_permutations.py --ignore=tests/unit/test_hashing.py --ignore=tests/unit/test_partitions.py
```

Authoritative artifact checks (same exclusions; three checks fail for the
known pre-existing mismatch documented below):

```powershell
$env:PC_RUN_ID = "external_v01_polaris_pr4992"
$env:PC_PHASE = "4"
python -m pytest tests/ -q --ignore=tests/metamorphic/test_phase2_permutations.py --ignore=tests/unit/test_hashing.py --ignore=tests/unit/test_partitions.py
```

Deterministic read-only recomputation against the distributed artifacts:

```powershell
python scripts/phase4_independent_audit.py --run-id external_v01_polaris_pr4992 --read-only
python scripts/phase4_generate_claims.py --run-id external_v01_polaris_pr4992 --verify-seal
```

Expected reviewer-snapshot outcomes: default suite 65 passed, 14 skipped;
authoritative mode 76 passed, 3 failed for the pre-existing
`processed/freeze_lattice.csv` byte mismatch (see anonymization report).
The three exclusions cover modules needing the `hypothesis` dev
dependency; installing the dev dependencies below enables the full suite.

## Environment setup

Prerequisites: Node >= 20, Python >= 3.11. The orchestrator resolves its
interpreter via `PC_PYTHON`, defaulting to `.venv` inside the repository
root (see `scripts/run_external_validation.mjs`).

Runtime and test dependency pins live in `pyproject.toml`; `uv.lock`
records the locked tree. The orchestrator will not use whatever Python
happens to be active: create `.venv` first, then install with that
interpreter (specifiers copied from `pyproject.toml`):

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e .
.venv\Scripts\python.exe -m pip install "jsonschema>=4.23,<5" "pyarrow>=20,<21" "PyYAML>=6.0,<7" "coverage[toml]>=7.6,<8" "hypothesis>=6.120,<7" "pytest>=8.3,<9" "pytest-cov>=6.0,<7" "ruff>=0.12,<1"
```

On POSIX use `.venv/bin/python` in place of `.venv\Scripts\python.exe`.
Alternatively, point the orchestrator at an already-provisioned
interpreter with `$env:PC_PYTHON`; without either `.venv` or `PC_PYTHON`
it stops with "Phase-1 Python environment not found".

## Full clean regeneration

The submitted ZIP supports read-only verification and deterministic
recomputation of the distributed artifacts; full canonical regeneration
requires the original source environment (including network access for
external source acquisition) and is not the reviewer path. Regenerated
reviewer bytes also differ from canonical seals on redacted provenance
fields by design; `REVIEW_SHA256SUMS.txt` is the reviewer integrity layer.

If a disposable recomputation is nevertheless attempted:

DO NOT run the regeneration command against the only authoritative
extracted copy of the reviewer artifact.

1. Keep the extracted artifact untouched as the authoritative copy.
2. Make a disposable second copy and work only there.
3. In the disposable copy ONLY, remove the sealed run directory
   `results/external_validation_v01/external_v01_polaris_pr4992`, because
   the orchestrator creates that run from scratch and the cleaner
   intentionally refuses to overwrite `SEALED` (this refusal is an
   integrity feature, not an error).
4. Install the locked dependencies into that copy's `.venv` as above and run `npm run phase4` there.
5. Compare regenerated outputs against the untouched authoritative copy
   rather than expecting canonical seals to reproduce byte-identically
   from reviewer bytes.

## Tests

Expected reviewer-snapshot outcomes, per `ANONYMIZATION_REPORT.json`:
default suite 65 passed, 14 skipped (three `hypothesis`-dependent modules
excluded unless dev dependencies are installed); authoritative mode 76
passed, 3 failed for the known pre-existing `freeze_lattice.csv`
mismatch. No failure is relabeled as a pass.

Notes:

- Three authoritative checks fail both before and after anonymization for a pre-existing
  `processed/freeze_lattice.csv` byte mismatch (see anonymization report); this negative
  evidence is preserved and is not caused by redaction. Seal-hash checks covering redacted
  provenance fields (`implementation_git_sha` aliases, sanitized ledger) are expected to
  differ from canonical seals on reviewer bytes; `REVIEW_SHA256SUMS.txt` is the reviewer
  integrity layer. Scientific comparisons ignore only approved redaction fields.
- Because this snapshot may be hosted inside an existing account during staging, its URL
  itself is not suitable as an anonymous reviewer link. Export as an OpenReview
  supplementary ZIP or mirror into a genuinely anonymous repository before exposure.
