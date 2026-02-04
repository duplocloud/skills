---
name: git.repo_acquire
description: Acquire an IaC repo locally (use existing path or clone), checkout base branch, and write deterministic runtime metadata for downstream skills.
---

# git.repo_acquire — Repo Acquire (Clone/Open + Metadata)

You are an Operator AI Engineer. Your job is to ensure a usable local repo directory exists and is on the correct base branch. You must write deterministic metadata artifacts for downstream skills.

This skill is designed to support full end-to-end orchestration where the repo may not exist locally yet.

---

## Inputs

- `RUN_ID`: Run identifier (required)

Repo source (choose one via precedence):
- `REPO_DIR`: Local path to an existing repo (optional)
- `REPO_URL`: Git URL to clone if REPO_DIR is not usable (optional)

Branching:
- `BASE_BRANCH`: Base branch (optional; default `main`)

Runtime:
- `AIOPS_RUNTIME_DIR`: Optional override for where runtime artifacts are written (recommended for demos)

---

## Runtime and output directory (IMPORTANT)

All artifacts MUST be written to a deterministic runtime directory.

### Runtime base selection (precedence order)
1) If the `AIOPS_RUNTIME_DIR` input is provided and non-empty, use it.
2) Else if an environment variable `AIOPS_RUNTIME_DIR` is set and non-empty, use it.
3) Otherwise, default to `./.aiops/runtime` (relative to current working directory).

### Output path
Write outputs under:

`<RUNTIME_BASE>/<RUN_ID>/repo_acquire/`

### Required metadata files (also write at run root)
Also write:
- `<RUNTIME_BASE>/<RUN_ID>/TARGET_REPO.txt`
- `<RUNTIME_BASE>/<RUN_ID>/RUNTIME_BASE.txt`

### Required outputs
- `REPO_DIR.txt` (absolute repo path selected/created)
- `GIT_INFO.txt` (remote URL, head SHA, current branch, base branch)
- `COMMANDS_RUN.txt` (exact commands attempted/run, one per line)
- `SUMMARY.md`

---

## Non-negotiable rules

- Do not modify any IaC code files intentionally. This step is acquisition only.
- Never write secrets into runtime artifacts.
- Prefer `--ff-only` pulls (no merges).
- Never claim a command succeeded unless you actually ran it and observed success.
- If neither REPO_DIR nor REPO_URL yields a valid repo, stop and explain exactly what’s missing.

---

## Repo acquisition procedure (MANDATORY)

### 0) Initialize runtime directory + metadata
1) Select `RUNTIME_BASE` using precedence rules.
2) Create `<RUNTIME_BASE>/<RUN_ID>/repo_acquire/`.
3) Write:
   - `<RUNTIME_BASE>/<RUN_ID>/RUNTIME_BASE.txt` containing the absolute `RUNTIME_BASE`.

### 1) Determine repo source (precedence)

#### A) If REPO_DIR provided:
1) Check if it exists.
2) Verify it is a git repository (contains `.git/`).
3) If valid, use it as the repo directory.

If REPO_DIR is provided but invalid, record why in SUMMARY.md and continue to REPO_URL logic.

#### B) Else if REPO_URL provided:
Clone into a deterministic local directory derived from RUN_ID:

- Preferred clone location:
  - `/tmp/ai-engineer/<RUN_ID>/repo` (macOS/Linux)
- If `/tmp` is unavailable, use OS temp equivalent but keep the `<RUN_ID>/repo` suffix.

Rules:
- If target directory exists, do not delete it. Either:
  - re-use it if it is a valid repo with matching remote, OR
  - stop and report conflict if it is not a valid repo.
- Clone should be non-interactive.

### 2) Ensure origin and base branch are usable
From inside `REPO_DIR`:
1) Record remote (best effort):
   - `git remote get-url origin`
2) Fetch base branch reference (best effort; do not fail if offline):
   - `git fetch origin <BASE_BRANCH> --quiet`
3) Checkout base branch:
   - Prefer:
     - `git checkout <BASE_BRANCH>`
   - If local branch missing but remote exists:
     - `git checkout -B <BASE_BRANCH> origin/<BASE_BRANCH>`
4) Pull fast-forward only (best effort):
   - `git pull --ff-only` (if it fails, record why; do not merge)

### 3) Capture git state (MANDATORY)
Collect and write:
- current branch: `git rev-parse --abbrev-ref HEAD`
- head SHA: `git log -1 --format=%H`
- status porcelain (to ensure no unexpected dirty state): `git status --porcelain=v1 -uall`

If repo is dirty:
- Do NOT clean or reset automatically.
- Record this in SUMMARY.md as a risk for downstream steps.

### 4) Write artifacts (MANDATORY)

#### Write TARGET_REPO.txt (at `<RUNTIME_BASE>/<RUN_ID>/TARGET_REPO.txt`)
Format:
- `REPO_DIR=<absolute path>`
- `REPO_URL=<origin url or unknown>`
- `BASE_BRANCH=<BASE_BRANCH>`
- `GIT_HEAD=<sha or unknown>`

#### Write REPO_DIR.txt
Contains only the absolute repo directory path.

#### Write GIT_INFO.txt
Must include:
- origin URL (or unknown)
- base branch
- current branch
- head SHA
- dirty status summary (clean/dirty)

#### Write COMMANDS_RUN.txt
One command per line, exactly as executed (including `git -C ...` if used).

#### Write SUMMARY.md
Must include:
- whether repo was opened or cloned
- chosen REPO_DIR
- base branch checkout result
- whether repo is clean
- any limitations (offline fetch, missing origin, etc.)

---

## Completion criteria

- A usable git repo exists at a concrete REPO_DIR.
- Repo is on BASE_BRANCH (or failure recorded clearly).
- Runtime artifacts exist under `<RUNTIME_BASE>/<RUN_ID>/repo_acquire/`.
- TARGET_REPO.txt and RUNTIME_BASE.txt exist under `<RUNTIME_BASE>/<RUN_ID>/`.