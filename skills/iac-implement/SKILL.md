---
name: iac.implement
description: Implement an approved IaC change plan with minimal diffs and repo conventions, generating PR-ready code changes with PR-diff-aware evidence.
---

# iac.implement — IaC Plan Implementation (PR-Diff Aware, Untracked + Staged Aware)

You are an Operator AI Engineer. Apply the plan exactly, following repo conventions and safety rules. You will modify repo files in this step.

## Inputs

- `REPO_DIR`: Local path to cloned repo (required)
- `RUN_ID`: Run identifier (required)
- `TARGET_ENV`: Target environment (required)
- `PLAN_FILE`: Path to the plan markdown (required)
- `FILES_TO_CHANGE`: Path to list of absolute files to change (required)
- `BASE_BRANCH`: Optional; default `main` (used to compute PR diff summary)
- `AIOPS_RUNTIME_DIR`: Optional override for where runtime artifacts are written (recommended for demos)

## Runtime and output directory (IMPORTANT)

### Runtime base selection (precedence order)
1) If `AIOPS_RUNTIME_DIR` input is provided and non-empty, use it.
2) Else if env var `AIOPS_RUNTIME_DIR` is set and non-empty, use it.
3) Otherwise, default to `<REPO_DIR>/.aiops/runtime`.

### Output path
Write outputs under:

`<RUNTIME_BASE>/<RUN_ID>/implement/`

### Required metadata files
Also write:
- `<RUNTIME_BASE>/<RUN_ID>/TARGET_REPO.txt`
- `<RUNTIME_BASE>/<RUN_ID>/RUNTIME_BASE.txt`

### Required outputs
- `FILES_WRITTEN.txt` (absolute runtime artifact paths only; de-duplicated)
- `REPO_CHANGES.txt` (repo-relative paths intended for PR: staged + tracked + untracked; de-duplicated)
- `DIFF_SUMMARY.md` (MUST reflect PR content vs BASE_BRANCH and include untracked/staged)
- `SUMMARY.md`
- `TOOLING.md`
- `COMMANDS_RUN.txt`

## Non-negotiable rules

- Never run: `terraform apply`, `terraform import`, or any `terraform state*`.
- Never add secrets or credentials.
- Keep diffs minimal; do not refactor unrelated files.
- Never claim a command succeeded unless you ran it and observed success.
- If unexpected files unrelated to the plan exist, do not delete them—document and stop if risky.

## PR-diff requirement (MANDATORY)

DIFF_SUMMARY.md MUST be generated from the repository’s **actual PR content**, including:
- staged changes (`git diff --cached`)
- tracked changes vs base (`git diff origin/<BASE_BRANCH>...HEAD`)
- untracked files (`git ls-files -o --exclude-standard`)

### Compute base ref (DIFF_BASE)
Best-effort:
- `git -C <REPO_DIR> fetch origin <BASE_BRANCH> --quiet`

Choose DIFF_BASE in this order:
1) `origin/<BASE_BRANCH>` if present
2) `<BASE_BRANCH>` if present
3) empty (no base available)

Record DIFF_BASE in TOOLING.md.

## S3 app logs bucket module requirements (if applicable)

If plan includes adding an app logs S3 bucket, the implementation MUST include:

- `data "aws_caller_identity" "current" {}`
- `data "aws_region" "current" {}`
- bucket name includes account_id and region
- SSE-KMS via:
  - `aws_kms_key` (rotation enabled)
  - `aws_kms_alias` (must start with `alias/`)
  - `aws_s3_bucket_server_side_encryption_configuration`
- lifecycle expiration via `aws_s3_bucket_lifecycle_configuration`
- public access blocked via `aws_s3_bucket_public_access_block` (all 4 true)
- ownership enforced via `aws_s3_bucket_ownership_controls` (`BucketOwnerEnforced`)
- versioning controlled by var; default disabled/suspended

## Procedure (MANDATORY)

1) **Init runtime + metadata**
   - Create `<RUNTIME_BASE>/<RUN_ID>/implement/`
   - Write `TARGET_REPO.txt` (repo path + origin URL if available)
   - Write `RUNTIME_BASE.txt`

2) **Read inputs**
   - Read PLAN_FILE and FILES_TO_CHANGE fully.
   - Treat FILES_TO_CHANGE as the contract.

3) **Apply plan**
   - Edit repo to match plan; keep diffs minimal.
   - Terraform fmt:
     - Check `terraform version`
     - If present run: `terraform fmt -recursive`
     - If not present: record as not-run in TOOLING.md (do not lie)

4) **Collect evidence**
   Run and record in COMMANDS_RUN.txt:
   - `git -C <REPO_DIR> status --porcelain=v1 -uall`
   - `git -C <REPO_DIR> diff --cached --name-status`
   - `git -C <REPO_DIR> diff --cached --stat`
   - If DIFF_BASE exists:
     - `git -C <REPO_DIR> diff --name-status <DIFF_BASE>...HEAD`
   - `git -C <REPO_DIR> ls-files -o --exclude-standard`

5) **Coverage check against FILES_TO_CHANGE (MANDATORY)**
   For each absolute path in FILES_TO_CHANGE:
   - confirm it exists on disk
   - if missing, mark NOT COVERED in SUMMARY.md

6) **Write REPO_CHANGES.txt (MANDATORY)**
   Include repo-relative paths from:
   - staged changes
   - tracked diff vs base (if available)
   - untracked files

7) **Write DIFF_SUMMARY.md (MANDATORY sections)**
   Must include:
   1) Modules added/changed
   2) Env wiring changes
   3) CI changes
   4) Changed files list (from REPO_CHANGES.txt)
   5) Untracked files to include in PR (if any)
   6) Notes (DIFF_BASE used, tooling limitations, idempotency)

8) **Write SUMMARY.md**
   Must state:
   - whether this run made edits or repo already matched plan
   - coverage: `COVERED X/Y planned files`
   - whether Terraform fmt ran
   - whether there are untracked files that must be staged

9) **Write TOOLING.md**
   Must include:
   - terraform availability result
   - whether fmt ran and where
   - DIFF_BASE chosen

10) **Write FILES_WRITTEN.txt**
   - list ONLY runtime artifact paths under `<RUNTIME_BASE>/<RUN_ID>/...`
   - no duplicates

## Completion criteria

- FILES_TO_CHANGE are covered (or explicit documented exceptions).
- Outputs exist under `<RUNTIME_BASE>/<RUN_ID>/implement/`.
- DIFF_SUMMARY.md reflects PR content (staged + untracked + tracked).
- REPO_CHANGES.txt exists and is accurate.