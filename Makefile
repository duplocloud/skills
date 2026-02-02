SHELL := /bin/bash

VENV ?= .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

SCHEMA := spec/schema/aiops-onboarding.v1.schema.json
SPEC_GLOB := spec/**/*.y*ml examples/**/spec/**/*.y*ml

help:
	@echo "Targets:"
	@echo "  make spec-validate"

venv:
	@test -x $(PY) || (python3 -m venv $(VENV) && $(PIP) install --upgrade pip)

dev-deps: venv
	@$(PIP) install -r requirements-dev.txt

spec-validate: dev-deps
	@$(PY) scripts/spec_validate.py --schema $(SCHEMA) --spec-glob "$(SPEC_GLOB)" --fail-on-empty

clean-venv:
	@rm -rf $(VENV)
