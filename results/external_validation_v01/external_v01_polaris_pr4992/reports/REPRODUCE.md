# Reproduce the External Validation

The submitted reviewer copy already contains the sealed run
`results/external_validation_v01/external_v01_polaris_pr4992` with its
`SEALED` marker. Do not run regeneration over that extracted copy: the
cleaner intentionally refuses to remove a sealed run, so `npm run phase4`
will stop at that safety gate. This refusal is an integrity feature, not
a scientific failure.

For read-only verification inside the extracted copy, use the pytest
suite and the read-only audit flags documented in `README_REVIEW.md`.

If a full recomputation is nevertheless attempted, use a disposable
reproduction copy only:

1. Keep the extracted artifact untouched as the authoritative copy.
2. Copy the artifact to a disposable location and work only there.
3. In the disposable copy ONLY, remove the sealed run directory
   `results/external_validation_v01/external_v01_polaris_pr4992`.
4. Install the locked dependencies (see `README_REVIEW.md`).
5. From the disposable copy root, run `npm run phase4`, which regenerates
   Phases 1-4, executes the full test suite, seals the run, proves
   cleaner refusal, and reruns the independent audit read-only.
6. Compare regenerated outputs against the untouched authoritative copy.
   Reviewer-byte outputs differ from canonical seals on redacted
   provenance fields by design.

Expected run ID: `external_v01_polaris_pr4992`.
Expected verdict: `PASS — POSITIVE EXTERNAL`.
