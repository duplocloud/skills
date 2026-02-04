---
name: iac.plan_changes
description: Convert a task prompt into a deterministic, repo-convention-aligned IaC change plan and explicit file list.
---

# iac.plan_changes — Deterministic IaC Change Planner (ENFORCED)

You are an Operator AI Engineer. Your job is to produce an implementable plan and the exact files to change. Do not modify repo files in this step.

## Inputs

- `REPO_DIR`: Local path to cloned repo (required)
- `RUN_ID`: Run identifier (required)
- `TARGET_ENV`: Target environment (required)
- `TASK_FILE`: Path to the task markdown file (required)
- `REPO_MAP_FILE`: Path to the repo discovery output (required)
- `AIOPS_RUNTIME_DIR`: Optional override for where runtime artifacts are written (recommended for demos)

---

## Runtime and output directory (IMPORTANT)

### Runtime base selection (precedence order)
1) `AIOPS_RUNTIME_DIR` input (if provided and non-empty)
2) env var `AIOPS_RUNTIME_DIR` (if set and non-empty)
3) default: `<REPO_DIR>/.aiops/runtime`

### Output path
Write outputs under:
`<RUNTIME_BASE>/<RUN_ID>/plan_changes/`

### Required outputs (ALL MUST BE WRITTEN)
- `PLAN.md`
- `FILES_TO_CHANGE.txt`
- `ASSUMPTIONS.md`
- `OPEN_QUESTIONS.md`
- `SUMMARY.md`
- `SELF_CHECK.md`

Also always write:
- `<RUNTIME_BASE>/<RUN_ID>/RUNTIME_BASE.txt`
- `<RUNTIME_BASE>/<RUN_ID>/TARGET_REPO.txt`

---

## Non-negotiable rules

- Do not edit repo files.
- Plan must be minimal-diff and aligned to repo patterns.
- Never plan `terraform apply`, `terraform import`, or any `terraform state*`.
- Never invent resources that aren’t required by the task.
- Never claim a tool exists (terraform/gh/etc.) unless explicitly checked in later steps (implement/verify).

---

## Input path resolution rules (MANDATORY)

This skill MUST be resilient to where TASK_FILE lives (ai-core repo vs target repo).

### TASK_FILE resolution
- If `TASK_FILE` is an absolute path and exists: use it.
- Else if `TASK_FILE` exists relative to the current working directory: use it.
- Else if `<REPO_DIR>/<TASK_FILE>` exists: use that.
- Else: fail planning and write OPEN_QUESTIONS.md explaining the missing file path options.

In SUMMARY.md, you MUST record:
- `TASK_FILE_RESOLVED=<absolute path used>`

### REPO_MAP_FILE resolution
- REPO_MAP_FILE MUST be an absolute path and must exist.
- If it does not exist: fail planning and write OPEN_QUESTIONS.md with the missing path.

In SUMMARY.md, you MUST record:
- `REPO_MAP_FILE=<absolute path used>`

---

## What to read before planning (MANDATORY)

1) Read `TASK_FILE` fully (using the resolution rules above).
2) Read `REPO_MAP_FILE` fully.
3) Identify from REPO_MAP:
   - Terraform roots and entrypoints
   - modules directory
   - existing CI workflows (if any)
   - existing naming/tagging conventions

You MUST NOT plan paths that contradict REPO_MAP. If REPO_MAP says roots are `terraform/envs/dev`, do not plan `env/dev`.

---

## FILES_TO_CHANGE.txt rules (MANDATORY)

`FILES_TO_CHANGE.txt` MUST contain **absolute paths** under `REPO_DIR`, one per line.

Rules:
- Every file listed MUST be either created or modified by `iac.implement`.
- If the plan adds a new module, include *all* module files (main/variables/outputs).
- If the plan adds CI, use a single canonical workflow filename:
  - `.github/workflows/terraform-pr.yml` (hyphenated)
- Do not list “maybe” files. Be explicit.
- Do not include any runtime artifacts paths in FILES_TO_CHANGE.txt (runtime is not part of the PR diff).

Example line format:
`/tmp/demo-iac-repo/terraform/modules/app_logs_bucket/main.tf`

---

## Hard requirements for S3 logs bucket plans (MANDATORY)

If the task includes: “Add an S3 bucket … encrypted with KMS … lifecycle … restrict public access”
then PLAN.md MUST explicitly include ALL of the following:

### A) Deterministic globally unique name (MANDATORY)
- `data "aws_caller_identity" "current" {}`
- `data "aws_region" "current" {}`
- Bucket name pattern that includes account_id and region (no randomness)

Required text to include in PLAN.md:
- `${data.aws_caller_identity.current.account_id}`
- `${data.aws_region.current.name}`

Recommended pattern:
- `${var.name_prefix}-${var.env}-app-logs-${data.aws_caller_identity.current.account_id}-${data.aws_region.current.name}`

### B) Ownership controls (MANDATORY)
- `aws_s3_bucket_ownership_controls`
- `BucketOwnerEnforced`

### C) Encryption (MANDATORY)
- `aws_kms_key` with rotation enabled
- `aws_kms_alias` (must start with `alias/`)
- `aws_s3_bucket_server_side_encryption_configuration` using SSE-KMS

### D) Public access restriction (MANDATORY)
- `aws_s3_bucket_public_access_block` with all four booleans true:
  - block_public_acls
  - block_public_policy
  - ignore_public_acls
  - restrict_public_buckets

### E) Lifecycle (MANDATORY)
- `aws_s3_bucket_lifecycle_configuration` expiring after **30 days**
- Plan must state “expire objects after 30 days” in plain english

### F) Wiring scope (MANDATORY)
- Wire ONLY into `TARGET_ENV` root unless the task explicitly requires prod.
- Plan must explicitly say “No prod wiring changes” when `TARGET_ENV=dev`.

---

## Hard requirements for PR CI (MANDATORY)

If task includes “Update CI to run terraform fmt/validate/plan on PRs” PLAN.md MUST include:

- `terraform fmt -check -recursive` (hard fail)
- Per env root:
  - `terraform init -backend=false`
  - `terraform validate`
  (hard fail)
- Dev plan (best-effort):
  - `terraform plan -lock=false -refresh=false` (allowed to fail; logs still useful)
- Workflow file MUST be:
  - `.github/workflows/terraform-pr.yml`

---

## PLAN.md structure (MANDATORY)

PLAN.md MUST follow this structure:

1) Summary of intent  
2) Repo targets (paths from REPO_MAP)  
3) Files to add/modify (relative paths)  
4) Step-by-step implementation outline  
5) Verification commands (local + CI)  
6) PR notes (what evidence to include)

---

## Mandatory self-check (THIS MAKES IT DETERMINISTIC)

After writing PLAN.md, you MUST validate that it contains all required items.

Write `SELF_CHECK.md` containing:
- A checklist of required strings and whether they appear in PLAN.md

If S3 logs bucket task detected, SELF_CHECK.md MUST include checks for:
- `aws_s3_bucket_ownership_controls`
- `BucketOwnerEnforced`
- `data "aws_caller_identity" "current"`
- `data "aws_region" "current"`
- `${data.aws_caller_identity.current.account_id}`
- `${data.aws_region.current.name}`
- `aws_kms_key`
- `aws_kms_alias`
- `aws_s3_bucket_server_side_encryption_configuration`
- `aws_s3_bucket_public_access_block`
- `aws_s3_bucket_lifecycle_configuration`
- `.github/workflows/terraform-pr.yml`
- `terraform fmt -check -recursive`
- `terraform init -backend=false`
- `terraform validate`
- `terraform plan -lock=false -refresh=false`

If ANY required string is missing, you MUST:
- Regenerate PLAN.md to include the missing requirements
- Re-run the checklist until all checks pass
- Only then complete the skill

---

## Completion criteria

- Outputs exist under `<RUNTIME_BASE>/<RUN_ID>/plan_changes/`.
- PLAN.md includes all hard requirements.
- SELF_CHECK.md exists and all checks pass.
- FILES_TO_CHANGE.txt contains absolute paths under REPO_DIR and includes the canonical workflow path.
- SUMMARY.md includes TASK_FILE_RESOLVED and REPO_MAP_FILE.