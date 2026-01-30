#!/usr/bin/env python3
import argparse
import glob
import json
import os
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def iter_yaml_files(spec_glob: str):
    return [Path(p) for p in glob.glob(spec_glob, recursive=True) if Path(p).is_file()]


def format_error(err):
    loc = ".".join([str(x) for x in err.absolute_path]) if err.absolute_path else "<root>"
    schema_loc = ".".join([str(x) for x in err.absolute_schema_path]) if err.absolute_schema_path else "<schema>"
    return f"- path: {loc}\n  message: {err.message}\n  schema_path: {schema_loc}"


def main():
    ap = argparse.ArgumentParser(description="Validate onboarding specs against JSON Schema.")
    ap.add_argument("--schema", required=True, help="Path to JSON schema file")
    ap.add_argument("--spec-glob", default="spec/**/*.y*ml", help="Glob for spec YAML files")
    ap.add_argument("--fail-on-empty", action="store_true", help="Fail if no specs found")
    args = ap.parse_args()

    schema_path = Path(args.schema)
    if not schema_path.exists():
        print(f"ERROR: schema not found: {schema_path}", file=sys.stderr)
        return 2

    schema = load_json(schema_path)
    validator = Draft202012Validator(schema)

    files = iter_yaml_files(args.spec_glob)
    if not files and args.fail_on_empty:
        print(f"ERROR: No specs found for glob: {args.spec_glob}", file=sys.stderr)
        return 2

    failures = 0
    for fpath in files:
        try:
            data = load_yaml(fpath)
            if data is None:
                raise ValueError("YAML file is empty or invalid")
        except Exception as e:
            failures += 1
            print(f"\n❌ {fpath}\n- YAML parse error: {e}")
            continue

        errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
        if errors:
            failures += 1
            print(f"\n❌ {fpath}")
            for err in errors:
                print(format_error(err))
        else:
            print(f"✅ {fpath}")

    if failures:
        print(f"\nFAILED: {failures} file(s) invalid.")
        return 1

    print("\nPASSED: all specs valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
