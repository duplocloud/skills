---
name: github-action-gen
description: Expert in creating GitHub Actions CI/CD workflows for DuploCloud deployments. Generates modular pipeline files (build, deploy, orchestration), handles multi-stage vs workflow builds, CodeArtifact integration, and automates pipeline testing. Use for GHA pipeline creation, troubleshooting build failures, or automating workflow operations.
---

# DuploCloud GitHub Actions Pipeline Generator

Generate and manage GitHub Actions workflows for building, pushing, and deploying container images to DuploCloud-managed infrastructure with battle-tested patterns from production migrations.

## When to Use This Skill

- User wants to create CI/CD pipelines for services running in DuploCloud
- User needs to troubleshoot or fix existing GitHub Actions build failures
- User wants to automate workflow triggering and monitoring across multiple repos
- User needs to migrate from TeamCity/Jenkins to GitHub Actions
- User has service mapping, infrastructure docs, or CI/CD analysis available

## Core Workflow Structure

Generated workflows follow a modular three-file pattern placed in `.github/workflows/`:

```
.github/workflows/
├── duplo-pipeline.yaml   # Orchestrates build → deploy (full CI/CD)
├── duplo-build.yaml      # Builds and pushes Docker image to registry
└── duplo-deploy.yaml     # Deploys image to DuploCloud service
```

**Critical: During iteration/testing, ONLY trigger `duplo-build.yaml`**
- Deploy will fail until DuploCloud services exist
- Focus on getting builds working first
- Full pipeline comes later after service provisioning

## Dockerfile Build Patterns (Battle-Tested)

### Pattern 1: Multi-Stage Dockerfile (Simple Services)

**Use when**: Service has NO private registry dependencies (no CodeArtifact, no private npm)

**Example**: ETL-service, billy-frontend, most Python services

**Structure**:
```dockerfile
# Builder stage
FROM gradle:7-jdk17 AS builder
WORKDIR /build
COPY . .
RUN ./gradlew build --no-daemon

# Runtime stage
FROM eclipse-temurin:17-jre
COPY --from=builder /build/build/libs/*.jar app.jar
CMD ["java", "-jar", "app.jar"]
```

**Workflow**: Simple, no pre-build steps needed
```yaml
- name: Build and Push Docker Image
  uses: Brookai/actions/build-image@v0.0.14
  # Docker build handles everything
```

### Pattern 2: Workflow Build + Single-Stage Dockerfile (Private Dependencies)

**Use when**: Service needs CodeArtifact, private Maven repos, or private npm registries

**Example**: report-service, brook-backend (anything with device-bus-data or internal libraries)

**Why**: Docker builds can't access AWS credentials; build must happen in workflow where DuploCloud CI Setup provides credentials

**Workflow steps**:
```yaml
# 1. Setup language runtime
- name: Set up JDK 17
  uses: actions/setup-java@v4
  with:
    java-version: '17'
    distribution: 'temurin'

# 2. DuploCloud CI Setup (provides AWS credentials)
- name: DuploCloud CI Setup
  uses: Brookai/actions@v0.0.14
  env:
    DUPLO_TENANT: devops

# 3. Generate CodeArtifact token and build JAR
- name: Build JAR with Gradle
  run: |
    export CODEARTIFACT_AUTH_TOKEN=$(aws codeartifact get-authorization-token \
      --domain brook \
      --domain-owner 173008660334 \
      --region us-east-1 \
      --query authorizationToken \
      --output text)
    chmod +x gradlew
    ./gradlew bootJar

# 4. Docker build (copy pre-built artifact)
- name: Build and Push Docker Image
  # Dockerfile just copies build/libs/*.jar
```

**Dockerfile** (single-stage):
```dockerfile
FROM eclipse-temurin:17-jre
WORKDIR /app
# Copy pre-built JAR from workflow
COPY build/libs/*.jar app.jar
CMD ["java", "-jar", "app.jar"]
```

**build.gradle.kts**:
```kotlin
repositories {
    mavenCentral()
    maven {
        url = uri("https://brook-173008660334.d.codeartifact.us-east-1.amazonaws.com/maven/brook-maven/")
        credentials {
            username = "aws"
            password = System.getenv("CODEARTIFACT_AUTH_TOKEN") ?: ""
        }
    }
}
```

### Pattern 3: Multi-Stage Frontend Dockerfile

**Use when**: Frontend app with public npm dependencies only

**Example**: billy-frontend (Vite/React)

```dockerfile
# Builder stage
FROM node:22-alpine AS builder
WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# Runtime stage
FROM nginx:stable-alpine
COPY --from=builder /build/dist /usr/share/nginx/html
```

## Common Mistakes to Avoid

### 1. Using Legacy S3 Maven Repos
**Problem**: TeamCity used S3 for Maven artifacts, no longer accessible
**Solution**: Switch to AWS CodeArtifact (use Pattern 2 above)

### 2. Building JARs Inside Docker When Private Dependencies Needed
**Problem**: Multi-stage Dockerfile tries to run gradle inside Docker without AWS credentials
**Error**: `Access Denied (Service: Amazon S3; Status Code: 403)` or `401 Unauthorized` from CodeArtifact
**Solution**: Use Pattern 2 - build in workflow, copy into Docker

### 3. Forgetting chmod +x gradlew
**Problem**: Fresh git checkouts don't have execute permissions
**Error**: `./gradlew: Permission denied`
**Solution**: Always add `chmod +x gradlew` before running gradle in workflow

### 4. Triggering duplo-pipeline.yaml During Testing
**Problem**: Pipeline includes deploy stage which fails when services don't exist
**Impact**: False failures, wasted debugging time
**Solution**: Use `duplo-build.yaml` for iteration, full pipeline only after deployment works

### 5. Incomplete YAML Syntax Fixes
**Problem**: GitHub Actions requires proper quoting for special characters in workflow names
**Error**: Workflow not recognized by workflow_dispatch API
**Correct**:
```yaml
name: "[Duplo] Build + Push Image"  # ✓ Entire string quoted
```
**Wrong**:
```yaml
name: "[Duplo]" Build + Push Image  # ✗ Only [Duplo] quoted
```

### 6. Using External Actions Blocked by Org Policy
**Problem**: Actions like `unfor2019/install-aws-cli-action@v1` not allowed by GitHub org policy
**Error**: `Action is not allowed`
**Solution**: Use runner's built-in AWS CLI (already on ubuntu-latest) or fork action to org

## DuploCloud Actions Reference

Use org-approved versions from `Brookai/actions`:

```yaml
# Current stable version (org policy compliant)
- name: DuploCloud CI Setup
  uses: Brookai/actions@v0.0.14
  env:
    DUPLO_TENANT: devops
```

**What DuploCloud CI Setup provides**:
- AWS credentials via JIT (Just-In-Time) generation
- ECR authentication for docker push
- CodeArtifact access for maven/npm
- No need to manage cloud credentials directly

## Workflow Examples and Templates

See `assets/templates/` for:
- Single-service build workflow
- Multi-service (monorepo) build workflow
- Build-only workflow (for iteration)
- Full pipeline workflow (build + deploy)

See `assets/examples/` for:
- Real-world workflows from the 6-repo migration
- CodeArtifact integration examples
- Multi-stage Dockerfile examples

## Automation Scripts (Reusable)

For pipeline iteration and troubleshooting, see `scripts/` directory:

**monitor-builds.sh** - Monitor multiple GitHub Actions runs until completion
- Poll-and-wait with status tracking
- Automatic error extraction from failed runs
- Progress indicators and structured logging

**trigger-workflows.sh** - Trigger workflow_dispatch across multiple repos
- Conditional input handling (repo-specific vs generic)
- Run ID extraction after trigger
- Batch operation support

**extract-errors.sh** - Extract and classify errors from failed runs
- Pattern-based error categorization
- Structured error reporting
- Integration with monitoring scripts

## Reference Documentation

Detailed patterns and troubleshooting guides:

- **[conventions.md](references/conventions.md)** - DuploCloud naming, tenant structure, common patterns
- **[dockerfile-patterns.md](references/dockerfile-patterns.md)** - When to use multi-stage vs workflow builds
- **[codeartifact.md](references/codeartifact.md)** - AWS CodeArtifact integration guide
- **[automation-patterns.md](references/automation-patterns.md)** - Reusable patterns for workflow automation
- **[troubleshooting.md](references/troubleshooting.md)** - Common errors and fixes

## Branching and Pull Request Workflow

When adding or updating workflows:
1. Create a `duplo` branch from the repo's default branch
2. Add/update workflow files on `duplo`
3. Push changes and create PR from `duplo` to default branch
4. Use short, plain commit messages (no AI/LLM references)

**Critical**: GitHub Actions requires workflows to exist on the **default branch** to be discoverable by API, but you can trigger them to run FROM any branch using the `ref` parameter.

**Iteration pattern**:
```bash
# Make changes on duplo branch
git checkout duplo
# ... make fixes ...
git commit -m "Fix JAR build in workflow"
git push

# Trigger workflow from duplo branch (runs fixed version)
gh workflow run duplo-build.yaml --ref duplo --field environment=dev01
```

## Triggering and Monitoring Workflows

### Manual Triggering

```bash
# For repos with service selector (monorepos)
gh workflow run duplo-build.yaml \
  --repo Brookai/billy \
  --ref duplo \
  --field environment=dev01-brook \
  --field service=all

# For single-service repos
gh workflow run duplo-build.yaml \
  --repo Brookai/ETL-service \
  --ref duplo \
  --field environment=dev01-brook
```

### Monitoring Runs

```bash
# List recent runs
gh run list --repo Brookai/billy --workflow duplo-build.yaml --limit 5

# Watch run in real-time
gh run watch <run-id> --repo Brookai/billy

# View failed logs
gh run view <run-id> --repo Brookai/billy --log-failed
```

### Automated Monitoring

Use `scripts/monitor-builds.sh` for parallel monitoring across multiple repos.

## Decision Trees

### Which Dockerfile Pattern?

```
Does the service have private dependencies?
├── YES (CodeArtifact, private npm, internal libraries)
│   └── Use Pattern 2: Workflow Build + Single-Stage Dockerfile
│       - Build artifacts in workflow (where AWS credentials available)
│       - Single-stage Dockerfile just copies pre-built artifacts
│       - Example: report-service, brook-backend
│
└── NO (only public dependencies)
    ├── Is it a frontend app?
    │   └── YES → Use Pattern 3: Multi-Stage Frontend
    │       - Build stage: npm ci + npm run build
    │       - Runtime stage: nginx
    │       - Example: billy-frontend
    │
    └── Is it a backend service?
        └── YES → Use Pattern 1: Multi-Stage Backend
            - Build stage: gradle/maven build
            - Runtime stage: copy JAR
            - Example: ETL-service, py-data
```

### Which Workflow to Trigger?

```
What are you testing?
├── Just validating Docker builds?
│   └── Trigger: duplo-build.yaml
│       - Build only, no deploy
│       - Safe for iteration
│       - Example: All initial testing
│
├── Testing deployment?
│   └── Trigger: duplo-deploy.yaml
│       - Requires: Services exist in DuploCloud
│       - Requires: Image already in ECR
│       - Example: After builds work, services created
│
└── Full CI/CD pipeline?
    └── Trigger: duplo-pipeline.yaml
        - Orchestrates build → deploy
        - Only after both work independently
        - Example: Production setup
```

## Environment Setup

### Required GitHub Secrets
- `DUPLO_TOKEN` - DuploCloud API token with appropriate permissions

### Required GitHub Variables
- `DUPLO_HOST` - DuploCloud portal URL (e.g., `https://duplo.cloud.brook.ai`)

### Required GitHub Environments
Create environments matching tenant names:
- `dev01-brook`
- `staging01-brook`
- `prod01-brook`

### AWS Profile Configuration (Local Development)

For local testing and CLI access:

```ini
# ~/.aws/config or project config/aws
[profile brook-duplocloud]
region = us-east-1
output = json
# Uses duploctl for JIT AWS credentials
credential_process = sh -c "duploctl jit aws --admin --host https://duplo.cloud.brook.ai --interactive -o json | jq '{Version: .Version, AccessKeyId: .AccessKeyId, SecretAccessKey: .SecretAccessKey, SessionToken: .SessionToken, Expiration: .Expiration}'"
```

## Lessons Learned from Production Migration

### Session Highlights (6-Repo Migration)
- **Iterations**: ~12 across 6 repos
- **Time**: ~3 hours of active work
- **Outcome**: All 6 repos building successfully
- **Key Insight**: CodeArtifact pattern was critical for services with private dependencies

### Error Patterns Documented
1. Permission denied (gradlew files)
2. File not found (pre-built artifacts expected)
3. Access denied (S3 Maven repos, CodeArtifact auth failures)
4. YAML syntax errors (unquoted special characters in names)
5. Build failures (dependency resolution, gradle version mismatches)

### Critical Discoveries
- **Token Management**: `export GITHUB_TOKEN` doesn't persist across Bash tool calls in automation
- **Array Handling**: Use `declare -a ARRAY=("item1" "item2")` with IFS parsing for reliability
- **GitHub CLI Best Practices**: Always add `sleep 2-3` after triggering workflows before fetching run IDs
- **Branch Strategy**: Workflows must exist on default branch for discovery but can run FROM any branch via `--ref`

### Cost Optimization
With reusable templates and scripts:
- **Monitoring**: Save ~10k tokens per iteration
- **Triggering**: Save ~5k tokens per batch
- **Error Analysis**: Save ~8k tokens per analysis
- **Total Savings**: 30-40% token reduction on similar work

## Safety and Security

### Credential Management
- Never hardcode tokens, passwords, or credentials in workflows
- Use GitHub secrets for `DUPLO_TOKEN`
- Use environment variables for `DUPLO_HOST`
- Let DuploCloud CI Setup handle AWS credential generation

### Commit Message Guidelines
- Keep under 10 words
- No AI/LLM references
- Focus on the what, not the why
- Examples:
  - "Fix JAR build in Dockerfile"
  - "Update action ref to v0.0.14"
  - "Add CodeArtifact integration"

### Branch Protection
- Never commit directly to main
- All changes via pull requests from `duplo` branch
- Keep main stable for production

## Getting Started

1. **Identify build pattern** - Does service have private dependencies?
2. **Choose Dockerfile approach** - Multi-stage or workflow build?
3. **Generate workflows** - Use templates from `assets/templates/`
4. **Test build only** - Trigger `duplo-build.yaml` first
5. **Iterate on failures** - Use troubleshooting guide and automation scripts
6. **Add deployment** - After services exist in DuploCloud
7. **Enable full pipeline** - Once build and deploy work independently

## Resources

- **Automation Workflow Guide**: `/Users/robert/workspaces/brook-ai/logs/duplo-pipeline-automation-workflow.md`
- **Session Log**: `/Users/robert/workspaces/brook-ai/logs/duplo-pipeline-run-2026-02-03.log`
- **Reusable Scripts Inventory**: `/Users/robert/workspaces/brook-ai/tmp/REUSABLE_SCRIPTS_INVENTORY.md`
- **Cleanup Report**: `/Users/robert/workspaces/brook-ai/tmp/CLEANUP_REPORT.md`
- **DuploCloud Actions**: https://github.com/duplocloud/actions (reference, use forked `Brookai/actions`)
- **Terraform Registry**: https://registry.terraform.io/modules/duplocloud/components/duplocloud/latest
