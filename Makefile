SHELL := /bin/bash

VENV ?= .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

SCHEMA := spec/schema/aiops-onboarding.v1alpha1.schema.json
# Multiple patterns are passed as a single quoted string to the validator.
SPEC_GLOB := spec/*.y*ml spec/**/*.y*ml examples/*/spec/*.y*ml examples/*/spec/**/*.y*ml

.PHONY: k8s-bootstrap
k8s-bootstrap: dev-deps
	@$(PY) scripts/k8s_bootstrap_runner.py --env dev --spec examples/django-k8s/spec/onboarding.dev.yaml

help:
	@echo "Targets:"
	@echo "  make spec-validate    Validate all spec YAML files against the schema"
	@echo "  make clean-venv       Remove local virtualenv"

venv:
	@test -x $(PY) || (python3 -m venv $(VENV) && $(PIP) install --upgrade pip)

dev-deps: venv
	@$(PIP) install -r requirements-dev.txt

spec-validate: dev-deps
	@$(PY) scripts/spec_validate.py --schema $(SCHEMA) --spec-glob "$(SPEC_GLOB)" --fail-on-empty

clean-venv:
	@rm -rf $(VENV)