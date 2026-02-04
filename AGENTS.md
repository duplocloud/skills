# AI Engineer Skill Registry (Allow-list)

This repository contains many skills under `skills/`, but the **AI Engineer is only allowed to EXECUTE**
the skills listed in this file.

The AI Engineer may DISCOVER other skills (read their `SKILL.md`) for planning, but must not execute them
unless they are added here.

## How to add a new skill

1) Create the skill under `skills/<skill-dir>/SKILL.md`
2) (Optional but recommended) Add a symlink under `.codex/skills/<skill-dir> -> ../../skills/<skill-dir>`
3) Add an entry below mapping the skill name to the SKILL.md path
4) Re-run discovery / orchestration

## Allowed skills

> Format: `- name:` is the invoked skill name, `path:` points to its SKILL.md in this repo.

- name: iac.repo_discover
  path: skills/iac-repo-discover/SKILL.md

- name: iac.plan_changes
  path: skills/iac-plan-changes/SKILL.md

- name: iac.implement
  path: skills/iac-implement/SKILL.md

- name: iac.verify
  path: skills/iac-verify/SKILL.md

- name: git.pr_ready
  path: skills/git-pr-ready/SKILL.md

- name: git.repo_acquire
  path: skills/git-repo-acquire/SKILL.md


- name: orchestrator.ai_engineer
  path: skills/orchestrator-ai_engineer/SKILL.md


# Optional / future (uncomment when ready)
# - name: k8s.bootstrap
#   path: skills/k8s-bootstrap/SKILL.md
#
# - name: tf.gen_module_stack
#   path: skills/tf-gen-module/SKILL.md
#
# - name: tf.module
#   path: skills/tf-module/SKILL.md