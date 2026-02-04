---
id: demo.task.s3_logs_bucket_and_ci.v2
title: Add app logs S3 bucket (KMS + 30d lifecycle) + PR Terraform checks
target_env: dev
---

# Task: Add an app logs bucket + PR checks (Terraform)

## Goal
Update the existing Terraform IaC repo to:
1) Add an S3 bucket for application logs
2) Encrypt it with KMS (customer-managed key)
3) Add lifecycle expiration for objects after 30 days
4) Block all forms of public access
5) Wire this to the **dev** environment only
6) Add CI on pull requests to run terraform fmt/validate/plan safely

## Constraints (non-negotiable)
- Do NOT run or add `terraform apply`, `terraform import`, or any `terraform state*` commands.
- Do NOT commit secrets or backend credentials.
- Prefer minimal diffs and follow repo conventions.

## Implementation requirements

### A) Bucket requirements
- Bucket must be encrypted using SSE-KMS with a dedicated KMS key created in Terraform.
- Bucket must have lifecycle expiration at 30 days for all objects.
- Bucket must block public access using S3 Public Access Block (all 4 flags true).
- Bucket naming MUST be:
  - deterministic AND
  - globally unique

**Deterministic + unique naming rule:**
Use AWS account ID + region from data sources to avoid collisions:
- `data.aws_caller_identity.current.account_id`
- `data.aws_region.current.name`

Recommended naming pattern:
`<name_prefix>-<env>-app-logs-<account_id>-<region>`

### B) Ownership controls
Enforce bucket ownership:
- `aws_s3_bucket_ownership_controls` with `BucketOwnerEnforced`

Do not manage ACLs unless required.

### C) Versioning
Implement `aws_s3_bucket_versioning` but default to **disabled** (or `Suspended`).
Expose a module variable so it can be enabled later.

### D) Wiring
Wire ONLY into the dev terraform root.
Do not change prod wiring.

### E) CI workflow (PR checks)
Add a PR workflow that runs:
- `terraform fmt -check -recursive` (hard fail)
- `terraform init -backend=false` + `terraform validate` for dev (hard fail)
- optional init/validate for prod if possible (hard fail if it runs)
- `terraform plan` for dev should be **best-effort** (do not block PR if plan fails due to backend/creds). Capture output in logs.

## Deliverables
- A new module for the bucket + KMS.
- Dev env wiring.
- GitHub Actions workflow for PR checks.
- A PR with a clear description and evidence (commands run + results).