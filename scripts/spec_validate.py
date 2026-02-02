import argparse
import glob
import json
import shlex
import sys

import yaml
import jsonschema


def main():
    parser = argparse.ArgumentParser(description="Validate specs against schema")
    parser.add_argument("--schema", required=True, help="Path to the JSON schema file")
    parser.add_argument(
        "--spec-glob",
        type=str,
        default=None,
        help='Glob pattern(s) for spec files (space-separated in quotes, as passed by Makefile)',
    )
    parser.add_argument("--fail-on-empty", action="store_true", help="Fail if no spec files are found")

    args = parser.parse_args()

    spec_files = []
    if args.spec_glob:
        # Makefile passes multiple glob patterns as ONE quoted string; split into patterns here.
        patterns = shlex.split(args.spec_glob)
        seen = set()
        for pattern in patterns:
            for path in glob.glob(pattern, recursive=True):
                seen.add(path)
        spec_files = sorted(seen)

    if not spec_files:
        print(f"ERROR: No specs found for glob: {args.spec_glob}")
        if args.fail_on_empty:
            sys.exit(2)
        return

    with open(args.schema) as f:
        schema = json.load(f)

    # Use Draft7Validator unless your schema explicitly depends on 2020-12 features.
    validator = jsonschema.Draft7Validator(schema)

    error_found = False

    for spec_file in spec_files:
        with open(spec_file) as f:
            try:
                spec = yaml.safe_load(f)
            except yaml.YAMLError as e:
                print(f"ERROR: Failed to parse YAML file {spec_file}: {e}")
                error_found = True
                continue

        errors = sorted(validator.iter_errors(spec), key=lambda e: list(e.path))
        if errors:
            print(f"❌ {spec_file}")
            for error in errors:
                print(f"  - {error.message}")
            error_found = True
        else:
            print(f"✅ {spec_file}")

    if error_found:
        sys.exit(1)

    print("\nPASSED: all specs valid.")


if __name__ == "__main__":
    main()