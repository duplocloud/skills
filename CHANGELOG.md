# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Introduced **spec-driven AI Ops framework** with a clear separation between:
  - human-readable onboarding specs
  - AI-authored skills
  - deterministic, CI-safe runners
- Added **k8s.bootstrap** capability to generate Kubernetes Helm scaffolding from a validated onboarding spec.
- Added a deterministic **k8s bootstrap runner** to execute the skill contract without requiring Codex or network access.
- Added runtime audit artifacts for skill execution:
  - `.aiops/runtime/<env>/k8s-bootstrap/SUMMARY.md`
  - `.aiops/runtime/<env>/k8s-bootstrap/FILES_WRITTEN.txt`
- Added example onboarding specs, including a Django-on-Kubernetes example, validated via JSON Schema.
- Added spec validation tooling (`make spec-validate`) to enforce schema compliance before execution.

### Changed
- Standardized skill output contracts to ensure repeatable, idempotent runs.
- Enforced deterministic execution semantics (no `apply`, no cluster mutations).
- Clarified the role of AI skills as **authoring tools**, with runners acting as the execution layer.

### Fixed
- Eliminated non-deterministic runtime artifacts (e.g., ad-hoc `output.yaml`) in favor of explicit, contract-defined outputs.
- Improved YAML/Helm validation flow to support Helm templating safely.

### Notes
- This is a POC iteration; backward compatibility with earlier experimental specs is not guaranteed.

## [0.0.5] - 2026-01-23
### Added

- AI Ops onboarding specification framework (v1)
- JSON Schema contract for onboarding specs
- Example onboarding specs (minimal and production)
- Spec validation tooling (Makefile + Python validator)
- CI workflow support for enforcing spec validity
- Local developer support via virtualenv-based spec validation

## [0.0.4] - 2026-01-23

### Updated 

- actually built out the tf-module skill

## [0.0.3] - 2026-01-22

## [0.0.2] - 2026-01-12

### Added 

- initial tf-module skill
- a publish action for github actions
- added contrib doc
- added a security doc
- added an open source license
