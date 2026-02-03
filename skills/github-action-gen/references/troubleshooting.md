# Troubleshooting Guide for DuploCloud GitHub Actions

Common errors encountered during GitHub Actions pipeline development and their solutions, based on production migration experience.

## Build Failures

### Error: JAR/Artifact Not Found in Docker Build

**Symptom**:
```
ERROR: failed to build: failed to solve: failed to compute cache key: failed to calculate checksum: "/build/libs/etl-service.jar": not found
```

**Cause**: Dockerfile expects pre-built artifact that doesn't exist

**Common scenarios**:
1. Single-stage Dockerfile without workflow build step
2. Multi-stage Dockerfile build failed silently
3. Wrong artifact path in COPY command

**Solution 1**: Convert to multi-stage Dockerfile (if no private dependencies)
```dockerfile
FROM gradle:7-jdk17 AS builder
WORKDIR /build
COPY . .
RUN ./gradlew build --no-daemon

FROM eclipse-temurin:17-jre
COPY --from=builder /build/build/libs/*.jar app.jar
```

**Solution 2**: Add workflow build step (if private dependencies exist)
```yaml
- name: Build JAR with Gradle
  run: |
    chmod +x gradlew
    ./gradlew bootJar --no-daemon

- name: Build Docker Image
  # Dockerfile: COPY build/libs/*.jar app.jar
```

### Error: Permission Denied (gradlew)

**Symptom**:
```
./gradlew: Permission denied
##[error]Process completed with exit code 126
```

**Cause**: gradlew doesn't have execute permissions in fresh git checkout

**Solution**: Add chmod before running gradle
```yaml
- name: Build JAR
  run: |
    chmod +x gradlew    # ← Add this
    ./gradlew bootJar
```

**Permanent fix**: Commit with execute permissions
```bash
git update-index --chmod=+x gradlew
git commit -m "Add execute permissions to gradlew"
```

### Error: Access Denied (S3 Maven Repository)

**Symptom**:
```
Access Denied (Service: Amazon S3; Status Code: 403; Error Code: AccessDenied)
Could not resolve: com.brook:device-bus-data:1.0.0
```

**Cause**: Trying to access legacy S3 Maven repo or CodeArtifact without credentials

**Solution**: Switch to CodeArtifact with token authentication

**build.gradle.kts**:
```kotlin
repositories {
    mavenCentral()
    maven {
        // OLD: s3://brook-maven-repo/releases
        // NEW: CodeArtifact URL
        url = uri("https://brook-173008660334.d.codeartifact.us-east-1.amazonaws.com/maven/brook-maven/")
        credentials {
            username = "aws"
            password = System.getenv("CODEARTIFACT_AUTH_TOKEN") ?: ""
        }
    }
}
```

**Workflow**:
```yaml
- name: Build with CodeArtifact
  run: |
    export CODEARTIFACT_AUTH_TOKEN=$(aws codeartifact get-authorization-token \
      --domain brook \
      --domain-owner 173008660334 \
      --region us-east-1 \
      --query authorizationToken \
      --output text)
    ./gradlew bootJar
```

See [codeartifact.md](codeartifact.md) for complete guide.

### Error: Frontend dist Folder Not Found

**Symptom**:
```
ERROR: failed to calculate checksum: "/dist": not found
```

**Cause**: Single-stage Dockerfile expects pre-built dist folder

**Solution**: Convert to multi-stage frontend build
```dockerfile
# Builder stage
FROM node:22-alpine AS builder
WORKDIR /build
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build    # ← Creates dist folder

# Runtime stage
FROM nginx:stable-alpine
COPY --from=builder /build/dist /usr/share/nginx/html
```

## Workflow Syntax Errors

### Error: Workflow Not Found / Not Dispatchable

**Symptom**:
```
gh workflow run duplo-build.yaml --ref duplo
Error: could not find any workflows named duplo-build.yaml
```

**Cause**: Workflow file has YAML syntax error preventing GitHub from recognizing it

**Common issue**: Incorrect quoting of workflow name
```yaml
# WRONG
name: "[Duplo]" Build + Push Image

# CORRECT
name: "[Duplo] Build + Push Image"
```

**Solution**: Fix YAML syntax, quote entire name string
```bash
# Check for syntax errors
cat .github/workflows/duplo-build.yaml | yq eval '.'

# Fix quotes in all workflows
sed -i '' 's/^name: "\[Duplo\]" \(.*\)/name: "[Duplo] \1"/' .github/workflows/*.yaml
```

### Error: Required Input Not Provided

**Symptom**:
```
{
  "message": "Required input 'environment' not provided",
  "status": "422"
}
```

**Cause**: Workflow_dispatch called without required inputs

**Solution**: Provide all required inputs
```bash
# Check workflow inputs
cat .github/workflows/duplo-build.yaml | grep -A 10 "inputs:"

# Provide inputs when triggering
gh workflow run duplo-build.yaml \
  --ref duplo \
  --field environment=dev01-brook \
  --field service=all  # If monorepo
```

### Error: Workflow Not on Default Branch

**Symptom**:
```
Error: workflow_dispatch event not found for workflow duplo-build.yaml on branch main
```

**Cause**: Workflow doesn't exist on default branch (GitHub requirement for discovery)

**Solution**: Either merge to default branch or push workflow file to default branch
```bash
# Option 1: Merge feature branch to main
gh pr create --base main --head duplo --title "Add DuploCloud workflows"

# Option 2: Cherry-pick workflow files to main
git checkout main
git checkout duplo -- .github/workflows/
git commit -m "Add workflow files for discovery"
git push

# Then trigger from feature branch
gh workflow run duplo-build.yaml --ref duplo
```

## Action Errors

### Error: Action Not Allowed by Organization Policy

**Symptom**:
```
##[error]Action 'unfor2019/install-aws-cli-action@v1' is not allowed by organization policy
All actions must be from Brookai, GitHub, or verified Marketplace
```

**Cause**: GitHub organization policy blocks external actions

**Solution 1**: Use built-in AWS CLI (recommended)
```yaml
# WRONG
- name: Install AWS CLI
  uses: unfor2019/install-aws-cli-action@v1

# RIGHT
# AWS CLI is already installed on ubuntu-latest runners
- name: DuploCloud CI Setup
  uses: Brookai/actions@v0.0.14
# AWS CLI now available
```

**Solution 2**: Fork action to organization
```bash
# Fork unfor2019/install-aws-cli-action to Brookai org
# Then update workflows
uses: Brookai/install-aws-cli-action@v1
```

### Error: DuploCloud Action Version Not Found

**Symptom**:
```
Unable to resolve action Brookai/actions@v0.0.15
```

**Cause**: Action version doesn't exist

**Solution**: Use latest stable version
```yaml
# Check latest version
gh release list --repo Brookai/actions

# Use stable version
- name: DuploCloud CI Setup
  uses: Brookai/actions@v0.0.14  # Current stable
```

## Deployment Errors (Expected During Iteration)

### Error: Service Not Found in DuploCloud

**Symptom**:
```
duploctl service update-image my-service
Error: Service 'my-service' not found in tenant 'dev01-brook'
##[error]Process completed with exit code 144
```

**Cause**: Service doesn't exist in DuploCloud yet

**This is EXPECTED during build iteration phase**

**Solution**: Only trigger `duplo-deploy.yaml` AFTER creating services in DuploCloud
```bash
# During iteration: Only test builds
gh workflow run duplo-build.yaml --ref duplo --field environment=dev01

# After services exist: Test deployment
gh workflow run duplo-deploy.yaml --ref duplo --field environment=dev01
```

### Error: Image Not Found in ECR

**Symptom**:
```
Error: Image '173008660334.dkr.ecr.us-east-1.amazonaws.com/my-service:abc123' not found
```

**Cause**: Deployment triggered before build completed or build failed

**Solution**: Ensure build succeeds first
```bash
# 1. Trigger build
gh workflow run duplo-build.yaml --ref duplo

# 2. Wait for completion
gh run list --workflow duplo-build.yaml --limit 1

# 3. Verify build succeeded
gh run view <run-id> --log

# 4. Then deploy
gh workflow run duplo-deploy.yaml --ref duplo
```

## Token and Authentication Errors

### Error: Token Not Persisting Between Bash Calls

**Symptom**: Works in one script, fails in another
```bash
# Call 1
export GITHUB_TOKEN=xxx

# Call 2 (different Bash tool invocation)
gh api ...  # Error: authentication required
```

**Cause**: Environment variables don't persist across separate Bash tool calls in automation tools

**Solution**: Use one of these patterns:

**Option 1**: Chain commands with &&
```bash
export GITHUB_TOKEN=xxx && gh workflow run ... && gh run list ...
```

**Option 2**: Embed token in script
```bash
#!/bin/bash
export GITHUB_TOKEN="ghp_xxxx"
gh workflow run ...
```

**Option 3**: Use heredoc pattern
```yaml
- name: Trigger and Monitor
  run: |
    export GITHUB_TOKEN="${{ secrets.GITHUB_TOKEN }}"
    gh workflow run duplo-build.yaml
    sleep 3
    gh run list --limit 1
```

### Error: DUPLO_TOKEN Not Found

**Symptom**:
```
Error: DUPLO_TOKEN environment variable not set
```

**Cause**: GitHub secret not configured or not passed to workflow

**Solution**: Configure GitHub secret and reference in workflow
```yaml
# Workflow
- name: DuploCloud CI Setup
  uses: Brookai/actions@v0.0.14
  env:
    DUPLO_TENANT: devops
    DUPLO_TOKEN: ${{ secrets.DUPLO_TOKEN }}  # ← Add if not automatic
```

Configure secret:
```bash
# Using gh CLI
gh secret set DUPLO_TOKEN --body "xxx" --repo Brookai/my-repo

# Or via GitHub UI:
# Repo → Settings → Secrets and variables → Actions → New repository secret
```

## Docker Build Errors

### Error: Docker BuildKit Parse Error

**Symptom**:
```
ERROR: failed to solve: failed to read dockerfile: open Dockerfile: no such file or directory
```

**Cause**: Dockerfile not in expected location or wrong build context

**Solution**: Verify dockerfile path and context
```yaml
- name: Build Docker Image
  uses: Brookai/actions/build-image@v0.0.14
  with:
    dockerfile: docker/Dockerfile      # ← Check path
    context: .                         # ← Check context
```

For monorepos:
```yaml
- name: Build Frontend Image
  uses: Brookai/actions/build-image@v0.0.14
  with:
    dockerfile: frontend/Dockerfile
    context: ./frontend               # ← Context is frontend dir
```

### Error: COPY Failed (File Not Found)

**Symptom**:
```
COPY failed: file not found in build context or excluded by .dockerignore: stat build/libs/*.jar: not found
```

**Cause**: File doesn't exist in build context

**Solution**: Check if file exists and is in context
```bash
# Local test
docker build -f Dockerfile -t test .
# Error shows what's missing

# Verify file exists
ls build/libs/*.jar

# Check .dockerignore isn't excluding it
cat .dockerignore
```

## GitHub API Errors

### Error: 401 Bad Credentials

**Symptom**:
```
{
  "message": "Bad credentials",
  "documentation_url": "https://docs.github.com/rest"
}
```

**Cause**: GitHub token invalid, expired, or has insufficient permissions

**Solution**: Generate new token with correct scopes
```bash
# Required scopes for workflows:
# - repo (full control)
# - workflow (update workflows)

# Test token
gh auth status

# Login with new token
gh auth login

# Or set explicitly
export GITHUB_TOKEN=ghp_xxxx
```

### Error: 422 Validation Failed

**Symptom**:
```
{
  "message": "Validation Failed",
  "errors": [...],
  "status": "422"
}
```

**Common causes**:
1. PR already exists for branch
2. Invalid workflow inputs
3. Branch doesn't exist

**Solution**: Check error details
```bash
# Check for existing PRs
gh pr list --head duplo

# Verify branch exists
gh api repos/Brookai/my-repo/branches/duplo

# Check workflow inputs match definition
cat .github/workflows/duplo-build.yaml | grep -A 10 "inputs:"
```

## Performance and Rate Limiting

### Error: API Rate Limit Exceeded

**Symptom**:
```
{
  "message": "API rate limit exceeded",
  "documentation_url": "https://docs.github.com/rest/overview/resources-in-the-rest-api#rate-limiting"
}
```

**Limits**:
- Unauthenticated: 60 requests/hour
- Authenticated: 5000 requests/hour

**Solution**: Use authenticated requests
```bash
# Set GitHub token
export GITHUB_TOKEN=xxx

# Or use gh CLI (auto-authenticates)
gh api repos/Brookai/my-repo
```

### Error: Workflow Timeout

**Symptom**:
```
##[error]The operation was canceled.
```

**Cause**: Workflow exceeded time limit (default: 6 hours for GitHub-hosted runners)

**Solution**: Optimize build or increase timeout
```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 60  # Default: 360 (6 hours)
```

## Debugging Techniques

### Enable Debug Logging

Set repository secrets:
```
ACTIONS_RUNNER_DEBUG=true
ACTIONS_STEP_DEBUG=true
```

Or in workflow:
```yaml
- name: Build with Debug
  run: ./gradlew bootJar --info --stacktrace
```

### Check Job Logs

```bash
# View latest run logs
gh run view $(gh run list --workflow duplo-build.yaml --limit 1 --json databaseId --jq '.[0].databaseId')

# View failed job logs only
gh run view <run-id> --log-failed

# Download all logs
gh run download <run-id>
```

### Test Workflow Locally (act)

```bash
# Install act (local GitHub Actions runner)
brew install act

# Test workflow
act workflow_dispatch -W .github/workflows/duplo-build.yaml

# With secrets
act --secret-file .env workflow_dispatch
```

### Validate Workflow YAML

```bash
# Using actionlint
brew install actionlint
actionlint .github/workflows/duplo-build.yaml

# Using yq
cat .github/workflows/duplo-build.yaml | yq eval '.'
```

## Common Gotchas

### Gotcha 1: Workflow Discovery Requires Default Branch

Workflows MUST exist on default branch for GitHub to "discover" them, but can run from any branch:

```bash
# Push workflow to main (for discovery)
git checkout main
git add .github/workflows/duplo-build.yaml
git commit -m "Add workflow"
git push

# But trigger from feature branch
gh workflow run duplo-build.yaml --ref duplo
```

### Gotcha 2: Sleep After Workflow Trigger

Run ID not immediately available after triggering:

```bash
# WRONG (run ID likely empty)
gh workflow run duplo-build.yaml --ref duplo
run_id=$(gh run list --limit 1 --json databaseId --jq '.[0].databaseId')

# RIGHT (add delay)
gh workflow run duplo-build.yaml --ref duplo
sleep 3  # ← Add delay
run_id=$(gh run list --limit 1 --json databaseId --jq '.[0].databaseId')
```

### Gotcha 3: Workflow Status "completed" != "success"

```bash
# Wrong assumption
if [ "$status" == "completed" ]; then
  # This runs even if build FAILED!
fi

# Correct check
status=$(gh run view $run_id --json status,conclusion --jq '.status + ":" + .conclusion')
if [ "$status" == "completed:success" ]; then
  echo "Build succeeded"
fi
```

### Gotcha 4: Base64 Decode Gotcha

```bash
# WRONG (garbled output)
echo "$content" | base64 -d

# RIGHT (use --decode)
echo "$content" | base64 --decode

# Or use Python
python3 -c "import base64, sys; print(base64.b64decode(sys.stdin.read()).decode())"
```

## Getting Help

### Useful Commands

```bash
# Check workflow syntax
gh workflow view duplo-build.yaml

# List recent runs
gh run list --workflow duplo-build.yaml --limit 10

# Re-run failed jobs
gh run rerun <run-id> --failed

# Cancel running workflow
gh run cancel <run-id>

# Watch run in real-time
gh run watch <run-id>
```

### Log Inspection

```bash
# Extract errors from logs
gh run view <run-id> --log-failed | grep -i "error"

# Get specific job logs
gh run view <run-id> --job <job-id> --log
```

### Automation Scripts

See `scripts/` directory for reusable troubleshooting scripts:
- `monitor-builds.sh` - Monitor and extract errors automatically
- `extract-errors.sh` - Parse and categorize errors from failed runs

## Resources

- Session Log: `/Users/robert/workspaces/brook-ai/logs/duplo-pipeline-run-2026-02-03.log`
- Automation Workflow: `/Users/robert/workspaces/brook-ai/logs/duplo-pipeline-automation-workflow.md`
- CodeArtifact Guide: [codeartifact.md](codeartifact.md)
- Dockerfile Patterns: [dockerfile-patterns.md](dockerfile-patterns.md)
- GitHub Actions Docs: https://docs.github.com/en/actions
- DuploCloud Actions: https://github.com/duplocloud/actions
