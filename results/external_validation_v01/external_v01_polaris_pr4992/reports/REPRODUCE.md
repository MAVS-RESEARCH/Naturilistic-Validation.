# Reproduce the External Validation

From the repository root with the locked Python environment available:

```text
npm run phase4
```

The command safely removes only the explicitly named unsealed run, regenerates Phases 1-4, executes the full test suite, seals the run, proves cleaner refusal, and reruns the independent audit read-only.

Expected run ID: `external_v01_polaris_pr4992`.
Expected verdict: `PASS — POSITIVE EXTERNAL`.
