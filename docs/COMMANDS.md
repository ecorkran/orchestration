# Command Reference

Complete reference for all orchestration CLI commands.

## review

Run structured reviews using built-in templates.

### review arch

Run an architectural review comparing a document against an architecture reference.

```
orchestration review arch <INPUT_FILE> --against <ARCH_DOC> [OPTIONS]
```

| Argument/Option | Type | Required | Default | Description |
|----------------|------|----------|---------|-------------|
| `INPUT_FILE` | string | yes | — | Document to review |
| `--against` | string | yes | — | Architecture document to review against |
| `--cwd` | string | no | config or `.` | Working directory |
| `-v`, `--verbose` | count | no | config or `0` | Verbosity level (use `-v` or `-vv`) |
| `--output` | string | no | `terminal` | Output format: `terminal`, `json`, `file` |
| `--output-path` | string | no | — | File path (required when `--output file`) |

```bash
orchestration review arch slice-design.md --against hld.md -v
orchestration review arch spec.md --against arch.md --output json
```

### review tasks

Run a task plan review comparing a task breakdown against its parent slice design.

```
orchestration review tasks <INPUT_FILE> --against <SLICE_DOC> [OPTIONS]
```

| Argument/Option | Type | Required | Default | Description |
|----------------|------|----------|---------|-------------|
| `INPUT_FILE` | string | yes | — | Task breakdown file to review |
| `--against` | string | yes | — | Parent slice design to review against |
| `--cwd` | string | no | config or `.` | Working directory |
| `-v`, `--verbose` | count | no | config or `0` | Verbosity level |
| `--output` | string | no | `terminal` | Output format |
| `--output-path` | string | no | — | File path for `--output file` |

```bash
orchestration review tasks 105-tasks.md --against 105-slice.md -v
```

### review code

Run a code review against the current project.

```
orchestration review code [OPTIONS]
```

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `--cwd` | string | no | config or `.` | Project directory to review |
| `--files` | string | no | — | Glob pattern to scope the review |
| `--diff` | string | no | — | Git ref to diff against |
| `--rules` | string | no | config `default_rules` | Path to additional rules file |
| `-v`, `--verbose` | count | no | config or `0` | Verbosity level |
| `--output` | string | no | `terminal` | Output format |
| `--output-path` | string | no | — | File path for `--output file` |

```bash
# Review all code in current directory
orchestration review code

# Review changes against main
orchestration review code --diff main -v

# Review specific files with custom rules
orchestration review code --files "src/**/*.py" --rules rules/python.md -vv

# Output JSON
orchestration review code --diff main --output json > review.json
```

### review list

List all available review templates.

```
orchestration review list
```

No options. Outputs template names and descriptions.

## config

Manage persistent configuration.

### config set

Set a configuration value.

```
orchestration config set <KEY> <VALUE> [OPTIONS]
```

| Argument/Option | Type | Required | Default | Description |
|----------------|------|----------|---------|-------------|
| `KEY` | string | yes | — | Config key to set |
| `VALUE` | string | yes | — | Value to set |
| `--project` | flag | no | false | Write to project-level config |
| `--cwd` | string | no | `.` | Working directory (for project config location) |

```bash
orchestration config set cwd ~/source/repos/myproject
orchestration config set verbosity 1
orchestration config set default_rules ./rules/python.md --project
```

### config get

Show the resolved value of a configuration key and its source.

```
orchestration config get <KEY> [OPTIONS]
```

| Argument/Option | Type | Required | Default | Description |
|----------------|------|----------|---------|-------------|
| `KEY` | string | yes | — | Config key to read |
| `--cwd` | string | no | `.` | Working directory |

```bash
$ orchestration config get cwd
cwd = ~/source/repos/myproject  (user)
```

### config list

Show all configuration keys with their resolved values and sources.

```
orchestration config list [OPTIONS]
```

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `--cwd` | string | no | `.` | Working directory |

```bash
$ orchestration config list
  cwd            ~/source/repos/myproject  (user)
  default_rules  ./rules/python.md         (project)
  verbosity      0                         (default)
```

### config path

Show configuration file locations and whether they exist.

```
orchestration config path [OPTIONS]
```

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `--cwd` | string | no | `.` | Working directory |

```bash
$ orchestration config path
  User:    ~/.config/orchestration/config.toml  exists
  Project: ./.orchestration.toml                not found
```

## spawn

Spawn a new agent instance.

```
orchestration spawn --name <NAME> [OPTIONS]
```

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `--name` | string | yes | — | Unique agent name |
| `--type` | string | no | `sdk` | Agent type |
| `--provider` | string | no | `sdk` | Provider to use |
| `--cwd` | string | no | `.` | Working directory |
| `--system-prompt` | string | no | — | System prompt |
| `--permission-mode` | string | no | `acceptEdits` | Permission mode |

## list

List running agents.

```
orchestration list [OPTIONS]
```

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `--state` | string | no | — | Filter by agent state |
| `--provider` | string | no | — | Filter by provider |

## task

Send a task prompt to an agent.

```
orchestration task <AGENT_NAME> <PROMPT>
```

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `AGENT_NAME` | string | yes | Target agent name |
| `PROMPT` | string | yes | Task prompt to send |

## shutdown

Shutdown agents.

```
orchestration shutdown <AGENT_NAME>
orchestration shutdown --all
```

| Argument/Option | Type | Required | Description |
|----------------|------|----------|-------------|
| `AGENT_NAME` | string | no | Agent to shut down |
| `--all` | flag | no | Shutdown all agents |

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (invalid arguments, missing files, runtime error, unknown config key) |
| 2 | Review verdict is FAIL |
