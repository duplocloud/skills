# AI Engineer Prompts (Demo)

These prompts define deterministic tasks for an “AI Engineer” agent to execute against a target IaC repo.

## How to use
1. Pick a task prompt under `tasks/`
2. Provide the target repo URL + base branch
3. Run the agent using your preferred tool (Codex / Claude), with ai-ops skills enabled
4. The agent should clone the target repo, create a branch, implement changes, run checks, and open a PR

## Why prompts (not YAML)
We use detailed prompts to stay flexible across AWS/GCP/Azure repos without schema churn, while still being deterministic enough for repeatable demos.

## Guardrails
All prompts enforce:
- no apply
- no secrets
- minimal diffs
- validation evidence in PR