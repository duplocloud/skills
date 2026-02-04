---
name: iac.repo_discover
description: Discover IaC repo structure (Terraform roots, modules, CI) and write a deterministic repo map for downstream skills.
---

# iac.repo_discover — IaC Repo Discovery

You are an Operator AI Engineer. Scan an IaC repository and produce a deterministic map of structure and key entry points. **Do not modify repo files**.

## Inputs

- `REPO_DIR`: Local path to cloned repo (required)
- `RUN_ID`: Run identifier (required)
- `TARGET_ENV`: Target environment (optional; default: `dev`)
- `TASK_FILE`: Path to the task markdown file (required)
- `AIOPS_RUNTIME_DIR`: Optional override for where runtime artifacts are written (recommended for demos)

## Runtime and output directory (IMPORTANT)

All artifacts MUST be written to a deterministic runtime directory.

### Runtime base selection (precedence order)
1) If `AIOPS_RUNTIME_DIR` input is provided and non-empty, use it.
2) Else if env var `AIOPS_RUNTIME_DIR` is set and non-empty, use it.
3) Otherwise default to `<REPO_DIR>/.aiops/runtime`.

### Output path
Write outputs under:

`<RUNTIME_BASE>/<RUN_ID>/repo_discover/`

### Required metadata files
Also write:
- `<RUNTIME_BASE>/<RUN_ID>/TARGET_REPO.txt`
- `<RUNTIME_BASE>/<RUN_ID>/RUNTIME_BASE.txt`

`TARGET_REPO.txt` MUST include:
- `REPO_DIR=<absolute path>`
- `GIT_REMOTE=<remote url or unknown>`
- `GIT_HEAD=<sha or unknown>`

### Required outputs
- `REPO_MAP.md`
- `FILES_SCANNED.txt`
- `SUMMARY.md`

## Non-negotiable rules

- Do not edit repo files.
- Do not run `terraform apply`, `terraform import`, or any `terraform state*`.
- Do not invent tooling. If unknown, write “unknown”.
- Be deterministic: same repo state → same map format.

## Discovery procedure (mandatory)

1) **Record runtime base choice**
   - Determine `RUNTIME_BASE` using the precedence rules.
   - Write `RUNTIME_BASE.txt`.
   - Write `TARGET_REPO.txt` (see required fields above).

2) **Identify IaC roots and layout**
   - Detect Terraform roots (common patterns):
     - `terraform/envs/<env>`
     - `envs/<env>`
     - `live/<env>`
     - `iac/<env>`
   - Detect modules directory (common patterns):
     - `terraform/modules`
     - `modules`
     - `iac/modules`
   - Detect backend config presence:
     - `backend.tf` / `terraform { backend ... }`
   - Detect provider hints:
     - `provider "aws"`, `google`, `azurerm`

3) **Identify CI/CD and automation**
   - Check `.github/workflows/` for Terraform workflows.
   - Check Makefile/scripts for `fmt/validate/init/plan` targets.
   - Record file locations and commands discovered.

4) **Create `REPO_MAP.md`**
   Must include:
   - Repo root + key folders
   - Terraform roots + env entrypoints (dev/prod if present)
   - Modules directory + existing module patterns
   - CI workflows found (or “none”)
   - Risks found (backend config, inconsistent quoting, unusual formatting)

5) **Create `FILES_SCANNED.txt`**
   - List only *important* files examined (not every file).
   - Include terraform root files, module examples, CI files, Makefile/scripts.

6) **Create `SUMMARY.md`**
   - Brief summary for downstream skills.

## Completion criteria

- Outputs exist under `<RUNTIME_BASE>/<RUN_ID>/repo_discover/`.
- `RUNTIME_BASE.txt` exists and matches selection.
- `REPO_MAP.md` provides enough signal for `iac.plan_changes`.