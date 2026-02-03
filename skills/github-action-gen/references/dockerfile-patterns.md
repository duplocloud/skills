# Dockerfile Patterns for DuploCloud GitHub Actions

This guide explains when to use each Dockerfile pattern based on production experience migrating 6 repositories from TeamCity to GitHub Actions.

## Decision Tree

```
Does your service have private dependencies?
├── YES → CodeArtifact, private Maven/npm, internal libraries
│   └── Pattern 2: Workflow Build + Single-Stage Dockerfile
│       Build artifacts in workflow, copy into Docker
│
└── NO → Only public dependencies (Maven Central, npm registry)
    ├── Frontend (React, Vue, Angular)?
    │   └── Pattern 3: Multi-Stage Frontend Dockerfile
    │       Build stage: npm ci + build
    │       Runtime: nginx/httpd
    │
    └── Backend (Java, Python, Go)?
        └── Pattern 1: Multi-Stage Backend Dockerfile
            Build stage: gradle/maven/pip
            Runtime: Copy artifacts
```

## Pattern 1: Multi-Stage Backend Dockerfile

### When to Use
- Service has **NO private dependencies**
- All dependencies from public registries (Maven Central, PyPI, crates.io)
- Build process doesn't require AWS credentials
- Self-contained build (no external artifact fetching)

### Examples from Migration
- `ETL-service` - Standard Java dependencies
- `chat-storage` - Public Java libraries
- `care-bot` - Standard dependencies

### Template (Java/Gradle)

```dockerfile
# ============================================
# Builder Stage
# ============================================
FROM gradle:7-jdk17 AS builder

# Set working directory
WORKDIR /build

# Copy only dependency files first (layer caching)
COPY build.gradle settings.gradle ./
COPY gradle gradle/
COPY gradlew ./

# Download dependencies (cached unless build files change)
RUN ./gradlew dependencies --no-daemon || return 0

# Copy source code
COPY src src/

# Build the application
RUN ./gradlew build --no-daemon

# ============================================
# Runtime Stage
# ============================================
FROM eclipse-temurin:17-jre-jammy

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Copy built artifact from builder
COPY --from=builder /build/build/libs/*.jar app.jar

# Set ownership
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port (if applicable)
EXPOSE 8080

# Health check (optional)
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s \
  CMD curl -f http://localhost:8080/actuator/health || exit 1

# Start application
CMD ["java", "-jar", "app.jar"]
```

### Template (Python)

```dockerfile
# Builder Stage
FROM python:3.11-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Runtime Stage
FROM python:3.11-slim

RUN groupadd -r appuser && useradd -r -g appuser appuser
WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /root/.local /home/appuser/.local
COPY . .

RUN chown -R appuser:appuser /app
USER appuser

ENV PATH=/home/appuser/.local/bin:$PATH

CMD ["python", "app.py"]
```

### Workflow Integration

Simple workflow - Docker build handles everything:

```yaml
- name: Checkout code
  uses: actions/checkout@v4

- name: DuploCloud CI Setup
  uses: Brookai/actions@v0.0.14
  env:
    DUPLO_TENANT: devops

- name: Build and Push Docker Image
  uses: Brookai/actions/build-image@v0.0.14
  with:
    dockerfile: Dockerfile
    context: .
    tags: |
      ${{ github.sha }}
      ${{ github.ref_name }}-latest
```

### Advantages
- Self-contained build
- Layer caching optimizes rebuild times
- No workflow complexity
- Works offline (no external secrets needed)

### Disadvantages
- Cannot access private registries (no AWS credentials in Docker)
- Build failures harder to debug (need to inspect Docker build logs)

---

## Pattern 2: Workflow Build + Single-Stage Dockerfile

### When to Use
- Service has **private dependencies** (CodeArtifact, private Maven/npm)
- Build requires AWS credentials
- Need access to S3, ECR, or other AWS services during build
- Gradle/Maven needs authentication to pull internal libraries

### Examples from Migration
- `report-service` - Depends on `device-bus-data` from CodeArtifact
- `brook-backend` - Internal library dependencies

### Template (Java with CodeArtifact)

**build.gradle.kts** (or build.gradle):
```kotlin
repositories {
    mavenCentral()

    // AWS CodeArtifact repository
    maven {
        url = uri("https://brook-173008660334.d.codeartifact.us-east-1.amazonaws.com/maven/brook-maven/")
        credentials {
            username = "aws"
            password = System.getenv("CODEARTIFACT_AUTH_TOKEN") ?: ""
        }
    }
}

dependencies {
    // Public dependencies
    implementation("org.springframework.boot:spring-boot-starter-web:3.2.0")

    // Private dependency from CodeArtifact
    implementation("com.brook:device-bus-data:1.0.0")
}
```

**Dockerfile** (single-stage):
```dockerfile
FROM eclipse-temurin:17-jre-jammy

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Copy pre-built JAR from workflow
# Workflow builds this with CodeArtifact credentials
COPY build/libs/*.jar app.jar

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=40s \
  CMD curl -f http://localhost:8080/actuator/health || exit 1

CMD ["java", "-jar", "app.jar"]
```

**Workflow** (duplo-build.yaml):
```yaml
name: "[Duplo] Build + Push Image"

on:
  workflow_dispatch:
    inputs:
      environment:
        required: true
        type: string

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      # Step 1: Set up Java runtime
      - name: Set up JDK 17
        uses: actions/setup-java@v4
        with:
          java-version: '17'
          distribution: 'temurin'

      # Step 2: Configure AWS credentials (for CodeArtifact)
      - name: DuploCloud CI Setup
        uses: Brookai/actions@v0.0.14
        env:
          DUPLO_TENANT: devops

      # Step 3: Generate CodeArtifact token and build JAR
      - name: Build JAR with Gradle
        run: |
          # Generate 12-hour CodeArtifact token
          export CODEARTIFACT_AUTH_TOKEN=$(aws codeartifact get-authorization-token \
            --domain brook \
            --domain-owner 173008660334 \
            --region us-east-1 \
            --query authorizationToken \
            --output text)

          # Ensure gradlew is executable
          chmod +x gradlew

          # Build JAR (will use CODEARTIFACT_AUTH_TOKEN from env)
          ./gradlew bootJar --no-daemon

      # Step 4: Build Docker image (just copies pre-built JAR)
      - name: Build and Push Docker Image
        uses: Brookai/actions/build-image@v0.0.14
        with:
          dockerfile: Dockerfile
          context: .
          tags: |
            ${{ github.sha }}
            ${{ github.ref_name }}-latest
```

### Advantages
- Access to AWS credentials during build
- Can pull from private registries (CodeArtifact, private npm, etc.)
- Build failures easier to debug (workflow logs more detailed)
- Faster iteration (can run gradle locally with same pattern)

### Disadvantages
- More workflow complexity
- Build step duplicated (in workflow AND potential local builds)
- Longer workflow YAML files

### Common Mistakes

**Mistake 1**: Forgetting `chmod +x gradlew`
```bash
# ERROR: ./gradlew: Permission denied

# FIX: Add before gradle commands
chmod +x gradlew
./gradlew bootJar
```

**Mistake 2**: Not setting `--no-daemon`
```bash
# Can cause hanging builds in CI
./gradlew build

# Better: Disable daemon in CI
./gradlew build --no-daemon
```

**Mistake 3**: Building inside Docker with multi-stage
```dockerfile
# WRONG: This fails because Docker build has no AWS credentials
FROM gradle:7-jdk17 AS builder
WORKDIR /build
COPY . .
RUN ./gradlew build  # ← Fails when pulling from CodeArtifact
```

---

## Pattern 3: Multi-Stage Frontend Dockerfile

### When to Use
- Frontend application (React, Vue, Angular, Svelte)
- Build process: `npm ci` + `npm run build`
- Static files served by nginx or similar
- Only public npm dependencies

### Examples from Migration
- `billy-frontend` - Vite + React application

### Template (Vite/React)

```dockerfile
# ============================================
# Builder Stage
# ============================================
FROM node:22-alpine AS builder

# Set working directory
WORKDIR /build

# Copy package files (layer caching)
COPY package.json package-lock.json ./

# Install dependencies
RUN npm ci --production=false

# Copy source code
COPY . .

# Build for production
RUN npm run build

# ============================================
# Runtime Stage
# ============================================
FROM nginx:stable-alpine

# Copy nginx configuration (if needed)
# COPY nginx.conf /etc/nginx/nginx.conf

# Copy built static files from builder
COPY --from=builder /build/dist /usr/share/nginx/html

# Expose port
EXPOSE 80

# nginx runs as root by default (can configure non-root if needed)
CMD ["nginx", "-g", "daemon off;"]
```

### Template (Next.js)

```dockerfile
# Builder Stage
FROM node:22-alpine AS builder
WORKDIR /build
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Runtime Stage (Node.js required for Next.js SSR)
FROM node:22-alpine
WORKDIR /app

RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy Next.js build output
COPY --from=builder /build/public ./public
COPY --from=builder /build/.next/standalone ./
COPY --from=builder /build/.next/static ./.next/static

USER nextjs
EXPOSE 3000

ENV PORT 3000
ENV HOSTNAME "0.0.0.0"

CMD ["node", "server.js"]
```

### Workflow Integration

Simple workflow - Docker build handles everything:

```yaml
- name: Checkout code
  uses: actions/checkout@v4

- name: DuploCloud CI Setup
  uses: Brookai/actions@v0.0.14
  env:
    DUPLO_TENANT: devops

- name: Build and Push Docker Image
  uses: Brookai/actions/build-image@v0.0.14
  with:
    dockerfile: frontend/Dockerfile
    context: ./frontend
    tags: |
      ${{ github.sha }}-frontend
      ${{ github.ref_name }}-frontend-latest
```

### Advantages
- Clean separation: build vs runtime
- Small runtime image (nginx:alpine ~15MB)
- Fast rebuilds with layer caching
- Standard nginx serving optimizations

### Disadvantages
- Build stage can be slow (npm install)
- Node modules not shared between builds (unless using cache)

### Optimization Tips

**Tip 1**: Use .dockerignore
```
# .dockerignore
node_modules
.git
.github
dist
build
*.log
.env
```

**Tip 2**: Cache npm dependencies in workflow
```yaml
- name: Cache node modules
  uses: actions/cache@v3
  with:
    path: ~/.npm
    key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
```

**Tip 3**: Multi-platform builds (if needed)
```yaml
- name: Build and Push
  uses: Brookai/actions/build-image@v0.0.14
  with:
    platforms: linux/amd64,linux/arm64
    dockerfile: Dockerfile
    context: .
```

---

## Converting Between Patterns

### From Pattern 1 to Pattern 2 (Adding Private Dependencies)

When you add a private dependency:

1. **Update build.gradle.kts**:
```kotlin
repositories {
    maven {
        url = uri("https://brook-173008660334.d.codeartifact.us-east-1.amazonaws.com/maven/brook-maven/")
        credentials {
            username = "aws"
            password = System.getenv("CODEARTIFACT_AUTH_TOKEN") ?: ""
        }
    }
}
```

2. **Convert Dockerfile to single-stage**:
```dockerfile
# Remove builder stage
FROM eclipse-temurin:17-jre
COPY build/libs/*.jar app.jar
CMD ["java", "-jar", "app.jar"]
```

3. **Add workflow build step**:
```yaml
- name: Build JAR with Gradle
  run: |
    export CODEARTIFACT_AUTH_TOKEN=$(aws codeartifact get-authorization-token ...)
    chmod +x gradlew
    ./gradlew bootJar
```

### From Pattern 2 to Pattern 1 (Removing Private Dependencies)

When you remove private dependencies:

1. **Remove CodeArtifact repo from build.gradle.kts**

2. **Convert to multi-stage Dockerfile**:
```dockerfile
FROM gradle:7-jdk17 AS builder
COPY . .
RUN ./gradlew build

FROM eclipse-temurin:17-jre
COPY --from=builder /build/build/libs/*.jar app.jar
```

3. **Simplify workflow** (remove build step)

---

## Common Gotchas

### Gotcha 1: Wrong COPY path in Dockerfile
```dockerfile
# If workflow builds in repo root, JAR is at:
COPY build/libs/*.jar app.jar  # ✓ Correct

# Not:
COPY /app/build/libs/*.jar app.jar  # ✗ Wrong
```

### Gotcha 2: Expecting dist folder that doesn't exist
```dockerfile
# Error: "/dist": not found
COPY dist /usr/share/nginx/html

# Solution: Use multi-stage build to CREATE dist first
FROM node:22-alpine AS builder
RUN npm run build  # Creates dist
FROM nginx:alpine
COPY --from=builder /build/dist /usr/share/nginx/html
```

### Gotcha 3: Forgetting to run build in workflow
```yaml
# Pattern 2 requires explicit build step
- name: Build JAR  # ← Don't forget this
  run: ./gradlew bootJar

- name: Build Docker
  # Dockerfile expects JAR to exist
```

---

## Testing Your Dockerfile

### Local Testing (Pattern 1)
```bash
docker build -t myapp:test .
docker run -p 8080:8080 myapp:test
curl http://localhost:8080/health
```

### Local Testing (Pattern 2)
```bash
# Step 1: Build artifact
export CODEARTIFACT_AUTH_TOKEN=$(aws codeartifact get-authorization-token ...)
./gradlew bootJar

# Step 2: Build Docker image
docker build -t myapp:test .

# Step 3: Run
docker run -p 8080:8080 myapp:test
```

### Local Testing (Pattern 3)
```bash
# Frontend
docker build -f frontend/Dockerfile -t myapp-ui:test ./frontend
docker run -p 80:80 myapp-ui:test
open http://localhost
```

---

## References

- Migration Log: `/Users/robert/workspaces/brook-ai/logs/duplo-pipeline-run-2026-02-03.log`
- CodeArtifact Guide: [codeartifact.md](codeartifact.md)
- Troubleshooting: [troubleshooting.md](troubleshooting.md)
