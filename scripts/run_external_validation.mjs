#!/usr/bin/env node

import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const repositoryRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");

function parseRunId(argv) {
  const index = argv.indexOf("--run-id");
  if (index < 0 || !argv[index + 1]) {
    throw new Error("--run-id is required");
  }
  const runId = argv[index + 1];
  if (!/^[A-Za-z0-9][A-Za-z0-9._-]{2,127}$/.test(runId)) {
    throw new Error("run_id contains unsupported characters");
  }
  return runId;
}

function parseThroughPhase(argv) {
  const index = argv.indexOf("--through-phase");
  if (index < 0) {
    return 2;
  }
  const phase = Number(argv[index + 1]);
  if (![1, 2].includes(phase)) {
    throw new Error("--through-phase must be 1 or 2");
  }
  return phase;
}

function pythonExecutable() {
  if (process.env.PC_PYTHON) {
    return resolve(repositoryRoot, process.env.PC_PYTHON);
  }
  const candidate = process.platform === "win32"
    ? resolve(repositoryRoot, ".venv", "Scripts", "python.exe")
    : resolve(repositoryRoot, ".venv", "bin", "python");
  if (!existsSync(candidate)) {
    throw new Error("Phase-1 Python environment not found; set PC_PYTHON or create .venv");
  }
  return candidate;
}

function run(python, script, runId, extraArgs = []) {
  execFileSync(
    python,
    [resolve(repositoryRoot, "scripts", script), "--run-id", runId, "--repo-root", repositoryRoot, ...extraArgs],
    { cwd: repositoryRoot, env: { ...process.env, PC_RUN_ID: runId }, stdio: "inherit" },
  );
}

const runId = parseRunId(process.argv.slice(2));
const throughPhase = parseThroughPhase(process.argv.slice(2));
const python = pythonExecutable();

// console.log: external.phase1.orchestrator.start
console.log(JSON.stringify({ event: "external.phase1.orchestrator.start", run_id: runId }));

// console.log: external.phase1.step01.clean_named_unsealed_run
console.log(JSON.stringify({ event: "external.phase1.step01.clean_named_unsealed_run", run_id: runId }));
run(python, "clean_named_run.py", runId);

// console.log: external.phase1.step02.verify_environment
console.log(JSON.stringify({ event: "external.phase1.step02.verify_environment", run_id: runId, node: process.version }));
execFileSync(python, ["--version"], { cwd: repositoryRoot, stdio: "inherit" });

// console.log: external.phase1.step03.lock_source
console.log(JSON.stringify({ event: "external.phase1.step03.lock_source", run_id: runId }));
run(python, "phase1_lock_source.py", runId);

// console.log: external.phase1.step04.preregister
console.log(JSON.stringify({ event: "external.phase1.step04.preregister", run_id: runId }));
run(python, "phase1_preregister.py", runId);

// console.log: external.phase1.step05.validate_eligibility
console.log(JSON.stringify({ event: "external.phase1.step05.validate_eligibility", run_id: runId }));
run(python, "phase1_validate.py", runId);

// console.log: external.phase1.step06.run_phase_tests
console.log(JSON.stringify({ event: "external.phase1.step06.run_phase_tests", run_id: runId }));
execFileSync(
  python,
  ["-m", "pytest", "-q", "--cov=pc_external", "--cov-report=term-missing", "--cov-report=xml"],
  { cwd: repositoryRoot, env: { ...process.env, PC_RUN_ID: runId, PC_PHASE: "1" }, stdio: "inherit" },
);

// console.log: external.phase1.orchestrator.complete
console.log(JSON.stringify({ event: "external.phase1.orchestrator.complete", run_id: runId }));

if (throughPhase === 1) {
  process.exit(0);
}

// console.log: external.phase2.orchestrator.start
console.log(JSON.stringify({ event: "external.phase2.orchestrator.start", run_id: runId }));

// console.log: external.phase2.step07.extract_contract_facts
console.log(JSON.stringify({ event: "external.phase2.step07.extract_contract_facts", run_id: runId }));
run(python, "phase2_extract_contract.py", runId);

// console.log: external.phase2.step08.validate_contract
console.log(JSON.stringify({ event: "external.phase2.step08.validate_contract", run_id: runId }));
run(python, "phase2_validate_contract.py", runId);

// console.log: external.phase2.step09.extract_touch
console.log(JSON.stringify({ event: "external.phase2.step09.extract_touch", run_id: runId }));
run(python, "phase2_extract_touch.py", runId);

// console.log: external.phase2.step10.seal_contract
console.log(JSON.stringify({ event: "external.phase2.step10.seal_contract", run_id: runId }));
run(python, "phase2_seal.py", runId);

// console.log: external.phase2.step11.run_authoritative_tests
console.log(JSON.stringify({ event: "external.phase2.step11.run_authoritative_tests", run_id: runId }));
execFileSync(
  python,
  ["-m", "pytest", "-q", "--cov=pc_external", "--cov-report=term-missing", "--cov-report=xml"],
  { cwd: repositoryRoot, env: { ...process.env, PC_RUN_ID: runId, PC_PHASE: "2" }, stdio: "inherit" },
);

// console.log: external.phase2.orchestrator.complete
console.log(JSON.stringify({ event: "external.phase2.orchestrator.complete", run_id: runId }));
