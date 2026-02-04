---
name: orchestrator.ai_engineer
description: End-to-end AI Engineer orchestration: acquire repo, discover, plan, implement, verify, and prepare PR artifacts using allow-listed skills.
---

# orchestrator.ai_engineer — End-to-End AI Engineer Orchestration

You are an Operator AI Engineer. Your job is to run the full workflow deterministically and leave PR-ready artifacts.

This skill **does not** implement IaC directly itself; it orchestrates these skills in order:
- `git.repo_acquire`
- `iac.repo_discover`
- `iac.plan_changes`
- `iac.implement`
- `iac.verify`
- `git.pr_ready`

## Inputs

- `REPO_URL`: Git URL to clone (required)
- `BASE_BRANCH`: Base branch to target (optional; default: `main`)
- `TARGET_ENV`: Target env (required, e.g. `dev`)
- `TASK_FILE`: Path to the task markdown file (required; must exist in the *ai-ops* repo workspace)
- `RUN_ID`: Run identifier (required)
- `AIOPS_RUNTIME_DIR`: Runtime base override (optional but recommended for demos)
- `CLONE_PARENT_DIR`: Where to clone the repo (optional; default: `/tmp`)
- `REPO_NAME`: Optional explicit directory name for clone (if omitted, derive from REPO_URL)

## Outputs

Write a single file at:
`<RUNTIME_BASE>/<RUN_ID>/orchestrator/SUMMARY.md`

Also write:
- `<RUNTIME_BASE>/<RUN_ID>/orchestrator/COMMANDS.txt` (high-level sequence of skill invocations)
- `<RUNTIME_BASE>/<RUN_ID>/orchestrator/POINTERS.md` (links/paths to downstream artifacts)

Where:
- `RUNTIME_BASE` is chosen by the same precedence rule used by other skills:
  1) `AIOPS_RUNTIME_DIR` input
  2) env var `AIOPS_RUNTIME_DIR`
  3) `<REPO_DIR>/.aiops/runtime` (but for this orchestrator, default to `ai-ops/.aiops/runtime` if provided)

## Non-negotiable rules

- Never run `terraform apply`, `terraform import`, or `terraform state*`.
- Never claim a step succeeded unless you actually ran it and observed completion.
- Every step must write its normal runtime artifacts under the same `<RUNTIME_BASE>/<RUN_ID>/...` tree.
- If a required dependency is missing (e.g., Terraform CLI), continue the workflow but record “not-run (missing dependency)” honestly.

## Procedure (MANDATORY)

### 0) Resolve runtime base
Choose `RUNTIME_BASE` using precedence:
1) `AIOPS_RUNTIME_DIR` input (if non-empty)
2) env var `AIOPS_RUNTIME_DIR`
3) default: `./.aiops/runtime` **in the ai-ops workspace**

Create:
- `<RUNTIME_BASE>/<RUN_ID>/orchestrator/`

### 1) Acquire repo (clone / update)
Invoke:
- `git.repo_acquire` with:
  - `REPO_URL=<REPO_URL>`
  - `BASE_BRANCH=<BASE_BRANCH>`
  - `CLONE_PARENT_DIR=<CLONE_PARENT_DIR>`
  - `REPO_NAME=<REPO_NAME>` (if provided)
  - `RUN_ID=<RUN_ID>`
  - `AIOPS_RUNTIME_DIR=<RUNTIME_BASE>`

This must produce a concrete `REPO_DIR` output (path to the working repo).

### 2) Repo discovery
Invoke:
- `iac.repo_discover` with:
  - `REPO_DIR=<from step 1>`
  - `RUN_ID=<RUN_ID>`
  - `TARGET_ENV=<TARGET_ENV>`
  - `TASK_FILE=<TASK_FILE>`
  - `AIOPS_RUNTIME_DIR=<RUNTIME_BASE>`

Capture:
- `REPO_MAP_FILE=<RUNTIME_BASE>/<RUN_ID>/repo_discover/REPO_MAP.md`

### 3) Plan
Invoke:
- `iac.plan_changes` with:
  - `REPO_DIR=<from step 1>`
  - `RUN_ID=<RUN_ID>`
  - `TARGET_ENV=<TARGET_ENV>`
  - `TASK_FILE=<TASK_FILE>`
  - `REPO_MAP_FILE=<from step 2>`
  - `AIOPS_RUNTIME_DIR=<RUNTIME_BASE>`

Capture:
- `PLAN_FILE=<RUNTIME_BASE>/<RUN_ID>/plan_changes/PLAN.md`
- `FILES_TO_CHANGE=<RUNTIME_BASE>/<RUN_ID>/plan_changes/FILES_TO_CHANGE.txt`

### 4) Implement
Invoke:
- `iac.implement` with:
  - `REPO_DIR=<from step 1>`
  - `RUN_ID=<RUN_ID>`
  - `TARGET_ENV=<TARGET_ENV>`
  - `BASE_BRANCH=<BASE_BRANCH>`
  - `PLAN_FILE=<from step 3>`
  - `FILES_TO_CHANGE=<from step 3>`
  - `AIOPS_RUNTIME_DIR=<RUNTIME_BASE>`

### 5) Verify
Invoke:
- `iac.verify` with:
  - `REPO_DIR=<from step 1>`
  - `RUN_ID=<RUN_ID>`
  - `TARGET_ENV=<TARGET_ENV>`
  - `PLAN_FILE=<from step 3>`
  - `AIOPS_RUNTIME_DIR=<RUNTIME_BASE>`

Capture:
- `VERIFY_RESULTS=<RUNTIME_BASE>/<RUN_ID>/verify/CHECK_RESULTS.md`

### 6) PR ready
Invoke:
- `git.pr_ready` with:
  - `REPO_DIR=<from step 1>`
  - `RUN_ID=<RUN_ID>`
  - `BASE_BRANCH=<BASE_BRANCH>`
  - `PR_TITLE=<derived from TASK_FILE first heading or a stable default>`
  - `VERIFY_RESULTS=<from step 5>`
  - `REPO_MAP_FILE=<from step 2>`
  - `PLAN_FILE=<from step 3>`
  - `AIOPS_RUNTIME_DIR=<RUNTIME_BASE>`

### 7) Orchestrator summary
Write:
- `COMMANDS.txt` listing the 6 skill invocations with resolved parameters.
- `POINTERS.md` listing the key artifact paths.
- `SUMMARY.md` including:
  - Repo URL + repo dir
  - Which env targeted
  - Whether terraform was available locally (from verify)
  - The PR body path and git commands path from `git.pr_ready`
  - Any limitations

## Completion criteria

- All invoked skills completed (or recorded limitations).
- Orchestrator outputs exist under `<RUNTIME_BASE>/<RUN_ID>/orchestrator/`.
- Downstream artifacts exist for discover/plan/implement/verify/pr_ready.