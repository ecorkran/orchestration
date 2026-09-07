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
    category: correctness
    summary: "Undefined variable in `run_review_with_profile` capability gate"
    location: "src/squadron/review/review_client.py#run_review_with_profile"
  - id: F002
    severity: concern
    category: testing
    summary: "Timeout test relies on a magic iteration count and a conditional assertion"
    location: "tests/tools/test_grep_bounds.py#test_partial_matches_survive_a_walk_timeout"
  - id: F003
    severity: note
    category: style
    summary: "Redundant exception tuple in `walk_tree`"
    location: "src/squadron/tools/builtin/_shared.py#walk_tree"
  - id: F004
    severity: pass
    category: design
    summary: "Capability gate is enforced mechanically at every tool-passing site"
    location: "tests/tools/test_effective_tools.py#test_every_tool_passing_agent_config_site_is_sanctioned"
  - id: F005
    severity: pass
    category: security
    summary: "Symlink jail-escape protection is observable, not just absence-based"
    location: "tests/tools/test_jail_symlinks.py"
  - id: F006
    severity: pass
    category: testing
    summary: "Per-tool-result history cap is soundly tested"
    location: "tests/providers/openai/test_tool_result_cap.py"
---

# Review: code — slice 266

**Verdict:** FAIL
**Model:** moonshotai/kimi-k2.7-code

## Findings

### [FAIL] Undefined variable in `run_review_with_profile` capability gate

The new gate calls `resolve_effective_tools(resolved_allowed_tools, ...)` before `resolved_allowed_tools` is ever assigned:

```python
resolved_allowed_tools, tools_suppressed_reason = resolve_effective_tools(
    resolved_allowed_tools,
    model_allows_tools=allows_tools,
    suppressed=no_tools,
)
```

The function parameter is `allowed_tools`, so the first argument should almost certainly be `allowed_tools`. Because the same undefined name is used as both the assignment target and the input, this will raise `NameError` at runtime and break all review commands.

The subsequent `should_inject_file_bodies(..., resolved_allowed_tools, ...)` call has the same problem.

### [CONCERN] Timeout test relies on a magic iteration count and a conditional assertion

The test monkeypatches `time.monotonic` and jumps the clock after an arbitrary `calls["n"] < 8` check. The exact number of monotonic calls depends on the internal implementation of `_grep_candidates`, `_search`, and `walk_tree`, so this assertion is fragile and may start failing or, worse, passing vacuously if the loop structure changes.

Additionally:

```python
if "hit.txt" in content:
    assert not is_error
    assert "search abandoned" in content
```

The `if` lets the test pass even when the fixture does not exercise the partial-match path. A stronger test would assert that `hit.txt` is present (or explain why that cannot be guaranteed) and would pin the clock jump to a concrete event rather than a magic count.

### [NOTE] Redundant exception tuple in `walk_tree`

```python
except (OSError, PermissionError):
```

`PermissionError` is a subclass of `OSError`, so catching both is redundant. Use `except OSError:`.

### [PASS] Capability gate is enforced mechanically at every tool-passing site

The AST-based enumeration guard in `_agent_config_tool_sites()` is an excellent ratchet: any new `AgentConfig(..., allowed_tools=...)` call site that does not route through `resolve_effective_tools` fails the build. This turns a cross-cutting policy into a testable invariant and prevents the `tool_use = false` capability from being silently ignored on future paths.

### [PASS] Symlink jail-escape protection is observable, not just absence-based

The symlink tests assert that the `jail escape` WARNING is logged rather than merely asserting that outside content is absent. That avoids the Python 3.13+ `rglob` behavior change making the tests pass vacuously. The design also correctly distinguishes file links from directory links and refuses descent through symlinked directories.

### [PASS] Per-tool-result history cap is soundly tested

The tests verify the mechanism (cap fires before append, budget guard does not run), the scaling behavior with history budget, and the floor that keeps ordinary tool results from being re-truncated. This directly addresses the failure mode described in issue #80 and prevents a single oversized result from forcing finalization.
