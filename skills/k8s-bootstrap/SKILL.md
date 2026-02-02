# Skill: k8s-bootstrap
Generate Kubernetes Helm chart for the application

## Non-negotiable rules
- MUST create runtime artifacts: `.aiops/runtime/<ENV>/k8s-bootstrap/SUMMARY.md` and `.aiops/runtime/<ENV>/k8s-bootstrap/FILES_WRITTEN.txt`.
- MUST NOT create `.aiops/runtime/<ENV>/k8s-bootstrap/output.yaml` (or any other runtime file not listed in the Output contract).
- MUST generate these Helm files for every run: `Chart.yaml`, `values-<ENV>.yaml`, `templates/namespace.yaml`, `templates/deployment.yaml`, `templates/service.yaml`.

## Output contract

This skill MUST generate (or update) the following files:

**Helm chart (always generated):**
- `k8s/helm/<app_name>/Chart.yaml`
- `k8s/helm/<app_name>/values-<ENV>.yaml`
- `k8s/helm/<app_name>/templates/namespace.yaml`
- `k8s/helm/<app_name>/templates/deployment.yaml`
- `k8s/helm/<app_name>/templates/service.yaml`

**Ingress (only if enabled in spec):**
- `k8s/helm/<app_name>/templates/ingress.yaml`

**Runtime artifacts (always generated):**
- `.aiops/runtime/<ENV>/k8s-bootstrap/SUMMARY.md`
- `.aiops/runtime/<ENV>/k8s-bootstrap/FILES_WRITTEN.txt`

This skill MUST NOT create any other files under `.aiops/runtime/<ENV>/k8s-bootstrap/` (in particular, do not create `output.yaml`).

## Validation steps
- If `helm` is available, render and validate rendered YAML: `helm template <app_name> k8s/helm/<app_name> -f k8s/helm/<app_name>/values-<ENV>.yaml > .aiops/runtime/<ENV>/k8s-bootstrap/rendered.yaml` and then YAML-parse `rendered.yaml`.
- If `helm` is not available, ensure Helm template expressions are quoted where they appear as YAML scalars (e.g., `namespace: "{{ .Values.namespace }}"`) and then YAML-parse the template files.

## Templates
Ensure the provided templates are YAML-parseable without Helm rendering by quoting scalar Helm expressions:

- In `templates/namespace.yaml`, set `name: "{{ .Values.namespace }}"`.
- In `templates/service.yaml`, set `namespace: "{{ .Values.namespace }}"`, and quote `port` and `targetPort` as `"{{ .Values.service.port }}"` and `"{{ .Values.service.targetPort }}"`.

## Completion checklist
- [ ] The required Helm files exist under `k8s/helm/<app_name>/`
- [ ] `FILES_WRITTEN.txt` lists every generated file (one per line)
- [ ] `SUMMARY.md` includes inputs, outputs, and validation results
- [ ] No `output.yaml` exists under `.aiops/runtime/<ENV>/k8s-bootstrap/`
