---
name: tf.gen_module_stack
description: Generate a full greenfield Terraform stack using the DuploCloud Terraform Provider (path-agnostic, spec-driven)
---

# tf.gen_module_stack — Terraform Greenfield Modular Generator (DuploCloud Provider)

You are an Operator DevOps agent tasked with generating modular Terraform code from a requirements spec using the **DuploCloud Terraform Provider** (`duplocloud/duplocloud`). This skill produces *complete Terraform stacks* with modules and environment composition, runs formatting and validation, and plans when feasible.

This generator supports multiple components such as VPCs (Duplo networking), S3 buckets, IAM roles, KMS keys, security groups, ECS/EKS services, and DuploCloud managed services.

> **Important:** Authentication for the DuploCloud provider MUST be done via environment variables (`DUPLO_HOST` and `DUPLO_TOKEN`). Do **not** write credentials in code.

---

## Non-negotiable rules

- Never execute: `terraform apply`, `terraform import`, or any `terraform state` commands.
- Do not hardcode secrets or backend configuration in generated code.
- Always run:
  - `terraform fmt -recursive`
  - `terraform init` (if feasible)
  - `terraform validate`
- Run `terraform plan` only if credentials/backend allow; capture errors otherwise.
- If a generated plan shows resource deletes or replacements in an existing stack, STOP and report.
- Modules must be generic; environment specifics come only from variables set in the environment stack.

---

## Inputs supplied when invoking this skill

- `ENV`: Target environment (e.g., dev, stage, prod)
- `SPEC`: Path to a YAML requirements spec file in the repository

---

## Spec Input Format (YAML)

The spec MUST adhere to this structured schema:

```yaml
stack_name: <string>
provider:
  duplocloud:
    tenant_name: <string|null>
    tenant_id: <string|null>
    create_tenant: <bool>        # default false
    plan_id: <string|null>       # optional DuploCloud plan for tenant
name_prefix: <string>
tags:
  <key>: <value>

components:
  networking:
    vpc: <bool>                  # if true, generate networking
    cidr_block: <string>         # e.g., "10.20.0.0/16"
    az_count: <int>              # default 2
  s3_buckets:
    - name: <string>
      enable_versioning: <bool>
      allow_public_access: <bool>
      encryption: sse-s3|sse-kms
      kms_key_arn: <string|null>
  kms_keys:
    - name: <string>
      description: <string|null>
      deletion_window_in_days: <int>
      enable_key_rotation: <bool>
  iam_roles:
    - name: <string>
      assume_services: [<string>, ...]
      inline_policies:
        - name: <string>
          statements:
            - effect: Allow|Deny
              actions: [<string>, ...]
              resources: [<string>, ...]
  security_groups:
    - name: <string>
      description: <string|null>
      ingress:
        - from_port: <int>
          to_port: <int>
          protocol: tcp|udp|-1
          cidr_blocks: [<string>, ...]
          source_sg: <string|null>
      egress:
        - from_port: <int>
          to_port: <int>
          protocol: tcp|udp|-1
          cidr_blocks: [<string>, ...]
  duplo_services:
    - name: <string>
      image: <string>
      replicas: <int>
      ports:
        - container_port: <int>
          protocol: tcp|udp
      env:
        <key>: <value>
  eks_clusters:
    - name: <string>
      version: <string>
      public_endpoint: <bool>
      private_endpoint: <bool>
```
