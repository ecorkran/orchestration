---
slice: m1-polish-and-publish
project: orchestration
lld: user/slices/106-slice.m1-polish-and-publish.md
dependencies: [foundation, sdk-agent-provider, cli-foundation, review-workflow-templates]
projectState: >
  Slices 100-105 complete. Review CLI works end-to-end with arch, tasks, and
  code templates. 232 tests passing, 0 pyright/ruff errors. Branch
  105-slice.review-workflow-templates is current.
dateCreated: 20260222
dateUpdated: 20260222
---

## Context Summary

- Working on m1-polish-and-publish slice (106)
- Polishes the M1 deliverable for external adoption: config persistence, verbosity levels, text color improvements, `--rules` flag, and documentation
- All prerequisite slices (100-105) are complete; the review CLI is functional
- Dependencies: `tomli-w` for TOML writing (Python 3.11+ has `tomllib` for reading)
- Next planned work: M2

---

## Tasks

### T1 — Add `tomli-w` dependency
- [ ] Add `tomli-w>=1.0` to `pyproject.toml` dependencies
- [ ] Run `uv sync` to install
  - [ ] SC: `uv pip list` shows `tomli-w` installed
  - [ ] SC: `uv run python -c "import tomli_w"` succeeds

### T2 — Config module: key definitions and defaults
- [ ] Create `src/orchestration/config/__init__.py` (module docstring only)
- [ ] Create `src/orchestration/config/keys.py`
  - [ ] Define `ConfigKey` dataclass: `name: str`, `type_: type`, `default: object`, `description: str`
  - [ ] Define `CONFIG_KEYS: dict[str, ConfigKey]` with initial keys from slice design:
    - `cwd` (str, default `"."`)
    - `verbosity` (int, default `0`)
    - `default_rules` (str | None, default `None`)
  - [ ] Helper `get_default(key: str) -> object` that returns the default for a key, raises `KeyError` for unknown keys
  - [ ] SC: All three keys defined with correct types and defaults
  - [ ] SC: `ruff check` and `pyright` pass

### T3 — Config module: manager (load, merge, persist)
- [ ] Create `src/orchestration/config/manager.py`
  - [ ] `user_config_path() -> Path` — returns `~/.config/orchestration/config.toml`
  - [ ] `project_config_path(cwd: str = ".") -> Path` — returns `{cwd}/.orchestration.toml`
  - [ ] `load_config(cwd: str = ".") -> dict[str, object]` — loads user config, overlays project config, fills defaults. Missing files are silently skipped (all keys have defaults).
  - [ ] `get_config(key: str, cwd: str = ".") -> object` — convenience for a single key
  - [ ] `set_config(key: str, value: str, project: bool = False, cwd: str = ".") -> None` — writes to the appropriate TOML file. Creates file/directories if needed. Validates key name against `CONFIG_KEYS`. Coerces string value to the key's declared type.
  - [ ] `resolve_config_source(key: str, cwd: str = ".") -> str` — returns `"project"`, `"user"`, or `"default"` indicating where the resolved value comes from
  - [ ] Use `tomllib` (stdlib) for reading, `tomli_w` for writing
  - [ ] SC: `ruff check` and `pyright` pass
  - [ ] SC: No silent fallback values — unknown keys raise `KeyError`

### T4 — Config manager tests
- [ ] Create `tests/config/__init__.py`
- [ ] Create `tests/config/conftest.py` with `tmp_path`-based fixtures for user and project config files
- [ ] Create `tests/config/test_manager.py`
  - [ ] Test: `load_config` returns defaults when no config files exist
  - [ ] Test: user config file overrides defaults
  - [ ] Test: project config file overrides user config
  - [ ] Test: precedence chain — project > user > default
  - [ ] Test: `get_config` returns single key value
  - [ ] Test: `set_config` creates user config file and directories
  - [ ] Test: `set_config` with `project=True` writes to project config
  - [ ] Test: `set_config` coerces string value to int for `verbosity`
  - [ ] Test: `set_config` raises `KeyError` for unknown key
  - [ ] Test: `resolve_config_source` returns correct source label
  - [ ] SC: All tests pass
  - [ ] SC: `ruff check` passes

### T5 — Config CLI commands
- [ ] Create `src/orchestration/cli/commands/config.py`
  - [ ] `config_app = typer.Typer(name="config", ...)`
  - [ ] `config set KEY VALUE [--project]` — calls `set_config`, prints confirmation with source
  - [ ] `config get KEY [--cwd DIR]` — calls `get_config` and `resolve_config_source`, prints value and source
  - [ ] `config list [--cwd DIR]` — iterates `CONFIG_KEYS`, prints each key's resolved value and source in aligned columns
  - [ ] `config path` — prints both config file paths with existence status
- [ ] Register `config_app` in `src/orchestration/cli/app.py` via `app.add_typer(config_app, name="config")`
  - [ ] SC: `orchestration config --help` works
  - [ ] SC: `ruff check` and `pyright` pass

### T6 — Config CLI tests
- [ ] Create `tests/config/test_cli_config.py`
  - [ ] Test: `config set KEY VALUE` writes to user config
  - [ ] Test: `config set KEY VALUE --project` writes to project config
  - [ ] Test: `config get KEY` displays resolved value and source
  - [ ] Test: `config list` shows all keys with values and sources
  - [ ] Test: `config path` shows both file paths
  - [ ] Test: unknown key produces error message and non-zero exit
  - [ ] SC: All tests pass
  - [ ] SC: `ruff check` passes

### T7 — Commit: config system
- [ ] `git add` and commit config module, CLI commands, and tests
  - [ ] SC: All tests pass before commit

### T8 — Verbosity levels in display_result
- [ ] Modify `_display_terminal` in `src/orchestration/cli/commands/review.py`
  - [ ] Accept `verbosity: int` parameter (default `0`)
  - [ ] Verbosity 0: verdict badge + finding headings with severity (no descriptions)
  - [ ] Verbosity 1: above + full finding descriptions
  - [ ] Verbosity 2: above + raw_output (tool usage details are embedded in agent output)
  - [ ] Update `display_result` signature to accept `verbosity`
  - [ ] Update `_run_review_command` to accept and pass through `verbosity`
- [ ] Add `-v` / `--verbose` flag to `review_arch`, `review_tasks`, `review_code` commands
  - [ ] `-v` sets verbosity 1, `-vv` sets verbosity 2 (use `typer.Option` count or explicit int)
  - [ ] If no flag, read default from config via `get_config("verbosity")`
- [ ] SC: `ruff check` and `pyright` pass

### T9 — Text color improvements
- [ ] Modify `_display_terminal` in `src/orchestration/cli/commands/review.py`
  - [ ] Severity badges: keep bright green (PASS), yellow/amber (CONCERN), red (FAIL)
  - [ ] Finding headings: use `bold white` (high luminance, readable on any background)
  - [ ] Body text (descriptions): use default terminal foreground (no explicit color style) instead of `dim`
  - [ ] File paths and code references: use `cyan`
  - [ ] All styling via Rich markup — no raw ANSI escape codes
- [ ] SC: Output is readable on both dark and light terminal backgrounds
- [ ] SC: `ruff check` passes

### T10 — Verbosity and display tests
- [ ] Update `tests/review/test_cli_review.py` (or create separate `test_verbosity.py` if cleaner)
  - [ ] Test: verbosity 0 shows verdict and finding headings but NOT descriptions
  - [ ] Test: verbosity 1 shows verdict, headings, AND descriptions
  - [ ] Test: verbosity 2 includes raw output
  - [ ] Test: `-v` flag sets verbosity 1
  - [ ] Test: config-based default verbosity is respected when no flag given
  - [ ] SC: All tests pass
  - [ ] SC: `ruff check` passes

### T11 — Commit: verbosity and text colors
- [ ] `git add` and commit review display changes and tests
  - [ ] SC: All tests pass before commit

### T12 — `--rules` flag on `review code`
- [ ] Modify `review_code` command in `src/orchestration/cli/commands/review.py`
  - [ ] Add `--rules PATH` option (default: `None`)
  - [ ] If no `--rules` flag, fall back to `get_config("default_rules")`
  - [ ] If rules path is set, read file content at CLI level
  - [ ] Pass rules content to `_run_review_command` as part of inputs or as separate parameter
- [ ] Modify `_execute_review` (or `run_review` in runner) to accept optional rules content
  - [ ] When rules content is provided, append to template's system prompt as `\n\n## Additional Review Rules\n\n{rules_content}`
  - [ ] The modification happens on a copy of the template's system_prompt, not the template itself
- [ ] SC: `ruff check` and `pyright` pass

### T13 — `--rules` flag tests
- [ ] Add tests to `tests/review/test_cli_review.py` (or new `test_rules.py`)
  - [ ] Test: `--rules path/to/file` reads the file and appends content to system prompt
  - [ ] Test: config-based `default_rules` is used when no `--rules` flag
  - [ ] Test: `--rules` flag overrides config-based default_rules
  - [ ] Test: missing rules file produces error and non-zero exit
  - [ ] SC: All tests pass
  - [ ] SC: `ruff check` passes

### T14 — Config integration for `--cwd` in review commands
- [ ] Modify review commands (`review_arch`, `review_tasks`, `review_code`) to read `cwd` from config when `--cwd` flag is not explicitly provided
  - [ ] CLI `--cwd` flag overrides config value
  - [ ] Config `cwd` overrides default `"."`
- [ ] Add tests for config-based cwd resolution
  - [ ] Test: review command uses config cwd when no `--cwd` flag
  - [ ] Test: `--cwd` flag overrides config value
  - [ ] SC: All tests pass

### T15 — Commit: rules flag and config integration
- [ ] `git add` and commit rules flag, config integration, and tests
  - [ ] SC: All tests pass before commit

### T16 — Full validation pass
- [ ] Run full test suite: `uv run pytest`
- [ ] Run type checker: `uv run pyright`
- [ ] Run linter/formatter: `uv run ruff check` and `uv run ruff format --check`
  - [ ] SC: All tests pass
  - [ ] SC: Zero pyright errors
  - [ ] SC: Zero ruff errors

### T17 — README.md
- [ ] Create `docs/README.md` (primary documentation for external users)
  - [ ] Hero section: one sentence, install command, one example
  - [ ] Quickstart: clone → install → configure credentials → run first review (target: 5 minutes)
  - [ ] Command reference: all commands with examples (review arch/tasks/code/list, config set/get/list/path)
  - [ ] Configuration: user vs project config, all keys, examples
  - [ ] Review templates: what each template does, when to use it
  - [ ] Architecture: brief overview for contributors
- [ ] SC: README enables a new user to install and run first review in under 5 minutes
- [ ] SC: All commands documented with examples

### T18 — COMMANDS.md
- [ ] Create `docs/COMMANDS.md` (full command reference)
  - [ ] Every command and subcommand with all flags, types, defaults
  - [ ] Usage examples for each command
  - [ ] Exit codes documented
  - [ ] SC: Every CLI command is represented

### T19 — TEMPLATES.md
- [ ] Create `docs/TEMPLATES.md` (template authoring guide for future user-defined templates)
  - [ ] YAML schema reference with all fields
  - [ ] Example template (annotated)
  - [ ] Explanation of `prompt_template` vs `prompt_builder`
  - [ ] Input definitions (required/optional)
  - [ ] How to register a custom template
  - [ ] Noted as future capability — not yet implemented for end users
  - [ ] SC: A developer can understand how to create a custom template from this guide

### T20 — Commit: documentation
- [ ] `git add` and commit all docs
  - [ ] SC: Documentation is committed

### T21 — Final build and validation
- [ ] Run full test suite: `uv run pytest`
- [ ] Run type checker: `uv run pyright`
- [ ] Run linter/formatter: `uv run ruff check` and `uv run ruff format --check`
  - [ ] SC: All tests pass
  - [ ] SC: Zero pyright errors
  - [ ] SC: Zero ruff errors

### T22 — DEVLOG entry
- [ ] Write session summary to DEVLOG.md per prompt.ai-project.system.md guidance
  - [ ] SC: DEVLOG entry captures slice 106 completion, commit hashes, test counts
