# DuploCloud Conventions and Patterns (Brook AI)

This document captures the actual conventions discovered during the GitHub Actions migration from TeamCity.

## Tenant Naming

Brook AI uses environment-based tenant naming:

- **Dev**: `dev01-brook` (devops tenant for testing)
- **Staging**: `staging01-brook` (future)
- **Production**: `prod01-brook` (future)

Pattern: `{env##}-{company}` where `##` is a sequence number (allows multiple dev environments)

## ECR Repository Naming

ECR repositories use simple service names without prefixes:
- `billy` (monorepo with frontend/backend/migrations)
- `care-bot`
- `ETL-service`
- `py-data`
- `report-service`
- `chat-storage`
- `brook-backend`

**Important**: ECR repo name must match the service name deployed in DuploCloud for proper image updates.

### ECR Repository Requirements

All ECR repositories must have these tags for DuploCloud visibility:
- `duplo-project=devops`
- `TENANT_NAME=devops`

Configuration:
- `imageTagMutability`: MUTABLE (allows tag reuse)
- `encryptionType`: KMS (using tenant's KMS key)

## Service Naming in DuploCloud

Service names in DuploCloud UI/API match repository names:
- `billy-frontend`, `billy-backend`, `billy-migrations` (from monorepo)
- `care-bot`, `ETL-service`, `py-data`, etc.

For monorepos with multiple services:
- Use service selector in workflow: `service=all` or `service=frontend`
- Build multiple images from one repo
- Each image pushed to separate ECR repo

## Environment Variables

Standard environment variables across all workflows:

### GitHub Secrets (Required)
- `DUPLO_TOKEN` - DuploCloud API token with admin permissions
- Format: Long-lived token from DuploCloud portal → Admin → API Tokens

### GitHub Variables (Required)
- `DUPLO_HOST` - DuploCloud portal URL
  - Example: `https://duplo.cloud.brook.ai`
  - Set at organization or repo level

### Workflow Environment Variables
- `DUPLO_TENANT` - Target tenant for DuploCloud CI Setup
  - Usually `devops` for development
  - Set in workflow env block: `env: DUPLO_TENANT: devops`

### Generated Environment Variables
- `CODEARTIFACT_AUTH_TOKEN` - Generated in workflow for services with private dependencies
  - Generated via: `aws codeartifact get-authorization-token`
  - Passed to gradle/maven as environment variable
  - Valid for 12 hours

## Secrets Management

Brook AI uses a hybrid approach:

### GitHub Secrets
- `DUPLO_TOKEN` - DuploCloud API access
- Application secrets managed through DuploCloud portal (not in GitHub)

### AWS Secrets Manager
- Database credentials stored in AWS Secrets Manager
- Accessed by services via DuploCloud-managed IAM roles
- No hardcoded credentials in code or workflows

### CodeArtifact Authentication
- No permanent credentials
- JIT tokens generated per workflow run
- Token passed as environment variable to build tools

## Common Patterns

### Image Tag Strategy

Brook AI uses dual tagging for traceability and convenience:
```yaml
tags: |
  ${{ github.sha }}
  ${{ github.ref_name }}-latest
```

- Git SHA: Immutable, exact version tracking
- Branch name + latest: Convenience for development (`duplo-latest`, `main-latest`)

### Branch to Environment Mapping

- **duplo branch** → `dev01-brook` tenant (build and deploy testing)
- **main branch** → `dev01-brook` tenant (stable development)
- **release branches** → `staging01-brook` tenant (future)
- **tags** → `prod01-brook` tenant (future, image promotion only)

### Workflow Dispatch Inputs

Standard inputs across all workflows:

**Single-service repos**:
```yaml
inputs:
  environment:
    required: true
    type: string
    description: 'DuploCloud environment (e.g., dev01-brook)'
```

**Multi-service repos (monorepos)**:
```yaml
inputs:
  environment:
    required: true
    type: string
  service:
    required: true
    type: choice
    options:
      - all
      - frontend
      - backend
      - migrations
```

### Approval Gates

Current state (development):
- Manual workflow_dispatch triggers for all environments
- No automatic deployments on push (commented out in workflows)
- Developer-triggered builds and deployments

Future state (production):
- Dev: Auto-deploy on push to main
- Staging: Manual approval + image promotion
- Prod: Manual approval + image promotion from staging

## Infrastructure Notes

### AWS Account
- Account ID: `173008660334`
- Region: `us-east-1` (primary)
- EKS Cluster: Managed by DuploCloud in `devops` tenant

### CodeArtifact
- Domain: `brook`
- Domain owner: `173008660334`
- Repository: `brook-maven` (Maven artifacts)
- URL pattern: `https://brook-173008660334.d.codeartifact.us-east-1.amazonaws.com/maven/brook-maven/`

### ECR
- Registry: `173008660334.dkr.ecr.us-east-1.amazonaws.com`
- Authentication: Handled by DuploCloud CI Setup action
- Naming: `{service-name}` (no tenant prefix in repo name)

### Legacy Infrastructure (Deprecated)

**DO NOT USE**:
- S3 Maven repositories (`s3://brook-maven-repo/releases`)
  - Replaced by CodeArtifact
  - Old URLs: `s3://brook-maven-repo/releases`, `s3://duploservices-devops-brook-maven-repo-173008660334/releases`
- TeamCity build artifacts
  - Migrated to GitHub Actions
- Self-hosted runners
  - Using GitHub-hosted `ubuntu-latest` runners

## DuploCloud Action Versions

### Current Stable Version
- `Brookai/actions@v0.0.14` - Org policy compliant (no external actions)
- Provides: DuploCloud CI Setup, AWS credentials via JIT, ECR authentication

### Version History
- `v0.0.13` - Had external action dependencies (blocked by org policy)
- `v0.0.14` - Fixed org policy compliance, uses built-in AWS CLI

### Updating Action Versions

When updating action versions across repos:
```bash
# Update all workflows in a repo
find .github/workflows -name "*.yaml" -exec sed -i '' 's|Brookai/actions@v0.0.13|Brookai/actions@v0.0.14|g' {} +
```

## Dockerfile Location Patterns

Standard locations:
- Root: `Dockerfile` (simple single-service repos)
- Docker directory: `docker/Dockerfile` (some services like ETL-service)
- Service subdirectory: `frontend/Dockerfile`, `backend/Dockerfile` (monorepos)

## Build Context Patterns

Standard build contexts:
- Root: `.` (most services)
- Subdirectory: `./frontend`, `./backend` (monorepos)

## Common Service Dependencies

Services with **private dependencies** (require CodeArtifact):
- `report-service` (depends on `device-bus-data`)
- `brook-backend` (depends on internal libraries)

Services with **only public dependencies**:
- `billy-frontend` (Vite, React from npm)
- `ETL-service` (standard Java libraries)
- `py-data` (public Python packages)
- `chat-storage` (public Java libraries)
- `care-bot` (public dependencies)

## Naming Conventions

### Workflow Names (GitHub UI)
Use `[Duplo]` prefix to distinguish from other workflows:
- `[Duplo] Build + Deploy Pipeline`
- `[Duplo] Build + Push Image`
- `[Duplo] Deploy Image`

**Important**: Quote entire name string to avoid YAML syntax errors:
```yaml
name: "[Duplo] Build + Push Image"  # Correct
```

### Commit Messages
- Keep under 10 words
- No AI/LLM references
- Focus on the change
- Examples from migration:
  - "Fix JAR build in Dockerfile"
  - "Update action ref to v0.0.14"
  - "Add CodeArtifact integration"
  - "Convert to multi-stage Dockerfile"

### Branch Names
- `duplo` - Integration branch for DuploCloud pipeline work
- `main` - Default stable branch
- `dev`, `master` - Legacy default branches (some repos)
- Feature branches: Short, descriptive (e.g., `fix-build`, `update-dockerfile`)

## Service-Specific Notes

### billy (Monorepo)
- Three services: frontend (Vite), backend (Java), migrations (SQL)
- Requires service selector in workflows
- Frontend: Multi-stage Node build
- Backend: Standard Java service

### report-service
- **Requires CodeArtifact** for `device-bus-data` library
- Build pattern: Workflow build + single-stage Dockerfile
- Uses Gradle with Kotlin DSL (build.gradle.kts)

### ETL-service
- Dockerfile location: `docker/Dockerfile` (non-standard)
- Multi-stage Dockerfile pattern
- Standard Java dependencies only

### care-bot
- Monorepo with service selector
- Similar to billy structure

## Migration Patterns Discovered

### From TeamCity
- TeamCity built artifacts separately, pushed to S3
- Dockerfiles expected pre-built JARs
- Migration: Convert to multi-stage builds OR workflow builds

### From S3 Maven to CodeArtifact
- Old: `s3://brook-maven-repo/releases`
- New: `https://brook-173008660334.d.codeartifact.us-east-1.amazonaws.com/maven/brook-maven/`
- Authentication: JIT tokens instead of AWS IAM roles

### Dockerfile Migrations
- Single-stage expecting pre-built → Multi-stage builder pattern
- Multi-stage with S3 auth → Workflow build + single-stage
- Frontend expecting pre-built dist → Multi-stage with npm ci + build

## Cost Optimization Patterns

### Reusable Scripts
- Monitoring script: ~10k tokens saved per iteration
- Trigger script: ~5k tokens saved per batch operation
- Error extraction: ~8k tokens saved per analysis
- **Total**: 30-40% reduction on repetitive pipeline work

### Template Usage
- Pre-built workflow templates for common patterns
- Copy and customize instead of generating from scratch
- Validate locally before committing

### Parallel Operations
- Trigger multiple workflows simultaneously
- Monitor builds in parallel
- Batch error analysis across repos
