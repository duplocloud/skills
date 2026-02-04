---
name: git.pr_ready
description: Create branch, commit changes, push, and open a PR with descriptive evidence and deterministic structure.
---

# git.pr_ready — PR-Ready Git Workflow (STAGED-DIFF Aware)

You are an Operator AI Engineer. Your job is to create a branch, commit changes, push, and open a PR.
The PR must be reviewer-friendly and must describe the **actual staged diff** that will be committed.

## Inputs

- `REPO_DIR`: Local path to cloned repo (required)
- `RUN_ID`: Run identifier (required)
- `BASE_BRANCH`: Base branch (optional; default: `main`)
- `BRANCH_NAME`: Branch name (optional; default: `feature/iac-change`)
- `PR_TITLE`: PR title (required)
- `VERIFY_RESULTS`: Path to verify results markdown (required)
- `REPO_MAP_FILE`: Path to repo discovery map markdown (required)
- `PLAN_FILE`: Path to plan markdown (required)
- `AIOPS_RUNTIME_DIR`: Optional override for where runtime artifacts are written (recommended for demos)

## Runtime and output directory (IMPORTANT)

### Runtime base selection (precedence order)
1) `AIOPS_RUNTIME_DIR` input (if provided and non-empty)
2) env var `AIOPS_RUNTIME_DIR` (if set and non-empty)
3) default: `<REPO_DIR>/.aiops/runtime`

### Output path
Write outputs under:
`<RUNTIME_BASE>/<RUN_ID>/pr_ready/`

### Required outputs (ALL MUST BE WRITTEN)
- `GIT_COMMANDS.txt` (commands run or to run, one per line)
- `COMMANDS_RUN.txt` (commands actually executed, one per line)
- `DIFF_SUMMARY.md` (staged diff summary grouped by category)
- `PR_BODY.md` (final PR description body)
- `SUMMARY.md` (human-friendly completion + next steps)

Also write metadata:
- `<RUNTIME_BASE>/<RUN_ID>/TARGET_REPO.txt` (repo path + remote URL if available)
- `<RUNTIME_BASE>/<RUN_ID>/RUNTIME_BASE.txt` (chosen runtime base)

## Non-negotiable rules

- Branch must be created from BASE_BRANCH.
- Commit message must be descriptive and stable.
- PR description must include evidence and limitations.
- Never include secrets.
- Never claim a command succeeded unless you ran it and observed success.

---

## Procedure (mandatory)

### 1) Ensure clean starting point
- `git -C <REPO_DIR> status --porcelain` must be empty before branching
  - Exception: if the task is specifically “PR-ready existing working tree”, document that in SUMMARY.md and proceed.

### 2) Create branch
Run (best-effort; do not fail the workflow if network is unavailable):
- `git -C <REPO_DIR> checkout <BASE_BRANCH>`
- `git -C <REPO_DIR> pull --ff-only` (if allowed)
- `git -C <REPO_DIR> checkout -b <BRANCH_NAME>`

### 3) Stage changes (source of truth)
- `git -C <REPO_DIR> add -A`

Capture the staged set (MANDATORY):
- `git -C <REPO_DIR> diff --cached --name-status`
- `git -C <REPO_DIR> diff --cached --stat`
- `git -C <REPO_DIR> diff --cached`

If staged changes are empty:
- STOP and write SUMMARY.md explaining “No staged changes; nothing to PR.”

### 4) Generate deterministic DIFF_SUMMARY.md (MANDATORY)
DIFF_SUMMARY.md MUST be based on **staged diff** (`--cached`) and include:

1) **Terraform modules added/changed**
2) **Env wiring changes**
3) **CI changes**
4) **Changed files list** (relative paths)
5) **Notes / limitations** (e.g., terraform not installed locally, best-effort plan, etc.)

Grouping rules:
- Module paths: `terraform/modules/**`
- Env wiring: `terraform/envs/<TARGET_ENV>/**` if present, else `terraform/envs/**`
- CI: `.github/workflows/**`

### 5) Build PR_BODY.md (MANDATORY)
PR_BODY.md MUST include:

#### 1) Summary
1–2 lines describing the outcome.

#### 2) What changed (from staged diff)
- Use the grouped DIFF_SUMMARY.md structure.
- Mention the exact workflow path if CI was added/changed.

If the staged diff includes an S3 logs bucket module, MUST explicitly mention:
- SSE-KMS encryption
- lifecycle expiration days
- public access blocks
- BucketOwnerEnforced ownership controls
- deterministic naming (account_id + region)

#### 3) Repo map highlights
From REPO_MAP_FILE:
- Terraform roots found
- Which root was modified and why

#### 4) Verification evidence
From VERIFY_RESULTS:
- Report fmt/validate/plan outcomes
- If terraform missing locally, explicitly state “not-run” and point to CI workflow that enforces checks.

#### 5) Plan reference
Point to PLAN_FILE and note that implementation followed the plan.

#### 6) Rollback
Clear steps:
- revert commit OR remove module + remove wiring + remove workflow

#### 7) Notes / assumptions
List anything that might impact correctness.

### 6) Commit
Use a stable commit message aligned with PR_TITLE:
- `git -C <REPO_DIR> commit -m "<PR_TITLE>"`

### 7) Push
- `git -C <REPO_DIR> push -u origin <BRANCH_NAME>`

### 8) Open PR
Prefer GitHub CLI:
- `gh pr create --base <BASE_BRANCH> --head <BRANCH_NAME> --title "<PR_TITLE>" --body-file <RUNTIME_BASE>/<RUN_ID>/pr_ready/PR_BODY.md`

If `gh` is not available:
- Write exact manual steps in SUMMARY.md including:
  - compare URL format
  - base/head
  - title
  - paste PR_BODY.md content

---

## Evidence + bookkeeping (MANDATORY)

- COMMANDS_RUN.txt MUST include the exact commands executed (one per line).
- GIT_COMMANDS.txt MUST include the “final list” of commands that represent the workflow (even if some were skipped).
- SUMMARY.md MUST state:
  - branch name
  - whether PR was created vs manual instructions
  - high-level change summary
  - any limitations (missing terraform/gh/network)

## Completion criteria

- Branch exists on remote.
- PR created (or exact manual steps provided).
- Runtime artifacts written under `<RUNTIME_BASE>/<RUN_ID>/pr_ready/`.