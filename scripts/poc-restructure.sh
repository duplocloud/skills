#!/usr/bin/env bash
set -euo pipefail

echo "=== AI Ops Core POC Restructure ==="

# 1. Create example directories
mkdir -p examples/django-k8s/spec
mkdir -p examples/django-k8s/golden/k8s/helm/django/templates
mkdir -p examples/django-k8s/golden/github/workflows

# 2. Rename schema to v1alpha1
if [ -f spec/schema/aiops-onboarding.v1.schema.json ]; then
  mv spec/schema/aiops-onboarding.v1.schema.json \
     spec/schema/aiops-onboarding.v1alpha1.schema.json
  echo "Renamed schema to v1alpha1"
fi

# 3. Update Makefile glob (safe replace)
sed -i.bak \
  's|^SPEC_GLOB :=.*|SPEC_GLOB := spec/**/*.y*ml examples/**/spec/**/*.y*ml|' \
  Makefile

rm -f Makefile.bak

echo "Folders created, schema renamed, Makefile updated."
echo "Next: paste file contents as instructed."