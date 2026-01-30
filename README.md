# Duplocloud Skills 

A curated list of Agent Skills made by duplo. Use these with any tools supporting Claude Skills. 

Supported Tools: 
- claude code
- openai codex
- github copilot

# DuploCloud AI Ops Framework

A curated and extensible **AI Ops framework** for DuploCloud engineers, built to **dramatically reduce client onboarding time** by combining:

- DevContainers (reproducible environments)
- AI Skills (reusable automation playbooks)
- AI Agents (Planner / Operator / Reviewer roles)
- Spec‑driven infrastructure and platform automation

Terraform is the first supported domain, but this framework is intentionally **not Terraform‑only**.

---

## What Problem This Solves

Client onboarding today involves a large amount of repeated, manual, and error‑prone work:

- Infrastructure scaffolding
- Environment setup
- CI/CD bootstrapping
- Platform configuration
- Migration planning

This framework uses **AI + contracts + guardrails** to automate the repeatable parts while keeping humans firmly in control of approvals and deployments.

---

## Core Concepts

### 1. DevContainers
All work is done inside a VS Code DevContainer so that:
- Every engineer uses the same toolchain
- Skill execution is deterministic
- Onboarding new engineers is frictionless

### 2. Skills
A **Skill** is a versioned, reusable automation unit that:
- Reads a validated spec
- Generates code or configuration
- Runs validation and planning steps
- Produces PR‑ready output and artifacts

Examples:
- `tf.gen_modular_stack` — Generate modular Terraform using the DuploCloud provider
- (future) `k8s.bootstrap`, `gha.generate_pipelines`, `s3.migration.plan`

### 3. AI Agents
Skills are executed by AI agents with clear separation of responsibility:

| Agent | Responsibility |
|------|---------------|
| Planner | Convert intent → structured spec |
| Operator | Execute skills and generate artifacts |
| Reviewer | Validate output and summarize risk |

AI **never deploys**. It prepares changes for human review.

---

## Onboarding Specification (Contract‑First)

Client onboarding is driven by a single YAML specification that acts as a **contract** between humans and automation.

- Versioned
- Schema‑validated
- Reviewable in PRs
- Reusable across environments

### Spec Location

```
spec/
├── schema/
│   └── aiops-onboarding.v1.schema.json
├── examples/
│   ├── minimal.dev.yaml
│   └── prod.yaml
```

Client repositories will contain **real onboarding specs**, while this repo provides the **schema and examples**.

---

## Spec Validation

All specs are validated against a JSON Schema before any AI skill is allowed to run.

### Local validation

```bash
make spec-validate
```

This will:
- Create a local Python virtualenv (`.venv/`)
- Install validation dependencies
- Validate all `spec/**/*.yaml` files

### CI enforcement

Client repos are expected to run the same validation in CI to prevent invalid specs from reaching automation.

---

## Terraform (Current Skill Family)

The first supported skill family targets Terraform using the **DuploCloud Terraform Provider**.

Capabilities include:
- Greenfield modular Terraform generation
- Environment separation (dev/stage/prod)
- Formatting, validation, and safe planning
- PR‑ready commits and runtime artifacts

Terraform is intentionally just the starting point.

---

## Repository Structure

```
ai-ops/
├── skills/                # Core reusable skills
├── spec/                  # Spec schema and examples
├── scripts/               # Validation and helper tooling
├── .github/workflows/     # CI workflows
├── Makefile               # Local developer workflows
└── README.md
```

---

## How This Scales

This framework is designed to grow by **adding skills**, not rewriting pipelines:

- Kubernetes bootstrapping
- GitHub Actions generation
- Database and S3 migration planning
- Security and compliance automation

Each new skill consumes the same validated spec and runs inside the same guardrails.

---

## Contributing

- Add or improve skills under `skills/`
- Propose spec changes via schema updates
- Add examples under `spec/examples/`
- Keep automation safe, explicit, and reviewable

---

## Guiding Principle

> **AI prepares. Humans approve. Systems deploy.**

This is how we scale safely.