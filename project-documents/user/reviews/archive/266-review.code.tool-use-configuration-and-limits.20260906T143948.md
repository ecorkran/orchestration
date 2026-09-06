---
docType: review
layer: project
reviewType: code
slice: tool-use-configuration-and-limits
project: squadron
verdict: CONCERNS
sourceDocument: project-documents/user/slices/266-slice.tool-use-configuration-and-limits.md
aiModel: moonshotai/kimi-k2.7-code
status: complete
dateCreated: 20260906
dateUpdated: 20260906
reviewedSha: a4d1aaf50ccdc71152a3a95955351b448c199e39
toolsGiven: [read_file, list_files, grep]
toolCallsMade: 45
findings:
  - id: F001
    severity: pass
    category: design
    summary: "Tool capability gate centralizes tool-use decisions in one function"
    location: "src/squadron/tools/effective.py:33"
  - id: F002
    severity: pass
    category: design
    summary: "Tool execution limits are centralized and monkeypatchable"
    location: "src/squadron/tools/limits.py:1"
  - id: F003
    severity: pass
    category: async
    summary: "Built-in tools run blocking and CPU-bound work off the event loop"
    location: "src/squadron/tools/builtin/bash_tool.py:66"
  - id: F004
    severity: pass
    category: testing
    summary: "Failure modes are observable and covered by unit and load tests"
    location: "tests/load/test_grep_timeout.py:1"
  - id: F005
    severity: pass
    category: testing
    summary: "SC1a enumeration guard prevents new AgentConfig tool-passing sites from skipping the gate"
    location: "tests/tools/test_effective_tools.py:287"
  - id: F006
    severity: pass
    category: error-handling
    summary: "MCP bridge maps SDK exception groups and timeouts into error results"
    location: "src/squadron/tools/mcp_bridge.py:1"
  - id: F007
    severity: concern
    category: style
    summary: "Project line length deviates from required 88-character baseline"
    location: "pyproject.toml:68"
  - id: F008
    severity: concern
    category: static-analysis
    summary: "pyright strict checking excludes tests despite rules requiring inclusion"
    location: "pyproject.toml:82"
---

# Review: code — slice 266

**Verdict:** CONCERNS
**Model:** moonshotai/kimi-k2.7-code

## Findings

### [PASS] Tool capability gate centralizes tool-use decisions in one function

`resolve_effective_tools` is the single place that combines model capability (`tool_use = false`) with run-level suppression (`--no-tools`). It returns both the effective tool list and a `SuppressionReason` so telemetry can distinguish the two denial causes (SC4). The `SuppressionReason` `StrEnum` values are stable identifiers persisted into artifacts, matching the design intent.

### [PASS] Tool execution limits are centralized and monkeypatchable

All limits (`MAX_READ_BYTES`, `BASH_TIMEOUT_S`, `GREP_TIMEOUT_S`, etc.) live in one module and are read at call time rather than captured at import. This lets tests monkeypatch them and lets the executor see patched values immediately. The module docstring explicitly records the slice 266 decision not to add a config surface for values nobody has had to change, with a pointer to issue #76 if that changes.

### [PASS] Built-in tools run blocking and CPU-bound work off the event loop

`bash`, `read_file`, `write_file`, `list_files`, and `grep` all route blocking syscalls, directory walks, subprocess I/O, and regex matching through `asyncio.to_thread`. The `grep` tool additionally passes the remaining whole-walk budget into `regex.search(..., timeout=remaining)` so catastrophic backtracking is bounded at the engine level, not with an unenforceable `asyncio.wait_for`.

### [PASS] Failure modes are observable and covered by unit and load tests

`bash` timeouts and `grep` budget exhaustion log at `WARNING` and return explicit error results. The load-test tier exercises the real `GREP_TIMEOUT_S` against a realistically-sized tree and concurrent callers, asserting the event loop stays responsive. Unit tests in `tests/tools/test_bash.py` and `tests/tools/test_grep.py` assert the same observable signals at smaller scales.

### [PASS] SC1a enumeration guard prevents new AgentConfig tool-passing sites from skipping the gate

`_agent_config_tool_sites` uses the AST to find every `AgentConfig(..., allowed_tools=...)` construction in `src/squadron` and fails the test if a new site is not in the sanctioned set. The test also verifies the sanctioned list has no stale entries and that legitimate no-tools sites are not flagged.

### [PASS] MCP bridge maps SDK exception groups and timeouts into error results

`call_mcp_tool` uses a single broad handler at the process boundary because the MCP SDK raises failures wrapped in `BaseExceptionGroup`. `_leaves` flattens the group and `_classify_failure` splits off `TimeoutError` before `OSError` so timeouts are not misreported as spawn failures. Real subprocess round-trips in `tests/tools/test_mcp_bridge.py` cover echo, error, empty, timeout, spawn failure, protocol error, and unclassified exception paths.

### [CONCERN] Project line length deviates from required 88-character baseline

The Python rules require PEP 8 with an 88-character line length and a baseline `[tool.ruff] line-length = 88`. This project sets `line-length = 104`. The configured ruff rule set is otherwise correct, but the line-length deviation means new code may drift beyond the modular-rule limit.

### [CONCERN] pyright strict checking excludes tests despite rules requiring inclusion

The Python rules require `[tool.pyright] include = ["src", "tests"]` with strict mode as a merge blocker. This project uses `include = ["src"]` and excludes tests, with a comment citing 868 existing test errors tracked in issue #50. Until that issue is resolved, test code is not checked under the same strict baseline as source code, which the rules identify as a risk because bugs in tests can mask bugs in code.
