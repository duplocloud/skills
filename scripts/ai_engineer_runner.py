#!/usr/bin/env python3
"""
Generic AI Engineer runner:
- Everything is driven by TASK_FILE + repo discovery.
- No hard-coded "S3 skill" logic; the model plans/implements from task text.
- Writes deterministic runtime artifacts under AIOPS_RUNTIME_DIR/RUN_ID/<step>/...

Prereqs:
  pip install openai
  export OPENAI_API_KEY=...
Optional:
  gh auth login   (for PR creation)
  terraform       (for local verify)
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple

# OpenAI Responses API (official SDK pattern)
# https://platform.openai.com/docs/guides/text  [oai_citation:1‡OpenAI Platform](https://platform.openai.com/docs/guides/text)
try:
    from openai import OpenAI
except Exception as e:
    OpenAI = None  # type: ignore


# ---------------------------
# Utilities
# ---------------------------

def run(cmd: list[str], cwd: Optional[Path] = None, check: bool = True) -> Tuple[int, str]:
    p = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if check and p.returncode != 0:
        raise RuntimeError(f"Command failed ({p.returncode}): {' '.join(cmd)}\n{p.stdout}")
    return p.returncode, p.stdout


def which(bin_name: str) -> Optional[str]:
    return shutil.which(bin_name)


def now_run_id() -> str:
    # deterministic-ish for humans; you can override by arg
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def write_text(p: Path, s: str) -> None:
    ensure_dir(p.parent)
    p.write_text(s, encoding="utf-8")


def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def git_remote_url(repo_dir: Path) -> str:
    try:
        _, out = run(["git", "-C", str(repo_dir), "remote", "get-url", "origin"], check=False)
        return out.strip() or "unknown"
    except Exception:
        return "unknown"


def safe_relpath(repo_dir: Path, abs_path: Path) -> str:
    try:
        rel = abs_path.relative_to(repo_dir)
        return str(rel)
    except Exception:
        return str(abs_path)


def extract_first_unified_diff(text: str) -> str:
    """
    Expect the model to output a single unified diff in a fenced block.
    We accept:
      ```diff
      ...
      ```
    or raw diff starting with "diff --git".
    """
    m = re.search(r"```diff\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip() + "\n"
    m2 = re.search(r"(^diff --git .*?$.*)", text, flags=re.DOTALL | re.MULTILINE)
    if m2:
        return m2.group(1).strip() + "\n"
    raise ValueError("No unified diff found in model output.")


def load_agents_allowlist(ai_core_root: Path) -> str:
    agents = ai_core_root / "AGENTS.md"
    if not agents.exists():
        return ""
    return agents.read_text(encoding="utf-8")


# ---------------------------
# Repo discovery (deterministic)
# ---------------------------

def repo_discover(repo_dir: Path) -> dict:
    """
    Minimal deterministic discover:
      - terraform roots
      - modules dir
      - github workflows presence
      - makefile targets presence
    """
    roots = []
    for p in [repo_dir / "terraform" / "envs"]:
        if p.exists() and p.is_dir():
            for envdir in sorted(p.iterdir()):
                if envdir.is_dir() and any(envdir.glob("*.tf")):
                    roots.append(str(envdir.relative_to(repo_dir)))

    modules_dirs = []
    for cand in [repo_dir / "terraform" / "modules", repo_dir / "modules"]:
        if cand.exists() and cand.is_dir():
            modules_dirs.append(str(cand.relative_to(repo_dir)))

    workflows = []
    wf_dir = repo_dir / ".github" / "workflows"
    if wf_dir.exists():
        for f in sorted(wf_dir.glob("*.yml")) + sorted(wf_dir.glob("*.yaml")):
            workflows.append(str(f.relative_to(repo_dir)))

    makefile = repo_dir / "Makefile"
    makefile_exists = makefile.exists()

    return {
        "repo_root": str(repo_dir),
        "terraform_roots": roots,
        "modules_dirs": modules_dirs,
        "workflows": workflows,
        "makefile_exists": makefile_exists,
    }


def render_repo_map_md(discovery: dict) -> str:
    return (
        "# REPO_MAP\n\n"
        f"- Repo root: `{discovery['repo_root']}`\n"
        f"- Terraform roots:\n" + "".join([f"  - `{r}`\n" for r in discovery["terraform_roots"]]) +
        f"- Modules dirs:\n" + "".join([f"  - `{m}`\n" for m in discovery["modules_dirs"]]) +
        f"- GitHub workflows:\n" + ("".join([f"  - `{w}`\n" for w in discovery["workflows"]]) if discovery["workflows"] else "  - none\n") +
        f"- Makefile: `{'present' if discovery['makefile_exists'] else 'missing'}`\n"
    )


# ---------------------------
# OpenAI calls (plan + implement)
# ---------------------------

def openai_client() -> "OpenAI":
    if OpenAI is None:
        raise RuntimeError("openai package not installed. Run: pip install openai")
    return OpenAI()


def model_call_text(model: str, system: str, user: str) -> str:
    client = openai_client()
    resp = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return resp.output_text


# ---------------------------
# Terraform verify
# ---------------------------

def terraform_verify(repo_dir: Path, tf_root_rel: str) -> dict:
    tf = which("terraform")
    result = {
        "terraform_root": str(repo_dir / tf_root_rel),
        "terraform_available": bool(tf),
        "fmt": {"status": "not-run", "output": "terraform not found"},
        "validate": {"status": "not-run", "output": "terraform not found"},
        "plan": {"status": "not-run", "output": "terraform not found"},
    }
    if not tf:
        return result

    # fmt
    _, out = run(["terraform", "fmt", "-check", "-recursive"], cwd=repo_dir, check=False)
    result["fmt"]["output"] = out
    result["fmt"]["status"] = "pass" if "Error:" not in out and "panic" not in out and "failed" not in out.lower() else "fail"

    # validate
    tf_root = repo_dir / tf_root_rel
    _, out_init = run(["terraform", "init", "-backend=false"], cwd=tf_root, check=False)
    _, out_val = run(["terraform", "validate"], cwd=tf_root, check=False)
    out = out_init + "\n" + out_val
    result["validate"]["output"] = out
    result["validate"]["status"] = "pass" if "Success!" in out_val or "Success!" in out else ("fail" if "Error:" in out else "fail")

    # plan (best-effort)
    _, out_plan = run(["terraform", "plan", "-lock=false", "-refresh=false"], cwd=tf_root, check=False)
    result["plan"]["output"] = out_plan
    if "Error:" in out_plan:
        result["plan"]["status"] = "best-effort fail"
    else:
        result["plan"]["status"] = "pass"

    return result


# ---------------------------
# Main flow
# ---------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ai-core-root", required=True, help="Path to ai-core repo (contains skills/, AGENTS.md, prompts/)")
    ap.add_argument("--repo-url", required=True, help="Git URL to clone (ssh or https)")
    ap.add_argument("--workdir", required=True, help="Local working directory for clone")
    ap.add_argument("--task-file", required=True, help="Path to task markdown (relative to ai-core-root or absolute)")
    ap.add_argument("--target-env", default="dev")
    ap.add_argument("--run-id", default="")
    ap.add_argument("--base-branch", default="main")
    ap.add_argument("--model", default="gpt-5.2")
    ap.add_argument("--pr-title", default="AI Engineer: IaC change")
    ap.add_argument("--pr-branch", default="feature/ai-engineer-change")
    args = ap.parse_args()

    ai_core_root = Path(args.ai_core_root).resolve()
    run_id = args.run_id or now_run_id()
    runtime_base = ai_core_root / ".aiops" / "runtime"
    repo_dir = Path(args.workdir).resolve()

    # Resolve task file
    task_path = Path(args.task_file)
    if not task_path.is_absolute():
        task_path = (ai_core_root / task_path).resolve()
    if not task_path.exists():
        raise FileNotFoundError(f"TASK_FILE not found: {task_path}")

    # Runtime dirs
    rd = runtime_base / run_id
    rd_repo_discover = rd / "repo_discover"
    rd_plan = rd / "plan_changes"
    rd_impl = rd / "implement"
    rd_verify = rd / "verify"
    rd_pr = rd / "pr_ready"
    for d in [rd_repo_discover, rd_plan, rd_impl, rd_verify, rd_pr]:
        ensure_dir(d)

    # Metadata
    write_text(rd / "RUNTIME_BASE.txt", str(runtime_base))
    write_text(rd / "TARGET_REPO.txt", f"REPO_DIR={repo_dir}\nREPO_URL={args.repo_url}\n")

    # 1) Acquire repo (clone or reuse)
    cmds = []
    if not repo_dir.exists():
        ensure_dir(repo_dir.parent)
        cmds.append(["git", "clone", args.repo_url, str(repo_dir)])
        run(cmds[-1], check=True)
    else:
        # best-effort fetch
        cmds.append(["git", "-C", str(repo_dir), "fetch", "--all", "--prune"])
        run(cmds[-1], check=False)

    write_text(rd_repo_discover / "COMMANDS_RUN.txt", "\n".join(" ".join(c) for c in cmds) + "\n")
    write_text(rd_repo_discover / "SUMMARY.md", f"- Repo acquired at `{repo_dir}`\n- origin: `{git_remote_url(repo_dir)}`\n")

    # 2) repo_discover (deterministic)
    disc = repo_discover(repo_dir)
    repo_map = render_repo_map_md(disc)
    write_text(rd_repo_discover / "REPO_MAP.md", repo_map)
    write_text(rd_repo_discover / "FILES_SCANNED.txt", "terraform/envs/* (if present)\n.github/workflows/* (if present)\nMakefile (if present)\n")
    write_text(rd_repo_discover / "SUMMARY.md", f"- Terraform roots: {disc['terraform_roots']}\n- Workflows: {disc['workflows'] or ['none']}\n")

    # Choose terraform root for verify (prefer target env)
    tf_root_rel = f"terraform/envs/{args.target_env}"
    if tf_root_rel not in disc["terraform_roots"] and disc["terraform_roots"]:
        tf_root_rel = disc["terraform_roots"][0]  # fallback
    write_text(rd_repo_discover / "TF_ROOT.txt", tf_root_rel + "\n")

    # 3) plan_changes (LLM)
    skill_plan_path = ai_core_root / "skills" / "iac-plan-changes" / "SKILL.md"
    system = "You are an Operator AI Engineer. Follow the provided SKILL.md exactly. Output only the required artifacts."
    user = (
        "SKILL.md:\n\n" + read_text(skill_plan_path) + "\n\n"
        "TASK_FILE:\n\n" + read_text(task_path) + "\n\n"
        "REPO_MAP.md:\n\n" + repo_map + "\n\n"
        f"PARAMS:\nREPO_DIR={repo_dir}\nRUN_ID={run_id}\nTARGET_ENV={args.target_env}\nAIOPS_RUNTIME_DIR={runtime_base}\n"
        "\nReturn JSON with keys: PLAN_MD, FILES_TO_CHANGE_TXT, ASSUMPTIONS_MD, OPEN_QUESTIONS_MD, SUMMARY_MD, SELF_CHECK_MD.\n"
        "Each value must be a string containing the full file contents.\n"
    )
    plan_out = model_call_text(args.model, system, user)
    plan_json = json.loads(plan_out)

    write_text(rd_plan / "PLAN.md", plan_json["PLAN_MD"])
    write_text(rd_plan / "FILES_TO_CHANGE.txt", plan_json["FILES_TO_CHANGE_TXT"])
    write_text(rd_plan / "ASSUMPTIONS.md", plan_json["ASSUMPTIONS_MD"])
    write_text(rd_plan / "OPEN_QUESTIONS.md", plan_json["OPEN_QUESTIONS_MD"])
    write_text(rd_plan / "SUMMARY.md", plan_json["SUMMARY_MD"])
    write_text(rd_plan / "SELF_CHECK.md", plan_json["SELF_CHECK_MD"])

    # 4) implement (LLM -> unified diff -> git apply)
    skill_impl_path = ai_core_root / "skills" / "iac-implement" / "SKILL.md"
    impl_user = (
        "SKILL.md:\n\n" + read_text(skill_impl_path) + "\n\n"
        "PLAN.md:\n\n" + plan_json["PLAN_MD"] + "\n\n"
        "FILES_TO_CHANGE.txt:\n\n" + plan_json["FILES_TO_CHANGE_TXT"] + "\n\n"
        "REPO_MAP.md:\n\n" + repo_map + "\n\n"
        f"PARAMS:\nREPO_DIR={repo_dir}\nRUN_ID={run_id}\nTARGET_ENV={args.target_env}\nBASE_BRANCH={args.base_branch}\n"
        "\nOutput a single unified diff (git-style) in a ```diff block. No extra prose.\n"
        "The diff must only touch files listed in FILES_TO_CHANGE.txt.\n"
    )
    diff_text = model_call_text(args.model, system, impl_user)
    unified = extract_first_unified_diff(diff_text)

    patch_file = rd_impl / "changes.diff"
    write_text(patch_file, unified)

    # Safety: ensure patch only touches expected paths
    expected_abs = [Path(line.strip()) for line in plan_json["FILES_TO_CHANGE_TXT"].splitlines() if line.strip()]
    expected_rel = set(safe_relpath(repo_dir, p) for p in expected_abs)
    touched = set(re.findall(r"^\+\+\+ b/(.+)$", unified, flags=re.MULTILINE))
    touched.discard("/dev/null")
    if not touched.issubset(expected_rel):
        raise RuntimeError(f"Patch touches unexpected files.\nTouched: {sorted(touched)}\nExpected: {sorted(expected_rel)}")

    # Apply
    run(["git", "-C", str(repo_dir), "apply", str(patch_file)], check=True)

    # 5) verify
    v = terraform_verify(repo_dir, tf_root_rel)
    write_text(rd_verify / "FMT_OUTPUT.txt", v["fmt"]["output"])
    write_text(rd_verify / "VALIDATE_OUTPUT.txt", v["validate"]["output"])
    write_text(rd_verify / "PLAN_OUTPUT.txt", v["plan"]["output"])
    write_text(rd_verify / "COMMANDS_RUN.txt", "terraform fmt/validate/plan (best-effort)\n")
    check_md = (
        "# IaC Verify Results\n\n"
        f"- Terraform root: {v['terraform_root']}\n"
        f"- Terraform CLI: {'available' if v['terraform_available'] else 'not available'}\n\n"
        "## Status\n"
        f"- fmt: {v['fmt']['status']}\n"
        f"- validate: {v['validate']['status']}\n"
        f"- plan: {v['plan']['status']}\n"
    )
    write_text(rd_verify / "CHECK_RESULTS.md", check_md)
    write_text(rd_verify / "SUMMARY.md", "See CHECK_RESULTS.md and *_OUTPUT.txt files.\n")

    # 6) PR ready (branch/commit/push/pr)
    # Create branch, commit staged changes, create PR if gh exists
    pr_cmds = []
    pr_cmds.append(["git", "-C", str(repo_dir), "checkout", args.base_branch])
    run(pr_cmds[-1], check=False)
    pr_cmds.append(["git", "-C", str(repo_dir), "checkout", "-b", args.pr_branch])
    run(pr_cmds[-1], check=True)
    pr_cmds.append(["git", "-C", str(repo_dir), "add", "-A"])
    run(pr_cmds[-1], check=True)
    pr_cmds.append(["git", "-C", str(repo_dir), "commit", "-m", args.pr_title])
    run(pr_cmds[-1], check=True)

    pr_body = (
        f"## Summary\n{args.pr_title}\n\n"
        "## Plan\n"
        f"- Plan: `{rd_plan / 'PLAN.md'}`\n\n"
        "## Verification\n"
        f"- Verify: `{rd_verify / 'CHECK_RESULTS.md'}`\n\n"
        "## Notes\n"
        "- This PR was generated by the AI Engineer runner.\n"
    )
    write_text(rd_pr / "PR_BODY.md", pr_body)
    write_text(rd_pr / "GIT_COMMANDS.txt", "\n".join(" ".join(c) for c in pr_cmds) + "\n")

    pr_created = False
    if which("gh"):
        # push + create PR
        pr_cmds2 = []
        pr_cmds2.append(["git", "-C", str(repo_dir), "push", "-u", "origin", args.pr_branch])
        run(pr_cmds2[-1], check=True)
        pr_cmds2.append([
            "gh", "pr", "create",
            "--base", args.base_branch,
            "--head", args.pr_branch,
            "--title", args.pr_title,
            "--body-file", str(rd_pr / "PR_BODY.md"),
        ])
        run(pr_cmds2[-1], check=True)
        pr_created = True
        write_text(rd_pr / "SUMMARY.md", "PR created via gh.\n")
        write_text(rd_pr / "GIT_COMMANDS.txt", read_text(rd_pr / "GIT_COMMANDS.txt") + "\n".join(" ".join(c) for c in pr_cmds2) + "\n")
    else:
        write_text(
            rd_pr / "SUMMARY.md",
            "gh not found. Manual PR steps:\n"
            f"1) git -C {repo_dir} push -u origin {args.pr_branch}\n"
            f"2) Open GitHub and create PR into {args.base_branch} with body from PR_BODY.md\n"
        )

    # Final orchestrator summary
    summary = (
        f"# AI Engineer Run Summary\n\n"
        f"- RUN_ID: `{run_id}`\n"
        f"- Repo: `{repo_dir}`\n"
        f"- Task: `{task_path}`\n"
        f"- Runtime: `{rd}`\n\n"
        "## Steps\n"
        "- repo_discover: complete\n"
        "- plan_changes: complete\n"
        "- implement: complete (patch applied)\n"
        f"- verify: complete (terraform {'available' if v['terraform_available'] else 'missing'})\n"
        f"- pr_ready: {'PR created' if pr_created else 'manual PR required'}\n"
    )
    write_text(rd / "ORCHESTRATOR_SUMMARY.md", summary)

    print(summary)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)