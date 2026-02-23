# Orchestration

AI-powered code review and multi-agent orchestration CLI built on Claude.

```bash
pip install orchestration
orchestration review code --diff main -v
```

## Quickstart

### 1. Install

```bash
git clone https://github.com/ecorkran/orchestration.git
cd orchestration
pip install -e ".[dev]"
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv sync
```

### 2. Configure credentials

Orchestration uses the Claude Agent SDK, which requires an Anthropic API key or Claude Max subscription:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### 3. Run your first review

Review your code changes against main:

```bash
orchestration review code --diff main -v
```

Review a task breakdown against its slice design:

```bash
orchestration review tasks tasks.md --against slice-design.md -v
```

That's it. You should see Rich-formatted output with a verdict and findings.

## What it does

Orchestration runs structured reviews using Claude as a backend. Each review type uses a purpose-built prompt template that tells Claude what to look for and how to report findings.

Three built-in review templates:

| Template | Purpose | Example |
|----------|---------|---------|
| `arch` | Architectural review | `review arch design.md --against hld.md` |
| `tasks` | Task plan review | `review tasks tasks.md --against slice.md` |
| `code` | Code review | `review code --diff main --files "src/**/*.py"` |

Each review produces a structured result with:
- **Verdict**: PASS, CONCERNS, or FAIL
- **Findings**: Individual items with severity (PASS, CONCERN, FAIL), title, and description

## Commands

### Review

```bash
# Architectural review
orchestration review arch <file> --against <arch-doc> [--cwd DIR] [-v|-vv]

# Task plan review
orchestration review tasks <file> --against <slice-doc> [--cwd DIR] [-v|-vv]

# Code review
orchestration review code [--cwd DIR] [--files PATTERN] [--diff REF] [--rules FILE] [-v|-vv]

# List available templates
orchestration review list
```

#### Output modes

```bash
# Rich terminal output (default)
orchestration review code --diff main

# JSON to stdout
orchestration review code --diff main --output json

# JSON to file
orchestration review code --diff main --output file --output-path result.json
```

#### Verbosity levels

| Level | Flag | Shows |
|-------|------|-------|
| 0 | (default) | Verdict + finding headings |
| 1 | `-v` | Above + full descriptions |
| 2 | `-vv` | Above + raw agent output |

#### Rules

Point code reviews at additional rules files:

```bash
orchestration review code --rules ./rules/python.md --diff main
```

Rules file content is appended to the review agent's system prompt. Your project's `CLAUDE.md` is already loaded automatically via the SDK's `setting_sources` mechanism.

### Configuration

Persistent configuration with user-level and project-level files:

```bash
# Set a config value (user-level)
orchestration config set cwd ~/source/repos/myproject

# Set a config value (project-level)
orchestration config set default_rules ./rules/python.md --project

# View a config value with its source
orchestration config get cwd

# List all config
orchestration config list

# Show config file locations
orchestration config path
```

#### Config files

| Level | Location | Purpose |
|-------|----------|---------|
| User | `~/.config/orchestration/config.toml` | Personal defaults |
| Project | `.orchestration.toml` (in cwd) | Project-specific overrides |

Precedence (highest to lowest): CLI flag > project config > user config > built-in default.

#### Available keys

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `cwd` | string | `.` | Default working directory for review commands |
| `verbosity` | int | `0` | Default verbosity level (0, 1, or 2) |
| `default_rules` | string | (none) | Default rules file path for code reviews |

### Agent management

```bash
# Spawn an agent
orchestration spawn --name my-agent

# List running agents
orchestration list

# Send a task to an agent
orchestration task my-agent "Analyze this code"

# Shutdown an agent
orchestration shutdown my-agent

# Shutdown all agents
orchestration shutdown --all
```

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success (PASS or CONCERNS verdict) |
| 1 | Error (invalid arguments, missing files, runtime error) |
| 2 | Review failed (FAIL verdict) |

## Architecture

```
src/orchestration/
├── cli/              # Typer CLI commands
│   └── commands/     # review, config, spawn, list, task, shutdown
├── config/           # Persistent TOML configuration
├── core/             # Agent registry, models, protocols
├── review/           # Review engine
│   ├── models.py     # ReviewResult, ReviewFinding, Verdict, Severity
│   ├── parsers.py    # Agent output -> structured results
│   ├── runner.py     # ClaudeSDKClient session management
│   ├── builders/     # Prompt builders (e.g., code review)
│   └── templates/    # YAML template definitions
│       └── builtin/  # arch.yaml, tasks.yaml, code.yaml
└── providers/        # Agent providers (SDK, Anthropic)
```

The review system is template-driven. Each template defines a system prompt, allowed tools, and input schema. The runner creates an ephemeral Claude session, executes the review, and parses the structured output.

For detailed command reference, see [COMMANDS.md](COMMANDS.md).
For template authoring, see [TEMPLATES.md](TEMPLATES.md).

## Development

```bash
# Install dev dependencies
uv sync

# Run tests
uv run pytest

# Type checking
uv run pyright

# Linting and formatting
uv run ruff check
uv run ruff format
```

## License

MIT
