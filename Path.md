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
| Phase 1 scientific implementation | Not started | No source manifest, preregistration, native case index, or eligibility verdict has been generated. |
| Phase 2 | Blocked by design | Requires sealed Phase-1 `ELIGIBLE`. |
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

The remaining bootstrap verification action is to commit and push these two files and confirm the remote branch contains the commit. That remote fact will be reported in the task handoff; it is intentionally not preclaimed here.

## 4. Phase execution records

The sections below are intentionally unfilled scientific records. They will be expanded in place as implementation proceeds.

## Phase 1 record — External System Lock and Preregistration

Status: **NOT YET IMPLEMENTED**

Required future entries:

- Run ID and timestamps.
- Planned versus actual scope.
- Full file inventory and implementation behavior.
- External source refs/tree hashes and admitted evidence list.
- Native case rule and exact case index.
- Target and intervention-surface findings.
- P1-E1 through P1-E8 evidence and verdict.
- Commands/tests/determinism results.
- Rejected attempts and semantic gaps.
- Plan deviations and downstream effects.
- Implementation commit, ledger commit, push verification.

## Phase 2 record — Extensional Contract and Touch

Status: **BLOCKED PENDING PHASE 1**

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

After this bootstrap commit is pushed and remotely verified, the next implementation action is Phase 1 only: create the source-lock/preregistration scaffolding and resolve the Polaris target/case/route hold without computing E/R/A touch or closure results.
