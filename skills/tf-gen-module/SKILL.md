---
name: tf.gen_modular_stack
description: Generate a greenfield Terraform stack using the DuploCloud Terraform Provider (path-agnostic, spec-driven, fail-fast for unmapped components)
---

# tf.gen_modular_stack — Terraform Greenfield Modular Generator (DuploCloud Provider)

You are an Operator DevOps agent tasked with generating modular Terraform code from a requirements spec using the **DuploCloud Terraform Provider** (`duplocloud/duplocloud`). This skill produces Terraform modules + environment composition, runs formatting and validation, and runs plan only when feasible.

This skill is **Duplo-first** and **schema-safe**: it will generate only components that map to known DuploCloud Terraform resources. It will STOP for components that require provider mappings not defined in this skill.

> **Important:** Authentication for the DuploCloud provider MUST be done via environment variables (`DUPLO_HOST` and `DUPLO_TOKEN`). Do **not** write credentials in code.

---

## Non-negotiable rules

- NEVER execute: `terraform apply`, `terraform import`, or any `terraform state *` commands.
- Do not hardcode secrets or backend configuration in committed code.
- Always run:
  - `terraform fmt -recursive`
  - `terraform init` (if feasible)
  - `terraform validate`
- Run `terraform plan` only if credentials/backend allow; capture errors otherwise.
- If a generated plan shows resource deletes or replacements in an existing stack, STOP and report.
- Modules must be generic; environment specifics come only from variables set in the environment stack.

---

## DuploCloud Provider Mapping Contract (NO guessing)

This skill MUST NOT invent DuploCloud Terraform resource names or fields.

Only generate components that map to known DuploCloud provider resources listed below.

### Approved DuploCloud Terraform resources (v1)

Use these resource types only:

- Tenant: `duplocloud_tenant`
- Infrastructure: `duplocloud_infrastructure`
- S3: `duplocloud_s3_bucket`
- Duplo Service: `duplocloud_duplo_service`
- Tenant network security rules (SG-equivalent): `duplocloud_tenant_network_security_rule`
- RDS: `duplocloud_rds_instance`

If the spec requests a component not covered by this list (example: IAM roles, EKS clusters, deep VPC subnet modeling), STOP and report:
- `unsupported component: <name>`
- `missing duplocloud provider mapping`

### Provider version pinning (required)

Always generate this in every `versions.tf`:

```hcl
terraform {
  required_providers {
    duplocloud = {
      source  = "duplocloud/duplocloud"
      version = "~> 0.11.32"
    }
  }
}