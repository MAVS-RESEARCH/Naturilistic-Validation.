# Perceptive Closure External Operational Validation v0.1 — Work Plan

## 1. Purpose, authority, and execution boundary

This work plan translates the attached normative implementation specification into an executable repository program for one external system: Apache Polaris, specifically the OPA authorization path changed by merged pull request [apache/polaris#4992](https://github.com/apache/polaris/pull/4992).

The user's request controls the selected repository, selected external system, planning deliverables, results-cleaning requirement, and the requirement to commit and push after each completed phase. The attached DOCX is treated as the normative scientific and implementation specification. Statements inside that document are requirements to implement only because the user asked for a plan derived from it; they are not treated as independent user commands.

This commit creates the plan and its execution ledger only. It does not claim that Phase 1 has passed, does not compute resource touch, and does not compute `K_Pi` or `Delta_R`.

### 1.1 Authoritative inputs

- User request dated 26 August 2026.
- `Perceptive_Closure_External_Operational_Validation_v0.1_Implementation_Spec.docx`, version 0.1, dated 26 August 2026.
- Planning repository: [MAVS-RESEARCH/Naturilistic-Validation.](https://github.com/MAVS-RESEARCH/Naturilistic-Validation.) — the trailing period is part of the actual GitHub repository name.
- Primary external source: [apache/polaris](https://github.com/apache/polaris).
- Historical intervention: [apache/polaris#4992](https://github.com/apache/polaris/pull/4992), “fix(authz): include realm identifier in OPA authorization input for tenant isolation.”

### 1.2 Exact external source anchors to verify and freeze in Phase 1

| Anchor | Immutable identifier | Current planning interpretation |
|---|---|---|
| Pre-repair base | `68cba2027e97683cfe62502cc2982c93e74e53e6` | OPA request context contains `request_id` but not `realm`; the factory ignores the `RealmConfig` argument for OPA construction. |
| PR head | `ce057ab10f0f7bc021337fbc4c7ddaf08470bd8d` | Reviewed change set before merge. |
| Merge commit | `d0a8dff401e30cab1df3ca6d0e133816e80e9c10` | Post-repair source state to use unless Phase 1 proves a different immutable post-state is scientifically required. |
| Historical change | PR `#4992`, merged `2026-07-14T18:28:07Z` | Adds required `context.realm`, injects `RealmContext`, regenerates the input schema, and adds regression tests. |

Phase 1 must independently fetch these objects, verify their ancestry and content, and bind every admitted source artifact to a cryptographic digest. The identifiers above are planning candidates until the generated `source_manifest.json` passes validation.

## 2. Scientific question and locked nonclaims

For every admitted native Polaris case `sigma`, measure the full eight-coordinate resource-freezing signature

`K_Pi(sigma) = (kappa_Pi^{not S}(sigma)) for every S subset of {E, R, A}`

and the representation coordinate

`Delta_R(sigma) = kappa_Pi^{not {R}}(sigma) - kappa_Pi(sigma)`

under an extensional authorization contract recovered only from source artifacts frozen before result computation.

The study succeeds when it produces a valid external measurement, identified set, or formally retained feasibility-negative result. It does not require a positive `Delta_R`.

The following claims remain mechanically locked false throughout all phases:

- PC is superior to another architecture, planner, model, benchmark, or authorization system.
- Positive `Delta_R` is prevalent in deployed systems.
- Apache Polaris is representative of a population of systems.
- PC improves accuracy, UAR/FRR, safety, latency, deployment readiness, or operator burden.
- One positive case establishes general representation necessity.
- One zero-gap case falsifies PC.
- This experiment establishes universal safety or zero error.

## 3. Preliminary Polaris Phase-1 eligibility audit

This is a planning audit, not the sealed Phase-1 verdict. Its purpose is to identify exactly what must be proved before implementation may advance.

| Gate | Planning evidence | Preliminary status | Required Phase-1 disposition |
|---|---|---|---|
| P1-E1 independent origin | Apache Polaris and its OPA integration predate this validation; PR #4992 merged before the v0.1 spec date. | Strong candidate pass | Verify repository history/timestamps and record origin evidence. |
| P1-E2 historical change | PR #4992 documents the cross-realm context gap and the realm-injection repair. | Strong candidate pass | Freeze PR body, commits, review discussion, changed files, and changelog entry. |
| P1-E3 source recoverability | Exact pre/base, head, and merge SHAs are fetchable. | Strong candidate pass | Fetch by SHA twice, rehash, and prove ancestry. |
| P1-E4 authorization target | Realm documentation promises realm isolation; PR consensus says OPA policies must be able to perform realm-based authorization. The added tests mostly assert serialized `input.context.realm`, not a paired cross-realm allow/deny decision. | **Conditional / unresolved** | Recover a native terminal allow/deny or certificate target from existing policies/tests/history. If only representation delivery is recoverable, mark target underidentified or ineligible rather than inventing a decision. |
| P1-E5 native cases | Post-repair tests include `testFactoryPassesRealmToAuthorizerContext`, `testFactoryUsesDistinctRealmValues`, `serializesInputWithRealm`, `serializesRealmInAuthorizePath`, and realm assertions in existing request-shape tests. | Candidate pass, scope unsealed | Freeze a deterministic source-only inclusion rule and enumerate all directly affected native cases. Confirm whether a true paired collision case exists. |
| P1-E6 intervention surface | The historical action “thread required realm into OPA context” is real and source-grounded. Possible competing routes include another native authorizer or another source-grounded realm isolation mechanism, but their admissibility within the same case has not been proved. | Minimum action exists; competing-route semantics unresolved | Admit only interventions supported by pre-existing Polaris artifacts. If the realm-injection repair is the sole closing route, classify it `R-ONLY ROUTE` or `SINGLE ACTION`; do not manufacture a non-R alternative. |
| P1-E7 no PC contamination | PR, tests, docs, and implementation predate this validation and contain no PC E/R/A labeling. | Candidate pass | Scan admitted artifacts and case origins; reject any PC-generated primary case. |
| P1-E8 execution/reconstruction | Unit tests use captured OPA requests; OPA integration tests and documented policy structure exist. | Candidate pass | Prove the chosen native behavior can run or be deterministically replayed at both source refs. |

**Planning verdict:** `PROVISIONAL HOLD`. Polaris is a strong Phase-1 candidate, but the scientific gate is not passed until the final authorization target, native cross-realm case population, and admissible competing-route surface are source-grounded and sealed. The implementation must retain an `INELIGIBLE` result if these cannot be established without author invention.

### 3.1 Phase-1 evidence set to inspect

At minimum, source locking will include the following paths at the relevant commit(s), plus any transitive files actually cited during semantic recovery:

- `extensions/auth/opa/opa-input-schema.json`
- `extensions/auth/opa/src/main/java/org/apache/polaris/extension/auth/opa/OpaAuthorizationConfig.java`
- `extensions/auth/opa/src/main/java/org/apache/polaris/extension/auth/opa/OpaPolarisAuthorizer.java`
- `extensions/auth/opa/src/main/java/org/apache/polaris/extension/auth/opa/OpaPolarisAuthorizerFactory.java`
- `extensions/auth/opa/src/main/java/org/apache/polaris/extension/auth/opa/model/Context.java`
- `extensions/auth/opa/src/main/java/org/apache/polaris/extension/auth/opa/model/README.md`
- `extensions/auth/opa/src/test/java/org/apache/polaris/extension/auth/opa/OpaPolarisAuthorizerFactoryTest.java`
- `extensions/auth/opa/src/test/java/org/apache/polaris/extension/auth/opa/OpaPolarisAuthorizerTest.java`
- relevant OPA integration-test policies and fixtures under `extensions/auth/opa/src/*IntTest*`
- `site/content/in-dev/unreleased/managing-security/external-pdp/opa.md`
- `site/content/in-dev/unreleased/realm.md`
- `runtime/service/src/main/java/org/apache/polaris/service/config/AuthorizationConfiguration.java`
- `polaris-core/src/main/java/org/apache/polaris/core/config/RealmConfig.java`
- `polaris-core/src/main/java/org/apache/polaris/core/context/RealmContext.java`
- the native internal and Ranger authorization paths only if they are proposed as source-grounded competing interventions
- PR #4992 body, commit messages, review comments, approvals, changed-file inventory, and changelog entry

## 4. Global implementation invariants

These constraints apply to every phase and every code path.

1. **External independence:** external source and the historical change predate this experiment.
2. **Source-first semantics:** every normative semantic fact resolves to a frozen source artifact and locator.
3. **No manual resource labels:** source inputs cannot assign E/R/A. Touch is compiled only from normalized `H`, canonical `P_R`, and normalized `Lambda` deltas.
4. **Common history universe:** every partition is an equivalence relation over one `U_H`, or uses an explicitly validated global restriction/extension rule.
5. **Same-instance freezing:** condition manifests differ only in the forbidden resource set, derived action mask, and downstream planner output.
6. **Full retention:** positive, null, infinite, partially identified, ineligible, and invalid outcomes remain visible.
7. **Information firewall:** Phase 1 cannot compute touch/results; Phase 2 cannot execute the freeze planner; Phase 3 cannot mutate the sealed contract; Phase 4 cannot mutate Phase 1–3 artifacts.
8. **Fail closed:** a missing source locator, hash mismatch, contract ambiguity, fidelity mismatch, invalid planner relation, or audit mismatch blocks stronger claims.
9. **Independent audit:** audit code cannot import production extraction, touch, planning, aggregation, or claim-decision functions.
10. **Extended-real correctness:** scientific values are `FINITE(value)`, `POS_INF`, or an explicit undefined relation; no large finite sentinel and no `infinity - infinity`.
11. **Nonnegative frozen costs:** unit intervention cost is primary. Native costs are secondary only when they pre-exist PC and are provenance-linked.
12. **Immutability:** accepted run artifacts are content-addressed, namespaced, sealed, and verified byte-stable after sealing.

## 5. Repository architecture

The repository root is itself the dedicated `pc_external_validation_v01` project, so no redundant nested project directory will be added.

```text
.
├── README.md
├── WorkPlan.md
├── Path.md
├── pyproject.toml
├── uv.lock
├── package.json
├── configs/
│   ├── experiment.yaml
│   ├── costs.yaml
│   ├── controls.yaml
│   └── completion_policy.yaml
├── external_source/
│   ├── source_manifest.json
│   ├── evidence_index.json
│   ├── native_case_index.json
│   └── snapshots/apache_polaris/{pre,post,history}/
├── schemas/
│   ├── source_manifest.schema.json
│   ├── preregistration.schema.json
│   ├── semantic_fact.schema.json
│   ├── extensional_contract.schema.json
│   ├── state.schema.json
│   ├── intervention.schema.json
│   ├── touch_record.schema.json
│   ├── native_case.schema.json
│   ├── freeze_result.schema.json
│   ├── completion_set.schema.json
│   ├── control_result.schema.json
│   ├── audit.schema.json
│   └── claim_ledger.schema.json
├── src/pc_external/
│   ├── source_lock.py
│   ├── evidence.py
│   ├── contract.py
│   ├── partitions.py
│   ├── authority.py
│   ├── interventions.py
│   ├── touch.py
│   ├── planner.py
│   ├── freeze.py
│   ├── completions.py
│   ├── controls.py
│   ├── claims.py
│   └── hashing.py
├── src/pc_external_audit/
│   ├── source_audit.py
│   ├── contract_audit.py
│   ├── touch_audit.py
│   ├── planner_audit.py
│   └── claims_audit.py
├── scripts/
│   ├── phase1_lock_source.py
│   ├── phase1_preregister.py
│   ├── phase1_validate.py
│   ├── phase2_extract_contract.py
│   ├── phase2_validate_contract.py
│   ├── phase2_extract_touch.py
│   ├── phase2_seal.py
│   ├── phase3_run_freezes.py
│   ├── phase3_run_controls.py
│   ├── phase3_validate.py
│   ├── phase3_aggregate.py
│   ├── phase4_independent_audit.py
│   ├── phase4_corruption_tests.py
│   ├── phase4_generate_claims.py
│   └── run_external_validation.mjs
├── tests/
│   ├── fixtures/
│   ├── unit/
│   ├── phase1/
│   ├── phase2/
│   ├── phase3/
│   ├── phase4/
│   ├── metamorphic/
│   └── corruption/
└── results/external_validation_v01/<run_id>/
    ├── manifests/
    ├── preregistration/
    ├── contract/
    ├── raw/
    ├── processed/
    ├── controls/
    ├── audit/
    ├── reports/
    └── SEALED
```

Normative JSON Schemas will use Draft 2020-12 and `additionalProperties: false`. Parquet outputs will have explicit column inventories and validators. Canonical JSON will use UTF-8, stable key ordering, normalized line endings, no scientific timestamps inside hashed objects, and SHA-256 digests.

## 6. Results hygiene and run discipline

The cloned planning repository contained only `LICENSE`; there were no previous `results/` artifacts to clear. This satisfies the user's initial clean-results requirement without deleting data.

Before every authoritative Phase-3 run:

1. Inventory `results/external_validation_v01/` and record the inventory in `Path.md`.
2. Remove only stale, explicitly named, **unsealed** run directories after resolving and verifying that the target is a strict child of the repository-owned results root.
3. Refuse recursive deletion of the results root, wildcard targets, unresolved paths, or any run containing `SEALED`.
4. If older tracked result sets must be absent from the final branch, remove them in an explicit, recoverable Git commit with their prior hashes recorded; never mutate a retained sealed run in place.
5. Create a new unique `run_id`; unequal existing artifacts may never be overwritten.

Every accepted run records the run ID, external source SHAs/tree hashes, implementation Git SHA, environment lock hash, config hash, source-manifest hash, native-case-index hash, contract hash, and artifact-graph hash.

Each script and orchestrator step emits one structured factual event with an immediately preceding identifying source comment. After source stabilization, Phase 4 audits event adjacency, IDs, and registered final line numbers.

## 7. Four-phase implementation plan

The phase count deliberately matches the specification's four scientific gates. Repository scaffolding, schemas, and generic test fixtures are created inside the earliest phase that needs them rather than becoming a fifth scientific phase.

---

## Phase 1 — External System Lock and Preregistration

### Objective and scope

Freeze the Apache Polaris source object, historical intervention, native case population, evidence roles, environment, cost policy, completion policy, route-degeneracy rule, nonclaims, and stop conditions before any E/R/A touch or `K_Pi` result can be produced.

This phase answers the user's specific eligibility question: can pre-existing Polaris source independently pin (a) the authorization target, (b) native cross-realm cases, (c) the historical intervention, and (d) enough admissible route semantics to support a faithful counterfactual? The result may be `ELIGIBLE` or `INELIGIBLE`; no fallback system may be silently substituted.

### Files and artifacts to create

- Project/tooling: `README.md`, `pyproject.toml`, `uv.lock`, `package.json`, `.gitignore`.
- Config: all four files in `configs/`, initially sealed with the Polaris IDs and all eight freeze sets but no touch assignments.
- Source evidence: `external_source/source_manifest.json`, `evidence_index.json`, `native_case_index.json`, and byte-exact snapshots of every cited source fragment.
- Phase-1 schemas: `source_manifest`, `preregistration`, `native_case`, plus shared strict-ID/hash definitions.
- Production modules: `hashing.py`, `source_lock.py`, `evidence.py`.
- Scripts: `phase1_lock_source.py`, `phase1_preregister.py`, `phase1_validate.py`, and the safe named-run cleaner used by the orchestrator.
- Results: `manifests/run_manifest.json`, `manifests/environment_lock.json`, `manifests/config_hashes.json`, `preregistration/preregistration.json`, `preregistration/native_case_index.json`, and `reports/phase1_eligibility.json`.
- Tests: `tests/unit/test_hashing.py`, `tests/phase1/*`, immutable-ref fixtures, manifest corruption fixtures, and deterministic case-index fixtures.

### Code to produce and how it will work

1. **Source lock.** Fetch Polaris by exact SHA into a cache outside normative artifacts; verify the repository origin, object type, commit ancestry, tree IDs, PR metadata, and two independent fetch/rehash passes. Copy only cited byte-exact artifacts into snapshots and record path, source ref, artifact role, byte hash, semantic hash, and allowed influence.
2. **Evidence indexing.** Assign stable content-derived artifact IDs and roles: `SOURCE_SEMANTICS`, `NATIVE_TARGET`, `NATIVE_TEST`, `HISTORICAL_REPAIR`, `EVALUATOR_ONLY`, or `EXCLUDED`. Phase-1 schemas will not contain E/R/A resource labels.
3. **Native case indexing.** Apply a preregistered source-only rule: include every upstream test/request assertion directly tied to PR #4992's realm distinction, with no filtering based on later closure results. Paired cross-realm cases must use existing source fixtures or exact source-defined valid combinations; PC-created examples can be diagnostic only.
4. **Target recovery audit.** Trace each case from request construction through OPA input and existing policy/test expectation to a native allow/deny or terminal certificate. Merely proving that `realm` is serialized is not automatically a terminal authorization target.
5. **Intervention-surface audit.** List only source-grounded actions. The historical realm-injection repair is a candidate action. Internal/Ranger authorizer switching, policy endpoint separation, name changes, or other routes enter `Q` only if Polaris source proves they are admissible at the declared checkpoint without changing the case identity. Otherwise they are excluded with reason codes.
6. **Preregistration.** Freeze `primary_system_id`, exact refs, PR ID, native-case rule, all eight freeze sets, unit primary cost, any eligible native secondary costs, completion cap `128`, positive sign-invariance rule, route classification, nonclaims, and stop conditions.
7. **Eligibility validator.** Implement P1-E1 through P1-E8 as machine-readable booleans with evidence paths and reason codes. It must stop Phase 2 unless all required gates pass.

Phase 1 may read external source but is prohibited from deriving touch, running a freeze mask, or invoking a closure planner.

### Verification and benchmarks

- Reject mutable branch-only refs, missing commits, wrong ancestry, duplicate artifact IDs, hash mismatches, unsealed config, missing historical evidence, result-dependent case rules, and `PC_GENERATED` primary cases.
- Re-run source lock and case indexing twice; canonical manifest/case hashes must match.
- Rename local cache paths; semantic hashes must remain unchanged.
- Reconstruct the case index independently from the rule and require exact equality.
- Run the relevant native Polaris tests or a deterministic source-faithful replay at both refs. Capture commands, environment, exit status, and outputs.
- Benchmark is not throughput: Phase 1 completeness is `8/8 eligibility gates`, `100% admitted artifacts hashed`, `100% native cases source-linked`, `0 manual resource labels`, and deterministic reruns.

### Exit gate and outputs

`ELIGIBLE` iff all P1-E gates pass, manifests and preregistration validate, at least one native case exists, source hashes are stable, native behavior is executable/reconstructable, and no primary case is PC-generated. Otherwise write and retain `INELIGIBLE` with reason codes and do not enter Phase 2.

### Phase completion transaction

1. Update the Phase-1 section of `Path.md` with planned-versus-actual scope, every file, commands, tests, results, failures, deviations, and gate evidence.
2. Commit implementation/results as a phase commit.
3. Commit the ledger update referencing the implementation commit.
4. Push both commits to `origin/main` and verify the remote contains them.

---

## Phase 2 — Extensional Contract Recovery and Mechanical Touch Extraction

### Objective and scope

Recover `M_ext = (S, s0, U_H, H, P_R, Lambda, omega, Q, Succ+, Terminal, A_Pi, c)` from the sealed Phase-1 evidence without observing freeze results, validate behavioral fidelity, represent ambiguity as exact completions, and derive every action's resource touch mechanically.

### Files and artifacts to create

- Schemas: `semantic_fact`, `extensional_contract`, `state`, `intervention`, `touch_record`, and `completion_set`.
- Production modules: `contract.py`, `partitions.py`, `authority.py`, `interventions.py`, `touch.py`, `completions.py`.
- Scripts: `phase2_extract_contract.py`, `phase2_validate_contract.py`, `phase2_extract_touch.py`, `phase2_seal.py`.
- Contract outputs: `semantic_facts.jsonl`, `history_universe.json`, `extensional_contract.json`, `completion_set.json`, `contract_provenance.json`, `touch_records.parquet`, `touch_summary.json`, `route_classification.json`, `fidelity_report.json`, and `CONTRACT_SEALED`.
- Tests: minimal E/R/A/mixed/empty touch fixtures, partition fixtures, completion fixtures, provenance-locator fixtures, taint fixtures, and native-fidelity cases.

### Code to produce and how it will work

1. **Two-pass architecture.** Pass A extracts immutable semantic facts with provenance and no resource labels. Pass B compiles those facts into PC objects only after fact validation.
2. **Semantic facts.** Each `SemanticFact` has a content-derived ID, subject, structured statement, artifact ID, exact locator, evidence type (`DIRECT`, `DERIVED`, `INCOMPLETE`), derivation rule, conflicts, and primary-inclusion flag.
3. **Common `U_H`.** Enumerate only source-valid authorization histories relevant to frozen cases. Each history has a stable ID and provenance. If a symbolic universe is necessary, its validity predicate and canonical case enumeration are explicit.
4. **`H`.** Normalize admitted authorization-relevant evidence by stable identities. Distinguish evidence existence from evidence admission.
5. **`P_R`.** Compute the certificate-facing partition over the same `U_H`: evaluate source-grounded representation keys, group history IDs, discard raw key names, sort blocks/members, and hash canonical blocks. Equality is equivalence-relation equality, not raw label equality. `partition_diff` emits witness history pairs.
6. **`Lambda`.** Canonicalize permitted sources, fields, predicates, attestations, and checks with admissibility status, distinct from whether information exists.
7. **`omega`.** Include only controller-visible fields supported by interfaces/replay semantics. Taint evaluator-only truth and reject any leak.
8. **Terminal/target semantics.** Bind each case's `A_Pi` and terminal certificate to native policies/tests/history. Conflicts create completion branches; they are never resolved by preference.
9. **`Q` and `Succ+`.** Every atomic intervention carries preconditions, atomicity, complete positive-support successors, public effect, provenance, unit cost, optional native cost, and no manually stored touch. Mixed effects remain atomic unless Polaris independently exposes subactions.
10. **Completions.** Generate dimensions only from conflicting or incomplete source facts, reject author priors, deduplicate by contract hash, and enumerate exactly up to `128`. Above the cap, use an exact symbolic identified-set solver if implemented; otherwise return `SEMANTICS_INSUFFICIENT`.
11. **Touch.** For every reachable `(state, action)`, union changes across all positive-support successors: E iff normalized `H` changes, R iff canonical `P_R` changes, A iff normalized `Lambda` changes. Emit concrete witnesses and provenance hashes.
12. **Route classification.** Classify each case before results as `NONDEGENERATE`, `R-ONLY ROUTE`, `SINGLE ACTION`, or `NO REPAIR SPACE`. A route is admitted because of source semantics, never because it creates a preferred result.
13. **Fidelity.** The unrestricted reconstructed model must reproduce native pre-repair and post-repair behavior, target, controller visibility, transition support, and atomicity for every completion admitted to Phase 3.

Phase 2 may read only frozen Phase-1 evidence and is prohibited from executing the freeze planner or viewing `K_Pi`.

### Verification and benchmarks

- Validate all source locators and prove every normative fact has lineage.
- Unit-test common-domain typing; partition rename invariance; witness generation; history order/duplicate invariance; authority-versus-metadata distinction; E/R/A/mixed/empty truth tables; successor-union touch; and manual-label rejection.
- Property-test permutation invariance of `U_H`, actions, artifacts, and serialization.
- Prove `100%` reachable state-action pairs have exactly one derived touch record and witness set.
- Require native fidelity on `100%` included cases/completions; one mismatch blocks Phase 3.
- Enumerate all completions when count is `<=128`; no sampling is permitted for primary results.
- Benchmark exactness and tractability: prefer `<=500` states per case after a provenance-preserving reduction. A computational limit yields a documented failure, not an approximate point estimate.

### Exit gate and outputs

- `IDENTIFIED`: unique valid contract, fidelity pass, touch pass.
- `PARTIALLY_IDENTIFIED`: exact finite completion family, every completion fidelity-valid, touch complete.
- `SEMANTICS_INSUFFICIENT`: required semantics cannot be recovered without invention.
- `INVALID`: source mutation, native mismatch, hidden-truth leakage, typing failure, or touch-invariant failure.

Only the first two states may advance to Phase 3. The same commit/push and `Path.md` transaction defined in Phase 1 applies.

---

## Phase 3 — Matched Resource-Freezing Experiment

### Objective and scope

Run the unrestricted condition and all seven nonempty resource-freeze conditions on byte-identical cases/contracts, compute exact closure complexity under every preregistered cost contract, execute ten mandatory controls, retain every outcome, and aggregate without filtering null or infinite rows.

### Files and artifacts to create

- Schemas: `freeze_result` and `control_result` plus Parquet type/column validators.
- Production modules: `planner.py`, `freeze.py`, `controls.py`.
- Scripts: `phase3_run_freezes.py`, `phase3_run_controls.py`, `phase3_validate.py`, `phase3_aggregate.py`.
- Raw outputs: condition manifests, `freeze_policy_traces.parquet`, `freeze_results.jsonl`, and planner certificates.
- Processed outputs: `case_results.parquet`, `identified_sets.parquet`, `summary.json`, `paper_table.csv`, full freeze-lattice tables, allocation reports, and failure cards.
- Control outputs: `control_results.jsonl` with transformation inputs, expected invariants, observed results, evidence, and pass/fail.
- Tests: exact planner fixtures, cycle/improper-policy fixtures, same-instance diff fixtures, action-mask fixtures, all eight freeze allocations, and aggregation-retention fixtures.

### Code to produce and how it will work

1. **Freeze lattice.** Execute exactly `F000 {}`, `F100 {E}`, `F010 {R}`, `F001 {A}`, `F110 {E,R}`, `F101 {E,A}`, `F011 {R,A}`, and `F111 {E,R,A}`.
2. **Action masks.** Retain an action iff its derived touch is disjoint from the forbidden set. Never split mixed-touch actions unless a distinct source-grounded action exists.
3. **Same-instance manifests.** Canonically serialize every condition. A validator permits differences only in the forbidden set, derived mask, and planner outputs; changes to initial state, target, `U_H`, `H/P_R/Lambda/omega`, successors, costs, identity, or provenance invalidate the entire Phase-3 namespace.
4. **Exact planner.** Use deterministic Dijkstra/dynamic programming for finite deterministic graphs and an exact observation-class proper-policy solver for positive-support branching. Detect improper cycles explicitly. Minimize worst-supported accumulated nonnegative cost to valid terminal closure. Retain all optimal action IDs in canonical order and emit proof certificates, including infinity/unreachability witnesses.
5. **Metrics.** Compute full unit-cost `K_Pi`, optional source-grounded native-cost `K_Pi`, `Delta_R` relations, structural-R and zero-gap flags, route class, identification status, and audit eligibility.
6. **Extended-real relations.** Emit `FINITE_POSITIVE`, `FINITE_ZERO`, `STRUCTURAL_POSITIVE`, `BOTH_INFINITE`, or `UNDEFINED`. `FINITE_NEGATIVE` under pure action removal is an invalid-run detector.
7. **Completions.** Solve every case × completion × freeze × cost contract. Aggregate exact identified sets; positive claims require point identification or positive sign invariant over all completions.
8. **Controls C1–C10.** Run representation-value rename, ordering permutation, irrelevant metadata perturbation, empty-touch no-op, exact freeze audit, mixed-action atomicity challenge, terminal-label isolation, provenance deletion, hidden-truth taint, and completion-order permutation on isolated copies.
9. **Complete retention.** Produce one result row or explicit failure card for every native case. Never drop zero-gap, both-infinite, partial, insufficient, or invalid rows.

### Verification and benchmarks

- Compare the production optimum with exhaustive policy enumeration or an alternate exact algorithm on all small graphs.
- Require all `8` conditions for every case/completion/cost contract and exact action-mask equality.
- Check action-removal monotonicity and superset-freeze monotonicity wherever values are comparable.
- Reject negative `Delta_R`, sentinel infinity, mismatched manifests, missing cases, missing freeze cells, mutated upstream hashes, or failed controls.
- Run C1–C10 with `10/10` required passes.
- Determinism benchmark: authoritative reruns must produce byte-identical processed scientific objects, excluding explicitly non-scientific timestamps.
- Runtime budget: cases × completions × `8` × cost contracts, normally minutes to low hours on a laptop; no GPU. If exact computation is infeasible, emit a computational-limit failure card rather than approximating.

### Result classification

- `POSITIVE_FINITE`: finite `F010 > F000`.
- `STRUCTURAL_R`: finite `F000`, infinite `F010`, with route-degeneracy qualifier.
- `ZERO_GAP`: finite equality.
- `BOTH_INFINITE`: no defined `Delta_R` claim.
- `PARTIAL_SIGN`: completions span zero/positive or otherwise multiple values.
- `INSUFFICIENT`: no complete admissible contract.
- `INVALID`: any scientific gate fails.

### Exit gate and outputs

`MEASURED` requires a sealed identified/partially identified contract, complete case allocation, all eight conditions, exact same-instance/action-mask validation, all ten controls, valid mathematical relations, and no upstream mutation. Otherwise the run is `INVALID RUN`; Phase 4 may diagnose it but cannot support claims.

Before an authoritative run, apply the results hygiene in Section 6 so only results generated by the new implementation remain on the working branch. The same commit/push and `Path.md` transaction defined in Phase 1 applies.

---

## Phase 4 — Independent Audit, Falsification, Claim Gate, and Seal

### Objective and scope

Independently recompute the scientific result from frozen raw inputs, prove the pipeline fails closed under deliberate corruption, generate only mechanically supported claim language, build the complete provenance graph, seal the run, and verify clean one-command reproduction.

### Files and artifacts to create

- Schema: `audit.schema.json`, `claim_ledger.schema.json`.
- Independent code: all five modules in `src/pc_external_audit/`; import guards forbid production semantic/planning/claim functions.
- Production claim module: `src/pc_external/claims.py` reads only audited gates and processed results.
- Scripts: `phase4_independent_audit.py`, `phase4_corruption_tests.py`, `phase4_generate_claims.py`, and finalized `run_external_validation.mjs`.
- Audit outputs: `independent_touch.parquet`, `independent_results.parquet`, `corruption_report.json`, `clause_audit.json`, `audit.json`, mismatch reports, import-scan report, and artifact graph.
- Reports: `CLAIMS.md`, `REPRODUCE.md`, `external_case_report.md`, `failure_cards.jsonl`, `console_log_registry.json`, and paper-facing tables.
- Seal: `SEALED` binding source, preregistration, contract, raw/processed results, controls, audit, claims, implementation SHA, environment, and artifact graph.
- Tests: independent recomputation, import-boundary scans, A1–A12 attacks, claim predicates, seal/cleaner refusal, and clean-environment reproduction.

### Code to produce and how it will work

1. **Independent source audit.** Rehash external artifacts, reconstruct the native case index from the preregistered rule, and verify every semantic locator.
2. **Independent semantics.** Rebuild `U_H`, `H`, `P_R`, `Lambda`, and touch with independently written normalization and comparison logic.
3. **Independent planner.** Recompute every freeze value and identified set using a second exact algorithm or exhaustive policy-tree enumeration. Compare scientific columns exactly.
4. **Aggregation audit.** Prove a bijection between native cases and result/failure-card allocation; detect filtered nulls, infinite rows, or altered table cells.
5. **Controls audit.** Re-run or independently verify C1–C10.
6. **Corruptions A1–A12.** On isolated copies, flip touch, alter a source byte, delete provenance, mutate a partition block, add/remove frozen actions, change an initial state, leak evaluator truth, change cost, drop a zero row, replace infinity with a sentinel, and hand-edit the claim ledger. Every attack must be detected by its intended fail-closed layer.
7. **Claim ledger.** Separate `external_operational_validation` from result sign. Mechanically lock prevalence, superiority, and deployment flags false. Generate every report sentence from a claim ID, evaluated predicate, and evidence paths; manual strengthening creates a hash mismatch.
8. **Artifact graph.** Trace every paper-facing value backward: result row → planner certificate → condition manifest → touch record → contract → semantic fact → frozen source. Traverse forward and backward and require zero unindexed scientific files.
9. **Seal and reproduction.** Seal all hashes, prove cleaner refusal, rerun the full audit read-only with identical hashes, then reproduce from a clean frozen environment with one command.

### Verification and benchmarks

- `100%` production/audit touch equality.
- `100%` production/audit scientific result equality.
- `10/10` mandatory controls pass.
- `12/12` deliberate corruptions detected.
- `0` independent-audit findings for a supported claim.
- `0` unindexed scientific artifacts.
- Post-seal bytes and hashes remain stable.
- One-command clean reproduction succeeds.
- All cases, including null and infinite outcomes, remain present.

### Final verdict taxonomy

- `PASS — POSITIVE EXTERNAL`
- `PASS — NULL EXTERNAL`
- `PASS — PARTIAL EXTERNAL`
- `PASS — FEASIBILITY NEGATIVE`
- `FAIL — INVALID EXPERIMENT`
- `STOP — THEORY CONFLICT`

Only the result-dependent language authorized by the claim ledger may enter paper-facing outputs. A positive case is described as one independently engineered instance; a null is a valid measured zero-gap case; a partial result is an identified set; insufficient semantics are retained without a point claim.

### Phase completion transaction

Update `Path.md` with a clause-by-clause planned-versus-actual record, commit scientific outputs and seal, commit the final ledger/reference update, push, verify the remote, and record the remote branch state. External tag/release publication remains optional and is not required for scientific validity.

## 8. Model training and anti-overfitting policy

No statistical or machine-learning model will be trained in this project. The external study uses exact semantic extraction, finite transition reconstruction, and exact planning. Therefore training/validation splits, learned-parameter benchmarks, and model-generalization claims are not applicable.

The analogous anti-overfitting protections are mandatory:

- The external system, source refs, case rule, cost policy, completion policy, and claim rules are frozen before results.
- Development unit fixtures are synthetic and may validate algorithms but can never enter the scientific external case population.
- Scientific cases come only from pre-existing Apache Polaris artifacts.
- The primary result is never tuned against a benchmark.
- Native fidelity checks are separate from planner unit fixtures.
- C1–C10 transformations are separate from the source cases used to define the contract.
- The independent audit implementation shares no production semantic/planning logic.
- A1–A12 corruption attacks are entirely different from the constructive fixtures used to implement the pipeline.
- Exact exhaustive/alternate-algorithm planner checks use separate small graphs from the external Polaris cases.
- All inconvenient outcomes are retained, so case/result selection cannot overfit toward a positive claim.

## 9. Data-contract minimums

The schemas must contain at least the fields required by the specification:

- `source_manifest`: run/system IDs, origin, pre/post refs, artifacts, source-tree hash, environment ref, creation metadata, manifest hash.
- `preregistration`: system/change IDs, case rule, costs, completion policy, route rule, claim rules, stop conditions, sealed-before-Phase-2 flag.
- `semantic_fact`: fact identity, subject, structured statement, source artifact/locator, evidence type/derivation, conflicts, primary inclusion.
- `extensional_contract`: `U_H`, states, initial state, `H/P_R/Lambda/omega`, terminal classes, targets, interventions, costs, source-manifest hash, contract hash.
- `state`: checkpoint, public payload, semantic hashes, terminal status.
- `intervention`: preconditions, provenance, atomicity, successors/support, public effect, costs.
- `touch_record`: case/completion/state/action, derived touch, E/R/A witnesses, contract hash.
- `native_case`: source case IDs, initial state, target, relevance proof, route class, evaluator truth reference if any.
- `freeze_result`: freeze/forbidden resources, action-mask hash, extended-real value, certificate and condition hashes.
- `completion_set`: status, dimensions, IDs, exact count, invariant fields, identified-set hash.
- `control_result`: transformation, expected invariant, observation, pass state, evidence.
- `audit`: source/contract/touch/planner/control/corruption outcomes, findings, overall pass, audit hash.
- `claim_ledger`: claim ID, predicate, support, evidence, prohibited dependencies, generated text.

Required Parquet columns will follow the specification for `touch_records`, `freeze_policy_traces`, `case_results`, and `independent_results`, including all eight freeze coordinates and lineage hashes.

## 10. Failure, provenance, and change control

- Before source lock: tooling failures create no scientific run.
- Phase-1 eligibility failure: retain `INELIGIBLE`; a new candidate requires a new run ID and preregistration.
- Phase-2 failure: retain semantic-gap/fidelity cards; do not run Phase 3.
- Phase-3 planner/control failure: invalidate the entire Phase-3 namespace; do not salvage favorable rows.
- Phase-4 mismatch: claims are unsupported until rerun from the last trusted sealed input.
- Post-seal contract gap: withdraw the completion verdict, retain the sealed diagnostic run, and restart affected downstream phases with a new run ID.
- No green test, favorable number, successful process exit, or timeout waiver can override a missing scientific clause or artifact.
- Any upstream scientific change invalidates downstream outputs and requires a clean named rerun.

`Path.md` is the human-readable execution ledger. Every material action records date/time, phase, scope, files, code behavior, commands, tests, outputs, gate evidence, deviations from this plan, rejected attempts, downstream invalidation, commit, push verification, and next action. It must never rewrite a failure into a pass.

## 11. Definition of done

The work is complete only when all twenty scientific checklist items from the specification are satisfied or a permitted feasibility-negative/invalid verdict is explicitly retained: system and source are frozen; cases are source-selected; `U_H`, `H`, `P_R`, `Lambda`, `omega`, targets, actions, support, and costs are provenanced; touch is mechanical; fidelity passes; completions are exact; all eight freezes run; unit cost is complete; controls and independent audit pass; corruptions fail closed; every case is allocated; claim discipline holds; the artifact graph is complete; the seal is stable; and one-command reproduction succeeds.

## 12. Specification coverage matrix

| Specification area | Work-plan coverage |
|---|---|
| Executive question, success outcomes, and nonclaims | Sections 1–2 and Phase-4 verdicts |
| Scientific definitions: `M_ext`, `U_H`, touch, freezing, closure, cost, completions | Sections 2, 4, Phase 2, Phase 3 |
| Global rules, threats, route degeneracy, firewall | Sections 3–4 and all phase gates |
| Repository architecture, identity, immutability, logging, one-command run | Sections 5–6 and Phase 4 |
| Phase 1 requirements/tests/exit | Phase 1, including the Polaris-specific hold audit |
| Phase 2 requirements/tests/exit | Phase 2 |
| Phase 3 lattice/planner/metrics/controls/failures/exit | Phase 3 |
| Phase 4 audit/corruptions/claims/evidence/seal | Phase 4 |
| Module-level contracts | Phase-specific file/code inventories |
| JSON/Parquet schema contracts | Section 9 and phase inventories |
| Unit, phase, property, metamorphic, and evidence tests | All verification subsections and Section 8 |
| Failure handling and bidirectional provenance | Section 10 |
| Runtime/workload budget | Phase 2 and Phase 3 benchmarks |
| Paper integration and constrained language | Phase 4 |
| Definition of done and verdict taxonomy | Section 11 and Phase 4 |
| Appendix A CLI/orchestrator | Repository scripts and Phase 4 one-command reproduction |
| Appendix B example config | `configs/experiment.yaml` and preregistration design |
| Appendix C freeze/delta/claim pseudocode | Phase 2 touch and Phase 3/4 algorithms |
| Appendix D output tables | Phase 3 processed outputs and Phase 4 reports |
| Appendix E independent audit checklist | Phase 4 tasks and benchmarks |
| Appendix F reviewer objections and stop rules | Sections 3, 4, 10 and claim gate |

This matrix is a navigation aid, not a waiver. Phase completion requires a fresh clause-by-clause audit against the DOCX and this plan, recorded in `Path.md`.
