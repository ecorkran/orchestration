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
dateCreated: 20260907
dateUpdated: 20260907
reviewedSha: f11f8ff9e8bd775c8c690810fced6ef6123f5220
toolsGiven: [read_file, list_files, grep]
toolCallsMade: 0
findings:
  - id: F001
    severity: concern
    category: testing
    summary: "list_files bounds tests patch the wrong Path method"
    location: "tests/tools/test_list_files_bounds.py:1"
  - id: F002
    severity: concern
    category: design
    summary: "walk_tree materializes directory children despite lazy docstring"
    location: "src/squadron/tools/builtin/_shared.py:63"
  - id: F003
    severity: concern
    category: documentation
    summary: "grep candidates docstring claims unsorted output but walk_tree sorts"
    location: "src/squadron/tools/builtin/search_tools.py:64"
  - id: F004
    severity: pass
    category: design
    summary: "Capability gate is centralized and enforced by enumeration test"
    location: "src/squadron/tools/effective.py:1"
  - id: F005
    severity: pass
    category: error-handling
    summary: "Tool result cap is observable and scales with the history budget"
    location: "src/squadron/providers/openai/agent.py:360"
---

# Review: code — slice 266

**Verdict:** CONCERNS
**Model:** moonshotai/kimi-k2.7-code

## Findings

### [CONCERN] list_files bounds tests patch the wrong Path method

The tests claim to assert that `list_files` stops *consuming* entries early (SC10), so they monkeypatch `Path.glob` and `Path.rglob` (lines 63 and 106). But the new implementation in `src/squadron/tools/builtin/file_tools.py` no longer calls `glob`/`rglob`; it walks via `walk_tree` from `_shared.py`, which uses `Path.iterdir()`. Consequently `_CountingGlob.consumed` stays at 0 and assertions such as `counter.consumed <= 51` pass vacuously. The tests should instrument `Path.iterdir` or `walk_tree` itself, or assert directly on the entries yielded.

### [CONCERN] walk_tree materializes directory children despite lazy docstring

`walk_tree` is documented as "Lazy by construction. Nothing here materializes the tree", yet it calls `sorted(root.iterdir())` at every directory level. `sorted()` eagerly builds a list of all direct children before yielding any entry, so a very wide root directory still pays the full listing-plus-sorting cost even when the caller caps output at `MAX_LIST_ENTRIES`. This contradicts the docstring and the SC10 goal of bounded work. Either document the per-directory materialization trade-off explicitly, or make the iterator truly lazy (e.g., yield unsorted and sort only the final collected slice).

### [CONCERN] grep candidates docstring claims unsorted output but walk_tree sorts

`_grep_candidates` still carries the docstring rationale "Deliberately lazy and unsorted: a sorted list would walk and materialize the entire tree before the caller's first deadline check...". Since the implementation now sources candidates from `walk_tree`, which sorts each directory's entries via `sorted(root.iterdir())`, the output is sorted per directory and the anti-materialization argument is no longer accurate. Update the docstring to reflect the new behavior.

### [PASS] Capability gate is centralized and enforced by enumeration test

`resolve_effective_tools` centralizes the tool-use capability decision, distinguishes model-capability denial from run-level suppression, and preserves the "nothing declared" case as non-suppression. The accompanying `tests/tools/test_effective_tools.py` uses AST analysis to enumerate every `AgentConfig(..., allowed_tools=...)` construction site and fails if a new site bypasses the gate — a strong, mechanical enforcement of SC1a.

### [PASS] Tool result cap is observable and scales with the history budget

The per-result history cap truncates oversized tool results before they are appended, logs the truncation at WARNING, and derives the limit from `limits.max_tool_result_chars` so it scales with `max_history_chars` while keeping a floor above `MAX_OUTPUT_BYTES`. The new tests verify both that the cap fires before the budget guard and that a normal-sized result passes through untouched.
