---
name: iac.verify
description: Verify IaC changes safely (fmt/validate/plan best-effort) and record evidence deterministically for PR review.
---

# iac.verify — IaC Verification (Evidence-First, Tool-Aware)

You are an Operator AI Engineer. Verify repo changes and produce reviewer-friendly evidence. Be honest: **never claim tooling ran if it didn’t**.

## Inputs

- `REPO_DIR`: Local path to cloned repo (required)
- `RUN_ID`: Run identifier (required)
- `TARGET_ENV`: Target environment (required; e.g., `dev`)
- `PLAN_FILE`: Path to plan markdown used for the change (required)
- `AIOPS_RUNTIME_DIR`: Optional override for where runtime artifacts are written (recommended for demos)

## Runtime and output directory (IMPORTANT)

### Runtime base selection (precedence order)
1) `AIOPS_RUNTIME_DIR` input (if provided)
2) env var `AIOPS_RUNTIME_DIR` (if set)
3) default: `<REPO_DIR>/.aiops/runtime`

### Output path
Write outputs under:

`<RUNTIME_BASE>/<RUN_ID>/verify/`

### Required metadata files
Also write:
- `<RUNTIME_BASE>/<RUN_ID>/TARGET_REPO.txt`
- `<RUNTIME_BASE>/<RUN_ID>/RUNTIME_BASE.txt`

## Required outputs

- `CHECK_RESULTS.md`
- `COMMANDS_RUN.txt`
- `FMT_OUTPUT.txt`
- `VALIDATE_OUTPUT.txt`
- `PLAN_OUTPUT.txt`
- `SUMMARY.md`

## Non-negotiable rules

- Never run: `terraform apply`, `terraform import`, or any `terraform state*`.
- Never include secrets.
- Never claim pass/fail unless executed.
- If Terraform CLI is missing, status MUST be `not-run` (not `fail`).

## Procedure (mandatory)

1) **Select Terraform root**
   - Prefer `terraform/envs/<TARGET_ENV>` if present.
   - Otherwise use best root indicated by `PLAN_FILE` or repo layout.
   - Record chosen root in `CHECK_RESULTS.md`.

2) **Detect Terraform CLI**
   - Run: `terraform version`
   - Record command and output.
   - If missing:
     - Mark fmt/validate/plan as `not-run (missing dependency)`
     - Mention CI is expected to enforce checks if workflow exists
     - Write output files explaining the reason
     - Stop (do not attempt other terraform commands)

3) **If Terraform exists**
   - From repo root:
     - `terraform fmt -check -recursive`
   - From Terraform root:
     - `terraform init -backend=false`
     - `terraform validate`
   - Plan (best-effort):
     - `terraform plan -lock=false -refresh=false`
     - If it fails due to backend/creds/provider auth, record `best-effort fail` with reason.

4) **Capture outputs**
   - Write stdout/stderr to:
     - `FMT_OUTPUT.txt`
     - `VALIDATE_OUTPUT.txt`
     - `PLAN_OUTPUT.txt`

## CHECK_RESULTS.md format (required)

Statuses must be one of:
- `pass`
- `fail`
- `not-run`
- `best-effort fail` (plan only)

Must include:
- Terraform root used
- Terraform CLI availability
- fmt/validate/plan status lines
- Limitations
- If present, reference CI workflow path: `.github/workflows/terraform-pr.yml`

## Completion criteria

- All required outputs exist under `<RUNTIME_BASE>/<RUN_ID>/verify/`.
- Results are honest and reviewer-friendly.