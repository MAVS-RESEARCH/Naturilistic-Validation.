# Perceptive Closure External Operational Validation v0.1 — Implementation Path

## 1. Ledger purpose and rules

This file is the append-only human-readable execution ledger for `WorkPlan.md`. It records what was actually implemented, how it was implemented, what evidence and tests support it, whether it follows the plan, every deviation or rejected attempt, and what may proceed next.

Rules for every future update:

1. Preserve failed and superseded attempts; do not rewrite them into passes.
2. Separate planning observations from sealed scientific results.
3. Record exact file paths, commands, test counts/results, artifact hashes, run IDs, and gate evidence when they exist.
4. State `FOLLOWS`, `DEVIATES`, or `NOT YET IMPLEMENTED` against the matching `WorkPlan.md` subsection.
5. Explain every deviation, its scientific effect, and which downstream artifacts are invalidated.
6. Update this ledger before each phase-completion push. The phase implementation commit is followed by a ledger commit that names it; both are pushed and remotely verified.
7. Do not call an eligibility, measurement, or audit gate passed until its machine-readable artifacts exist and its complete tests pass.

## 2. Current status dashboard

| Work item | Status | Evidence / note |
|---|---|---|
| Repository acquisition | Complete | Exact GitHub repository with trailing period connected as `origin`; `main` tracks `origin/main`. |
| Prior-results cleanup | Complete by inspection | Fresh clone contains only `LICENSE`; no `results/` directory or prior scientific output existed. Nothing was deleted. |
| Attached spec review | Complete for planning | Full structural extraction reviewed: 1 section, 414 top-level paragraphs, 74 tables, 148 tracked insertions, 0 tracked deletions, 0 comment references. |
| `WorkPlan.md` setup | Complete in current bootstrap change | Four scientific phases, complete file/code/test/benchmark/gate coverage, Polaris-specific hold audit. |
| `Path.md` setup | Complete in current bootstrap change | Ledger structure and initial factual record created. |
| Phase 1 scientific implementation | Complete — `ELIGIBLE` | Authoritative run `external_v01_polaris_pr4992`; 8/8 gates passed; 26 source artifacts; 8 native cases; report hash `ec183d55f54367b5fd694de21074e64d2da6b973e9b1e40ee0737fc7043f552c`. |
| Phase 2 | Authorized, not started | Phase 1 permits contract recovery only; route degeneracy and terminal-decision identification remain explicit Phase-2 obligations. |
| Phase 3 | Blocked by design | Requires sealed Phase-2 identified/partially identified contract. |
| Phase 4 | Blocked by design | Requires Phase-3 raw inputs; invalid runs may be audited diagnostically only. |

## 3. Bootstrap record — 26 August 2026

### 3.1 Scope requested

Create `WorkPlan.md` and `Path.md` from the attached implementation specification; divide all practical implications into an appropriate number of phases; state per-phase scope, files, code, coding approach, training/benchmark requirements, and anti-overfitting controls; use Apache Polaris OPA PR #4992 as the primary external system; start with an eligibility audit; keep only new results; and plan automatic commit/push after each completed phase.

### 3.2 Input distinction

- User instructions were treated as execution authority.
- The attached DOCX was treated as normative source material to translate into the requested plan, not as an independent request to begin all four phases immediately.
- Only one attached document was available. The phrase “both docs” was interpreted as the user's written request plus the attached normative specification; no nonexistent second attachment was invented.

### 3.3 Repository acquisition

Initial workspace state was an empty initialized Git repository with no commits checked out. The literal URL without the repository-name period returned “Repository not found.” Organization discovery showed the actual repository is named `MAVS-RESEARCH/Naturilistic-Validation.` with a trailing period.

Actions completed:

- Connected `origin` to `https://github.com/MAVS-RESEARCH/Naturilistic-Validation..git`.
- Fetched `origin/main`.
- Checked out local `main` tracking `origin/main`.
- Verified the upstream tree contained only `LICENSE` before this bootstrap change.
- Verified there was no `results/` directory, so no previous result was removed or overwritten.

Plan conformance: **FOLLOWS** the user's clone/clean-results requirement and `WorkPlan.md` Section 6. The discovery step corrected the ambiguous trailing punctuation without changing the intended repository.

### 3.4 Specification review

The document was inspected structurally in document order, including headings, body text, all 74 tables, headers/footers, tracked-change markers, and appendices A–F. Key normative content captured in `WorkPlan.md` includes:

- the full external model `M_ext` and common-`U_H` typing rule;
- extensional E/R/A touch and atomic freeze semantics;
- exact extended-real closure values and `Delta_R` relations;
- unit-cost primary analysis and source-grounded native-cost restriction;
- exact completion families capped at 128 unless an exact symbolic solver exists;
- independence, source-first semantics, no manual labels, same-instance comparisons, full retention, preregistration, audit independence, and claim discipline;
- route-degeneracy taxonomy and phase information firewall;
- complete recommended repository, schemas, modules, scripts, results tree, run identity, immutability, structured logging, and one-command execution;
- every Phase-1 through Phase-4 objective, script, test, control, corruption, artifact, and exit state;
- C1–C10, A1–A12, unit/phase/property/metamorphic tests, failure cards, provenance, runtime limits, paper language, final verdicts, and the 20-item definition of done.

The DOCX renderer could not run because LibreOffice/`soffice` is unavailable in the current environment. Per the document-reading fallback, the planning review used complete structural extraction and did not claim a visual-layout pass. This limitation does not affect the Markdown deliverables, but it is retained here for accuracy.

Plan conformance: **FOLLOWS** the requirement to study the specification deeply and the `WorkPlan.md` coverage matrix. No scientific code or result was produced during document review.

### 3.5 Apache Polaris PR #4992 planning audit

Read-only investigation established:

- PR title: “fix(authz): include realm identifier in OPA authorization input for tenant isolation.”
- PR created 7 July 2026 and merged 14 July 2026, before the 26 August 2026 implementation specification.
- Base SHA: `68cba2027e97683cfe62502cc2982c93e74e53e6`.
- Head SHA: `ce057ab10f0f7bc021337fbc4c7ddaf08470bd8d`.
- Merge SHA: `d0a8dff401e30cab1df3ca6d0e133816e80e9c10`.
- Pre-repair OPA `Context` exposes `request_id` but no realm; `OpaPolarisAuthorizerFactory.create(RealmConfig)` uses the globally injected OPA URI/config and does not pass realm information to the OPA input.
- Polaris realm documentation independently states that realms isolate resources, authentication, authorization, and persistence.
- PR #4992 makes realm required in the OPA context model/schema, constructor-injects `RealmContext`, and always emits `input.context.realm`.
- Review discussion explicitly requested and accepted end-to-end verification of `RealmContext → factory → context.realm` and a distinct-realm variant.
- Native post-repair tests include `testFactoryPassesRealmToAuthorizerContext`, `testFactoryUsesDistinctRealmValues`, `serializesInputWithRealm`, `serializesRealmInAuthorizePath`, and additional realm assertions in established request-shape tests.
- The existing OPA documentation at the pre-repair ref defines an OPA input context containing only `request_id` and examples of final policy allow/deny behavior, while the PR-specific regression tests mainly validate the added representation field.
- The historical realm-injection repair is a clearly source-grounded intervention. Candidate non-R alternatives—another authorizer path, separate authority, configuration change, or globally unique names—are not yet admitted; their same-case admissibility and atomicity require source evidence.

Planning disposition:

- Independent target/change/source pinning: strong.
- Native realm-related case enumeration: likely possible, but exact population is not sealed.
- Final terminal authorization target: unresolved because serialization tests alone do not prove a paired cross-realm allow/deny outcome.
- Competing routes: unresolved. If none are source-grounded, the case must remain route-degenerate rather than receiving an invented alternative.
- Overall: `PROVISIONAL HOLD`, not a scientific `ELIGIBLE` verdict.

Plan conformance: **FOLLOWS** `WorkPlan.md` Section 3 and Phase 1. No touch labels, freeze conditions, `K_Pi`, or `Delta_R` were computed.

### 3.6 Files created in this bootstrap change

- `WorkPlan.md`: complete four-phase implementation plan and specification coverage matrix.
- `Path.md`: this execution ledger, initialized with current state, evidence, limitations, and phase templates.

No code, schemas, configuration, external source snapshots, or scientific result files have been created yet.

### 3.7 Verification performed for the Markdown deliverables

Completed checks:

- Confirmed `WorkPlan.md` and `Path.md` exist at repository root and are nonempty.
- Confirmed the four WorkPlan phase headings occur once each and in the same Phase 1 → Phase 4 order as the normative specification; matching future-record sections exist in `Path.md`.
- Confirmed all eight freeze IDs are present: F000, F100, F010, F001, F110, F101, F011, and F111.
- Confirmed the plan explicitly includes the endpoints of the ten-control and twelve-corruption suites (C1/C10 and A1/A12), their complete descriptions, and their required pass counts.
- Confirmed required scientific objects and gates are covered: `U_H`, `H`, `P_R`, `Lambda`, `omega`, `Succ+`, `Terminal`, `A_Pi`, exact completion cap 128, `CONTRACT_SEALED`, `SEALED`, independent audit, claim ledger, safe results cleaning, phase commits/pushes, and the explicit no-model-training statement.
- Ran Git whitespace/error checking with no reported errors.
- Inspected the document heads/tails and repository status; only the two requested Markdown files are new.

### 3.8 Bootstrap Git and remote record

- Documentation implementation commit: `c1da59ca7cc2b3e38a6f228f82e2b8d2d58b0eea` (`docs: establish external validation work plan`).
- Push target: `origin/main`.
- Remote verification immediately after push: `refs/heads/main` resolved to the same full SHA as local `HEAD`.
- Working tree after the implementation push: clean and synchronized with `origin/main`.

This ledger evidence is committed as a follow-up documentation record and pushed before handoff, consistent with the two-commit phase-completion pattern prescribed by `WorkPlan.md` even though the bootstrap is not itself a scientific phase.

## 4. Phase execution records

The sections below are intentionally unfilled scientific records. They will be expanded in place as implementation proceeds.

## Phase 1 record — External System Lock and Preregistration

Status: **COMPLETE — ELIGIBLE**

Authoritative run ID: `external_v01_polaris_pr4992`

Execution date: 26 August 2026

Plan conformance: **FOLLOWS** `WorkPlan.md` Phase 1. The only added production module is `src/pc_external/eventlog.py`, required to implement the user's literal `console.log` request and the specification's structured logging rule. It does not change scientific semantics.

### Phase 1.1 Planned versus actual scope

The implementation remained inside Phase 1. It acquired and hash-locked external source, assigned evidence roles, generated the source-only native case population, recovered a native certificate target, preregistered all analysis rules, validated P1-E1 through P1-E8, reproduced the relevant pre/post source behavior deterministically, stress-tested failure boundaries, and generated an `ELIGIBLE` verdict.

It did not derive E/R/A touch, execute any resource freeze, construct `U_H`, compile an extensional contract, invoke a closure planner, compute `K_Pi` or `Delta_R`, produce a case result, or generate a scientific claim. A filename audit found no touch, freeze, planner, case-result, identified-set, claim-ledger, or final `SEALED` artifact under the Phase-1 result directory.

### Phase 1.2 Immutable external anchors

| Item | Frozen value |
|---|---|
| Repository | `https://github.com/apache/polaris.git` |
| Pre-repair ref | `68cba2027e97683cfe62502cc2982c93e74e53e6` |
| PR head ref | `ce057ab10f0f7bc021337fbc4c7ddaf08470bd8d` |
| Post-repair merge ref | `d0a8dff401e30cab1df3ca6d0e133816e80e9c10` |
| Historical change | `apache/polaris#4992` |
| Merge time | `2026-07-14T18:28:07Z`, before the `2026-08-26` specification date |
| Source manifest hash | `82498e35c2917fc0d0f3c489e7fddb89680a6eee1a3107e1c6d30ddc2c1d863e` |
| Source artifacts | 26 total: 8 `SOURCE_SEMANTICS`, 4 `NATIVE_TEST`, 2 `NATIVE_TARGET`, 10 `HISTORICAL_REPAIR`, 2 `EXCLUDED` |

Two independent filtered Git materializations fetched all three SHAs. Both passes verified object type `commit`, pre→post ancestry, equal tree IDs, and equal artifact hashes while using distinct temporary paths. The PR API history set was fetched twice and its canonical content matched. Every admitted source byte is stored under `external_source/snapshots/apache_polaris/` and indexed with byte SHA-256, normalized-text SHA-256, role, allowed influence, source ref, and repository-relative snapshot path.

### Phase 1.3 Native case rule and exact population

Frozen rule: include every upstream post-repair JUnit test method in the two PR-changed OPA test files whose body directly asserts equality on `input.context.realm`. The extractor uses the preregistered regex, assigns content-derived case IDs, and never reads Phase-2/3 output. A separately written reconstruction in `phase1_validate.py` recovered the exact same eight `(source method, expected realm)` pairs.

| Case ID | Upstream method | Expected realm | Method line | Assertion line |
|---|---|---:|---:|---:|
| `case:0a4d7152004aa6215f57` | `testFactoryUsesDistinctRealmValues` | `realm-b` | 239 | 285 |
| `case:7e1f9f910973f4196bb8` | `serializesBasicOpaInput` | `test-realm` | 77 | 125 |
| `case:906ed0caa75d4067918d` | `serializesHierarchicalTarget` | `prod-realm` | 131 | 225 |
| `case:aa50750cd1fc52dc9f56` | `serializesMultiLevelNamespaceTarget` | `analytics-realm` | 270 | 376 |
| `case:bc4db6fc3b742b39f763` | `authorizeIncludesStructuredParentsFromSecurable` | `catalog-realm` | 709 | 752 |
| `case:ca9fa12876555b9cb025` | `testFactoryPassesRealmToAuthorizerContext` | `factory-realm` | 184 | 230 |
| `case:e034f27f2bbfbf3b6a1f` | `serializesInputWithRealm` | `explicit-realm` | 1108 | 1141 |
| `case:e3e390037ac4ad9ad277` | `serializesRealmInAuthorizePath` | `tenant-xyz` | 1147 | 1174 |

All eight cases are `UPSTREAM_NATIVE`, all eight resolve to a frozen post-repair test artifact and exact line locator, and none was generated by PC. The case-index hash is recorded in the run manifest and `case_index_determinism.json` reports exact equality between production and independent reconstruction.

### Phase 1.4 Target and intervention-surface disposition

The source independently identifies the primary target as an `AUTHORIZATION_INPUT_CERTIFICATE`: `input.context.realm` must equal the realm identifier injected through the native OPA authorizer path. Native tests execute authorization requests against mock OPA endpoints and assert the emitted field; pre-existing OPA documentation defines how Rego consumes that input for allow/deny decisions.

The pre/post source-faithful replay proved all nine required observations:

- pre-repair `Context` omits `realm`;
- pre-repair `buildContext()` omits `.realm(...)`;
- pre-repair OPA schema omits `realm`;
- post-repair `Context` requires `String realm()`;
- post-repair `buildContext()` emits `.realm(realm)`;
- post-repair factory reads `realmContext.getRealmIdentifier()`;
- post-repair schema marks `realm` required;
- the eight native realm assertions are present;
- pre-existing OPA documentation defines default deny and allow rules.

One intervention is admitted: the historical PR #4992 action that threads required realm context through the factory and authorizer into `input.context.realm`.

Four candidate alternatives are explicitly excluded:

- switching to the internal authorizer changes the authorization mechanism and is not a PR-grounded same-instance repair;
- switching to Ranger has the same problem;
- a per-realm OPA policy URI is not supported by the pre-repair application-scoped OPA configuration/factory path;
- globally renaming principals/resources is not the historical repair and would change case identity.

Consequently, Phase 1 answers the eligibility question as follows: target pinning, case pinning, historical intervention, and the minimum real action surface are recoverable; competing-route count is zero. The system is `ELIGIBLE_FOR_ROUTE_DEGENERATE_CONTRACT_RECOVERY`, not established as nondegenerate. Phase 2 must classify the route as `R-ONLY ROUTE` or `SINGLE ACTION` unless additional already-frozen evidence supports another route, and it must still determine whether terminal decision semantics are point identified.

The retained limitation is exact: upstream does not contain one paired test that executes colliding names in two realms against a single realm-sensitive Rego policy. No such case was synthesized for the primary population.

### Phase 1.5 P1-E1 through P1-E8 gate evidence

| Gate | Result | Primary evidence |
|---|---|---|
| P1-E1 Independent origin | PASS | Frozen PR metadata and `experiment.yaml` establish merge before specification. |
| P1-E2 Historical change | PASS | PR body/commits/files/reviews/comments plus post-repair code/changelog; at least six required historical artifacts present. |
| P1-E3 Source recoverability | PASS | Exact SHAs, object/ancestry/tree checks, two source passes, two equal history passes, 26/26 hashes. |
| P1-E4 Authorization target | PASS | Native certificate target in `evidence_index.json`, eight test assertions, and OPA allow/deny policy documentation. |
| P1-E5 Native cases | PASS | Eight cases; source-only rule; exact independent reconstruction. |
| P1-E6 Intervention surface | PASS | One real historical realm-injection action; four unsupported alternatives excluded rather than invented. |
| P1-E7 No PC contamination | PASS | 0 PC-generated primary cases; 0 manual resource-label keys in source records. |
| P1-E8 Execution/reconstruction | PASS | Deterministic pre/post source-faithful replay passes 9/9 checks. |

Machine verdict: `ELIGIBLE`; Phase-2 authorization flag: `true`; eligibility report hash: `ec183d55f54367b5fd694de21074e64d2da6b973e9b1e40ee0737fc7043f552c`.

### Phase 1.6 Project and implementation files created

Project/tooling:

- `.gitattributes`
- `.gitignore`
- `README.md`
- `pyproject.toml`
- `uv.lock`
- `package.json`

Sealed configuration:

- `configs/experiment.yaml`
- `configs/costs.yaml`
- `configs/controls.yaml`
- `configs/completion_policy.yaml`

Strict schemas:

- `schemas/common.schema.json`
- `schemas/source_manifest.schema.json`
- `schemas/preregistration.schema.json`
- `schemas/native_case.schema.json`
- `schemas/phase1_eligibility.schema.json`

Production modules:

- `src/pc_external/__init__.py`
- `src/pc_external/eventlog.py`
- `src/pc_external/hashing.py`
- `src/pc_external/evidence.py`
- `src/pc_external/source_lock.py`

Scripts/orchestrator:

- `scripts/__init__.py`
- `scripts/clean_named_run.py`
- `scripts/phase1_lock_source.py`
- `scripts/phase1_preregister.py`
- `scripts/phase1_validate.py`
- `scripts/run_external_validation.mjs`

Test files and fixtures:

- `tests/fixtures/immutable_refs.json`
- `tests/fixtures/manifest_corruptions.json`
- `tests/fixtures/native_case_java.txt`
- `tests/unit/test_hashing.py`
- `tests/phase1/test_authoritative_artifacts.py`
- `tests/phase1/test_cleaner.py`
- `tests/phase1/test_evidence.py`
- `tests/phase1/test_logging_registry.py`
- `tests/phase1/test_manifest_corruption.py`
- `tests/phase1/test_source_lock.py`

### Phase 1.7 Complete generated artifact inventory

Root evidence indexes:

- `external_source/source_manifest.json`
- `external_source/evidence_index.json`
- `external_source/native_case_index.json`

Historical snapshots:

- `external_source/snapshots/apache_polaris/history/pr.json`
- `external_source/snapshots/apache_polaris/history/commits.json`
- `external_source/snapshots/apache_polaris/history/files.json`
- `external_source/snapshots/apache_polaris/history/reviews.json`
- `external_source/snapshots/apache_polaris/history/review_comments.json`
- `external_source/snapshots/apache_polaris/history/issue_comments.json`

Post-repair snapshots:

- `external_source/snapshots/apache_polaris/post/CHANGELOG.md`
- `external_source/snapshots/apache_polaris/post/extensions/auth/opa/opa-input-schema.json`
- `external_source/snapshots/apache_polaris/post/extensions/auth/opa/src/main/java/org/apache/polaris/extension/auth/opa/OpaPolarisAuthorizer.java`
- `external_source/snapshots/apache_polaris/post/extensions/auth/opa/src/main/java/org/apache/polaris/extension/auth/opa/OpaPolarisAuthorizerFactory.java`
- `external_source/snapshots/apache_polaris/post/extensions/auth/opa/src/main/java/org/apache/polaris/extension/auth/opa/model/Context.java`
- `external_source/snapshots/apache_polaris/post/extensions/auth/opa/src/main/java/org/apache/polaris/extension/auth/opa/model/README.md`
- `external_source/snapshots/apache_polaris/post/extensions/auth/opa/src/test/java/org/apache/polaris/extension/auth/opa/OpaPolarisAuthorizerFactoryTest.java`
- `external_source/snapshots/apache_polaris/post/extensions/auth/opa/src/test/java/org/apache/polaris/extension/auth/opa/OpaPolarisAuthorizerTest.java`

Pre-repair snapshots:

- `external_source/snapshots/apache_polaris/pre/extensions/auth/opa/opa-input-schema.json`
- `external_source/snapshots/apache_polaris/pre/extensions/auth/opa/src/main/java/org/apache/polaris/extension/auth/opa/OpaAuthorizationConfig.java`
- `external_source/snapshots/apache_polaris/pre/extensions/auth/opa/src/main/java/org/apache/polaris/extension/auth/opa/OpaPolarisAuthorizer.java`
- `external_source/snapshots/apache_polaris/pre/extensions/auth/opa/src/main/java/org/apache/polaris/extension/auth/opa/OpaPolarisAuthorizerFactory.java`
- `external_source/snapshots/apache_polaris/pre/extensions/auth/opa/src/main/java/org/apache/polaris/extension/auth/opa/model/Context.java`
- `external_source/snapshots/apache_polaris/pre/extensions/auth/opa/src/test/java/org/apache/polaris/extension/auth/opa/OpaPolarisAuthorizerFactoryTest.java`
- `external_source/snapshots/apache_polaris/pre/extensions/auth/opa/src/test/java/org/apache/polaris/extension/auth/opa/OpaPolarisAuthorizerTest.java`
- `external_source/snapshots/apache_polaris/pre/extensions/auth/ranger/src/main/java/org/apache/polaris/extension/auth/ranger/RangerPolarisAuthorizerFactory.java`
- `external_source/snapshots/apache_polaris/pre/runtime/service/src/main/java/org/apache/polaris/service/auth/DefaultPolarisAuthorizerFactory.java`
- `external_source/snapshots/apache_polaris/pre/runtime/service/src/main/java/org/apache/polaris/service/config/AuthorizationConfiguration.java`
- `external_source/snapshots/apache_polaris/pre/site/content/in-dev/unreleased/managing-security/external-pdp/opa.md`
- `external_source/snapshots/apache_polaris/pre/site/content/in-dev/unreleased/realm.md`

Run artifacts:

- `results/external_validation_v01/external_v01_polaris_pr4992/manifests/run_manifest.json`
- `results/external_validation_v01/external_v01_polaris_pr4992/manifests/source_manifest.json`
- `results/external_validation_v01/external_v01_polaris_pr4992/manifests/environment_lock.json`
- `results/external_validation_v01/external_v01_polaris_pr4992/manifests/config_hashes.json`
- `results/external_validation_v01/external_v01_polaris_pr4992/preregistration/preregistration.json`
- `results/external_validation_v01/external_v01_polaris_pr4992/preregistration/native_case_index.json`
- `results/external_validation_v01/external_v01_polaris_pr4992/reports/source_lock_determinism.json`
- `results/external_validation_v01/external_v01_polaris_pr4992/reports/case_index_determinism.json`
- `results/external_validation_v01/external_v01_polaris_pr4992/reports/native_replay.json`
- `results/external_validation_v01/external_v01_polaris_pr4992/reports/console_log_registry.json`
- `results/external_validation_v01/external_v01_polaris_pr4992/reports/phase1_eligibility.json`

There are 40 generated files totaling 326,813 bytes. Only one run directory exists, so the repository contains only new results from the current implementation.

### Phase 1.8 Code behavior and implementation method

- `hashing.py` implements canonical UTF-8 JSON, SHA-256, normalized-line-ending semantic hashes, stable content IDs, streaming file hashes, and atomic JSON replacement.
- `source_lock.py` performs two independent filtered Git acquisitions, exact object/ancestry/tree verification, safe repository-relative snapshot materialization, two canonical PR-history fetches, deterministic manifest generation, environment/config locking, and root/run artifact writes. GitHub history requests use `GH_TOKEN` or `GITHUB_TOKEN` when available and otherwise remain public; credentials are confined to request headers and are never logged or written to artifacts.
- `evidence.py` validates immutable refs and run IDs, enforces unique artifact IDs/paths, extracts native cases with the frozen source-only predicate, produces exact line locators, counts forbidden manual touch-label keys, builds the evidence index, and seals preregistration/nonclaims.
- `eventlog.py` exposes a typed `console.log` interface that emits one canonical JSON event per line and flushes immediately.
- `clean_named_run.py` accepts only a safe run ID, resolves the target, requires it to be a direct child of the owned results root, refuses `SEALED`, and removes only the named unsealed directory.
- `phase1_validate.py` performs schema/hash/config/snapshot validation, independent case reconstruction, pre/post replay, all eight eligibility gates, line-level logging adjacency audit, and final run-manifest state transition.
- `run_external_validation.mjs` is fail-fast and executes named-run cleanup, environment verification, source lock, preregistration, eligibility validation, and the full coverage test suite in order.

### Phase 1.9 Structured console statements and identifying comments

`console_log_registry.json` reports 24 statements, 24 immediately adjacent identifying comments, 24 matching event IDs, and registry hash `16dd24498fb1c5b58270e6d467f695b66d91fa9805323d2d25ffa3d6431ee32a`.

| File | Comment line | `console.log` line | Identifying comment |
|---|---:|---:|---|
| `scripts/clean_named_run.py` | 35 | 36 | `# console.log: external.phase1.clean_named_run.start` |
| `scripts/clean_named_run.py` | 40 | 41 | `# console.log: external.phase1.clean_named_run.noop` |
| `scripts/clean_named_run.py` | 46 | 47 | `# console.log: external.phase1.clean_named_run.refused` |
| `scripts/clean_named_run.py` | 50 | 51 | `# console.log: external.phase1.clean_named_run.complete` |
| `scripts/phase1_lock_source.py` | 31 | 32 | `# console.log: external.phase1.lock_source.start` |
| `scripts/phase1_lock_source.py` | 34 | 35 | `# console.log: external.phase1.lock_source.materialize` |
| `scripts/phase1_lock_source.py` | 40 | 41 | `# console.log: external.phase1.lock_source.complete` |
| `scripts/phase1_preregister.py` | 43 | 44 | `# console.log: external.phase1.preregister.start` |
| `scripts/phase1_preregister.py` | 53 | 54 | `# console.log: external.phase1.preregister.index_evidence` |
| `scripts/phase1_preregister.py` | 72 | 73 | `# console.log: external.phase1.preregister.complete` |
| `scripts/phase1_validate.py` | 241 | 242 | `# console.log: external.phase1.validate.start` |
| `scripts/phase1_validate.py` | 254 | 255 | `# console.log: external.phase1.validate.schemas` |
| `scripts/phase1_validate.py` | 261 | 262 | `# console.log: external.phase1.validate.hashes` |
| `scripts/phase1_validate.py` | 299 | 300 | `# console.log: external.phase1.validate.native_replay` |
| `scripts/phase1_validate.py` | 339 | 340 | `# console.log: external.phase1.validate.eligibility_gates` |
| `scripts/phase1_validate.py` | 493 | 494 | `# console.log: external.phase1.validate.complete` |
| `scripts/run_external_validation.mjs` | 46 | 47 | `// console.log: external.phase1.orchestrator.start` |
| `scripts/run_external_validation.mjs` | 49 | 50 | `// console.log: external.phase1.step01.clean_named_unsealed_run` |
| `scripts/run_external_validation.mjs` | 53 | 54 | `// console.log: external.phase1.step02.verify_environment` |
| `scripts/run_external_validation.mjs` | 57 | 58 | `// console.log: external.phase1.step03.lock_source` |
| `scripts/run_external_validation.mjs` | 61 | 62 | `// console.log: external.phase1.step04.preregister` |
| `scripts/run_external_validation.mjs` | 65 | 66 | `// console.log: external.phase1.step05.validate_eligibility` |
| `scripts/run_external_validation.mjs` | 69 | 70 | `// console.log: external.phase1.step06.run_phase_tests` |
| `scripts/run_external_validation.mjs` | 77 | 78 | `// console.log: external.phase1.orchestrator.complete` |

The registry is generated from final source and checked by `test_logging_registry.py`; it is not a manually maintained line-number list.

### Phase 1.10 Verification and stress-test evidence

Authoritative environment:

- Python `3.12.13`
- Node `v22.15.0`
- Git `2.49.0.windows.1`
- Windows 11 AMD64
- dependency lock SHA-256 `c14b5dbe50efe7a91fc1776a7d00f5b58e3a8aae3f6c2436168ea5cc4f4d008a`
- implementation Git SHA bound in the environment lock: `7f4e7904f8fa01b48020017f1181b1bb70fc926e`
- environment hash `f814eeca1b17623ed7acb574f34d1c7291fed428fe66b7066268a8532b911cdc`

Final authoritative tests:

- `35 passed`, `0 failed`, `0 skipped` with `PC_RUN_ID=external_v01_polaris_pr4992`.
- Branch-aware coverage: `88.83%`, above the enforced `85%` minimum.
- Ruff formatting/lint: pass.
- Python compilation: pass.
- Node syntax check: pass.
- Git whitespace/error check for authored/generated normative files: pass.
- Strict JSON Schema validation: source manifest, preregistration, all eight native cases, and eligibility report pass.
- Immutable-ref negative fixtures reject branch names, short SHAs, uppercase SHA, and empty refs.
- Missing-commit and divergent-history fixtures prove the source lock rejects unavailable objects and wrong pre→post ancestry.
- Manifest corruption tests reject duplicate IDs/paths, self-hash mutation, and byte-corrupted snapshots.
- Configuration tests prove any absent or false `phase1_sealed` flag fails closed.
- Named negative tests reject insufficient historical evidence, result-dependent case rules, and `PC_GENERATED` primary cases.
- Cleaner tests remove only the named unsealed run, preserve siblings, reject path traversal, and refuse a sealed run.
- Source-lock fixture uses a three-commit local upstream and proves two independent materializations plus deterministic native-case extraction.
- GitHub history-provider tests prove public default requests and optional authenticated requests without credential persistence.
- Hypothesis property test exercises canonical JSON round-trip/order invariance.

Full clean-rerun stress test:

- Baseline authoritative file count: `40`.
- The safe cleaner removed only `external_v01_polaris_pr4992`.
- The complete orchestrator refetched, rebuilt, revalidated, and retested the phase.
- Regenerated file count: `40`.
- SHA-256 byte differences across every `external_source/` and run artifact: `0`.
- Final rerun tests: `35 passed`; coverage `88.83%`.

Scientific completeness metrics:

- eligibility gates: `8/8`;
- admitted artifact hash coverage: `26/26` (`100%`);
- native case source linkage: `8/8` (`100%`);
- source acquisition passes: `2` plus `2` equal PR-history fetches;
- manual resource-label count in source records: `0`;
- PC-generated primary cases: `0`;
- production/independent case-index match: exact;
- structured log/comment adjacency: `24/24`;
- prohibited downstream scientific outputs: `0`.

### Phase 1.11 Rejected and superseded attempts

These attempts are retained as process evidence and are not cited as authoritative results:

1. The first pre-authoritative test run had `22 passed`, `2 skipped`, and one failure because one authoritative test accessed a not-yet-generated root artifact without applying the module skip guard. The guard was corrected; this run produced no scientific result.
2. The first staged whitespace check detected extra blank lines at EOF in authored files. `.gitattributes` now enforces LF and the extra blank lines were removed before authoritative artifacts were generated.
3. An initial authoritative run passed 8/8 gates and 26 tests but did not yet produce the required line-level console registry. Its unsealed run directory was deleted by the safe cleaner and regenerated after the registry/audit was implemented.
4. A subsequent run passed 27 tests, but review found that a diagnostic determinism report stored hashes of random temporary cache directory names. Those fields never affected source semantics or the manifest, but they prevented byte-identical full artifact reproduction. They were removed, the implementation SHA changed, and all artifacts were regenerated. No output from that superseded run was committed.
5. A clause-level audit found three fail-closed predicates implemented inline but not independently named in tests: result-dependent case selection, missing historical evidence, and PC-generated primary cases. The predicates were isolated, three negative tests were added, and the artifacts were regenerated; commits `76c936e…` and `ba68c30…` were superseded.
6. The first clean rerun after that hardening was interrupted by GitHub's unauthenticated API rate limit after the safe cleaner removed the unsealed named result. The command failed closed and produced no verdict. An optional authenticated-header path was added and tested without persisting the token; artifacts were regenerated from commit `738cf16…`.
7. The final literal WorkPlan audit found four more production-enforced boundaries without isolated negative tests: missing commit, wrong ancestry, unsealed config, and snapshot-byte corruption. Named adversarial tests were added, yielding final implementation commit `7f4e790…`; all authoritative artifacts were regenerated twice and matched byte for byte.

Only the final artifacts bound to implementation SHA `7f4e790…` and committed in `f823d7a…` are authoritative. Earlier result commits are retained as superseded process history but are not present as extra run directories or cited as scientific evidence.

### Phase 1.12 Model training and overfitting disposition

No model was trained, tuned, selected, or benchmarked. Algorithm-development fixtures are separate from the eight scientific native Polaris cases. The primary case rule, refs, target, unit cost, completion cap, route rule, nonclaims, and stop conditions were sealed before any future touch or closure result. Null, infinite, partial, invalid, and route-degenerate outcomes remain mandatory in later phases.

### Phase 1.13 Clause-by-clause WorkPlan compliance audit

| WorkPlan Phase-1 requirement | Compliance | Evidence |
|---|---|---|
| Freeze source, history, cases, rules, costs, completions, route rule, nonclaims, stops before resource results | PASS | Config hashes, preregistration hash, source manifest; no Phase-2/3 outputs. |
| Create all project/tooling files | PASS | Six files listed in Phase 1.6, including generated `uv.lock`. |
| Create all four sealed configs | PASS | `phase1_sealed: true`; hashes bound in preregistration. |
| Create source/evidence/case indexes and byte-exact snapshots | PASS | 29 external-source files; 26 manifest records; 100% hash verification. |
| Create Phase-1 schemas and shared definitions | PASS | Five strict Draft-2020-12 schemas with `additionalProperties: false` for normative top-level/records. |
| Implement `hashing.py`, `source_lock.py`, `evidence.py` | PASS | Final implementation SHA and 88.83% enforced coverage. |
| Implement three Phase-1 scripts and safe cleaner | PASS | Scripts execute through fail-fast orchestrator; cleaner adversarial tests pass. |
| Create required result manifests/preregistration/report | PASS | All required paths plus determinism, replay, and logging audit reports. |
| Fetch exact SHAs twice; verify types, ancestry, trees, hashes | PASS | `source_lock_determinism.json`; source manifest fetch verification all true. |
| Assign allowed evidence roles without manual E/R/A source labels | PASS | Role counts recorded; manual resource-label keys `0`. |
| Deterministic source-only native case selection | PASS | Eight cases; independent reconstruction exact; no result terms in rule. |
| Recover native target rather than treating serialization alone as unqualified final decision | PASS with retained limitation | Target explicitly typed as input certificate; OPA policy consumption linked; paired collision decision absent and disclosed. |
| Admit only source-grounded interventions and exclude invented routes | PASS | One admitted historical action; four exclusions with reasons; route-degenerate disposition. |
| Seal refs, all 8 freeze IDs, unit cost, completion cap 128, claim/sign rules, nonclaims, stops | PASS | `preregistration.json` schema-valid and hash-sealed. |
| Implement P1-E1–P1-E8 and block Phase 2 on failure | PASS | 8/8 machine gates; validator returns nonzero for `INELIGIBLE`. |
| No touch extraction or planner in Phase 1 | PASS | Downstream artifact-name audit `NONE`; no such modules/scripts implemented. |
| Reject mutable refs, missing commits, wrong ancestry, corrupt manifests/snapshots, unsealed config, result-dependent cases, PC-generated cases, and missing history | PASS | Each rejection has a named negative test; all fail closed in the 35-test authoritative suite. |
| Rerun locking; cache paths do not affect semantic hashes | PASS | Two acquisition passes and clean full rerun; 40 files, 0 byte differences. |
| Reconstruct case index independently | PASS | `case_index_determinism.json` exact match. |
| Execute native behavior or deterministic source-faithful replay at both refs | PASS | Nine pre/post checks in `native_replay.json`; exact refs and commands recorded. |
| Phase benchmark: 8/8 gates, 100% artifact/case linkage, 0 manual labels | PASS | Eligibility metrics meet every threshold. |
| Commit implementation/results, update ledger, push, verify | PASS | Implementation `7f4e790…`, authoritative data `f823d7a…`, and ledger `9d18b11…` were pushed to `origin/main`; local and remote ledger SHAs matched. |

Compliance conclusion: **NO OPEN PHASE-1 IMPLEMENTATION OR SCIENTIFIC COMPLIANCE GAP**. Phase 1 is `ELIGIBLE`. The paired-policy limitation and absence of competing routes are scientific properties of the frozen external evidence, not implementation omissions, and are binding inputs to Phase 2.

The final read-only compliance command checked 32 required Phase-1 paths with 0 missing; exactly one run directory; `ELIGIBLE`, 8/8 passed gates, and `phase2_authorized=true`; 100% artifact hash coverage; 100% native-case linkage; 0 manual labels; 0 PC-generated primary cases; exact environment binding to implementation `7f4e790…`; 24 structured statements with adjacent, ID-matching comments; 0 prohibited downstream outputs; and passing Ruff format/lint, Python compilation, Node syntax, and Git whitespace checks. The command returned exit code 0.

### Phase 1.14 Commit structure before remote transaction

- `4ac63beb48be77708e08c16b4961cbf1426123cc` — initial production Phase-1 implementation.
- `4510fc0d142f089e4aeb42d19827b2015ba399de` — deterministic line-ending enforcement.
- `f0c8acc1ded8f71da7e44f0940cd9f5142eaf475` — line-level console event audit.
- `76c936ecd34821c19b79e593756ab9e6c7d2423a` — removed transient cache names; later superseded by explicit boundary-test hardening.
- `ba68c30b72d5dec45c37a6e061cd3a116711a254` — first reproducible result commit; superseded after the clause-level test audit.
- `28152b5084484782d653863f33947db710ed94fb` — isolated the result-dependency, missing-history, and PC-origin predicates and tests.
- `738cf163c57ee5223042fe6f1fa60917f820c3b1` — added credential-safe authenticated GitHub history fetching after a recorded API rate-limit failure.
- `3c303ed4ecb1fbc0830354459f373cfb54386b58` — intermediate result binding; superseded by the final rejection-boundary audit.
- `7f4e7904f8fa01b48020017f1181b1bb70fc926e` — final implementation bound into the authoritative environment lock, including every literal Phase-1 rejection test.
- `f823d7af9663c242f2984fed8b0c21f5164e30e3` — authoritative external evidence and final Phase-1 results.
- Ledger commit: the commit containing this Phase-1 record.

The remote push and SHA verification are recorded in a follow-up ledger subsection after the push succeeds; no remote state is preclaimed here.

### Phase 1.15 Phase-completion transaction and remote verification

- Final implementation bound in the environment: `7f4e7904f8fa01b48020017f1181b1bb70fc926e`.
- Final authoritative result commit: `f823d7af9663c242f2984fed8b0c21f5164e30e3`.
- Complete Phase-1 ledger commit: `9d18b11c5c1a0111eb448523b7380b55677994a9`.
- Push target: `origin/main` at `https://github.com/MAVS-RESEARCH/Naturilistic-Validation..git`.
- Push range: `426f417..9d18b11`.
- Immediate remote verification: local `HEAD` and `refs/heads/main` both resolved to `9d18b11c5c1a0111eb448523b7380b55677994a9`.
- Repository state immediately after verification: clean and synchronized. This subsection is the factual follow-up record of that completed transaction.

Phase-completion transaction: **PASS**.

## Phase 2 record — Extensional Contract and Touch

Status: **AUTHORIZED — NOT STARTED**

Required future entries:

- Contract/completion IDs and hashes.
- `U_H`, `H`, `P_R`, `Lambda`, `omega`, terminal, target, `Q`, `Succ+`, and cost construction.
- Every file/module/schema created.
- Fidelity outcomes, touch completeness, route classification.
- Unit/property/metamorphic tests and exact completion count.
- Exit state and seal evidence.
- Deviations, failures, commits, and push verification.

## Phase 3 record — Matched Freeze Experiment

Status: **BLOCKED PENDING PHASE 2**

Required future entries:

- Pre-run results inventory and safe cleanup record.
- All case/completion/cost allocations across F000–F111.
- Planner implementation/certificates and alternate exact cross-check.
- Same-instance and action-mask diffs.
- C1–C10 outcomes.
- Full retained results/failure cards and classifications.
- Determinism/runtime results, deviations, commits, and push verification.

## Phase 4 record — Independent Audit, Claims, and Seal

Status: **BLOCKED PENDING PHASE 3**

Required future entries:

- Independent implementation boundary and import scan.
- Source/case/contract/touch/planner/result recomputation.
- C1–C10 independent verification and A1–A12 detection results.
- Claim ledger predicates and exact allowed language.
- Artifact graph completeness, seal hashes, cleaner refusal, post-seal stability.
- Clean one-command reproduction.
- Final verdict, paper outputs, deviations, commits, and push verification.

## 5. Next authorized action

After the Phase-1 commits are pushed and remotely verified, the next authorized scientific action is Phase 2 only: recover and seal the extensional contract and mechanically derive touch from the already frozen evidence. Phase 2 may not add a competing route or paired primary case that was not admitted by Phase 1.
