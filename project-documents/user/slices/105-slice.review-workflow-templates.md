---
docType: slice-design
slice: review-workflow-templates
project: orchestration
parent: 100-slices.orchestration-v2.md
dependencies: [foundation, sdk-agent-provider, cli-foundation]
interfaces: [end-to-end-testing]
status: not started
dateCreated: 20260221
dateUpdated: 20260221
---

# Slice Design: Review Workflow Templates

## Overview

Implement predefined review workflow templates and a CLI `review` command that executes them. Each template defines a complete agent configuration — system prompt, allowed tools, permission mode, and prompt construction — for a specific review type. The `review` command creates a `ClaudeSDKClient` session, executes the review as a single exchange, displays the output, and exits.

Three initial review types:
- **Architectural review** — evaluate a slice design or plan against an architecture document and stated goals
- **Task plan review** — check a task breakdown against its parent slice design for completeness and feasibility
- **Code review** — review code files against language-specific rules, testing standards, and project conventions

## Value

Direct developer value. Reviews are the highest-frequency interaction with the orchestration system during active development (1-4 per hour during design/implementation cycles). After this slice:

- `orchestration review arch path/to/slice.md --against path/to/arch.md` immediately evaluates whether a slice design aligns with the architecture, flags antipatterns, and identifies gaps — without the developer composing a custom prompt each time.
- `orchestration review tasks path/to/tasks.md --against path/to/slice.md` verifies that a task breakdown covers all success criteria from the slice design.
- `orchestration review code --cwd ./project` runs a code review against CLAUDE.md project conventions and language-specific rules.

Each review that catches a problem before implementation saves significant rework time. These templates encode review expertise that would otherwise be ad-hoc prompt construction.

## Technical Scope

### Included

- `ReviewTemplate` dataclass defining the template configuration schema
- Three built-in templates: `arch`, `tasks`, `code`
- Template registry for looking up templates by name
- CLI `review` subcommand with per-template argument handling
- `ClaudeSDKClient` session per review — reviews bypass the agent registry (ephemeral, no persistent agent) but use the full client for future capability access (hooks, interrupts, custom tools)
- Prompt construction from template + user-supplied file paths
- Structured review output with severity levels (PASS / CONCERN / FAIL per finding)
- `orchestration review list` to show available templates
- Unit tests for template construction, prompt assembly, and CLI argument parsing

### Excluded

- Hook callbacks for v1 — `ClaudeSDKClient` supports hooks natively, so the `ReviewTemplate` schema includes an optional `hooks` field from day one. No hook callbacks are wired in the initial templates, but adding them later requires zero architectural change (see Tracked Enhancements).
- Custom user-defined templates (YAML/JSON template files) — built-in templates only for v1. User templates are a clear enhancement once the template schema stabilizes.
- Structured JSON output via SDK `output_format` — plain text with conventional formatting for v1. Machine-parseable output is a natural enhancement for CI integration.
- Multi-agent reviews (e.g., two reviewers with different perspectives) — requires message bus (M2).
- Interactive review mode (follow-up questions after initial review) — the `ClaudeSDKClient` infrastructure now supports this, but the CLI command exits after one exchange for v1. See Tracked Enhancements.
- Review result persistence / history — results display to terminal only. Saving to file is a straightforward enhancement.

## Dependencies

### Prerequisites

- **Foundation** (complete): `Settings`, logging, error hierarchy
- **SDK Agent Provider** (complete): Validates that the SDK integration works. Note: reviews use `ClaudeSDKClient` directly from `claude-agent-sdk` — they do not go through `SDKAgentProvider` or the agent registry, since reviews are ephemeral single-exchange tasks, not persistent named agents.
- **CLI Foundation** (complete): Typer app entry point for adding the `review` subcommand.

### External Packages

- **claude-agent-sdk** (already in pyproject.toml): `ClaudeSDKClient`, `ClaudeAgentOptions`
- **typer** (already in pyproject.toml): CLI subcommand
- **rich** (transitive via typer): Formatted review output

## Technical Decisions

### Why `ClaudeSDKClient` (Not `query()`)

The SDK provides two invocation modes. `query()` is a convenience wrapper that creates a new session per call — simpler but limited. `ClaudeSDKClient` provides explicit lifecycle control with the full feature surface: hooks, custom tools, interrupts, and session continuity.

The complexity difference is minimal — two extra lines with the context manager:

```python
# query() — fire and forget
async for message in query(prompt=prompt, options=options):
    handle(message)

# ClaudeSDKClient — context manager handles connect/disconnect
async with ClaudeSDKClient(options=options) as client:
    await client.query(prompt)
    async for message in client.receive_response():
        handle(message)
```

The capability difference is large. Everything the orchestration system will need in the near term — hook-based audit trails, interruptible agents, custom MCP tools for orchestration integration, session caching — requires `ClaudeSDKClient`. Standardizing now avoids a future migration from `query()` to `ClaudeSDKClient` across the review runner, the SDK agent provider, and any other SDK touchpoint.

For reviews specifically: each review creates a fresh `ClaudeSDKClient` instance, uses it for one exchange, and the context manager tears it down. This provides the same session isolation as `query()` while leaving the hooks and custom tools options available from day one.

### Why Direct SDK (Not Agent Registry)

The existing CLI flow for persistent agents is: `spawn` → `task` → `shutdown`. Reviews don't fit this lifecycle. A review is: configure → execute → display → done. No agent persists between reviews.

Using `ClaudeSDKClient` directly (not through the agent registry):
- Eliminates the spawn/shutdown ceremony for an ephemeral operation
- Each review gets a fresh session with no context leakage between reviews
- Simpler mental model: `orchestration review arch ...` does the complete operation in one command
- No orphaned agents if the process is interrupted

### Template as Python Dataclass (Not External Files)

Built-in templates are defined as Python dataclasses in `review/templates/`. This means:
- Templates are type-checked and validated at import time
- System prompts are version-controlled with the code
- No file-loading or parsing complexity for v1
- Templates can include Python logic for prompt construction (e.g., conditional sections based on inputs)

The template schema is designed so that a future "user templates" feature can load YAML/JSON files and construct the same dataclass. The schema doesn't depend on being defined in Python.

### Review-Specific Prompt Construction

Each template defines a `build_prompt()` method that takes user-supplied inputs (file paths, options) and produces the final prompt string. This is where template-specific logic lives:

- `arch` template: constructs a prompt referencing the input document and context document, with evaluation criteria for architectural alignment
- `tasks` template: constructs a prompt that cross-references task items against slice design success criteria
- `code` template: constructs a prompt that identifies files to review and applies language-specific rules

The prompt tells the agent which files to `Read` — the agent does the actual file reading via tools. The CLI doesn't pre-read files and paste content into the prompt, because the agent needs tool access to navigate the project structure (e.g., following imports, reading referenced files).

### Read-Only by Default, Configurable per Template

All three initial templates restrict tools to read-only operations: `Read`, `Glob`, `Grep`. The `code` template additionally allows `Bash` for git operations (e.g., `git diff`, `git log`) but with `permission_mode="bypassPermissions"` only when the tool set is restricted to safe operations.

Templates define their own tool sets. A future "refactoring review" template could include `Edit` and `Write` tools if the review produces automated fixes.

### Output Format Convention

Reviews produce findings with severity levels. Rather than enforcing JSON schema output (which adds SDK complexity), the system prompt instructs the agent to use a consistent text format:

```
## Summary
[overall assessment: PASS | CONCERNS | FAIL]

## Findings

### [PASS|CONCERN|FAIL] Finding title
Description of the finding with specific file/line references.
```

This is human-readable in the terminal and grep-parseable for basic automation. A future enhancement can add `output_format` JSON schema for machine consumption.

## Package Structure

```
src/orchestration/review/
├── __init__.py
├── templates.py          # ReviewTemplate dataclass, template registry
├── runner.py             # Review execution: build prompt → ClaudeSDKClient → format output
└── builtin/
    ├── __init__.py
    ├── arch.py            # Architectural review template
    ├── tasks.py           # Task plan review template
    └── code.py            # Code review template

src/orchestration/cli/commands/
└── review.py             # CLI review subcommand

tests/review/
├── __init__.py
├── test_templates.py     # Template construction and validation
├── test_runner.py        # Prompt assembly and query integration (SDK mocked)
├── test_builtin_arch.py  # Arch template prompt construction
├── test_builtin_tasks.py # Tasks template prompt construction
├── test_builtin_code.py  # Code template prompt construction
└── test_cli_review.py    # CLI argument parsing and command flow
```

## Component Design

### ReviewTemplate Schema

```python
@dataclass
class ReviewTemplate:
    """Configuration for a review workflow."""
    name: str                           # Short identifier (e.g., "arch", "tasks", "code")
    description: str                    # Human-readable description for `review list`
    system_prompt: str                  # System prompt for the review agent
    allowed_tools: list[str]            # SDK tools the agent can use
    permission_mode: str                # SDK permission mode
    setting_sources: list[str] | None   # SDK setting sources (e.g., ["project"] for CLAUDE.md)
    required_inputs: list[str]          # Required CLI arguments (e.g., ["input", "against"])
    optional_inputs: list[str]          # Optional CLI arguments
    hooks: dict | None = None           # Optional SDK hooks (ClaudeSDKClient HookEvent → HookMatcher)
                                        # None for v1 built-in templates; field exists for future use

    def build_prompt(self, inputs: dict[str, str]) -> str:
        """Construct the review prompt from user-supplied inputs."""
        ...
```

The `hooks` field is present in the schema from day one but set to `None` in all v1 templates. When hook callbacks are added later (audit logging, Bash command filtering), they slot into this field with no schema change.

### Template Registry

```python
_TEMPLATES: dict[str, ReviewTemplate] = {}

def register_template(template: ReviewTemplate) -> None: ...
def get_template(name: str) -> ReviewTemplate | None: ...
def list_templates() -> list[ReviewTemplate]: ...
```

Built-in templates auto-register at import time (same pattern as provider registry).

### Review Runner

```python
async def run_review(template: ReviewTemplate, inputs: dict[str, str]) -> None:
    """Execute a review: build prompt, run ClaudeSDKClient session, display output."""
    prompt = template.build_prompt(inputs)
    options = ClaudeAgentOptions(
        system_prompt=template.system_prompt,
        allowed_tools=template.allowed_tools,
        permission_mode=template.permission_mode,
        setting_sources=template.setting_sources,
        cwd=inputs.get("cwd"),
        hooks=template.hooks,       # None for v1 — ready for future hook callbacks
    )
    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt)
        async for message in client.receive_response():
            # Display assistant text, summarize tool use, capture result
            ...
```

## CLI `review` Subcommand

### Commands

#### `review arch`

```
orchestration review arch INPUT --against CONTEXT [--cwd DIR]
```

- `INPUT` (positional, required): Path to the document being reviewed (slice design, plan, etc.)
- `--against` (required): Path to the architecture document or HLD to review against
- `--cwd` (optional): Working directory for file reads. Defaults to current directory.

Example:
```
orchestration review arch slices/105-slice.review-workflow-templates.md \
  --against architecture/100-arch.orchestration-v2.md
```

#### `review tasks`

```
orchestration review tasks INPUT --against CONTEXT [--cwd DIR]
```

- `INPUT` (positional, required): Path to the task breakdown file
- `--against` (required): Path to the parent slice design
- `--cwd` (optional): Working directory. Defaults to current directory.

Example:
```
orchestration review tasks tasks/105-tasks.review-workflow-templates.md \
  --against slices/105-slice.review-workflow-templates.md
```

#### `review code`

```
orchestration review code [--cwd DIR] [--files PATTERN] [--diff REF]
```

- `--cwd` (optional): Project directory to review. Defaults to current directory.
- `--files` (optional): Glob pattern to scope the review (e.g., `"src/**/*.py"`). Without this, the agent determines scope from project structure.
- `--diff` (optional): Git ref to diff against (e.g., `main`, `HEAD~3`). When provided, the review focuses on changed files.

Example:
```
orchestration review code --cwd ./orchestration --diff main
```

#### `review list`

```
orchestration review list
```

Displays available templates with name and description. Example output:

```
Available review templates:
  arch    Architectural review — evaluate document against architecture/HLD
  tasks   Task plan review — check task breakdown against slice design
  code    Code review — review code against project conventions and rules
```

## Built-in Template Details

### `arch` — Architectural Review

**Purpose:** Evaluate whether a design document (slice design, plan, spec) aligns with the parent architecture document and stated goals.

**System prompt core themes:**
- Check alignment with stated architectural goals and principles
- Identify violations of architectural boundaries or layer responsibilities
- Flag scope creep beyond what the architecture defines
- Verify dependency directions are correct
- Check that integration points match what consuming/providing slices expect
- Detect common antipatterns: over-engineering, under-specification, hidden dependencies, template stuffing

**Tools:** `Read`, `Glob`, `Grep` — read-only. The agent reads both documents and any referenced files.

**Prompt construction:** Tells the agent: read the input document at `{input}`, read the architecture/context at `{against}`, evaluate alignment, report findings with severity.

### `tasks` — Task Plan Review

**Purpose:** Verify that a task breakdown covers all success criteria from the parent slice design and that tasks are correctly sequenced, properly scoped, and independently completable.

**System prompt core themes:**
- Cross-reference each success criterion from the slice design against tasks
- Identify success criteria with no corresponding task (gaps)
- Identify tasks that don't trace to any success criterion (scope creep)
- Check task sequencing: dependencies respected, no circular deps
- Verify each task is completable by "a junior AI with clear success criteria" (per process guide)
- Flag tasks that are too large (should be split) or too granular (should be merged)

**Tools:** `Read`, `Glob`, `Grep` — read-only.

**Prompt construction:** Tells the agent: read the task file at `{input}`, read the slice design at `{against}`, perform cross-reference analysis, report findings.

### `code` — Code Review

**Purpose:** Review code against language-specific rules, testing standards, and project conventions.

**System prompt core themes:**
- Follow project conventions from CLAUDE.md (loaded via `setting_sources=["project"]`)
- Apply language-appropriate style and correctness checks
- Verify test coverage patterns (test-with, not test-after)
- Check error handling patterns
- Flag security concerns
- Evaluate naming, structure, and documentation quality

**Tools:** `Read`, `Glob`, `Grep`, `Bash` — Bash is included for git operations (`git diff`, `git log`, `git show`).

**Permission mode:** `bypassPermissions` — the tool set is already restricted to safe operations.

**Setting sources:** `["project"]` — loads CLAUDE.md from the `cwd`, giving the agent access to project-specific conventions and rules.

**Prompt construction:** When `--diff` is provided, the prompt tells the agent to run `git diff {ref}` to identify changed files, then review those files. When `--files` is provided, the prompt scopes the review to matching files. When neither is provided, the agent uses Glob/Grep to survey the project and focuses on areas it deems most useful to review.

## Data Flow

### Review Execution (All Templates)

```
User: orchestration review arch slice.md --against arch.md
  │
  ▼
CLI (review command)
  │ resolves template: get_template("arch")
  │ collects inputs: {input: "slice.md", against: "arch.md"}
  │ validates: required inputs present
  ▼
ReviewRunner.run_review(template, inputs)
  │ prompt = template.build_prompt(inputs)
  │ options = ClaudeAgentOptions(
  │   system_prompt=template.system_prompt,
  │   allowed_tools=["Read", "Glob", "Grep"],
  │   permission_mode="bypassPermissions",
  │   cwd=inputs.get("cwd", "."),
  │   hooks=template.hooks,  # None for v1
  │ )
  ▼
ClaudeSDKClient(options=options) — context manager
  │ connect() → spawns SDK subprocess
  │ client.query(prompt) → sends review request
  │ client.receive_response() → yields messages
  │   Agent reads input file via Read tool
  │   Agent reads context file via Read tool
  │   Agent may Glob/Grep for referenced files
  │   Agent produces review findings
  │ disconnect() → tears down subprocess (automatic via context manager)
  ▼
CLI displays formatted output
  │ Summary line: PASS / CONCERNS / FAIL
  │ Individual findings with severity
  │
  ▼
Process exits (no persistent agent, no cleanup needed)
```

## Integration Points

### Provides to Other Slices

- **End-to-End Testing (slice 17):** Review commands are testable CLI surfaces. Integration tests can verify that a known-bad slice design produces FAIL findings against an architecture doc.

### Consumes from Prior Slices

- **CLI Foundation (slice 103):** Typer app entry point. The `review` subcommand is added to the existing app.
- **Foundation:** `Settings` for configuration, logging for review execution events.

### Does NOT Consume

- **Agent Registry:** Reviews use ephemeral `ClaudeSDKClient` sessions. No agent registration, no lifecycle management.
- **SDK Agent Provider:** Reviews use `ClaudeSDKClient` directly from `claude-agent-sdk`, not through the orchestration provider layer. The provider adds value for persistent agents with orchestration integration. Reviews don't need that.

## Success Criteria

### Functional Requirements

- `orchestration review arch INPUT --against CONTEXT` executes an architectural review and displays findings
- `orchestration review tasks INPUT --against CONTEXT` executes a task plan review and displays findings
- `orchestration review code [--cwd DIR] [--files PATTERN] [--diff REF]` executes a code review and displays findings
- `orchestration review list` displays all available templates with descriptions
- Review output includes a summary assessment (PASS/CONCERNS/FAIL) and individual findings with severity levels
- Reviews use read-only tools by default (no file modifications during review)
- Code review loads CLAUDE.md project conventions via `setting_sources=["project"]`
- Code review supports scoping via `--files` glob pattern or `--diff` git ref
- Invalid template name produces a clear error listing available templates
- Missing required arguments produce clear usage errors
- SDK errors (CLI not found, process failure) produce user-friendly messages

### Technical Requirements

- All tests pass with `ClaudeSDKClient` mocked at the import boundary
- Type checker passes with zero errors
- `ruff check` and `ruff format` pass
- Template construction has test coverage for all three built-in templates
- Prompt assembly has test coverage (correct file paths inserted, optional args handled)
- CLI argument parsing has test coverage (required args, optional args, defaults)
- Review runner has test coverage (mock ClaudeSDKClient → verify options construction and prompt)

## Tracked Enhancements

### Hook Callbacks (Zero Architectural Cost)

The `ReviewTemplate` schema includes a `hooks` field and the runner passes it through to `ClaudeSDKClient`. Adding hook callbacks requires only defining the callback functions and wiring them into template definitions — no structural changes to the runner, CLI, or template schema.

Likely first hooks:
- **Audit logging** (`PostToolUse`): Log which files the review agent read, for traceability.
- **Bash command filtering** (`PreToolUse`, matcher: `"Bash"`): Conditionally block Bash commands based on the command string, rather than relying solely on the coarse `allowed_tools` list.

### User-Defined Templates

Allow users to define custom review templates as YAML files in a conventional location (e.g., `.orchestration/templates/` or a configurable directory). The `ReviewTemplate` schema is designed to be serializable, so YAML loading would construct the same dataclass. The template registry would scan both built-in and user directories.

### Structured JSON Output

Add `--output json` flag to review commands. Uses the SDK's `output_format` option with a JSON schema defining the review findings structure. Enables CI integration (parse review results, fail builds on FAIL findings).

### Review Result Persistence

Save review results to a file (e.g., in a `reviews/` directory). Enables tracking review history, comparing reviews over time, and auditing review coverage.

### Interactive Review Mode (Low Cost)

Since the runner already uses `ClaudeSDKClient`, enabling follow-up questions requires only keeping the client session open after the initial review and adding a prompt loop. "Explain finding #3 in more detail" or "How would you fix the issue in section X?" — the session continuity is already there. The main work is the CLI interaction loop and a `--interactive` flag.

## Implementation Notes

### Suggested Implementation Order

1. **`ReviewTemplate` dataclass + template registry** (effort: 1/5) — Schema (including `hooks` field), registration, lookup. No SDK interaction.
2. **Built-in template definitions** (effort: 1/5) — `arch`, `tasks`, `code` templates with system prompts and prompt construction logic. The system prompts are the most important design artifact here — they encode the review expertise.
3. **Review runner** (effort: 1/5) — `run_review()` function: build prompt, construct `ClaudeAgentOptions`, create `ClaudeSDKClient` session, execute review, format and display output.
4. **CLI `review` subcommand** (effort: 1/5) — Typer commands for `review arch`, `review tasks`, `review code`, `review list`. Argument parsing, template lookup, delegation to runner.
5. **Tests** (effort: 1/5) — Template construction, prompt assembly, runner (with mocked SDK), CLI argument parsing.

### Testing Strategy

All tests mock `ClaudeSDKClient` at the import boundary. The mock's `receive_response()` returns a predefined async iterator of `AssistantMessage` and `ResultMessage` objects.

Test categories:

- **Template tests:** Verify `ReviewTemplate` construction, `build_prompt()` output for various input combinations, registry lookup, `hooks` field passthrough.
- **Runner tests:** Verify `ClaudeAgentOptions` construction from template fields. Verify that `ClaudeSDKClient` is instantiated with correct options. Verify `query()` is called with the built prompt. Verify output formatting.
- **CLI tests:** Verify argument parsing via Typer's `CliRunner`. Verify error messages for missing args, invalid template names.
- **Prompt quality tests (optional but valuable):** Snapshot tests for the actual prompt strings produced by each template. If the prompt changes, the snapshot forces a deliberate review of the change.

### System Prompt Development

The system prompts for each template are the most design-sensitive part of this slice. They encode what "a good review" means. Rather than trying to perfect them in this design document, the implementation should:

1. Start with a reasonable initial prompt based on the themes listed in the template details above
2. Test with real documents from this project (the orchestration slice designs and arch doc are perfect test inputs)
3. Iterate based on output quality — the system prompts will likely need 2-3 rounds of refinement

This is an area where the implementing agent should be given latitude to refine prompts through testing rather than being held to a rigid specification.
