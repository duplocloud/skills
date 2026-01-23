# Duplocloud Skills 

A curated collection of Agent Skills for Duplocloud workflows. These skills follow the [open agent skills standard](https://agentskills.io) and work across multiple AI coding assistants.

## What are Agent Skills?

Agent Skills are modular, filesystem-based capabilities that extend AI agents with domain-specific expertise. Each skill packages instructions, metadata, and optional resources (scripts, templates, documentation) that agents use automatically when relevant to your task.

**Key Benefits:**
- **Reusable expertise**: Create once, use automatically across conversations
- **Progressive disclosure**: Only metadata loads initially; full instructions load on-demand
- **Composable**: Combine skills to build complex workflows
- **Shareable**: Distribute skills across teams or the community

## Supported Platforms

These skills work with any tool supporting the agent skills standard:

### Claude (Anthropic)
- **Claude Code**: Desktop IDE with native skills support
- **Claude API**: Programmatic access with skills
- **Claude.ai**: Web interface with custom skills
- **Documentation**: [Agent Skills Overview](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)

Skills are stored in `.claude/skills/` directories and use progressive loading (metadata → instructions → resources).

### OpenAI Codex
- **Codex CLI**: Command-line interface
- **Codex IDE Extensions**: VS Code and other editors
- **Documentation**: [Agent Skills](https://developers.openai.com/codex/skills/)

Skills are stored in `.codex/skills/` with support for repo-level, user-level, and admin-level scopes.

### Gemini CLI (Google)
- **Gemini CLI**: Terminal-based AI assistant
- **Documentation**: [Agent Skills](https://geminicli.com/docs/cli/skills/)

Skills are stored in `.gemini/skills/` with workspace, user, and extension-level discovery.

### GitHub Copilot
- **Copilot Coding Agent**: In-editor agent mode
- **GitHub Copilot CLI**: Command-line tool
- **VS Code Insiders**: Agent mode support
- **Documentation**: [About Agent Skills](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills)

Skills are stored in `.github/skills/` (project) or `~/.copilot/skills/` (personal).

## Skill Structure

Every skill requires a `SKILL.md` file with YAML frontmatter:

```markdown
---
name: skill-name
description: What the skill does and when to use it
---

# Skill Instructions

Clear, step-by-step guidance for the agent to follow.

## Examples

Concrete examples demonstrating skill usage.
```

**Optional components:**
- `scripts/`: Executable code the agent can run
- `references/`: Documentation, schemas, examples
- `assets/`: Templates, boilerplate, resources

## Available Skills

### tf-module
Terraform module creation using Duplocloud provided resources and patterns.

**Location**: `skills/tf-module/`

## How the Devcontainer System Works

### Architecture Overview

The Duplocloud skills distribution system uses a devcontainer feature-based architecture:

```
┌─────────────────────────────────────────────────────────────┐
│ This Repo (duplocloud/tools/skills)                         │
│ - Source skills in skills/ directory                        │
│ - Each skill has SKILL.md + optional resources              │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ Published as .skill archives
                 ↓
┌─────────────────────────────────────────────────────────────┐
│ duplocloud/ai-ops (GitHub Releases)                         │
│ - .skill files (ZIP archives)                               │
│ - SHA256 checksums                                          │
│ - Version-tagged releases (v0.0.2, etc.)                    │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ Downloaded by duplo-skills CLI
                 ↓
┌─────────────────────────────────────────────────────────────┐
│ duplocloud/devcontainers (AI Feature)                       │
│ - Installs Node.js runtime                                  │
│ - Installs duplo-skills CLI globally                        │
│ - Provides skill download automation                        │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ Used in devcontainer.json
                 ↓
┌─────────────────────────────────────────────────────────────┐
│ Your Project (.devcontainer/devcontainer.json)              │
│ - References ghcr.io/duplocloud/devcontainers/ai:1          │
│ - Skills downloaded to ~/.claude/skills, etc.               │
└─────────────────────────────────────────────────────────────┘
```

### The Workflow

1. **Skill Creation** (this repo)
   - Skills are developed in `skills/` directory
   - Each skill has a `SKILL.md` with YAML frontmatter
   - Optional scripts, references, and assets included

2. **Packaging & Publishing** (automated)
   - GitHub Actions workflow packages skills as `.skill` ZIP archives
   - Archives published to [duplocloud/ai-ops releases](https://github.com/duplocloud/ai-ops/releases)
   - SHA256 checksums automatically provided by GitHub API for each asset

3. **Distribution** (devcontainer feature)
   - The [AI base feature](https://github.com/duplocloud/devcontainers/tree/main/src/ai) provides `duplo-skills` CLI
   - CLI downloads `.skill` files from GitHub releases
   - Automatically extracts and verifies checksums

4. **Installation** (your environment)
   - Add AI feature to your devcontainer
   - Use `duplo-skills` command to download skills
   - Skills available to Claude, Codex, Gemini, or Copilot

### Why This Approach?

**Benefits:**
- **Version Control**: Pin to specific skill versions via `DUPLO_SKILLS_VERSION`
- **Integrity**: SHA256 checksums ensure files aren't corrupted
- **Automation**: Devcontainer features handle setup automatically
- **Cross-Platform**: Same `.skill` files work across all AI platforms
- **CI/CD Ready**: GitHub token authentication for automated workflows

## How Skills are Distributed

Skills from this repository are packaged as `.skill` archive files (ZIP format) and published as GitHub release artifacts in the [duplocloud/ai-ops](https://github.com/duplocloud/ai-ops) repository. Each release contains:
- `.skill` files containing the skill directory structure
- SHA256 checksums automatically provided by GitHub API
- Automatic checksum verification during installation

**Latest Release**: [v0.0.2](https://github.com/duplocloud/ai-ops/releases/tag/v0.0.2)

## Installation Methods

### Method 1: Devcontainer Features (Recommended)

The easiest way to install skills is using the [duplocloud/devcontainers](https://github.com/duplocloud/devcontainers) AI feature system. This automatically installs the `duplo-skills` CLI and downloads skills into your environment.

#### Quick Setup

Add the AI base feature to your `.devcontainer/devcontainer.json`:

```json
{
  "features": {
    "ghcr.io/duplocloud/devcontainers/ai:1": {}
  }
}
```

This installs:
- Node.js runtime
- `duplo-skills` CLI for downloading skills
- Automatic checksum verification
- Support for version pinning

#### Using the duplo-skills CLI

Once the AI feature is installed, use the `duplo-skills` command to download skills:

```bash
# Download to Claude skills directory
duplo-skills --dir ~/.claude/skills --skill tf-module

# Download to Codex skills directory
duplo-skills --dir ~/.codex/skills --skill tf-module

# Download to Gemini skills directory
duplo-skills --dir ~/.gemini/skills --skill tf-module

# Download to GitHub Copilot skills directory
duplo-skills --dir ~/.copilot/skills --skill tf-module

# Pin to a specific version
DUPLO_SKILLS_VERSION=v0.0.2 duplo-skills --dir ~/.claude/skills --skill tf-module
```

#### Authentication

For CI/CD or to avoid GitHub API rate limits:

```bash
# With GitHub token (recommended for CI/CD)
GITHUB_TOKEN=${{ secrets.GITHUB_TOKEN }} duplo-skills --dir ~/.claude/skills --skill tf-module

# Rate limits:
# - Unauthenticated: 60 requests/hour
# - Authenticated: 5000 requests/hour
```

#### Environment Variables

- `DUPLO_SKILLS_VERSION` - Specify release version (default: "latest")
- `GITHUB_TOKEN` or `GH_TOKEN` - GitHub token for authenticated API requests

### Method 2: Manual Installation

Download `.skill` files directly from [GitHub releases](https://github.com/duplocloud/ai-ops/releases):

**For Claude.ai:**
1. Go to claude.ai → Settings → Features → Skills
2. Click "Upload skill"
3. Select the `.skill` file
4. Toggle the skill ON to activate it

**For other platforms:**
1. Download the `.skill` file
2. Extract the ZIP archive
3. Copy the extracted folder to your platform's skills directory:
   - Claude: `.claude/skills/` or `~/.claude/skills/`
   - Codex: `.codex/skills/` or `~/.codex/skills/`
   - Gemini: `.gemini/skills/` or `~/.gemini/skills/`
   - GitHub Copilot: `.github/skills/` or `~/.copilot/skills/`

## Creating Custom Skills

1. Create a directory for your skill
2. Add a `SKILL.md` file with frontmatter and instructions
3. Optionally add scripts, references, or assets
4. Place in the appropriate skills directory for your platform

See the [Agent Skills Specification](https://agentskills.io/specification) for detailed guidance.

## Security Considerations

**Only use skills from trusted sources.** Skills can execute code and access files, so:
- Review all skill contents before use
- Be cautious with skills that fetch external data
- Audit scripts and resources thoroughly
- Treat skills like installing software

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on contributing new skills.

## License

See [LICENSE](LICENSE) for details.

## Resources

- [Agent Skills Specification](https://agentskills.io/specification)
- [Claude Agent Skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)
- [OpenAI Codex Skills](https://developers.openai.com/codex/skills/)
- [Gemini CLI Skills](https://geminicli.com/docs/cli/skills/)
- [GitHub Copilot Skills](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills)
- [Anthropic Skills Repository](https://github.com/anthropics/skills)
- [Awesome Copilot Collection](https://github.com/github/awesome-copilot)
