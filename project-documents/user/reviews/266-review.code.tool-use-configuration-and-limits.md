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
dateCreated: 20260908
dateUpdated: 20260908
reviewedSha: 495f0b3e30b73482a4f2903b9ef515590ed7171c
toolsGiven: [read_file, list_files, grep]
toolCallsMade: 0
findings:
  - id: F001
    severity: concern
    category: design-principles
    summary: "`_search` helper in grep tool is too long and mixes responsibilities"
    location: "src/squadron/tools/builtin/search_tools.py:175-267"
  - id: F002
    severity: concern
    category: design-principles
    summary: "`_run_tool_loop` has grown too large and handles too many concerns"
    location: "src/squadron/providers/openai/agent.py#_run_tool_loop"
  - id: F003
    severity: note
    category: code-style
    summary: "Conditional expression inside `for` loop reduces readability"
    location: "src/squadron/review/review_client.py:346"
  - id: F004
    severity: pass
    category: design-principles
    summary: "Capability gate centralizes tool-suppression decisions cleanly"
    location: "src/squadron/tools/effective.py:35"
  - id: F005
    severity: pass
    category: security
    summary: "Walked tool entries correctly re-check symlink jail escape"
    location: "src/squadron/tools/builtin/_shared.py:57"
  - id: F006
    severity: pass
    category: correctness
    summary: "Tool-enabled reviews retain the git diff while omitting injected bodies"
    location: "src/squadron/review/review_client.py:136-147"
  - id: F007
    severity: pass
    category: error-handling
    summary: "Per-tool-result cap prevents a single result from exhausting history"
    location: "src/squadron/providers/openai/agent.py:450-466"
---

# Review: code — slice 266

**Verdict:** CONCERNS
**Model:** moonshotai/kimi-k2.7-code

## Findings

### [CONCERN] `_search` helper in grep tool is too long and mixes responsibilities

The nested `_search` function is roughly 90 lines. It validates the pattern, compiles the regex, sets up the deadline, walks the tree, reads files, matches lines, handles three different timeout/error cases, and formats the result. The project convention asks for functions around 50 lines "where practical," and this function is a clear Single Responsibility Principle violation. Extracting smaller helpers (e.g., `_compile_pattern`, `_scan_candidate`, `_format_matches`) would make the logic easier to test and maintain.

### [CONCERN] `_run_tool_loop` has grown too large and handles too many concerns

The method now manages the iteration budget, history budget, final-iteration withdrawal notice, per-tool-result truncation, tool execution, and telemetry stamping. Adding the final-iteration reservation and result cap is correct behavior, but the method is now well beyond the project's ~50-line function guidance. Consider extracting the finalization notice and the tool-result truncation into small helper methods so the loop's control flow stays readable.

### [NOTE] Conditional expression inside `for` loop reduces readability

The line `for key, value in inputs.items() if include_bodies else ():` is syntactically valid but slightly clever. Assigning the iterable to a named variable first (e.g., `entries = inputs.items() if include_bodies else ()`) would make the intent obvious at a glance.

### [PASS] Capability gate centralizes tool-suppression decisions cleanly

`resolve_effective_tools` cleanly distinguishes "model capability denied," "run suppressed," "both," and "nothing declared," and the `SuppressionReason` enum produces stable, human-readable telemetry values. The default-allow semantics for absent `tool_use` are also clearly documented.

### [PASS] Walked tool entries correctly re-check symlink jail escape

`contained_in_jail` closes the symlink escape route that `_resolve_in_jail` cannot cover because it only validates the caller-supplied entry path. Both `grep` and `list_files` now re-check every walked candidate, and the refusal is logged at WARNING without leaking the jail boundary to the model.

### [PASS] Tool-enabled reviews retain the git diff while omitting injected bodies

Always invoking `_inject_file_contents` with the new `include_bodies` flag correctly preserves the diff on the tools path while still suppressing full file-body injection. This fixes the regression described in issue #81 and matches slice 265's stated intent.

### [PASS] Per-tool-result cap prevents a single result from exhausting history

The per-result truncation happens before the result is appended to history, and `limits.resolve_tool_result_cap` clamps the configured value up to a floor derived from the largest built-in tool bound. This satisfies the design requirement that the whole-conversation budget guard remain a backstop rather than the first line of defense.
