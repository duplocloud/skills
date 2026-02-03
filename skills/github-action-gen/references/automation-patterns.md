# Automation Patterns for GitHub Actions Workflows

Reusable patterns for automating workflow operations, monitoring, and error analysis based on production pipeline migration experience.

## Overview

During the migration of 6 repositories from TeamCity to GitHub Actions, several automation patterns emerged that significantly improved efficiency and reduced manual work. This guide documents those patterns with working examples.

## Core Automation Patterns

### Pattern A: Parallel Workflow Monitoring

**Use case**: Monitor multiple GitHub Actions runs simultaneously until all complete

**Benefits**:
- Track 6+ builds in parallel
- Automatic error extraction from failed runs
- Progress indicators and completion tracking
- Structured logging for post-mortem analysis

**Implementation**: See [scripts/monitor-builds.sh](../scripts/monitor-builds.sh.template)

**Key components**:
```bash
# Array-based tracking
declare -a RUNS=(
  "billy:21645427485"
  "ETL-service:21645432102"
  "report-service:21645436716"
  # ... more repos
)

# Poll-and-wait loop
while [ $completed_count -lt $total_count ]; do
  for entry in "${RUNS[@]}"; do
    IFS=':' read -r repo run_id <<< "$entry"

    # Check status via GitHub API
    status=$(gh run view $run_id --repo Brookai/$repo \
      --json status,conclusion \
      --jq '.status + ":" + (.conclusion // "running")')

    IFS=':' read -r run_status conclusion <<< "$status"

    if [ "$run_status" == "completed" ]; then
      ((completed_count++))
      if [ "$conclusion" == "success" ]; then
        echo "✓ $repo: SUCCESS"
      else
        echo "✗ $repo: FAILED ($conclusion)"
      fi
    else
      echo "⋯ $repo: IN PROGRESS"
    fi
  done

  sleep 30  # Poll every 30 seconds
done
```

**Usage**:
```bash
# Configure runs to monitor
declare -a RUNS=(
  "my-repo1:12345678"
  "my-repo2:12345679"
)

# Start monitoring
./scripts/monitor-builds.sh
```

**Output**:
```
=== Monitoring Build Status ===

⋯ my-repo1: IN PROGRESS
⋯ my-repo2: IN PROGRESS

Progress: 0/2 completed

✓ my-repo1: SUCCESS
⋯ my-repo2: IN PROGRESS

Progress: 1/2 completed

✓ my-repo1: SUCCESS
✓ my-repo2: SUCCESS

Progress: 2/2 completed

=== All builds completed! ===
```

---

### Pattern B: Batch Workflow Triggering

**Use case**: Trigger workflow_dispatch across multiple repositories with varying inputs

**Benefits**:
- Trigger 6 builds simultaneously
- Conditional input handling (repo-specific vs generic)
- Run ID extraction for monitoring
- Error handling and structured logging

**Implementation**: See [scripts/trigger-workflows.sh](../scripts/trigger-workflows.sh.template)

**Key components**:
```bash
# Repos with service selector (monorepos)
for repo in billy care-bot; do
  gh workflow run duplo-build.yaml \
    --repo Brookai/$repo \
    --ref duplo \
    --field environment=dev01-brook \
    --field service=all

  sleep 3  # Wait for run ID to be available

  run_id=$(gh run list \
    --repo Brookai/$repo \
    --workflow=duplo-build.yaml \
    --limit 1 \
    --json databaseId \
    --jq '.[0].databaseId')

  echo "$repo triggered: run_id=$run_id"
done

# Single-service repos (no service selector)
for repo in ETL-service py-data report-service chat-storage; do
  gh workflow run duplo-build.yaml \
    --repo Brookai/$repo \
    --ref duplo \
    --field environment=dev01-brook

  sleep 3
  run_id=$(gh run list --repo Brookai/$repo --workflow=duplo-build.yaml --limit 1 --json databaseId --jq '.[0].databaseId')

  echo "$repo triggered: run_id=$run_id"
done
```

**Usage**:
```bash
# Trigger all builds
./scripts/trigger-workflows.sh

# Output:
# billy triggered: run_id=21645427485
# care-bot triggered: run_id=21645429729
# ETL-service triggered: run_id=21645432102
# ...
```

---

### Pattern C: Error Extraction & Classification

**Use case**: Extract and categorize errors from failed GitHub Actions runs

**Benefits**:
- Automated error pattern detection
- Categorization (JAR_NOT_FOUND, FILE_NOT_FOUND, BUILD_ERROR, etc.)
- Structured error reporting
- Integration with monitoring scripts

**Implementation**: See [scripts/extract-errors.sh](../scripts/extract-errors.sh.template)

**Key components**:
```bash
for entry in "${RUNS[@]}"; do
  IFS=':' read -r repo run_id <<< "$entry"

  # Get failed job logs
  error_logs=$(gh run view $run_id --repo Brookai/$repo --log-failed 2>&1 | \
    grep -B 5 "##\[error\]" | tail -10)

  # Classify error type
  if echo "$error_logs" | grep -q "not found"; then
    error_type="JAR_NOT_FOUND"
    error_msg=$(echo "$error_logs" | grep "not found" | head -1)
  elif echo "$error_logs" | grep -q "No such file"; then
    error_type="FILE_NOT_FOUND"
    error_msg=$(echo "$error_logs" | grep "No such file" | head -1)
  elif echo "$error_logs" | grep -q "Access Denied"; then
    error_type="ACCESS_DENIED"
    error_msg=$(echo "$error_logs" | grep "Access Denied" | head -1)
  elif echo "$error_logs" | grep -q "Permission denied"; then
    error_type="PERMISSION_DENIED"
    error_msg=$(echo "$error_logs" | grep "Permission denied" | head -1)
  else
    error_type="UNKNOWN"
    error_msg="$error_logs"
  fi

  echo "[$repo] $error_type: $error_msg"
done
```

**Error categories**:
- `JAR_NOT_FOUND` - Pre-built JAR expected but missing
- `FILE_NOT_FOUND` - Generic file not found errors
- `ACCESS_DENIED` - S3, CodeArtifact, ECR access issues
- `PERMISSION_DENIED` - gradlew, script permissions
- `YAML_SYNTAX` - Workflow syntax errors
- `BUILD_ERROR` - Gradle/Maven/npm build failures
- `UNKNOWN` - Uncategorized errors

---

### Pattern D: Workflow Dispatch with Input Validation

**Use case**: Trigger workflows with validation and error handling

**Benefits**:
- Validate required inputs before triggering
- Handle different workflow input patterns
- Error detection and reporting

**Implementation**:
```bash
#!/bin/bash

trigger_workflow() {
  local repo=$1
  local workflow=$2
  local environment=$3
  local service=$4  # Optional

  # Validate inputs
  if [ -z "$repo" ] || [ -z "$workflow" ] || [ -z "$environment" ]; then
    echo "ERROR: Missing required parameters"
    echo "Usage: trigger_workflow <repo> <workflow> <environment> [service]"
    return 1
  fi

  # Build API call
  local inputs="{\"environment\":\"$environment\""
  if [ -n "$service" ]; then
    inputs="$inputs,\"service\":\"$service\""
  fi
  inputs="$inputs}"

  # Trigger workflow
  response=$(gh api -X POST \
    "repos/Brookai/$repo/actions/workflows/$workflow/dispatches" \
    -f ref=duplo \
    -f "inputs=$inputs" 2>&1)

  if [ $? -ne 0 ]; then
    echo "ERROR triggering $repo/$workflow: $response"
    return 1
  fi

  echo "✓ $repo/$workflow triggered successfully"
  return 0
}

# Usage
trigger_workflow "billy" "duplo-build.yaml" "dev01-brook" "all"
trigger_workflow "ETL-service" "duplo-build.yaml" "dev01-brook"
```

---

### Pattern E: Poll-and-Wait with Timeout

**Use case**: Wait for workflow completion with timeout

**Benefits**:
- Non-blocking wait
- Timeout prevention
- Status updates

**Implementation**:
```bash
wait_for_completion() {
  local repo=$1
  local run_id=$2
  local timeout=${3:-600}  # Default: 10 minutes
  local poll_interval=${4:-30}  # Default: 30 seconds

  local elapsed=0

  while [ $elapsed -lt $timeout ]; do
    status=$(gh run view $run_id --repo Brookai/$repo \
      --json status,conclusion \
      --jq '.status + ":" + (.conclusion // "running")')

    IFS=':' read -r run_status conclusion <<< "$status"

    if [ "$run_status" == "completed" ]; then
      echo "Build completed: $conclusion"
      [ "$conclusion" == "success" ] && return 0 || return 1
    fi

    echo "Build in progress... ($elapsed/$timeout seconds)"
    sleep $poll_interval
    elapsed=$((elapsed + poll_interval))
  done

  echo "ERROR: Timeout after $timeout seconds"
  return 2
}

# Usage
wait_for_completion "billy" "21645427485" 1200 30  # 20 min timeout, 30s poll
```

---

### Pattern F: Conditional Workflow Selection

**Use case**: Select appropriate workflow based on repository characteristics

**Benefits**:
- Handle monorepo vs single-service patterns
- Automatic input detection
- Flexible batch operations

**Implementation**:
```bash
# Repository configuration
declare -A REPO_CONFIG=(
  ["billy"]="monorepo:frontend,backend,migrations"
  ["care-bot"]="monorepo:service1,service2"
  ["ETL-service"]="single"
  ["py-data"]="single"
)

trigger_appropriate_workflow() {
  local repo=$1
  local environment=$2

  local config=${REPO_CONFIG[$repo]}

  if [[ $config == monorepo:* ]]; then
    # Extract services
    local services=${config#monorepo:}
    echo "Triggering monorepo build for $repo (services: $services)"

    gh workflow run duplo-build.yaml \
      --repo Brookai/$repo \
      --ref duplo \
      --field environment=$environment \
      --field service=all
  else
    echo "Triggering single-service build for $repo"

    gh workflow run duplo-build.yaml \
      --repo Brookai/$repo \
      --ref duplo \
      --field environment=$environment
  fi
}

# Usage
for repo in "${!REPO_CONFIG[@]}"; do
  trigger_appropriate_workflow "$repo" "dev01-brook"
done
```

---

## Advanced Patterns

### Pattern G: Incremental Retry with Backoff

**Use case**: Retry failed builds with exponential backoff

```bash
retry_with_backoff() {
  local repo=$1
  local max_attempts=3
  local backoff=60  # Start with 60 seconds

  for attempt in $(seq 1 $max_attempts); do
    echo "Attempt $attempt/$max_attempts for $repo"

    # Trigger workflow
    gh workflow run duplo-build.yaml --repo Brookai/$repo --ref duplo

    sleep 5  # Wait for run ID

    run_id=$(gh run list --repo Brookai/$repo --workflow=duplo-build.yaml --limit 1 --json databaseId --jq '.[0].databaseId')

    # Wait for completion
    if wait_for_completion "$repo" "$run_id" 600; then
      echo "✓ $repo build succeeded on attempt $attempt"
      return 0
    fi

    if [ $attempt -lt $max_attempts ]; then
      echo "Build failed, retrying in $backoff seconds..."
      sleep $backoff
      backoff=$((backoff * 2))  # Exponential backoff
    fi
  done

  echo "✗ $repo build failed after $max_attempts attempts"
  return 1
}
```

### Pattern H: Parallel Execution with Process Management

**Use case**: Run multiple operations in parallel

```bash
#!/bin/bash

# Run multiple monitors in parallel
for repo in billy ETL-service py-data; do
  (
    # Subshell for each repo
    echo "Starting monitor for $repo"
    ./scripts/monitor-single-build.sh "$repo" &> "logs/$repo-monitor.log"
  ) &
done

# Wait for all background jobs
wait

echo "All monitors completed"
```

### Pattern I: Structured Logging

**Use case**: Consistent logging format for analysis

```bash
LOG_FILE="/path/to/pipeline-run.log"

log_entry() {
  local level=$1
  local repo=$2
  local message=$3

  timestamp=$(date '+%Y-%m-%d %H:%M:%S')

  cat >> $LOG_FILE << EOF

[$timestamp] [$level] REPO: $repo
MESSAGE: $message
---
EOF
}

# Usage
log_entry "INFO" "billy" "Build triggered successfully"
log_entry "ERROR" "ETL-service" "Build failed: JAR not found"
log_entry "SUCCESS" "py-data" "Build completed in 3m 42s"
```

---

## Token and Credential Management

### Pattern J: GitHub Token Handling

**Problem**: `export GITHUB_TOKEN` doesn't persist across Bash tool calls

**Solutions**:

**Solution 1**: Chain commands
```bash
export GITHUB_TOKEN=xxx && gh workflow run ... && gh run list ...
```

**Solution 2**: Embed in script
```bash
#!/bin/bash
export GITHUB_TOKEN="ghp_xxxx"
# Rest of script...
```

**Solution 3**: Source from file
```bash
#!/bin/bash
source /path/to/.env  # Contains: GITHUB_TOKEN=xxx
# Rest of script...
```

**Solution 4**: Heredoc pattern in workflows
```yaml
- name: Run automation
  run: |
    export GITHUB_TOKEN="${{ secrets.GITHUB_TOKEN }}"
    ./scripts/automate.sh
```

### Pattern K: CodeArtifact Token Management

**Pattern**: Generate fresh token per operation

```bash
get_codeartifact_token() {
  aws codeartifact get-authorization-token \
    --domain brook \
    --domain-owner 173008660334 \
    --region us-east-1 \
    --query authorizationToken \
    --output text
}

# Usage in script
export CODEARTIFACT_AUTH_TOKEN=$(get_codeartifact_token)

# Verify token
if [ -z "$CODEARTIFACT_AUTH_TOKEN" ]; then
  echo "ERROR: Failed to generate CodeArtifact token"
  exit 1
fi

./gradlew bootJar
```

---

## Cost Optimization Patterns

### Pattern L: Batch Operations

**Savings**: ~30-40% token reduction on repetitive tasks

**Before** (iterative):
```python
# Multiple agent invocations
for repo in repos:
    agent.read_workflow(repo)
    agent.trigger_workflow(repo)
    agent.monitor_workflow(repo)
    agent.analyze_errors(repo)
```

**After** (batched):
```bash
# Single script handles all repos
./scripts/trigger-workflows.sh   # Triggers all 6 repos
./scripts/monitor-builds.sh      # Monitors all in parallel
./scripts/extract-errors.sh      # Analyzes all failures
```

**Token savings**:
- Trigger: ~5k tokens saved per batch (vs 6 individual triggers)
- Monitor: ~10k tokens saved per iteration (vs polling individually)
- Analysis: ~8k tokens saved per analysis (vs 6 individual analyses)

### Pattern M: Template Reuse

Use pre-built scripts instead of generating from scratch:

```bash
# Copy template
cp scripts/monitor-builds.sh.template my-monitor.sh

# Customize
sed -i '' 's/{{ORG}}/Brookai/g' my-monitor.sh
sed -i '' 's/{{REPOS}}/repo1 repo2 repo3/g' my-monitor.sh

# Run
./my-monitor.sh
```

---

## Testing and Validation

### Pattern N: Local Workflow Validation

**Before committing**:
```bash
# Validate YAML syntax
yamllint .github/workflows/duplo-build.yaml

# Or use actionlint
actionlint .github/workflows/duplo-build.yaml

# Or use yq
cat .github/workflows/duplo-build.yaml | yq eval '.'
```

### Pattern O: Dry-Run Pattern

**Test without triggering**:
```bash
#!/bin/bash

DRY_RUN=${DRY_RUN:-false}

trigger_workflow() {
  local repo=$1

  if [ "$DRY_RUN" == "true" ]; then
    echo "[DRY RUN] Would trigger: gh workflow run duplo-build.yaml --repo Brookai/$repo"
    return 0
  fi

  gh workflow run duplo-build.yaml --repo Brookai/$repo
}

# Usage
DRY_RUN=true ./scripts/trigger-workflows.sh  # Test
DRY_RUN=false ./scripts/trigger-workflows.sh  # Actually run
```

---

## Real-World Examples

### Example 1: Full Pipeline Iteration Cycle

```bash
#!/bin/bash
# Complete iteration: trigger → monitor → analyze → fix

set -e

LOG_FILE="logs/iteration-$(date +%Y%m%d-%H%M%S).log"

# 1. Trigger all builds
echo "=== Triggering builds ===" | tee -a $LOG_FILE
./scripts/trigger-workflows.sh | tee -a $LOG_FILE

# 2. Monitor until completion
echo "=== Monitoring builds ===" | tee -a $LOG_FILE
./scripts/monitor-builds.sh | tee -a $LOG_FILE

# 3. Extract errors from failures
echo "=== Analyzing failures ===" | tee -a $LOG_FILE
./scripts/extract-errors.sh | tee -a $LOG_FILE

# 4. Summarize
echo "=== Summary ===" | tee -a $LOG_FILE
grep -E "(SUCCESS|FAILED)" $LOG_FILE | sort | uniq -c
```

### Example 2: Progressive Rollout

```bash
#!/bin/bash
# Deploy to repos in stages, stopping on failure

REPOS=("billy" "ETL-service" "py-data" "report-service" "chat-storage" "care-bot")

for repo in "${REPOS[@]}"; do
  echo "Deploying $repo..."

  # Trigger
  gh workflow run duplo-build.yaml --repo Brookai/$repo --ref duplo
  sleep 5

  # Get run ID
  run_id=$(gh run list --repo Brookai/$repo --workflow=duplo-build.yaml --limit 1 --json databaseId --jq '.[0].databaseId')

  # Wait for completion
  if ! wait_for_completion "$repo" "$run_id" 600; then
    echo "ERROR: $repo deployment failed, stopping rollout"
    exit 1
  fi

  echo "✓ $repo deployed successfully"
done

echo "All repos deployed!"
```

---

## Resources

- **Session Log**: `/Users/robert/workspaces/brook-ai/logs/duplo-pipeline-run-2026-02-03.log`
- **Reusable Scripts**: [../scripts/](../scripts/)
- **Cleanup Report**: `/Users/robert/workspaces/brook-ai/tmp/CLEANUP_REPORT.md`
- **Scripts Inventory**: `/Users/robert/workspaces/brook-ai/tmp/REUSABLE_SCRIPTS_INVENTORY.md`
