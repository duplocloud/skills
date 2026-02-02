# DuploCloud AI Ops Framework

This repository is a **spec-driven automation framework** for DuploCloud onboarding and day-2 operations.

It combines:
- **Customer-facing onboarding specs** (validated, version-controlled)
- **AI Agent Skills** (design-time guidance for assistants like Codex / Claude)
- **Deterministic runners** (CI-safe scripts that generate artifacts without requiring AI)

The result: **faster client onboarding** with repeatable, reviewable outputs — even when AI tools are offline.

---

## Read this first

### What engineers should (and should not) do

- ✅ **Do** start from the customer-facing example spec and iterate.
- ✅ **Do** run `make spec-validate` before generating anything.
- ✅ **Do** use `make <skill>` targets to generate artifacts deterministically.
- ❌ **Do not** hand-write internal machine specs from scratch.
- ❌ **Do not** rely on an AI assistant being online to run generation.

### The core model

```
Customer intent (human-friendly spec)
        ↓
Validated spec (schema-checked contract)
        ↓
Deterministic runner (Python)
        ↓
Generated artifacts (Helm / Terraform / GitHub Actions / …)
```

AI skills (`skills/*/SKILL.md`) are used to **author and evolve** runners and templates. They are **not required at runtime**.

---

## Quickstart

### Prerequisites

- Python 3
- `make`

### Setup

```bash
make dev-deps
```

### Validate specs

```bash
make spec-validate
```

---

## End-to-end example: Django app to Kubernetes (Helm)

This repository includes a working example that demonstrates the framework end to end.

### What it shows

- A customer-facing onboarding spec
- Validation via JSON Schema
- Deterministic artifact generation (no AI required)
- Golden outputs for review/demos

### Files

- Input spec:
  - `examples/django-k8s/spec/onboarding.dev.yaml`
- Deterministic runner:
  - `scripts/k8s_bootstrap_runner.py`
- Generated Helm chart (golden output for review):
  - `examples/django-k8s/golden/k8s/helm/django/`

### Run it

```bash
make spec-validate
make k8s-bootstrap
```

> Output artifacts are written deterministically, and runtime audit files are emitted under `.aiops/runtime/`.

---

## Repository layout

```
skills/                    # AI Agent Skills (design-time guidance)
  <skill>/SKILL.md

scripts/                   # Deterministic runners + tooling
  spec_validate.py
  k8s_bootstrap_runner.py

spec/                      # Spec schemas and example specs
  schema/
  examples/

examples/                  # End-to-end examples
  django-k8s/
    spec/                  # Customer-facing intent (input)
    golden/                # Reviewable generated outputs

.aiops/                    # Runtime/audit outputs (ignored by git)
.codex/skills/             # Optional symlinks to make Codex discover skills
```

---

## Specs

### Philosophy

Specs are the **contract** between onboarding intent and automation.

- Specs are **version-controlled** and **schema-validated**.
- Specs are **idempotent**: they can evolve over time.
- Specs are designed so **engineers don’t write them from scratch**; start from examples and iterate.

### Validate specs

```bash
make spec-validate
```

---

## Skills vs runners

### Skills (`skills/*`)

- Human-readable instructions (YAML frontmatter + markdown)
- Used by AI assistants (Codex / Claude / Gemini / Copilot) to produce consistent changes
- Great for:
  - scaffolding new skills
  - refactoring templates
  - generating runner updates

### Runners (`scripts/*`)

- Deterministic executors
- Generate artifacts from validated specs
- Designed for:
  - repeatable runs
  - CI execution
  - offline execution

This separation ensures the framework is usable even if an AI tool times out.

---

## Available skills

### tf-module

Terraform module creation using DuploCloud provided resources and patterns.

**Location**: `skills/tf-module/`

### k8s-bootstrap

Generate Kubernetes Helm scaffolding from an onboarding spec.

**Location**: `skills/k8s-bootstrap/`

Run deterministically:

```bash
make k8s-bootstrap
```

---

## Devcontainer and skill distribution (optional)

This repo also supports distributing skills to multiple AI platforms (Codex, Claude, Gemini, Copilot) via devcontainers.

### Platforms

- **Claude (Anthropic)**: skills in `.claude/skills/` — see Anthropic docs.
- **OpenAI Codex**: skills in `.codex/skills/` — see OpenAI docs.
- **Gemini CLI**: skills in `.gemini/skills/` — see Gemini docs.
- **GitHub Copilot**: skills in `.github/skills/` or `~/.copilot/skills/` — see GitHub docs.

### Installing skills via devcontainer features

Add the AI feature to your `.devcontainer/devcontainer.json`:

```json
{
  "features": {
    "ghcr.io/duplocloud/devcontainers/ai:1": {}
  }
}
```

Then install skills:

```bash
# Example for Codex
./scripts/codex-skill-new.sh <skill-dir> <skill-name> "<description>"
```

> Note: This repository may include `.codex/skills/*` symlinks to improve Codex discovery. The source of truth remains in `skills/`.

---

## Security

- Treat skills like code: review before running.
- Never commit secrets.
- Prefer ephemeral credentials (OIDC where possible).

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## License

See [LICENSE](LICENSE).
