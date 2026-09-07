---
docType: review
layer: project
reviewType: code
slice: tool-use-configuration-and-limits
project: squadron
verdict: FAIL
sourceDocument: project-documents/user/slices/266-slice.tool-use-configuration-and-limits.md
aiModel: moonshotai/kimi-k2.7-code
status: complete
dateCreated: 20260907
dateUpdated: 20260907
reviewedSha: f11f8ff9e8bd775c8c690810fced6ef6123f5220
toolsGiven: [read_file, list_files, grep]
toolCallsMade: 0
findings:
  - id: F001
    severity: fail
    category: error-handling
    summary: "Undefined variable in `run_review_with_profile` tool resolution"
    location: "src/squadron/review/review_client.py:124-126"
  - id: F002
    severity: concern
    category: type-safety
    summary: "`max_history_chars` may be `None` when passed to integer-only cap helper"
    location: "src/squadron/providers/openai/agent.py:363"
  - id: F003
    severity: concern
    category: error-handling
    summary: "Broad exception swallowing in summary action"
    location: "src/squadron/pipeline/actions/summary.py:265"
  - id: F004
    severity: pass
    category: testing
    summary: "Tool capability gate is well-tested and cleanly integrated"
    location: "tests/tools/test_effective_tools.py"
  - id: F005
    severity: pass
    category: design
    summary: "Builtin tool refactor reduces file sizes without breaking imports"
    location: "src/squadron/tools/builtin/__init__.py"
  - id: F006
    severity: pass
    category: correctness
    summary: "Tool result and walk limits include observable failure modes"
    location: "tests/providers/openai/test_tool_result_cap.py; tests/tools/test_grep_bounds.py; tests/tools/test_list_files_bounds.py"
---

# Review: code — slice 266

**Verdict:** FAIL
**Model:** moonshotai/kimi-k2.7-code

## Findings

### [FAIL] Undefined variable in `run_review_with_profile` tool resolution

In `run_review_with_profile` the call to `resolve_effective_tools` reads `resolved_allowed_tools` on its right-hand side while simultaneously assigning its first return value to `resolved_allowed_tools` on the left-hand side:

```python
resolved_allowed_tools, tools_suppressed_reason = resolve_effective_tools(
    resolved_allowed_tools,
    ...
)
```

This raises `NameError` at runtime because the name is referenced before it is bound. The input to the function should be the `allowed_tools` parameter that the function receives. The same bug appears to be present in the provided diff for this block.

### [CONCERN] `max_history_chars` may be `None` when passed to integer-only cap helper

`OpenAICompatibleAgent.__init__` declares `max_history_chars: int | None = None`, but the new per-result cap code passes it directly to `limits.max_tool_result_chars(max_history_chars)`, whose signature expects `int`. If the agent is ever constructed without an explicit history budget, this will raise a `TypeError`. The value should be narrowed or defaulted before the call.

### [CONCERN] Broad exception swallowing in summary action

The summary action uses `except Exception as exc:  # noqa: BLE001` to wrap any failure in a `SummaryError` without re-raising. Per the project Python rules, a broad handler must either re-raise after logging, include an inline justification for swallowing, or be a documented top-level process-boundary handler. The `noqa` comment alone does not explain why this action boundary must suppress all failures, which risks masking provider bugs or transient errors.

### [PASS] Tool capability gate is well-tested and cleanly integrated

`resolve_effective_tools` truth-table tests, alias parsing, CLI flag threading, the SC1a enumeration guard over `AgentConfig` call sites, and end-to-end review/dispatch/summary/audit paths are comprehensively covered. Tests correctly distinguish model-capability suppression from `--no-tools` suppression and verify that un-gated artifacts remain unchanged.

### [PASS] Builtin tool refactor reduces file sizes without breaking imports

The 690-line `builtin.py` module is split into focused modules (`_shared`, `bash_tool`, `file_tools`, `search_tools`) under a package whose public import surface is preserved. Shared helpers avoid duplication and each module stays near the project’s ~300-line guideline.

### [PASS] Tool result and walk limits include observable failure modes

New tests assert that the per-result history cap fires before the conversation budget guard, that pattern-length and walk timeouts produce visible markers/advice, that dependency directories are pruned, and that symlink jail escapes are logged at WARNING. These align with the failure-mode enumeration rule.
