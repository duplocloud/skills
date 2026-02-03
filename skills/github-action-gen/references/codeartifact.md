# AWS CodeArtifact Integration Guide

Complete guide for integrating AWS CodeArtifact with GitHub Actions workflows for DuploCloud deployments.

## What is CodeArtifact?

AWS CodeArtifact is a managed artifact repository service that works with common package managers:
- Maven (Java)
- Gradle (Java/Kotlin)
- npm (Node.js)
- pip (Python)
- NuGet (.NET)

It replaces legacy S3-based Maven repositories with proper authentication, versioning, and access control.

## When to Use CodeArtifact

Use CodeArtifact when your service has **private/internal dependencies**:
- Internal shared libraries (e.g., `device-bus-data`)
- Forked versions of public libraries
- Proprietary code shared across services
- Dependencies that shouldn't be public

**Don't use** for services with only public dependencies - use multi-stage Docker builds instead.

## Brook AI CodeArtifact Configuration

### Repository Details
- **AWS Account**: 173008660334
- **Region**: us-east-1
- **Domain**: brook
- **Repository**: brook-maven (Maven/Gradle artifacts)
- **URL**: `https://brook-173008660334.d.codeartifact.us-east-1.amazonaws.com/maven/brook-maven/`

### Authentication
CodeArtifact uses **temporary tokens** (12-hour validity):
- Generated via `aws codeartifact get-authorization-token`
- Passed to build tools as environment variable
- No permanent credentials in code or configs

## Integration Patterns

### Pattern 1: Java/Gradle with CodeArtifact

**build.gradle.kts** (Kotlin DSL):
```kotlin
repositories {
    // Public repositories first (faster for common dependencies)
    mavenCentral()

    // AWS CodeArtifact for private dependencies
    maven {
        url = uri("https://brook-173008660334.d.codeartifact.us-east-1.amazonaws.com/maven/brook-maven/")
        credentials {
            username = "aws"
            password = System.getenv("CODEARTIFACT_AUTH_TOKEN") ?: ""
        }
    }
}

dependencies {
    // Public dependencies (from Maven Central)
    implementation("org.springframework.boot:spring-boot-starter-web:3.2.0")
    implementation("org.postgresql:postgresql:42.7.1")

    // Private dependencies (from CodeArtifact)
    implementation("com.brook:device-bus-data:1.0.0")
    implementation("com.brook:common-utils:2.1.0")
}
```

**build.gradle** (Groovy DSL):
```groovy
repositories {
    mavenCentral()

    maven {
        url 'https://brook-173008660334.d.codeartifact.us-east-1.amazonaws.com/maven/brook-maven/'
        credentials {
            username 'aws'
            password System.getenv('CODEARTIFACT_AUTH_TOKEN') ?: ''
        }
    }
}

dependencies {
    implementation 'org.springframework.boot:spring-boot-starter-web:3.2.0'
    implementation 'com.brook:device-bus-data:1.0.0'
}
```

### Pattern 2: Maven (pom.xml)

**pom.xml**:
```xml
<project>
    <repositories>
        <repository>
            <id>maven-central</id>
            <url>https://repo1.maven.org/maven2</url>
        </repository>

        <repository>
            <id>brook-codeartifact</id>
            <url>https://brook-173008660334.d.codeartifact.us-east-1.amazonaws.com/maven/brook-maven/</url>
        </repository>
    </repositories>

    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
            <version>3.2.0</version>
        </dependency>

        <dependency>
            <groupId>com.brook</groupId>
            <artifactId>device-bus-data</artifactId>
            <version>1.0.0</version>
        </dependency>
    </dependencies>
</project>
```

**settings.xml** (for authentication):
```xml
<settings>
    <servers>
        <server>
            <id>brook-codeartifact</id>
            <username>aws</username>
            <password>${env.CODEARTIFACT_AUTH_TOKEN}</password>
        </server>
    </servers>
</settings>
```

### Pattern 3: npm (Node.js)

**.npmrc** (in project root):
```ini
# Public npm registry (default)
registry=https://registry.npmjs.org/

# Brook internal packages use CodeArtifact
@brook:registry=https://brook-173008660334.d.codeartifact.us-east-1.amazonaws.com/npm/brook-npm/
//brook-173008660334.d.codeartifact.us-east-1.amazonaws.com/npm/brook-npm/:always-auth=true
//brook-173008660334.d.codeartifact.us-east-1.amazonaws.com/npm/brook-npm/:_authToken=${CODEARTIFACT_AUTH_TOKEN}
```

**package.json**:
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "@brook/shared-components": "^1.5.0"
  }
}
```

### Pattern 4: Python (pip)

**pip.conf** or **pip.ini**:
```ini
[global]
index-url = https://pypi.org/simple
extra-index-url = https://aws:${CODEARTIFACT_AUTH_TOKEN}@brook-173008660334.d.codeartifact.us-east-1.amazonaws.com/pypi/brook-pypi/simple/
```

**requirements.txt**:
```
# Public packages
requests==2.31.0
flask==3.0.0

# Private packages (from CodeArtifact)
brook-data-client==1.2.3
brook-auth-lib==2.0.1
```

## GitHub Actions Workflow Integration

### Complete Workflow Example (Java)

```yaml
name: "[Duplo] Build + Push Image"

on:
  workflow_dispatch:
    inputs:
      environment:
        required: true
        type: string
        description: 'Target environment (e.g., dev01-brook)'

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      # 1. Checkout code
      - name: Checkout repository
        uses: actions/checkout@v4

      # 2. Set up Java runtime
      - name: Set up JDK 17
        uses: actions/setup-java@v4
        with:
          java-version: '17'
          distribution: 'temurin'

      # 3. Configure AWS credentials via DuploCloud
      - name: DuploCloud CI Setup
        uses: Brookai/actions@v0.0.14
        env:
          DUPLO_TENANT: devops

      # 4. Generate CodeArtifact token and build
      - name: Build JAR with CodeArtifact dependencies
        run: |
          # Generate 12-hour CodeArtifact authentication token
          export CODEARTIFACT_AUTH_TOKEN=$(aws codeartifact get-authorization-token \
            --domain brook \
            --domain-owner 173008660334 \
            --region us-east-1 \
            --query authorizationToken \
            --output text)

          # Verify token was generated
          if [ -z "$CODEARTIFACT_AUTH_TOKEN" ]; then
            echo "ERROR: Failed to generate CodeArtifact token"
            exit 1
          fi

          # Make gradlew executable (required in fresh checkout)
          chmod +x gradlew

          # Build JAR (gradle will use CODEARTIFACT_AUTH_TOKEN from environment)
          ./gradlew bootJar --no-daemon --info

      # 5. Build and push Docker image
      - name: Build and Push Docker Image to ECR
        uses: Brookai/actions/build-image@v0.0.14
        with:
          dockerfile: Dockerfile
          context: .
          image-name: ${{ github.event.repository.name }}
          tags: |
            ${{ github.sha }}
            ${{ github.ref_name }}-latest
```

### Node.js/npm Workflow

```yaml
- name: Set up Node.js
  uses: actions/setup-node@v4
  with:
    node-version: '20'

- name: DuploCloud CI Setup
  uses: Brookai/actions@v0.0.14
  env:
    DUPLO_TENANT: devops

- name: Build with CodeArtifact dependencies
  run: |
    export CODEARTIFACT_AUTH_TOKEN=$(aws codeartifact get-authorization-token \
      --domain brook \
      --domain-owner 173008660334 \
      --region us-east-1 \
      --query authorizationToken \
      --output text)

    npm ci
    npm run build

- name: Build Docker Image
  # ... (Dockerfile copies pre-built dist/)
```

### Python Workflow

```yaml
- name: Set up Python
  uses: actions/setup-python@v5
  with:
    python-version: '3.11'

- name: DuploCloud CI Setup
  uses: Brookai/actions@v0.0.14
  env:
    DUPLO_TENANT: devops

- name: Install dependencies with CodeArtifact
  run: |
    export CODEARTIFACT_AUTH_TOKEN=$(aws codeartifact get-authorization-token \
      --domain brook \
      --domain-owner 173008660334 \
      --region us-east-1 \
      --query authorizationToken \
      --output text)

    # Install using pip with CodeArtifact auth
    pip install -r requirements.txt

- name: Build Docker Image
  # ...
```

## Single-Stage Dockerfile (Required for CodeArtifact Pattern)

When using CodeArtifact, use a **single-stage** Dockerfile that expects pre-built artifacts:

```dockerfile
FROM eclipse-temurin:17-jre-jammy

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Copy pre-built JAR from workflow
# (Built with CodeArtifact credentials in GitHub Actions)
COPY build/libs/*.jar app.jar

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

CMD ["java", "-jar", "app.jar"]
```

**Why not multi-stage?**
- Docker build step has NO access to AWS credentials
- Can't authenticate to CodeArtifact during build
- Results in `401 Unauthorized` or `403 Access Denied` errors

## Local Development Setup

### Option 1: Using duploctl (Recommended)

Configure AWS profile with JIT credentials:

```ini
# ~/.aws/config or project config/aws
[profile brook-duplocloud]
region = us-east-1
output = json
credential_process = sh -c "duploctl jit aws --admin --host https://duplo.cloud.brook.ai --interactive -o json | jq '{Version: .Version, AccessKeyId: .AccessKeyId, SecretAccessKey: .SecretAccessKey, SessionToken: .SessionToken, Expiration: .Expiration}'"
```

Generate token for local builds:

```bash
# Use AWS profile
export AWS_PROFILE=brook-duplocloud

# Generate CodeArtifact token
export CODEARTIFACT_AUTH_TOKEN=$(aws codeartifact get-authorization-token \
  --domain brook \
  --domain-owner 173008660334 \
  --region us-east-1 \
  --query authorizationToken \
  --output text)

# Build locally
./gradlew bootJar
```

### Option 2: Using Long-Lived AWS Credentials

```bash
# Set AWS credentials
export AWS_ACCESS_KEY_ID=xxx
export AWS_SECRET_ACCESS_KEY=xxx
export AWS_SESSION_TOKEN=xxx  # If using temporary credentials

# Generate token
export CODEARTIFACT_AUTH_TOKEN=$(aws codeartifact get-authorization-token \
  --domain brook \
  --domain-owner 173008660334 \
  --region us-east-1 \
  --query authorizationToken \
  --output text)

# Build
./gradlew bootJar
```

## Troubleshooting

### Error: 401 Unauthorized from CodeArtifact

**Symptom**:
```
Could not GET 'https://brook-173008660334.d.codeartifact.us-east-1.amazonaws.com/maven/brook-maven/com/brook/device-bus-data/1.0.0/device-bus-data-1.0.0.pom'.
Received status code 401 from server: Unauthorized
```

**Causes**:
1. `CODEARTIFACT_AUTH_TOKEN` not set
2. Token expired (12-hour validity)
3. Token not passed to gradle correctly

**Solutions**:
```bash
# Verify token is set
echo $CODEARTIFACT_AUTH_TOKEN

# Re-generate token
export CODEARTIFACT_AUTH_TOKEN=$(aws codeartifact get-authorization-token ...)

# Check build.gradle.kts uses correct env var
password = System.getenv("CODEARTIFACT_AUTH_TOKEN") ?: ""
```

### Error: 403 Access Denied from CodeArtifact

**Symptom**:
```
Access Denied
The security token included in the request is invalid.
```

**Causes**:
1. AWS credentials not configured
2. DuploCloud CI Setup not run
3. Wrong AWS account/region

**Solutions**:
```yaml
# Ensure DuploCloud CI Setup runs BEFORE CodeArtifact token generation
- name: DuploCloud CI Setup
  uses: Brookai/actions@v0.0.14
  env:
    DUPLO_TENANT: devops

# Then generate token
- name: Build with CodeArtifact
  run: |
    export CODEARTIFACT_AUTH_TOKEN=$(aws codeartifact get-authorization-token ...)
```

### Error: Dependency not found in CodeArtifact

**Symptom**:
```
Could not find com.brook:device-bus-data:1.0.0.
Searched in the following locations:
  - https://brook-173008660334.d.codeartifact.us-east-1.amazonaws.com/maven/brook-maven/...
```

**Causes**:
1. Artifact not published to CodeArtifact
2. Wrong version specified
3. Wrong repository URL

**Solutions**:
```bash
# List packages in CodeArtifact
aws codeartifact list-packages \
  --domain brook \
  --domain-owner 173008660334 \
  --repository brook-maven \
  --region us-east-1

# List package versions
aws codeartifact list-package-versions \
  --domain brook \
  --domain-owner 173008660334 \
  --repository brook-maven \
  --package device-bus-data \
  --format maven \
  --namespace com.brook \
  --region us-east-1
```

### Error: Multi-stage Docker build fails with CodeArtifact

**Symptom**:
```
ERROR: failed to solve: process "/bin/sh -c ./gradlew build" did not complete successfully: exit code: 1
> Could not resolve com.brook:device-bus-data:1.0.0
```

**Cause**: Docker build has no access to AWS credentials

**Solution**: Use workflow build pattern (see [dockerfile-patterns.md](dockerfile-patterns.md#pattern-2-workflow-build--single-stage-dockerfile))

## Publishing to CodeArtifact

### Gradle Publishing (build.gradle.kts)

```kotlin
plugins {
    `maven-publish`
}

publishing {
    publications {
        create<MavenPublication>("maven") {
            from(components["java"])
            groupId = "com.brook"
            artifactId = "device-bus-data"
            version = "1.0.0"
        }
    }

    repositories {
        maven {
            url = uri("https://brook-173008660334.d.codeartifact.us-east-1.amazonaws.com/maven/brook-maven/")
            credentials {
                username = "aws"
                password = System.getenv("CODEARTIFACT_AUTH_TOKEN")
            }
        }
    }
}
```

Publish:
```bash
export CODEARTIFACT_AUTH_TOKEN=$(aws codeartifact get-authorization-token ...)
./gradlew publish
```

### npm Publishing

```bash
# Login to CodeArtifact npm registry
aws codeartifact login \
  --tool npm \
  --domain brook \
  --domain-owner 173008660334 \
  --repository brook-npm \
  --region us-east-1

# Publish package
npm publish --registry https://brook-173008660334.d.codeartifact.us-east-1.amazonaws.com/npm/brook-npm/
```

## Migration from S3 Maven Repository

### Old Pattern (Deprecated)

```kotlin
repositories {
    maven {
        url = uri("s3://brook-maven-repo/releases")
        authentication {
            create<AwsImAuthentication>("awsIm")
        }
    }
}
```

**Problems**:
- Requires AWS credentials in Docker build
- Access denied errors (IAM role issues)
- No version control or audit trail
- Difficult to manage permissions

### New Pattern (CodeArtifact)

```kotlin
repositories {
    maven {
        url = uri("https://brook-173008660334.d.codeartifact.us-east-1.amazonaws.com/maven/brook-maven/")
        credentials {
            username = "aws"
            password = System.getenv("CODEARTIFACT_AUTH_TOKEN")
        }
    }
}
```

**Benefits**:
- Temporary token authentication (no permanent credentials)
- Proper versioning and audit trail
- Fine-grained access control
- Works in GitHub Actions without S3 access

### Migration Steps

1. Publish artifacts to CodeArtifact:
   ```bash
   # For each artifact in S3
   aws s3 cp s3://brook-maven-repo/releases/com/brook/device-bus-data/1.0.0/ ./local-copy/ --recursive
   # Then publish to CodeArtifact using gradle publish
   ```

2. Update all repos:
   - Change `build.gradle.kts` to use CodeArtifact URL
   - Update workflows to generate token
   - Convert to single-stage Dockerfile
   - Test builds

3. Verify:
   - All builds succeed with CodeArtifact
   - No more S3 access denied errors
   - Local builds work with `duploctl jit aws`

## Best Practices

### 1. Token Generation
- Always generate token fresh in each workflow run
- Don't cache or reuse tokens across runs
- Verify token is set before building

### 2. Repository Order
```kotlin
repositories {
    mavenCentral()          // First (public, faster)
    maven { /* CodeArtifact */ }  // Last (private, slower)
}
```

### 3. Error Handling
```yaml
- name: Build with CodeArtifact
  run: |
    export CODEARTIFACT_AUTH_TOKEN=$(aws codeartifact get-authorization-token ...)

    if [ -z "$CODEARTIFACT_AUTH_TOKEN" ]; then
      echo "ERROR: CodeArtifact token not generated"
      exit 1
    fi

    ./gradlew bootJar --info  # --info for better error messages
```

### 4. Local Development
- Use AWS profile with `duploctl jit aws`
- Set `CODEARTIFACT_AUTH_TOKEN` in shell profile or direnv
- Document setup in project README

## Resources

- AWS CodeArtifact Documentation: https://docs.aws.amazon.com/codeartifact/
- Migration Log: `/Users/robert/workspaces/brook-ai/logs/duplo-pipeline-run-2026-02-03.log`
- Dockerfile Patterns: [dockerfile-patterns.md](dockerfile-patterns.md)
- Troubleshooting Guide: [troubleshooting.md](troubleshooting.md)
